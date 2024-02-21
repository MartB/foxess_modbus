"""Holds all entity descriptions for all entities across all inverters"""

import itertools
from typing import Iterable

from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.number import NumberMode
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import UnitOfTime

from ..common.register_type import RegisterType
from ..const import H1_SET
from ..const import H3_SET
from ..const import KH
from .charge_period_descriptions import CHARGE_PERIODS
from .entity_factory import EntityFactory
from .inverter_model_spec import EntitySpec
from .inverter_model_spec import ModbusAddressesSpec
from .inverter_model_spec import ModbusAddressSpec
from .modbus_battery_sensor import ModbusBatterySensorDescription
from .modbus_fault_sensor import ModbusFaultSensorDescription
from .modbus_integration_sensor import ModbusIntegrationSensorDescription
from .modbus_inverter_state_sensor import H1_INVERTER_STATES
from .modbus_inverter_state_sensor import KH_INVERTER_STATES
from .modbus_inverter_state_sensor import ModbusInverterStateSensorDescription
from .modbus_lambda_sensor import ModbusLambdaSensorDescription
from .modbus_number import ModbusNumberDescription
from .modbus_sensor import ModbusSensorDescription
from .modbus_version_sensor import ModbusVersionSensorDescription
from .modbus_work_mode_select import ModbusWorkModeSelectDescription
from .remote_control_description import REMOTE_CONTROL_DESCRIPTION
from .validation import Min
from .validation import Range

# hass type hints are messed up, and mypy doesn't see inherited dataclass properties on the EntityDescriptions
# mypy: disable-error-code="call-arg"


# TODO: There should be equivalent registers for the H3 somewhere
BMS_CONNECT_STATE_ADDRESS = [
    ModbusAddressSpec(models=H1_SET, input=11058, holding=31029),
    ModbusAddressSpec(models=[KH], input=11058, holding=31028),
    ModbusAddressSpec(models=H3_SET, holding=31042),
]


def _version_entities() -> Iterable[EntityFactory]:
    # Named so that they sort together
    yield ModbusVersionSensorDescription(
        key="master_version",
        address=[ModbusAddressSpec(models=[*H1_SET, KH, *H3_SET], input=10016, holding=30016)],
        name="Version: Master",
        icon="mdi:source-branch",
    )
    yield ModbusVersionSensorDescription(
        key="slave_version",
        address=[ModbusAddressSpec(models=[*H1_SET, KH, *H3_SET], input=10017, holding=30017)],
        name="Version: Slave",
        icon="mdi:source-branch",
    )
    yield ModbusVersionSensorDescription(
        key="manager_version",
        address=[ModbusAddressSpec(models=[*H1_SET, KH, *H3_SET], input=10018, holding=30018)],
        name="Version: Manager",
        icon="mdi:source-branch",
    )


def _pv_entities() -> Iterable[EntityFactory]:
    def _pv_voltage(key: str, addresses: list[ModbusAddressesSpec], name: str) -> EntityFactory:
        return ModbusSensorDescription(
            key=key,
            addresses=addresses,
            name=name,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="V",
            scale=0.1,
            round_to=1,
            # This can go negative if no panels are attached
        )

    def _pv_current(key: str, addresses: list[ModbusAddressesSpec], name: str) -> EntityFactory:
        return ModbusSensorDescription(
            key=key,
            addresses=addresses,
            name=name,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="A",
            scale=0.1,
            round_to=1,
            # This can a small amount negative
            post_process=lambda x: max(x, 0),
            validate=[Range(0, 100)],
        )

    def _pv_power(key: str, addresses: list[ModbusAddressesSpec], name: str) -> EntityFactory:
        return ModbusSensorDescription(
            key=key,
            addresses=addresses,
            name=name,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement="kW",
            icon="mdi:solar-power-variant-outline",
            scale=0.001,
            round_to=0.01,
            # This can go negative if no panels are attached
            post_process=lambda x: max(x, 0),
        )

    def _pv_energy_total(key: str, models: list[EntitySpec], name: str, source_entity: str) -> EntityFactory:
        return ModbusIntegrationSensorDescription(
            key=key,
            models=models,
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement="kWh",
            integration_method="left",
            name=name,
            source_entity=source_entity,
            unit_time=UnitOfTime.HOURS,
            icon="mdi:solar-power-variant-outline",
        )

    yield _pv_voltage(
        key="pv1_voltage",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11000], holding=[31000]),
            ModbusAddressesSpec(models=H3_SET, holding=[31000]),
        ],
        name="PV1 Voltage",
    )
    yield _pv_current(
        key="pv1_current",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11001], holding=[31001]),
            ModbusAddressesSpec(models=H3_SET, holding=[31001]),
        ],
        name="PV1 Current",
    )
    yield _pv_power(
        key="pv1_power",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11002], holding=[31002]),
            ModbusAddressesSpec(models=H3_SET, holding=[31002]),
        ],
        name="PV1 Power",
    )
    yield _pv_energy_total(
        key="pv1_energy_total",
        models=[
            EntitySpec(
                models=[*H1_SET, KH],
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
            EntitySpec(
                models=H3_SET,
                register_types=[RegisterType.HOLDING],
            ),
        ],
        name="PV1 Power Total",
        source_entity="pv1_power",
    )
    yield _pv_voltage(
        key="pv2_voltage",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11003], holding=[31003]),
            ModbusAddressesSpec(models=H3_SET, holding=[31003]),
        ],
        name="PV2 Voltage",
    )
    yield _pv_current(
        key="pv2_current",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11004], holding=[31004]),
            ModbusAddressesSpec(models=H3_SET, holding=[31004]),
        ],
        name="PV2 Current",
    )
    yield _pv_power(
        key="pv2_power",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11005], holding=[31005]),
            ModbusAddressesSpec(models=H3_SET, holding=[31005]),
        ],
        name="PV2 Power",
    )
    yield _pv_energy_total(
        key="pv2_energy_total",
        models=[
            EntitySpec(
                models=[*H1_SET, KH],
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
            EntitySpec(
                models=H3_SET,
                register_types=[RegisterType.HOLDING],
            ),
        ],
        name="PV2 Power Total",
        source_entity="pv2_power",
    )
    yield _pv_voltage(
        key="pv3_voltage",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11096], holding=[31039]),
        ],
        name="PV3 Voltage",
    )
    yield _pv_current(
        key="pv3_current",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11097], holding=[31040]),
        ],
        name="PV3 Current",
    )
    yield _pv_power(
        key="pv3_power",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11098], holding=[31041]),
        ],
        name="PV3 Power",
    )
    yield _pv_energy_total(
        key="pv3_energy_total",
        models=[
            EntitySpec(
                models=[KH],
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
        ],
        name="PV3 Power Total",
        source_entity="pv3_power",
    )
    yield _pv_voltage(
        key="pv4_voltage",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11099], holding=[31042]),
        ],
        name="PV4 Voltage",
    )
    yield _pv_current(
        key="pv4_current",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11100], holding=[31043]),
        ],
        name="PV4 Current",
    )
    yield _pv_power(
        key="pv4_power",
        addresses=[
            ModbusAddressesSpec(models=[KH], input=[11101], holding=[31044]),
        ],
        name="PV4 Power",
    )
    yield _pv_energy_total(
        key="pv4_energy_total",
        models=[
            EntitySpec(
                models=[KH],
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
        ],
        name="PV4 Power Total",
        source_entity="pv4_power",
    )
    yield ModbusLambdaSensorDescription(
        key="pv_power_now",
        models=[
            EntitySpec(
                models=H1_SET,
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
            EntitySpec(
                models=H3_SET,
                register_types=[RegisterType.HOLDING],
            ),
        ],
        sources=["pv1_power", "pv2_power"],
        method=sum,
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:solar-power-variant-outline",
    )
    yield ModbusLambdaSensorDescription(
        key="pv_power_now",
        models=[
            EntitySpec(
                models=[KH],
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            ),
        ],
        sources=["pv1_power", "pv2_power", "pv3_power", "pv4_power"],
        method=sum,
        name="PV Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:solar-power-variant-outline",
    )


def _h1_current_voltage_power_entities() -> Iterable[EntityFactory]:
    yield ModbusSensorDescription(
        key="invbatvolt",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11006], holding=[31020]),
        ],
        name="Inverter Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        # This can go negative if no battery is attached
    )
    yield ModbusSensorDescription(
        key="invbatcurrent",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11007], holding=[31021]),
        ],
        name="Inverter Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="load_power",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11023], holding=[31016]),
            ModbusAddressesSpec(models=[KH], input=[11023], holding=[31054, 31053]),
        ],
        name="Load Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="rvolt",  # Ideally rename to grid_voltage?
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11009], holding=[31006]),
        ],
        entity_registry_enabled_default=False,
        name="Grid Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        signed=False,
        validate=[Range(0, 300)],
    )
    yield ModbusSensorDescription(
        key="rcurrent",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11010], holding=[31007]),
        ],
        name="Inverter Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="rpower",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11011], holding=[31008]),
            ModbusAddressesSpec(models=[KH], input=[11011], holding=[31046, 31045]),
        ],
        name="Inverter Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:export",
        scale=0.001,
        round_to=0.01,
        # Negative = charging batteries
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="rpower_Q",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11012]),
        ],
        entity_registry_enabled_default=False,
        name="Inverter Power (Reactive)",
        # REACTIVE_POWER only supports var, not kvar
        # device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kvar",
        icon="mdi:export",
        scale=0.001,
        round_to=0.01,
        # Negative = charging batteries
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="rpower_S",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11013]),
        ],
        entity_registry_enabled_default=False,
        name="Inverter Power (Apparent)",
        # APPARENT_POWER only supports VA, not kVA
        # device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kVA",
        icon="mdi:export",
        scale=0.001,
        round_to=0.01,
        # Negative = charging batteries
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_rvolt",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11015], holding=[31010]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        signed=False,
        validate=[Range(0, 300)],
    )
    yield ModbusSensorDescription(
        key="eps_rcurrent",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11016], holding=[31011]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_rpower",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11017], holding=[31012]),
            ModbusAddressesSpec(models=[KH], input=[11017], holding=[31048, 31047]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        post_process=lambda x: max(x, 0),
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_rpower_Q",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11018]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Power (Reactive)",
        # REACTIVE_POWER only supports var, not kvar
        # device_class=SensorDeviceClass.REACTIVE_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kvar",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        post_process=lambda x: max(x, 0),
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_rpower_S",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11019]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Power (Apparent)",
        # APPARENT_POWER only supports VA, not kVA
        # device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kVA",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        post_process=lambda x: max(x, 0),
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_ct",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11021], holding=[31014]),
            ModbusAddressesSpec(models=[KH], input=[11021], holding=[31050, 31049]),
        ],
        name="Grid CT",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:meter-electric-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="feed_in",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11021], holding=[31014]),
            ModbusAddressesSpec(models=[KH], input=[11021], holding=[31050, 31049]),
        ],
        name="Feed-in",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-import",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: v if v > 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_consumption",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11021], holding=[31014]),
            ModbusAddressesSpec(models=[KH], input=[11021], holding=[31050, 31049]),
        ],
        name="Grid Consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-export",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: abs(v) if v < 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="ct2_meter",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11022], holding=[31015]),
            ModbusAddressesSpec(models=[KH], input=[11022], holding=[31052, 31051]),
        ],
        name="CT2 Meter",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:meter-electric-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )


def _h3_current_voltage_power_entities() -> Iterable[EntityFactory]:
    yield ModbusSensorDescription(
        key="grid_voltage_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31006])],
        entity_registry_enabled_default=False,
        name="Grid Voltage R",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        signed=False,
        validate=[Range(0, 300)],
    )
    yield ModbusSensorDescription(
        key="grid_voltage_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31007])],
        entity_registry_enabled_default=False,
        name="Grid Voltage S",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        signed=False,
        validate=[Range(0, 300)],
    )
    yield ModbusSensorDescription(
        key="grid_voltage_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31008])],
        entity_registry_enabled_default=False,
        name="Grid Voltage T",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        signed=False,
        validate=[Range(0, 300)],
    )
    yield ModbusSensorDescription(
        key="inv_current_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31009])],
        name="Inverter Current R",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="inv_current_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31010])],
        name="Inverter Current S",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="inv_current_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31011])],
        name="Inverter Current T",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="inv_power_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31012])],
        name="Inverter Power R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="inv_power_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31013])],
        name="Inverter Power S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="inv_power_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31014])],
        name="Inverter Power T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_power_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31022])],
        entity_registry_enabled_default=False,
        name="EPS Power R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_power_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31023])],
        entity_registry_enabled_default=False,
        name="EPS Power S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="eps_power_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31024])],
        entity_registry_enabled_default=False,
        name="EPS Power T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:power-socket",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_ct_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31026])],
        name="Grid CT R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:meter-electric-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="feed_in_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31026])],
        name="Feed-in R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-import",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: v if v > 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_consumption_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31026])],
        name="Grid Consumption R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-export",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: abs(v) if v < 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_ct_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31027])],
        name="Grid CT S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:meter-electric-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="feed_in_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31027])],
        name="Feed-in S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-import",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: v if v > 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_consumption_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31027])],
        name="Grid Consumption S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-export",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: abs(v) if v < 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_ct_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31028])],
        name="Grid CT T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:meter-electric-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="feed_in_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31028])],
        name="Feed-in T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-import",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: v if v > 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="grid_consumption_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31028])],
        name="Grid Consumption T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:transmission-tower-export",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: abs(v) if v < 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="load_power_R",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31029])],
        name="Load Power R",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="load_power_S",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31030])],
        name="Load Power S",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="load_power_T",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31031])],
        name="Load Power T",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )


def _inverter_entities() -> Iterable[EntityFactory]:
    yield ModbusSensorDescription(
        key="invbatpower",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11008], holding=[31022]),
            ModbusAddressesSpec(models=H3_SET, holding=[31036]),
        ],
        name="Inverter Battery Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        scale=0.001,
        round_to=0.01,
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="battery_discharge",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11008], holding=[31022]),
            ModbusAddressesSpec(models=H3_SET, holding=[31036]),
        ],
        name="Battery Discharge",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:battery-arrow-down-outline",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: v if v > 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="battery_charge",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11008], holding=[31022]),
            ModbusAddressesSpec(models=H3_SET, holding=[31036]),
        ],
        name="Battery Charge",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="kW",
        icon="mdi:battery-arrow-up-outline",
        scale=0.001,
        round_to=0.01,
        post_process=lambda v: abs(v) if v < 0 else 0,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="rfreq",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11014], holding=[31009]),
            ModbusAddressesSpec(models=H3_SET, holding=[31015]),
        ],
        entity_registry_enabled_default=False,
        name="Grid Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Hz",
        scale=0.01,
        round_to=0.1,
        signed=False,
        validate=[Range(0, 60)],
    )
    yield ModbusSensorDescription(
        key="eps_frequency",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11020], holding=[31013]),
            ModbusAddressesSpec(models=H3_SET, holding=[31025]),
        ],
        entity_registry_enabled_default=False,
        name="EPS Frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Hz",
        scale=0.01,
        round_to=0.1,
        signed=False,
        validate=[Range(0, 60)],
    )
    yield ModbusSensorDescription(
        key="invtemp",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11024], holding=[31018]),
            ModbusAddressesSpec(models=H3_SET, holding=[31032]),
        ],
        name="Inverter Temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        scale=0.1,
        round_to=0.5,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="ambtemp",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11025], holding=[31019]),
            ModbusAddressesSpec(models=H3_SET, holding=[31033]),
        ],
        name="Ambient Temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        scale=0.1,
        round_to=0.5,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="batvolt",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11034]),
            ModbusAddressesSpec(models=H3_SET, holding=[31034]),
        ],
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="V",
        scale=0.1,
        round_to=1,
        validate=[Min(0)],
    )
    yield ModbusSensorDescription(
        key="bat_current",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11035]),
            ModbusAddressesSpec(models=H3_SET, holding=[31035]),
        ],
        name="Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        round_to=1,
        validate=[Range(-100, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="battery_soc",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11036], holding=[31024]),
            ModbusAddressesSpec(models=H3_SET, holding=[31038]),
        ],
        # TODO: There might be an equivalent register for the H3?
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="Battery SoC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        signed=False,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_kwh_remaining",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11037])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS kWh Remaining",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        scale=0.01,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusBatterySensorDescription(
        key="battery_temp",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[11038], holding=[31023]),
            ModbusAddressesSpec(models=H3_SET, holding=[31037]),
        ],
        # TODO: There might be an equivalent register for the H3
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="Battery Temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        scale=0.1,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_charge_rate",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11041], holding=[31025])],
        entity_registry_enabled_default=False,
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Charge Rate",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        signed=False,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_discharge_rate",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11042], holding=[31026])],
        entity_registry_enabled_default=False,
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Discharge Rate",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        signed=False,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_cell_temp_high",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11043])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Cell Temp High",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        scale=0.1,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_cell_temp_low",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11044])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Cell Temp Low",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        scale=0.1,
        validate=[Range(0, 100)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_cell_mv_high",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11045])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Cell mV High",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        signed=False,
        round_to=10,
        validate=[Min(0)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_cell_mv_low",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11046])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Cell mV Low",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="mV",
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_cycle_count",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11048])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        name="BMS Cycle Count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusBatterySensorDescription(
        key="bms_watthours_total",
        addresses=[ModbusAddressesSpec(models=[*H1_SET, KH], input=[11049])],
        bms_connect_state_address=BMS_CONNECT_STATE_ADDRESS,
        entity_registry_enabled_default=False,
        name="BMS Energy Throughput",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        scale=0.001,
        round_to=1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusFaultSensorDescription(
        key="inverter_fault_code",
        # We don't map Fault Code 3, as it's unused
        addresses=[
            ModbusAddressesSpec(
                # These addresses are correct for the KH, but the fault codes are not
                models=H1_SET,
                input=[11061, 11062, 11064, 11065, 11066, 11067, 11068],
                holding=[31031, 31032, 31034, 31035, 31036, 31037, 31038],
            ),
            ModbusAddressesSpec(models=H3_SET, holding=[31044, 31045, 31047, 31048, 31049, 31050, 31051]),
        ],
        name="Inverter Fault Code",
        icon="mdi:alert-circle-outline",
    )
    yield ModbusInverterStateSensorDescription(
        key="inverter_state",
        address=[ModbusAddressSpec(models=H1_SET, input=11056, holding=31027)],
        name="Inverter State",
        states=H1_INVERTER_STATES,
    )
    yield ModbusInverterStateSensorDescription(
        key="inverter_state",
        address=[ModbusAddressSpec(models=[KH], input=11056, holding=31027)],
        name="Inverter State",
        states=KH_INVERTER_STATES,
    )
    yield ModbusSensorDescription(
        key="state_code",
        addresses=[ModbusAddressesSpec(models=H3_SET, holding=[31041])],
        name="Inverter State Code",
        state_class=SensorStateClass.MEASUREMENT,
    )
    # There are 32xxx holding registers on the H1, but they're only accessible over RS485
    yield ModbusSensorDescription(
        key="solar_energy_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11070, 11069]),
            ModbusAddressesSpec(models=[KH], input=[11070, 11069], holding=[32001, 32000]),
            ModbusAddressesSpec(models=H3_SET, holding=[32001, 32000]),
        ],
        name="Solar Generation Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusSensorDescription(
        key="solar_energy_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11071]),
            ModbusAddressesSpec(models=[KH], input=[11071], holding=[32002]),
            ModbusAddressesSpec(models=H3_SET, holding=[32002]),
        ],
        name="Solar Generation Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:solar-power",
        scale=0.1,
        signed=False,
        validate=[Range(0, 1000)],
    )
    yield ModbusSensorDescription(
        key="battery_charge_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11073, 11072]),
            ModbusAddressesSpec(models=[KH], input=[11073, 11072], holding=[32004, 32003]),
            ModbusAddressesSpec(models=H3_SET, holding=[32004, 32003]),
        ],
        name="Battery Charge Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-up-outline",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusIntegrationSensorDescription(
        key="battery_charge_total",
        models=[EntitySpec(models=H1_SET, register_types=[RegisterType.HOLDING])],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-up-outline",
        integration_method="left",
        name="Battery Charge Total",
        source_entity="battery_charge",
        unit_time=UnitOfTime.HOURS,
    )
    yield ModbusSensorDescription(
        key="battery_charge_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11074]),
            ModbusAddressesSpec(models=[KH], input=[11074], holding=[32005]),
            ModbusAddressesSpec(models=H3_SET, holding=[32005]),
        ],
        name="Battery Charge Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-up-outline",
        scale=0.1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="battery_discharge_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11076, 11075]),
            ModbusAddressesSpec(models=[KH], input=[11076, 11075], holding=[32007, 32006]),
            ModbusAddressesSpec(models=H3_SET, holding=[32007, 32006]),
        ],
        name="Battery Discharge Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-down-outline",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusIntegrationSensorDescription(
        key="battery_discharge_total",
        models=[EntitySpec(models=H1_SET, register_types=[RegisterType.HOLDING])],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-down-outline",
        integration_method="left",
        name="Battery Discharge Total",
        source_entity="battery_discharge",
        unit_time=UnitOfTime.HOURS,
    )
    yield ModbusSensorDescription(
        key="battery_discharge_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11077]),
            ModbusAddressesSpec(models=[KH], input=[11077], holding=[32008]),
            ModbusAddressesSpec(models=H3_SET, holding=[32008]),
        ],
        name="Battery Discharge Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:battery-arrow-down-outline",
        scale=0.1,
        validate=[Range(0, 100)],
    )
    yield ModbusSensorDescription(
        key="feed_in_energy_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11079, 11078]),
            ModbusAddressesSpec(models=[KH], input=[11079, 11078], holding=[32010, 32009]),
            ModbusAddressesSpec(models=H3_SET, holding=[32010, 32009]),
        ],
        name="Feed-in Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-import",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusIntegrationSensorDescription(
        key="feed_in_energy_total",
        models=[
            EntitySpec(models=H1_SET, register_types=[RegisterType.HOLDING]),
        ],
        name="Feed-in Total",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        integration_method="left",
        source_entity="feed_in",
        unit_time=UnitOfTime.HOURS,
        icon="mdi:transmission-tower-import",
    )
    yield ModbusSensorDescription(
        key="feed_in_energy_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11080]),
            ModbusAddressesSpec(models=[KH], input=[11080], holding=[32011]),
            ModbusAddressesSpec(models=H3_SET, holding=[32011]),
        ],
        name="Feed-in Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-import",
        scale=0.1,
        validate=[Range(0, 1000)],
    )
    yield ModbusSensorDescription(
        key="grid_consumption_energy_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11082, 11081]),
            ModbusAddressesSpec(models=[KH], input=[11082, 11081], holding=[32013, 32012]),
            ModbusAddressesSpec(models=H3_SET, holding=[32013, 32012]),
        ],
        name="Grid Consumption Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-export",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusIntegrationSensorDescription(
        key="grid_consumption_energy_total",
        models=[EntitySpec(models=H1_SET, register_types=[RegisterType.HOLDING])],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        integration_method="left",
        name="Grid Consumption Total",
        source_entity="grid_consumption",
        unit_time=UnitOfTime.HOURS,
        icon="mdi:transmission-tower-export",
    )
    yield ModbusSensorDescription(
        key="grid_consumption_energy_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11083]),
            ModbusAddressesSpec(models=[KH], input=[11083], holding=[32014]),
            ModbusAddressesSpec(models=H3_SET, holding=[32014]),
        ],
        name="Grid Consumption Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:transmission-tower-export",
        scale=0.1,
        validate=[Range(0, 1000)],
    )
    yield ModbusSensorDescription(
        key="total_yield_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11085, 11084]),
            ModbusAddressesSpec(models=[KH], input=[11085, 11084], holding=[32016, 32015]),
            ModbusAddressesSpec(models=H3_SET, holding=[32016, 32015]),
        ],
        name="Yield Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:export",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusSensorDescription(
        key="total_yield_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11086]),
            ModbusAddressesSpec(models=[KH], input=[11086], holding=[32017]),
            ModbusAddressesSpec(models=H3_SET, holding=[32017]),
        ],
        name="Yield Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:export",
        scale=0.1,
        # unsure if this actually goes negative
        validate=[Range(-100, 100)],
    )
    yield ModbusSensorDescription(
        key="input_energy_total",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11088, 11087]),
            ModbusAddressesSpec(models=[KH], input=[11088, 11087], holding=[32019, 32018]),
            ModbusAddressesSpec(models=H3_SET, holding=[32019, 32018]),
        ],
        name="Input Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:import",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusSensorDescription(
        key="input_energy_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11089]),
            ModbusAddressesSpec(models=[KH], input=[11089], holding=[32020]),
            ModbusAddressesSpec(models=H3_SET, holding=[32020]),
        ],
        name="Input Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:import",
        scale=0.1,
        # unsure if this actually goes negative
        validate=[Range(-1000, 1000)],
    )
    yield ModbusSensorDescription(
        key="load_power_total",
        addresses=[
            # TODO: There are registers for H1, but we currently use an integration
            # ModbusAddressesSpec(
            #     models=H1_SET, input=[11091, 11090]
            # ),
            ModbusAddressesSpec(models=[KH], input=[11091, 11090], holding=[32022, 32021]),
            ModbusAddressesSpec(models=H3_SET, holding=[32022, 32021]),
        ],
        name="Load Energy Total",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement="kWh",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.1,
        signed=False,
        validate=[Min(0)],
    )
    yield ModbusIntegrationSensorDescription(
        key="load_power_total",
        models=[
            EntitySpec(
                models=H1_SET,
                register_types=[RegisterType.INPUT, RegisterType.HOLDING],
            )
        ],
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement="kWh",
        icon="mdi:home-lightning-bolt-outline",
        integration_method="left",
        name="Load Energy Total",
        source_entity="load_power",
        unit_time=UnitOfTime.HOURS,
    )
    yield ModbusSensorDescription(
        key="load_energy_today",
        addresses=[
            ModbusAddressesSpec(models=H1_SET, input=[11092]),
            ModbusAddressesSpec(models=[KH], input=[11092], holding=[32023]),
            ModbusAddressesSpec(models=H3_SET, holding=[32023]),
        ],
        name="Load Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="kWh",
        icon="mdi:home-lightning-bolt-outline",
        scale=0.1,
        # unsure if this actually goes negative
        validate=[Range(-1000, 1000)],
    )


def _configuration_entities() -> Iterable[EntityFactory]:
    yield ModbusWorkModeSelectDescription(
        key="work_mode",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41000),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41000),
        ],
        name="Work Mode",
        options_map={0: "Self Use", 1: "Feed-in First", 2: "Back-up"},
    )
    # Sensors are a bit nicer to look at: keep for consistency with other numbers
    yield ModbusSensorDescription(
        key="max_charge_current",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[41007]),
            ModbusAddressesSpec(models=[*H3_SET, KH], holding=[41007]),
        ],
        name="Max Charge Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        validate=[Range(0, 50)],
    )
    yield ModbusNumberDescription(
        key="max_charge_current",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41007),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41007),
        ],
        name="Max Charge Current",
        mode=NumberMode.BOX,
        device_class=NumberDeviceClass.CURRENT,
        native_min_value=0,
        native_max_value=50,
        native_step=0.1,
        native_unit_of_measurement="A",
        scale=0.1,
        validate=[Range(0, 50)],
    )
    yield ModbusSensorDescription(
        key="max_discharge_current",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[41008]),
            ModbusAddressesSpec(models=[*H3_SET, KH], holding=[41008]),
        ],
        name="Max Discharge Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="A",
        scale=0.1,
        validate=[Range(0, 50)],
    )
    yield ModbusNumberDescription(
        key="max_discharge_current",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41008),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41008),
        ],
        name="Max Discharge Current",
        mode=NumberMode.BOX,
        device_class=NumberDeviceClass.CURRENT,
        native_min_value=0,
        native_max_value=50,
        native_step=0.1,
        native_unit_of_measurement="A",
        scale=0.1,
        validate=[Range(0, 50)],
    )
    # Sensor kept for back compat
    yield ModbusSensorDescription(
        key="min_soc",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[41009]),
            ModbusAddressesSpec(models=[*H3_SET, KH], holding=[41009]),
        ],
        name="Min SoC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
        native_unit_of_measurement="%",
        validate=[Range(0, 100)],
    )
    yield ModbusNumberDescription(
        key="min_soc",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41009),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41009),
        ],
        name="Min SoC",
        mode=NumberMode.BOX,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        device_class=NumberDeviceClass.BATTERY,
        icon="mdi:battery-arrow-down",
        validate=[Range(0, 100)],
    )
    # Sensor kept for back compat
    yield ModbusSensorDescription(
        key="max_soc",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[41010]),
            ModbusAddressesSpec(models=[*H3_SET, KH], holding=[41010]),
        ],
        name="Max SoC",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        icon="mdi:battery-arrow-up",
        validate=[Range(0, 100)],
    )
    yield ModbusNumberDescription(
        key="max_soc",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41010),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41010),
        ],
        name="Max SoC",
        mode=NumberMode.BOX,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        device_class=NumberDeviceClass.BATTERY,
        icon="mdi:battery-arrow-up",
        validate=[Range(0, 100)],
    )
    # Sensor kept for back compat
    yield ModbusSensorDescription(
        key="min_soc_on_grid",
        addresses=[
            ModbusAddressesSpec(models=[*H1_SET, KH], input=[41011]),
            ModbusAddressesSpec(models=[*H3_SET, KH], holding=[41011]),
        ],
        name="Min SoC (On Grid)",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        icon="mdi:battery-arrow-down",
        validate=[Range(0, 100)],
    )
    yield ModbusNumberDescription(
        key="min_soc_on_grid",
        address=[
            ModbusAddressSpec(models=[*H1_SET, KH], input=41011),
            ModbusAddressSpec(models=[*H3_SET, KH], holding=41011),
        ],
        name="Min SoC (On Grid)",
        mode=NumberMode.BOX,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        device_class=NumberDeviceClass.BATTERY,
        icon="mdi:battery-arrow-down",
        validate=[Range(0, 100)],
    )


ENTITIES: list[EntityFactory] = list(
    itertools.chain(
        _version_entities(),
        _pv_entities(),
        _h1_current_voltage_power_entities(),
        _h3_current_voltage_power_entities(),
        _inverter_entities(),
        _configuration_entities(),
        (description for x in CHARGE_PERIODS for description in x.entity_descriptions),
        REMOTE_CONTROL_DESCRIPTION.entity_descriptions,
    )
)
