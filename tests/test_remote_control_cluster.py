"""Tests for deciding which inverter in a cluster drives remote control"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.foxess_modbus import RemoteControlCluster
from custom_components.foxess_modbus.const import ENTITY_ID_PREFIX
from custom_components.foxess_modbus.const import REMOTE_CONTROL_ROLE_MASTER
from custom_components.foxess_modbus.const import REMOTE_CONTROL_ROLE_SLAVE
from custom_components.foxess_modbus.entities.modbus_remote_control_config import ModbusRemoteControlAddressConfig
from custom_components.foxess_modbus.remote_control_manager import RemoteControlManager

_PARALLEL_MASTER_ADDRESS = 31146

_ADDRESSES = ModbusRemoteControlAddressConfig(
    remote_enable=44000,
    timeout_set=44001,
    active_power=[44002, 44003],
    work_mode=41000,
    work_mode_map=None,
    battery_soc=[31024],
    max_soc=41010,
    invbatpower=[31022],
    pwr_limit_bat_up=[44012],
    pv_voltages=[31000],
)


def _inverter(hass: HomeAssistant, prefix: str, reports_master: bool | None) -> Any:
    """A controller whose inverter reports itself as the parallel master, or hasn't said yet"""

    controller = MagicMock()
    controller.hass = hass
    controller.inverter_details = {ENTITY_ID_PREFIX: prefix}

    def read(address: int, **_kwargs: Any) -> int | None:
        if address == _PARALLEL_MASTER_ADDRESS:
            return None if reports_master is None else int(reports_master)
        return 0

    controller.read.side_effect = read
    controller.remote_control_manager = RemoteControlManager(controller, _ADDRESSES, 10)
    return controller


def _manager(controller: Any) -> RemoteControlManager:
    return controller.remote_control_manager  # type: ignore[no-any-return]


def _role(controller: Any) -> Any:
    """The role the cluster gave this inverter, as it reports it to the UI"""
    info = _manager(controller).cluster_info
    return None if info is None else info["role"]


def _slaves(controller: Any) -> Any:
    info = _manager(controller).cluster_info
    return None if info is None else info["slaves"]


def _build(hass: HomeAssistant, *inverters: tuple[str, str, bool | None]) -> list[Any]:
    """Wire up a cluster from (prefix, configured role, what the inverter reports)"""

    controllers = [_inverter(hass, prefix, reports) for prefix, _role, reports in inverters]
    members = [(controller, role) for controller, (_p, role, _r) in zip(controllers, inverters, strict=True)]
    cluster = RemoteControlCluster("default", members)
    cluster.apply(dict(members))
    return controllers


async def test_configured_roles_are_used_to_start_with(hass: HomeAssistant) -> None:
    """Nothing has been read yet when the cluster is first wired up"""

    master, slave = _build(
        hass,
        ("master", REMOTE_CONTROL_ROLE_MASTER, None),
        ("slave", REMOTE_CONTROL_ROLE_SLAVE, None),
    )

    assert _role(master) == "master"
    assert _role(slave) == "slave"
    assert _slaves(master) == ["slave"]


async def test_agreeing_inverters_change_nothing(hass: HomeAssistant) -> None:
    master, slave = _build(
        hass,
        ("master", REMOTE_CONTROL_ROLE_MASTER, True),
        ("slave", REMOTE_CONTROL_ROLE_SLAVE, False),
    )

    _manager(master).cluster.role_detected()  # type: ignore[union-attr]

    assert _role(master) == "master"
    assert _role(slave) == "slave"
    assert _slaves(master) == ["slave"]


async def test_the_inverters_win_when_they_disagree(hass: HomeAssistant) -> None:
    """Configured the wrong way round, so the cluster follows what the inverters say"""

    configured_master, configured_slave = _build(
        hass,
        ("configured_master", REMOTE_CONTROL_ROLE_MASTER, False),
        ("configured_slave", REMOTE_CONTROL_ROLE_SLAVE, True),
    )

    _manager(configured_master).cluster.role_detected()  # type: ignore[union-attr]

    assert _role(configured_slave) == "master"
    assert _role(configured_master) == "slave"
    # The inverter demoted to slave must not still be holding the one which now drives the cluster
    assert _slaves(configured_slave) == ["configured_master"]
    assert _slaves(configured_master) == []


async def test_nothing_moves_until_every_inverter_has_answered(hass: HomeAssistant) -> None:
    """One answer doesn't say which of them is in charge"""

    configured_master, configured_slave = _build(
        hass,
        ("configured_master", REMOTE_CONTROL_ROLE_MASTER, False),
        ("configured_slave", REMOTE_CONTROL_ROLE_SLAVE, None),
    )

    _manager(configured_master).cluster.role_detected()  # type: ignore[union-attr]

    assert _role(configured_master) == "master"
    assert _role(configured_slave) == "slave"


@pytest.mark.parametrize("reports", [(True, True), (False, False)])
async def test_a_nonsense_answer_leaves_the_configuration_alone(
    hass: HomeAssistant, reports: tuple[bool, bool]
) -> None:
    """Two masters, or none, means these aren't one parallel system"""

    master, slave = _build(
        hass,
        ("master", REMOTE_CONTROL_ROLE_MASTER, reports[0]),
        ("slave", REMOTE_CONTROL_ROLE_SLAVE, reports[1]),
    )

    _manager(master).cluster.role_detected()  # type: ignore[union-attr]

    assert _role(master) == "master"
    assert _role(slave) == "slave"
