"""Sensor which reports whether the inverter's clock has drifted from Home Assistant's"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from typing import cast

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.const import Platform
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt as dt_util

from ..common.entity_controller import EntityController
from ..common.types import Inv
from ..common.types import RegisterPollType
from ..common.types import RegisterType
from .entity_factory import ENTITY_DESCRIPTION_KWARGS
from .entity_factory import EntityFactory
from .inverter_model_spec import ModbusAddressesSpec
from .modbus_entity_mixin import ModbusEntityMixin

# How far the clock has to be out before it matters. Charge periods are set to the minute, and the daily
# energy totals are stamped to the day, so anything under a minute changes nothing observable. The reading
# is only ever whole seconds either side, so a threshold also keeps measurement noise out of the state
_DRIFT_THRESHOLD_SECONDS = 60


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusClockDriftSensorDescription(BinarySensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusClockDriftSensor"""

    # Year, month, day, hour, minute, second, in that order
    addresses: list[ModbusAddressesSpec]

    @property
    def entity_type(self) -> type[Entity]:
        return BinarySensorEntity

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
            "type": "binary-sensor",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
        }


class ModbusClockDriftSensor(ModbusEntityMixin, BinarySensorEntity):
    """Whether the inverter's own clock has drifted away from Home Assistant's.

    The inverter keeps local time, with no offset of its own, so this compares it against Home Assistant's
    local time. An inverter whose clock has slipped will timestamp its own daily energy totals wrongly and
    run its charge periods at the wrong time, neither of which shows up anywhere else.

    How far it has drifted is an attribute rather than the state: the figure is only interesting once it is
    large enough to act on, and as a state it would write a new value on every poll for a second of noise.
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
        self.entity_id = self._get_entity_id(Platform.BINARY_SENSOR)

    @property
    def _drift_seconds(self) -> int | None:
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
    def is_on(self) -> bool | None:
        drift = self._drift_seconds
        return None if drift is None else abs(drift) >= _DRIFT_THRESHOLD_SECONDS

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        drift = self._drift_seconds
        return None if drift is None else {"drift_seconds": drift}

    @property
    def addresses(self) -> list[int]:
        return self._addresses

    @property
    def register_poll_type(self) -> RegisterPollType:
        # A clock drifts over weeks, so reading it with everything else only buys noise
        return RegisterPollType.SLOWLY
