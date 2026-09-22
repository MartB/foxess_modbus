from dataclasses import dataclass
from enum import StrEnum
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
from .inverter_model_spec import ModbusAddressesSpec
from .inverter_model_spec import ModbusAddressSpec
from .modbus_entity_mixin import ModbusEntityMixin


class VersionFormat(StrEnum):
    """How the bytes of a version register are laid out"""

    # The whole word is decimal: 223 is 2.23
    DECIMAL = "decimal"
    # A byte each, rendered as hex: 0x0214 is 2.14
    HEX = "hex"
    # A byte each, rendered as decimal: 0x0214 is the 2.020 the app shows for a BMS master, and 0x010D
    # the 1.013 it shows for another
    DECIMAL_BYTES = "decimal_bytes"


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusVersionSensorDescription(SensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusVersionSensor"""

    address: list[ModbusAddressSpec]
    version_format: VersionFormat

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
        return ModbusVersionSensor(controller, self, address) if address is not None else None

    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        addresses = self._addresses_for_inverter_model(self.address, inverter_model, register_type)
        if addresses is None:
            return None

        return {
            "type": "sensor",
            "key": self.key,
            "name": self.name,
            "addresses": addresses,
            "version_format": self.version_format,
        }


class ModbusVersionSensor(ModbusEntityMixin, SensorEntity):
    """Sensor class."""

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusVersionSensorDescription,
        address: int,
    ) -> None:
        self._controller = controller
        self.entity_description = entity_description
        self._address = address
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> str | None:
        entity_description = cast(ModbusVersionSensorDescription, self.entity_description)
        value = self._controller.read(self._address, signed=False)
        if value is None:
            return None

        if entity_description.version_format == VersionFormat.HEX:
            return f"{value >> 8:X}.{value & 0xFF:02X}"

        if entity_description.version_format == VersionFormat.DECIMAL_BYTES:
            return f"{value >> 8}.{value & 0xFF:03d}"

        return f"{value // 100}.{value % 100:02}"

    @property
    def addresses(self) -> list[int]:
        return [self._address]

    @property
    def register_poll_type(self) -> RegisterPollType:
        # Firmware does change, just not often, and a connection can outlive an update by weeks
        return RegisterPollType.SLOWLY


@dataclass(kw_only=True, **ENTITY_DESCRIPTION_KWARGS)
class ModbusProtocolVersionSensorDescription(SensorEntityDescription, EntityFactory):  # type: ignore[misc]
    """Description for ModbusProtocolVersionSensor"""

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
        return ModbusProtocolVersionSensor(controller, self, addresses) if addresses is not None else None

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


class ModbusProtocolVersionSensor(ModbusEntityMixin, SensorEntity):
    """Exposes the inverter's 32-bit Fox modbus document version, e.g. V1.05.03.00

    The bytes are BCD-style, so they're rendered in hex, the same as VersionFormat.HEX above.
    """

    def __init__(
        self,
        controller: EntityController,
        entity_description: ModbusProtocolVersionSensorDescription,
        addresses: list[int],
    ) -> None:
        self._controller = controller
        self.entity_description = entity_description
        self._addresses = addresses
        self.entity_id = self._get_entity_id(Platform.SENSOR)

    @property
    def native_value(self) -> str | None:
        value = self._controller.read(self._addresses, signed=False)
        if value is None:
            return None

        b0, b1, b2, b3 = ((value >> shift) & 0xFF for shift in (24, 16, 8, 0))
        return f"V{b0:X}.{b1:02X}.{b2:02X}.{b3:02X}"

    @property
    def addresses(self) -> list[int]:
        return list(self._addresses)

    @property
    def register_poll_type(self) -> RegisterPollType:
        # Firmware does change, just not often, and a connection can outlive an update by weeks
        return RegisterPollType.SLOWLY
