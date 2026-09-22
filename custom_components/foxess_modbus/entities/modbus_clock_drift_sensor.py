"""Sensor which reports how far the inverter's clock has drifted from Home Assistant's"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import cast

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import Platform
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from ..common.entity_controller import EntityController
from ..common.types import Inv
from ..common.types import RegisterType
from .entity_factory import ENTITY_DESCRIPTION_KWARGS
from .entity_factory import EntityFactory
from .inverter_model_spec import ModbusAddressesSpec
from .modbus_entity_mixin import ModbusEntityMixin


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusClockDriftSensorDescription(SensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusClockDriftSensor"""

    # Year, month, day, hour, minute, second, in that order
    addresses: list[ModbusAddressesSpec]

    @property
    def entity_type(self) -> type[Entity]:
        return SensorEntity

    def create_entity_if_supported(
        self,
        controller: EntityController,
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> Entity | None:
        addresses = self._addresses_for_inverter_model(self.addresses, inverter_model, register_type)
        return ModbusClockDriftSensor(controller, self, addresses) if addresses is not None else None

    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        addresses = self._addresses_for_inverter_model(self.addresses, inverter_model, register_type)
        if addresses is None:
            return None

        return {
            "type": "sensor",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
        }


class ModbusClockDriftSensor(ModbusEntityMixin, SensorEntity):
    """How far ahead of Home Assistant the inverter's own clock is, in seconds.

    The inverter keeps local time, with no offset of its own, so this compares it against Home Assistant's
    local time. An inverter whose clock has slipped will timestamp its own daily energy totals wrongly and
    run its charge periods at the wrong time, neither of which shows up anywhere else.
    """

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusClockDriftSensorDescription,
        addresses: list[int],
    ) -> None:
        self._controller = controller
        self.entity_description = entity_description
        self._addresses = addresses
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> int | None:
        parts = [self._controller.read(address, signed=False) for address in self._addresses]
        if any(part is None for part in parts):
            return None

        year, month, day, hour, minute, second = cast(list[int], parts)
        try:
            # Naive on purpose: the inverter keeps wall-clock time, and so does the value it's
            # compared against
            inverter_time = datetime(year, month, day, hour, minute, second)  # noqa: DTZ001
        except ValueError:
            # An unset or half-written clock, rather than a drifting one
            return None

        return round((inverter_time - dt_util.now().replace(tzinfo=None)).total_seconds())

    @property
    def addresses(self) -> list[int]:
        return self._addresses
