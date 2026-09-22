"""The client used to talk Modbus"""

import logging
from typing import Any
from typing import Awaitable
from typing import Callable
from typing import TypeVar

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusSerialParams
from modbus_connection import ModbusTcpParams
from modbus_connection import ModbusUdpParams
from modbus_connection import ModbusUnit
from modbus_connection.exceptions import ClientClosedError
from modbus_connection.exceptions import ModbusConnectionError
from modbus_connection.exceptions import ModbusDesyncError
from modbus_connection.exceptions import ModbusError
from modbus_connection.exceptions import ModbusProtocolError
from modbus_connection.exceptions import ModbusTimeoutError
from modbus_connection.tmodbus import ModbusConnection

from ..common.types import ConnectionType
from ..common.types import RegisterType
from ..const import RTU_OVER_TCP
from ..const import SERIAL
from ..const import TCP
from ..const import UDP
from ..inverter_adapters import InverterAdapter

_LOGGER = logging.getLogger(__name__)

T = TypeVar("T")

# Some serial devices need a short delay between requests. Also do this for the inverter, just in case it
# helps. tcp and rtu-over-tcp get it too: some cheap RS485<->TCP bridges can't keep up with back-to-back
# requests, and answer the next request with the previous one's data. Raise this if one still does
_MESSAGE_SPACING_SECONDS = 30 / 1000

# Delaying for a second after establishing a connection seems to help the inverter stability,
# see https://github.com/nathanmarlor/foxess_modbus/discussions/132
_CONNECT_DELAY_SECONDS = 1.0

# The library reraises rather than retrying, so transient failures are retried here instead
_NUM_RETRIES = 3

_MULTIPLE_CONNECTIONS_ADVICE = (
    "Please ensure that your adapter is correctly configured to allow multiple connections, see the "
    "instructions at https://github.com/nathanmarlor/foxess_modbus/wiki"
)


def _connection_params(
    protocol: str, config: dict[str, Any]
) -> ModbusTcpParams | ModbusUdpParams | ModbusSerialParams:
    """Describe this connection the way modbus_connection expects it"""
    if protocol == TCP:
        return ModbusTcpParams(host=config["host"], port=config["port"])
    if protocol == UDP:
        return ModbusUdpParams(host=config["host"], port=config["port"])
    if protocol == RTU_OVER_TCP:
        # RTU framing carried over a socket is a serial line which happens to be delivered by TCP, and
        # that is how modbus_connection models it. An IPv6 literal has to be bracketed, or the address's
        # own colons read as the port separator
        host = config["host"]
        address = f"[{host}]" if ":" in host else host
        return ModbusSerialParams(device=f"socket://{address}:{config['port']}", framer="rtu")
    if protocol == SERIAL:
        return ModbusSerialParams(device=config["port"], baudrate=config["baudrate"], framer="rtu")
    raise AssertionError()


class ModbusClient:
    """Modbus"""

    def __init__(self, hass: HomeAssistant, protocol: str, adapter: InverterAdapter, config: dict[str, Any]) -> None:
        """Init"""
        self._hass = hass
        self._config = config
        self._protocol = protocol

        is_delayed = protocol in (SERIAL, TCP, RTU_OVER_TCP) or adapter.connection_type == ConnectionType.LAN
        is_lan_socket = protocol in (TCP, RTU_OVER_TCP) and adapter.connection_type == ConnectionType.LAN

        self._connection = ModbusConnection(
            _connection_params(protocol, config),
            message_spacing=_MESSAGE_SPACING_SECONDS if is_delayed else None,
            connect_delay=_CONNECT_DELAY_SECONDS if is_lan_socket else None,
        )
        # One handle per slave. They are cheap, and all serialize behind the connection's own lock
        self._units: dict[int, ModbusUnit] = {}

    def _unit(self, slave: int) -> ModbusUnit:
        unit = self._units.get(slave)
        if unit is None:
            unit = self._units[slave] = self._connection.for_unit(slave)
        return unit

    async def close(self) -> None:
        """Close the connection for good. Every later request on it fails"""
        _LOGGER.debug("Closing connection to modbus on %s", self)
        await self._connection.close()

    async def _recycle(self) -> None:
        """Drop the link, so that the next request opens a fresh one.

        `close()` is permanent, refusing everything which comes after it, so recovering from a bad link
        has to use `disconnect()` instead.
        """
        try:
            await self._connection.disconnect()
        except ModbusError:
            _LOGGER.debug("Error dropping the connection to %s", self, exc_info=True)

    async def _call(self, message: str, call: Callable[..., Awaitable[T]], *args: Any) -> T:
        """Make a request, retrying the failures which a retry can do something about.

        A timeout or a dropped link is worth another go. A device which answered with an exception has
        made its mind up, so that one goes straight back to the caller.
        """
        for attempt in range(_NUM_RETRIES):
            try:
                return await call(*args)
            except ClientClosedError as ex:
                # The connection was closed for good, so every later attempt fails the same way
                raise ModbusClientFailedError(message, self, ex) from ex
            except (ModbusTimeoutError, ModbusConnectionError) as ex:
                if attempt == _NUM_RETRIES - 1:
                    raise ModbusClientFailedError(message, self, ex) from ex
                _LOGGER.debug("%s (attempt %s of %s): %s", message, attempt + 1, _NUM_RETRIES, ex)
            except ModbusProtocolError as ex:
                # The reply didn't match what was asked, which means the stream is out of step. Recycle
                # the link, rather than leaving every later request reading the one before it's answer
                _LOGGER.warning("%s. %s", message, _MULTIPLE_CONNECTIONS_ADVICE)
                await self._recycle()
                raise ModbusClientFailedError(message, self, ex) from ex
            except ModbusError as ex:
                raise ModbusClientFailedError(message, self, ex) from ex
        raise AssertionError()

    async def read_registers(
        self,
        start_address: int,
        num_registers: int,
        register_type: RegisterType,
        slave: int,
    ) -> list[int]:
        """Read registers"""
        unit = self._unit(slave)
        description = f"Type: {register_type}; start: {start_address}; count: {num_registers}; slave: {slave}"

        if register_type == RegisterType.HOLDING:
            read = unit.read_holding_registers
        elif register_type == RegisterType.INPUT:
            read = unit.read_input_registers
        else:
            raise AssertionError()

        registers = await self._call(f"Error reading registers. {description}", read, start_address, num_registers)

        # rtu_over_tcp has no length prefix, so a delayed or partial reply can desync the stream and leave
        # responses paired with the wrong requests. Trusting the count then writes values to the wrong
        # addresses, so treat a mismatch as a transient error and let the caller retry the read
        if len(registers) != num_registers:
            message = (
                f"Error reading registers. {description}. Expected {num_registers} registers but received "
                f"{len(registers)}. This usually indicates a framing/desync issue on the connection."
            )
            _LOGGER.warning(message)
            await self._recycle()
            raise ModbusClientFailedError(message, self, ModbusDesyncError(message))

        return registers

    async def write_registers(self, register_address: int, register_values: list[int], slave: int) -> None:
        """Write registers"""
        unit = self._unit(slave)
        message = f"Error writing registers. Start: {register_address}; values: {register_values}; slave: {slave}"

        if len(register_values) > 1:
            await self._call(message, unit.write_registers, register_address, [int(v) for v in register_values])
        else:
            await self._call(message, unit.write_register, register_address, int(register_values[0]))

    def __str__(self) -> str:
        if self._protocol == SERIAL:
            return f"{self._config['port']}"
        return f"{self._protocol}://{self._config['host']}:{self._config['port']}"


class ModbusClientFailedError(Exception):
    """Raised when the ModbusClient fails to read/write"""

    def __init__(self, message: str, client: ModbusClient, response: ModbusError) -> None:
        super().__init__(f"{message} from {client}: {response}")
        self.message = message
        self.client = client
        self.response = response

    def __str__(self) -> str:
        return f"{self.message} from {self.client}: {self.response}"
