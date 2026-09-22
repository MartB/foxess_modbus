"""Sensor which maps a register value to a name"""

from dataclasses import dataclass
from typing import Any
from typing import cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import Platform
from homeassistant.helpers.entity import Entity

from ..common.entity_controller import EntityController
from ..common.types import Inv
from ..common.types import RegisterPollType
from ..common.types import RegisterType
from .entity_factory import ENTITY_DESCRIPTION_KWARGS
from .entity_factory import EntityFactory
from .inverter_model_spec import ModbusAddressSpec
from .modbus_entity_mixin import ModbusEntityMixin


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusEnumSensorDescription(SensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusEnumSensor.

    ModbusInverterStateSensor covers registers whose values run 0, 1, 2...; this one covers registers
    which use sparse codes, where a list would be mostly padding.
    """

    address: list[ModbusAddressSpec]
    values: dict[int, str]
    poll_type: RegisterPollType = RegisterPollType.PERIODICALLY

    @property
    def entity_type(self) -> type[Entity]:
        return SensorEntity

    def create_entity_if_supported(
        self,
        controller: EntityController,
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> Entity | None:
        address = self._address_for_inverter_model(self.address, inverter_model, register_type)
        return ModbusEnumSensor(controller, self, address) if address is not None else None

    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        addresses = self._addresses_for_inverter_model(self.address, inverter_model, register_type)
        if addresses is None:
            return None

        return {
            "type": "sensor",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
            "values": {str(k): v for k, v in sorted(self.values.items())},
        }


class ModbusEnumSensor(ModbusEntityMixin, SensorEntity):
    """Sensor which reports the name of whatever code a register holds"""

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusEnumSensorDescription,
        address: int,
    ) -> None:
        self._controller = controller
        self.entity_description = entity_description
        self._address = address
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> str | None:
        entity_description = cast(ModbusEnumSensorDescription, self.entity_description)
        value = self._controller.read(self._address, signed=False)
        if value is None:
            return None
        # An unknown code still says what it was, so it can be identified and added
        return entity_description.values.get(value, f"Unknown ({value})")

    @property
    def addresses(self) -> list[int]:
        return [self._address]

    @property
    def register_poll_type(self) -> RegisterPollType:
        return cast(ModbusEnumSensorDescription, self.entity_description).poll_type
