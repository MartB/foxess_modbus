from datetime import timedelta
from typing import Any
from typing import Iterable
from typing import cast
from unittest.mock import MagicMock

import pytest
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.json import JSONSnapshotExtension

from custom_components.foxess_modbus.common.entity_controller import ModbusControllerEntity
from custom_components.foxess_modbus.common.types import ConnectionType
from custom_components.foxess_modbus.common.types import Inv
from custom_components.foxess_modbus.common.types import InverterModel
from custom_components.foxess_modbus.common.types import RegisterPollType
from custom_components.foxess_modbus.const import DOMAIN
from custom_components.foxess_modbus.const import ENTITY_ID_PREFIX
from custom_components.foxess_modbus.const import FRIENDLY_NAME
from custom_components.foxess_modbus.const import INVERTER_BASE
from custom_components.foxess_modbus.const import INVERTER_CONN
from custom_components.foxess_modbus.const import INVERTER_MODEL
from custom_components.foxess_modbus.const import INVERTER_VERSION
from custom_components.foxess_modbus.const import UNIQUE_ID_PREFIX
from custom_components.foxess_modbus.entities.battery_modules import _ModuleVersionSensor
from custom_components.foxess_modbus.entities.devices import BATTERY
from custom_components.foxess_modbus.entities.devices import BMS
from custom_components.foxess_modbus.entities.devices import device_for_key
from custom_components.foxess_modbus.entities.entity_descriptions import ENTITIES
from custom_components.foxess_modbus.entities.inverter_model_spec import ModbusAddressesSpec
from custom_components.foxess_modbus.entities.modbus_clock_drift_sensor import ModbusClockDriftSensor
from custom_components.foxess_modbus.entities.modbus_clock_drift_sensor import ModbusClockDriftSensorDescription
from custom_components.foxess_modbus.entities.modbus_entity_mixin import device_info
from custom_components.foxess_modbus.inverter_profiles import INVERTER_PROFILES
from custom_components.foxess_modbus.inverter_profiles import Version
from custom_components.foxess_modbus.inverter_profiles import create_entities


@pytest.fixture
def snapshot_json(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(extension_class=JSONSnapshotExtension)


async def test_creates_all_entities(hass: HomeAssistant) -> None:
    controller = MagicMock()
    controller.hass = hass

    for profile in INVERTER_PROFILES.values():
        for connection_type, connection_type_profile in profile.connection_types.items():
            for entity_type in [SensorEntity, BinarySensorEntity, SelectEntity, NumberEntity]:
                controller.inverter_details = {
                    INVERTER_BASE: profile.model,
                    INVERTER_CONN: connection_type,
                    ENTITY_ID_PREFIX: "",
                    UNIQUE_ID_PREFIX: "",
                }

                # Asserts if e.g. the ModbusAddressSpecs match
                # We can't test IntegrationSensors (which have depends_on_other_entities=True), as HA throws up saying
                # that the entity it depends on doesn't exist (as we're not actually creating entities).
                entities = create_entities(entity_type, controller, filter_depends_on_other_entites=False)

                for entity in entities:
                    for address in cast(ModbusControllerEntity, entity).addresses:
                        for start, end in connection_type_profile.special_registers.invalid_register_ranges:
                            if start <= address <= end:
                                raise AssertionError(
                                    f"Profile {profile.model} Entity {entity.unique_id} address {address} lies in "
                                    f"range ({start}, {end})"
                                )


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "model" in metafunc.fixturenames:
        inputs = []
        for model, profile in INVERTER_PROFILES.items():
            for connection_type, connection_type_profile in profile.connection_types.items():
                for version in connection_type_profile.versions:
                    v = "latest" if version is None else f"v{version}"
                    inputs.append((model, connection_type, v))

        metafunc.parametrize(("model", "connection_type", "version"), inputs)


def test_entities(
    model: InverterModel, connection_type: ConnectionType, version: str, snapshot_json: SnapshotAssertion
) -> None:
    # syrupy doesn't like keys which aren't strings
    def _process(d: Any) -> None:
        if isinstance(d, dict):
            for k, v in d.copy().items():
                if not isinstance(k, str):
                    del d[k]
                    d[str(k)] = v
                _process(v)
        elif isinstance(d, str):
            pass
        elif isinstance(d, Iterable):
            for v in d:
                _process(v)

    connection_type_profile = INVERTER_PROFILES[model].connection_types[connection_type]
    v = None if version == "latest" else Version.parse(version.lstrip("v"))
    inv = connection_type_profile.get_inv_for_version(v)

    entities = []
    for entity_factory in ENTITIES:
        serialized = entity_factory.serialize(inv, connection_type_profile.register_type)
        if serialized is not None:
            _process(serialized)
            entities.append(serialized)

    entities.sort(key=lambda x: x.get("key", ""))

    assert entities == snapshot_json


def test_entity_devices(snapshot_json: SnapshotAssertion) -> None:
    """Which entities sit on a sub-device rather than on the inverter itself"""

    devices = {}
    for entity_factory in ENTITIES:
        key = getattr(entity_factory, "key", None)
        device = device_for_key(key) if key is not None else None
        if device is not None:
            devices[key] = "/".join(device.path)

    assert devices == snapshot_json


def test_sub_devices_hang_off_the_inverter() -> None:
    """A sub-device has to name its parent exactly as the parent registers itself, or HA rejects it"""

    def identifier(info: DeviceInfo) -> tuple[str, ...]:
        (value,) = info["identifiers"]
        return cast(tuple[str, ...], value)

    inv_details = {
        FRIENDLY_NAME: "Garage",
        INVERTER_MODEL: InverterModel.H3,
        INVERTER_CONN: ConnectionType.AUX,
    }
    inverter = device_info(inv_details)
    battery = device_info(inv_details, BATTERY)
    bms = device_info(inv_details, BMS[1])

    assert battery["via_device"] == identifier(inverter)
    assert bms["via_device"] == identifier(inverter)
    assert identifier(battery) == (*identifier(inverter), "battery")

    # services/utils.py finds the inverter from a device by looking here, so a service call can target a
    # sub-device and still reach the right controller
    for info in (inverter, battery, bms):
        assert identifier(info)[0] == DOMAIN
        assert identifier(info)[3] == "Garage"


@pytest.mark.parametrize(("offset", "expected_on"), [(0, False), (-30, False), (90, True), (-300, True)])
async def test_clock_drift(hass: HomeAssistant, offset: int, expected_on: bool) -> None:
    """The inverter keeps local wall-clock time, so drift is that against Home Assistant's"""

    inverter_time = dt_util.now() + timedelta(seconds=offset)
    registers = dict(
        zip(
            range(49222, 49228),
            (
                inverter_time.year,
                inverter_time.month,
                inverter_time.day,
                inverter_time.hour,
                inverter_time.minute,
                inverter_time.second,
            ),
            strict=True,
        )
    )

    controller = MagicMock()
    controller.hass = hass
    controller.inverter_details = {ENTITY_ID_PREFIX: "", UNIQUE_ID_PREFIX: ""}
    controller.read.side_effect = lambda address, **_kwargs: registers.get(address)

    description = ModbusClockDriftSensorDescription(
        key="inverter_clock_drift",
        addresses=[ModbusAddressesSpec(holding=list(registers), models=Inv.ALL)],
        name="Clock Drifted",
    )
    sensor = ModbusClockDriftSensor(controller, description, list(registers))

    # Only a drift worth acting on turns it on; a second either way is how the clock reads, not drift
    assert sensor.is_on is expected_on

    # How far it has drifted is still there to look at. The registers only carry whole seconds, so allow
    # for the truncation
    attributes = sensor.extra_state_attributes
    assert attributes is not None
    assert abs(attributes["drift_seconds"] - offset) <= 1

    # A clock which has never been set reads as nothing, rather than as a drift of decades
    registers[49222] = 0
    assert sensor.is_on is None
    assert sensor.extra_state_attributes is None


async def test_poll_types_agree(hass: HomeAssistant) -> None:
    """Entities sharing a register have to agree on how often it's read.

    The controller keeps one poll type per address and asserts on a mismatch, so a description which reads
    something once per connection can't share an address with one which wants it every poll.
    """

    controller = MagicMock()
    controller.hass = hass

    for profile in INVERTER_PROFILES.values():
        for connection_type, connection_type_profile in profile.connection_types.items():
            for version in connection_type_profile.versions:
                controller.inverter_details = {
                    INVERTER_BASE: profile.model,
                    INVERTER_CONN: connection_type,
                    INVERTER_VERSION: None if version is None else str(version),
                    ENTITY_ID_PREFIX: "",
                    UNIQUE_ID_PREFIX: "",
                }

                claimed: dict[int, tuple[str, RegisterPollType]] = {}
                for entity_type in [SensorEntity, BinarySensorEntity, SelectEntity, NumberEntity]:
                    for entity in create_entities(entity_type, controller, filter_depends_on_other_entites=False):
                        modbus_entity = cast(ModbusControllerEntity, entity)
                        for address in modbus_entity.addresses:
                            owner, poll_type = claimed.get(address, (None, modbus_entity.register_poll_type))
                            if poll_type != modbus_entity.register_poll_type:
                                raise AssertionError(
                                    f"{profile.model}/{connection_type}/{version}: register {address} is "
                                    f"{poll_type} for '{owner}' but "
                                    f"{modbus_entity.register_poll_type} for '{entity.unique_id}'"
                                )
                            claimed.setdefault(address, (str(entity.unique_id), modbus_entity.register_poll_type))


@pytest.mark.parametrize(
    ("register", "index", "expected"),
    [
        # What the official app reports for these two batteries: every module of the 12e's five-module
        # stack is on 1.15, behind a different high byte, and the 6e's single module is on 1.13
        (0x101F, 1, "1.15"),
        (0x201F, 2, "1.15"),
        (0x501F, 5, "1.15"),
        (0x101D, 1, "1.13"),
        # The high byte is the module's position, so a mismatch means this isn't our module's word
        (0x201F, 1, None),
        (0x0000, 1, None),
    ],
)
async def test_battery_module_version(hass: HomeAssistant, register: int, index: int, expected: str | None) -> None:
    controller = MagicMock()
    controller.hass = hass
    controller.inverter_details = {ENTITY_ID_PREFIX: "", UNIQUE_ID_PREFIX: ""}
    controller.read.side_effect = lambda _address, **_kwargs: register

    sensor = _ModuleVersionSensor(controller, index)
    assert sensor.native_value == expected
    assert sensor.addresses == [37033 + index - 1]
