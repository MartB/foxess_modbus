"""Tests for how a connection's settings are handed to modbus_connection"""

import warnings
from typing import Any

import pytest
from modbus_connection import ModbusSerialParams
from modbus_connection import ModbusTcpParams
from modbus_connection import ModbusUdpParams
from modbus_connection.tmodbus import ModbusConnection

from custom_components.foxess_modbus.client.modbus_client import _connection_params
from custom_components.foxess_modbus.const import RTU_OVER_TCP
from custom_components.foxess_modbus.const import SERIAL
from custom_components.foxess_modbus.const import TCP
from custom_components.foxess_modbus.const import UDP

_TCP_CONFIG = {"host": "10.0.1.50", "port": 502}
_SERIAL_CONFIG = {"port": "/dev/ttyUSB0", "baudrate": 9600}


@pytest.mark.parametrize(
    ("protocol", "config", "expected_type", "expected_endpoint"),
    [
        (TCP, _TCP_CONFIG, ModbusTcpParams, ("tcp", "10.0.1.50", 502)),
        (UDP, _TCP_CONFIG, ModbusUdpParams, ("udp", "10.0.1.50", 502)),
        # RTU framing over a socket is modelled as a serial line carried by TCP, not as a TCP link.
        # Passing it as a TCP link with an rtu framer is deprecated, and warns
        (RTU_OVER_TCP, _TCP_CONFIG, ModbusSerialParams, ("serial", "socket://10.0.1.50:502")),
        # An IPv6 literal has to be bracketed, or its own colons read as the port separator
        (
            RTU_OVER_TCP,
            {"host": "fd00::1", "port": 502},
            ModbusSerialParams,
            ("serial", "socket://[fd00::1]:502"),
        ),
        (SERIAL, _SERIAL_CONFIG, ModbusSerialParams, ("serial", "/dev/ttyUSB0")),
    ],
)
def test_connection_params(
    protocol: str,
    config: dict[str, Any],
    expected_type: type,
    expected_endpoint: tuple[str, ...],
) -> None:
    """Each protocol maps to the params type and endpoint which addresses that device"""
    with warnings.catch_warnings():
        # A mapping which the library considers deprecated must fail the test, not merely warn
        warnings.simplefilter("error", DeprecationWarning)
        params = _connection_params(protocol, config)

    assert isinstance(params, expected_type)
    assert params.endpoint == expected_endpoint

    # The params have to be ones the backend will actually accept
    connection = ModbusConnection(params)
    assert not connection.connected


def test_rtu_over_tcp_and_serial_share_an_identity() -> None:
    """rtu-over-tcp to a host is the same device as a serial link to that socket.

    modbus_connection shares one connection between everything addressing the same endpoint, so these
    have to agree, or two holds on one device would open two competing links to it.
    """
    over_tcp = _connection_params(RTU_OVER_TCP, _TCP_CONFIG)
    direct = ModbusSerialParams(device="socket://10.0.1.50:502", framer="rtu")

    assert over_tcp.endpoint == direct.endpoint


def test_unknown_protocol_is_rejected() -> None:
    with pytest.raises(AssertionError):
        _connection_params("carrier-pigeon", _TCP_CONFIG)


def test_serial_keeps_the_configured_line_speed() -> None:
    params = _connection_params(SERIAL, {"port": "/dev/ttyUSB0", "baudrate": 19200})

    assert isinstance(params, ModbusSerialParams)
    assert params.baudrate == 19200
    assert params.framer == "rtu"
