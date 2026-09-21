"""Sensor which reads an ASCII string spread over a run of registers"""

from dataclasses import dataclass
from typing import Any

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
from .inverter_model_spec import ModbusAddressesSpec
from .modbus_entity_mixin import ModbusEntityMixin


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusStringSensorDescription(SensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusStringSensor.

    Serial numbers and the like are ASCII spread over consecutive registers. Fox uses both encodings:
    one character per register (the 300xx identity block) and two, high byte first (the BMS and dongle
    serials), so which one applies has to be stated.
    """

    addresses: list[ModbusAddressesSpec]
    chars_per_register: int = 1

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
        return ModbusStringSensor(controller, self, addresses) if addresses is not None else None

    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        addresses = self._addresses_for_inverter_model(self.addresses, inverter_model, register_type)
        if addresses is None:
            return None

        return {
            "type": "sensor",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
            "chars_per_register": self.chars_per_register,
        }


class ModbusStringSensor(ModbusEntityMixin, SensorEntity):
    """Sensor which decodes a run of registers as ASCII"""

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusStringSensorDescription,
        addresses: list[int],
    ) -> None:
        self._controller = controller
        self.entity_description = entity_description
        self._addresses = addresses
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> str | None:
        two_chars = self.entity_description.chars_per_register == 2  # type: ignore[attr-defined]
        chars: list[str] = []
        for address in self._addresses:
            value = self._controller.read(address, signed=False)
            if value is None:
                return None
            candidates = ((value >> 8) & 0xFF, value & 0xFF) if two_chars else (value & 0xFF,)
            for char in candidates:
                if char == 0:  # NUL terminates, and pads a string of odd length
                    continue
                if not 0x20 <= char <= 0x7E:
                    return None
                chars.append(chr(char))
        result = "".join(chars).strip()
        return result if result else None

    @property
    def addresses(self) -> list[int]:
        return self._addresses

    @property
    def register_poll_type(self) -> RegisterPollType:
        # These never change while the inverter is running, so there's no point polling them
        return RegisterPollType.ON_CONNECTION
