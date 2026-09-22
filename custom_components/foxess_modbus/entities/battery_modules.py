"""Discovers the modules making up the battery stack, and reads the serial number of each.

The number of modules is only known once the inverter has been polled, so these entities can't be created
along with all the others at startup: doing that would leave a row of "unknown" serial numbers on every
system with fewer modules than the largest stack we support.

The module count and the BMS master serial both come from entities which *are* created at startup, so
reading them back through the controller doubles as the check for whether this inverter has a BMS table at
all: the controller only holds a value for an address some entity asked it to poll.
"""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.const import Platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..common.entity_controller import EntityController
from ..common.entity_controller import ModbusControllerEntity
from ..common.types import Inv
from ..common.types import RegisterPollType
from .devices import BATTERY
from .devices import assign_device
from .inverter_model_spec import ModbusAddressesSpec
from .modbus_entity_mixin import ModbusEntityMixin
from .modbus_string_sensor import ModbusStringSensor
from .modbus_string_sensor import ModbusStringSensorDescription

_LOGGER = logging.getLogger(__name__)

# The number of modules in the stack, as reported by the inverter (31136) or by the BMS itself (37032)
_MODULE_COUNT_ADDRESSES = (31136, 37032)
# BMS1 Master SN. If this isn't being polled then this inverter has no BMS table, and there's nothing to do
_MASTER_SERIAL_ADDRESS = 37005
# BMS1 Slave1 SN. The spec documents the table as far as Slave2; it carries on at the same stride, which is
# how a stack of more than two modules reports itself
_SLAVE_SERIAL_ADDRESS = 37097
_SLAVE_SERIAL_STRIDE = 16
_SLAVE_SERIAL_LENGTH = 8
# BMS1 Slave1 Version, one register per module, documented as far as Slave 2 like the serials
_SLAVE_VERSION_ADDRESS = 37033
# The table has room for far more than any real stack. Cap it so that a garbage read can't create hundreds
# of entities, and so we stay well clear of BMS1 Voltage at 37609
_MAX_MODULES = 16


def async_setup_battery_modules(controller: EntityController, async_add_entities: AddEntitiesCallback) -> None:
    """Start watching for the modules of this inverter's battery stack"""
    _BatteryModuleDiscovery(controller, async_add_entities).start()


class _BatteryModuleDiscovery(ModbusControllerEntity):
    """Listens to the controller's polls, and adds a serial number per module once it knows how many there are.

    This isn't an entity, but registering as one is how a listener gets told about polls. It holds no
    addresses of its own, so it doesn't add anything to the poll.
    """

    def __init__(self, controller: EntityController, async_add_entities: AddEntitiesCallback) -> None:
        self._controller = controller
        self._async_add_entities = async_add_entities
        self._added = 0

    def start(self) -> None:
        self._controller.register_modbus_entity(self)

    @property
    def addresses(self) -> list[int]:
        return []

    @property
    def register_poll_type(self) -> RegisterPollType:
        return RegisterPollType.ON_CONNECTION

    def is_connected_changed_callback(self) -> None:
        pass

    def update_callback(self, _changed_addresses: set[int]) -> None:
        count = self._module_count()
        if count <= self._added:
            return

        # The controller is partway through notifying its listeners, so registering entities (and with them
        # their addresses) has to wait until it's finished
        self._controller.hass.loop.call_soon(self._add_modules, count)

    def _module_count(self) -> int:
        # The master serial is only polled on the models whose BMS table this is, so if it's missing then
        # none of this applies to this inverter
        if self._controller.read(_MASTER_SERIAL_ADDRESS, signed=False) is None:
            return 0

        for address in _MODULE_COUNT_ADDRESSES:
            count = self._controller.read(address, signed=False)
            if count is not None and count > 0:
                if count > _MAX_MODULES:
                    _LOGGER.warning(
                        "Inverter reports %s battery modules at register %s, which is more than the %s we "
                        "support. Ignoring the rest",
                        count,
                        address,
                        _MAX_MODULES,
                    )
                return min(count, _MAX_MODULES)

        return 0

    def _add_modules(self, count: int) -> None:
        if count <= self._added:
            return

        entities: list[Entity] = []
        for index in range(self._added + 1, count + 1):
            assign_device(_serial_key(index), BATTERY)
            assign_device(_version_key(index), BATTERY)
            entities.append(_module_serial_entity(self._controller, index))
            entities.append(_ModuleVersionSensor(self._controller, index))

        _LOGGER.info("Battery stack has %s module(s): adding %s", count, [x.entity_id for x in entities])
        self._added = count
        self._async_add_entities(entities)
        # Serial numbers are only read on connection, and we've just missed this inverter's
        self._controller.request_connection_read()


def _serial_key(index: int) -> str:
    return f"bms_slave_{index}_serial_number"


def _version_key(index: int) -> str:
    return f"bms_slave_{index}_version"


class _ModuleVersionSensor(ModbusEntityMixin, SensorEntity):
    """The firmware version of one module of the battery stack.

    The register holds the module's position in the stack in the top nibble and its version in the low
    byte, and that version byte splits into nibbles again: 0x1F is the 1.15 the official app reports, 0x1D
    is 1.13. Reading the position back is how we know the top of the word isn't part of the version - the
    five modules of one stack all report 1.15, as 0x101F through 0x501F.

    The low nibble stops at 15, so a module on x.16 would read here as (x+1).0. Nothing has been seen that
    high to check against.
    """

    def __init__(self, controller: EntityController, index: int) -> None:
        self._controller = controller
        self._index = index
        self._address = _SLAVE_VERSION_ADDRESS + index - 1
        self.entity_description = SensorEntityDescription(
            key=_version_key(index),
            name=f"BMS Slave {index} Version",
            icon="mdi:source-branch",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> str | None:
        value = self._controller.read(self._address, signed=False)
        if value is None or value >> 12 != self._index:
            return None
        version = value & 0xFF
        return f"{version >> 4}.{version & 0x0F:02d}"

    @property
    def addresses(self) -> list[int]:
        return [self._address]

    @property
    def register_poll_type(self) -> RegisterPollType:
        # Slowly rather than on connection, so a module firmware update shows up the same day
        return RegisterPollType.SLOWLY


def _module_serial_entity(controller: EntityController, index: int) -> ModbusStringSensor:
    start = _SLAVE_SERIAL_ADDRESS + _SLAVE_SERIAL_STRIDE * (index - 1)
    addresses = list(range(start, start + _SLAVE_SERIAL_LENGTH))
    description = ModbusStringSensorDescription(
        key=_serial_key(index),
        addresses=[ModbusAddressesSpec(holding=addresses, models=Inv.ALL)],
        chars_per_register=2,
        name=f"BMS Slave {index} Serial Number",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    return ModbusStringSensor(controller, description, addresses)
