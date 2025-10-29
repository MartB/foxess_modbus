"""Select"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, cast, List

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import Platform
from homeassistant.helpers.entity import Entity

from ..common.entity_controller import EntityController
from ..common.types import Inv, RegisterType
from .base_validator import BaseValidator
from .entity_factory import ENTITY_DESCRIPTION_KWARGS, EntityFactory
from .inverter_model_spec import ModbusAddressSpec
from .modbus_entity_mixin import ModbusEntityMixin

_LOGGER: logging.Logger = logging.getLogger(__package__)


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusNumberDescription(NumberEntityDescription, EntityFactory):  # type: ignore[misc]
    """Custom number entity description"""

    address: list[ModbusAddressSpec]
    mode: NumberMode = NumberMode.AUTO
    scale: float | None = None
    post_process: Callable[[float], float] | None = None
    validate: list[BaseValidator] = field(default_factory=list)

    @property
    def entity_type(self) -> type[Entity]:
        return NumberEntity

    def create_entity_if_supported(
        self,
        controller: EntityController,
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> Entity | None:
        addresses = self._addresses_for_inverter_model(self.address, inverter_model, register_type)
        if addresses is None:
            return None
        return ModbusNumber(controller, self, addresses)

    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        addresses = self._addresses_for_inverter_model(self.address, inverter_model, register_type)
        if addresses is None:
            return None

        return {
            "type": "number",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
            "scale": self.scale,
        }


class ModbusNumber(ModbusEntityMixin, NumberEntity):
    """Number class supporting single or multiple Modbus registers (little-endian)."""

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusNumberDescription,
        addresses: int | List[int],
    ) -> None:
        """Initialize the sensor."""
        self._controller = controller
        self.entity_description = entity_description
        self._addresses = [addresses] if isinstance(addresses, int) else list(addresses)
        self.entity_id = self._get_entity_id(Platform.NUMBER)

    @property
    def native_value(self) -> int | float | None:
        desc = cast(ModbusNumberDescription, self.entity_description)

        # Read value(s)
        values = self._controller.read(self._addresses, signed=False)
        if values is None:
            return None

        # Normalize to list
        if isinstance(values, int):
            values = [values]

        # Combine little-endian
        value = sum((v & 0xFFFF) << (16 * i) for i, v in enumerate(values))
        original = value

        # Apply scale and post-processing
        if desc.scale is not None:
            value *= desc.scale
        if desc.post_process is not None:
            value = desc.post_process(float(value))

        if not self._validate(desc.validate, value, original):
            return None

        return value

    @property
    def mode(self) -> NumberMode:
        return cast(ModbusNumberDescription, self.entity_description).mode

    async def async_set_native_value(self, value: float) -> None:
        desc = cast(ModbusNumberDescription, self.entity_description)

        # Clamp to min/max
        if desc.native_min_value is not None and desc.native_max_value is not None:
            value = max(desc.native_min_value, min(desc.native_max_value, value))

        # Apply inverse scale
        if desc.scale is not None:
            value = value / desc.scale

        int_value = int(round(value))

        # Write single or multiple registers (little-endian)
        if len(self._addresses) == 1:
            await self._controller.write_register(self._addresses[0], int_value)
        else:
            # Split into 16-bit words little-endian
            words = [(int_value >> (16 * i)) & 0xFFFF for i in range(len(self._addresses))]
            await self._controller.write_registers(self._addresses[0], words)

    @property
    def addresses(self) -> list[int]:
        return self._addresses
