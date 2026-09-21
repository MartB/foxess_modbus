"""Entity Factory"""

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Sequence

from homeassistant.helpers.entity import Entity
from homeassistant.util.frozen_dataclass_compat import FrozenOrThawed

from ..common.entity_controller import EntityController
from ..common.types import Inv
from ..common.types import RegisterType
from .inverter_model_spec import InverterModelSpec


# HA introduced a FrozenOrThawed metaclass which is used by EntityDescription.
# This conflicts with ABC's metaclass.
# We need to combine EntityDescription's metaclass with ABC's metaclass, see
# https://github.com/nathanmarlor/foxess_modbus/issues/480. This is to allow HA to move to frozen entity descriptions
# (to aid caching), and will start logging deprecation warnings in 2024.x.
class EntityFactoryMetaclass(FrozenOrThawed, type(ABC)):  # type: ignore
    """
    Metaclass to use for EntityFactory.
    """


ENTITY_DESCRIPTION_KWARGS = {"frozen": True}


def _specificity(spec: InverterModelSpec) -> int:
    """Sort key: the fewer models a spec covers, the more specific it is.

    An Inv is cumulative, so a model can match both a broad family spec and a narrow "this version differs"
    one. Sorting by this means the narrowest wins.
    """
    return spec.models.value.bit_count()


class EntityFactory(ABC, metaclass=EntityFactoryMetaclass):  # type: ignore
    """Factory which can create entities"""

    @property
    @abstractmethod
    def entity_type(self) -> type[Entity]:
        """Fetch the type of entity that this factory creates"""

    @property
    def depends_on_other_entities(self) -> bool:
        """Return true if this entity depends on other entities, and so should be constructed last."""
        return False

    @abstractmethod
    def create_entity_if_supported(
        self,
        controller: EntityController,
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> Entity | None:
        """Instantiate a new entity. The returned type must match self.entity_type"""

    @abstractmethod
    def serialize(self, inverter_model: Inv, register_type: RegisterType) -> dict[str, Any] | None:
        """Serialize to a dict, used for snapshot testing."""

    def _match_specs(self) -> list[InverterModelSpec]:
        """The specs which decide whether this description applies, whatever the subclass calls them"""
        for attr in ("addresses", "address", "models", "period_start_address"):
            value = getattr(self, attr, None)
            if isinstance(value, (list, tuple)):
                specs = [x for x in value if isinstance(x, InverterModelSpec)]
                if specs:
                    return specs
        return []

    def match_score(self, inverter_model: Inv, register_type: RegisterType) -> tuple[int, int] | None:
        """How well this description fits the given model, or None if it doesn't apply at all.

        An Inv is cumulative, so a spec written for an older firmware still matches a newer one, and
        several descriptions can end up sharing a key. Rank by the most recent model bit a spec covers,
        then by how narrowly it's scoped, so the newest applicable description wins rather than whichever
        happens to be declared first.
        """
        best: tuple[int, int] | None = None
        for spec in self._match_specs():
            if spec.addresses_for_inverter_model(register_type=register_type, models=inverter_model) is None:
                continue
            score = ((inverter_model & spec.models).value.bit_length(), -spec.models.value.bit_count())
            if best is None or score > best:
                best = score
        return best

    def _supports_inverter_model(
        self,
        address_specs: Sequence[InverterModelSpec],
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> bool:
        """Helper to determine whether this entity description supports the given inverter model and register type"""

        return any(
            spec.addresses_for_inverter_model(register_type=register_type, models=inverter_model) is not None
            for spec in address_specs
        )

    def _address_for_inverter_model(
        self,
        address_specs: Sequence[InverterModelSpec],
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> int | None:
        """
        Helper to fetch single address of an entity, on this inverter model and connection type combination, given the
        set of InverterModelSpec which was given to the entity description. Returns None if this entity is not supported
        on the model/connection type combination.

        If more than one spec matches, the most specific one wins (see _specificity).
        """

        for spec in sorted(address_specs, key=_specificity):
            addresses = spec.addresses_for_inverter_model(register_type=register_type, models=inverter_model)
            if addresses and len(addresses) == 1:
                return addresses[0]

        return None

    def _addresses_for_inverter_model(
        self,
        address_specs: Sequence[InverterModelSpec],
        inverter_model: Inv,
        register_type: RegisterType,
    ) -> list[int] | None:
        """Helper to fetch the addresses of an entity, on this inverter and connection type combination, given the
        set of which was given to the entity description. Returns None if this entity is not supported
        on the model/connection type combination.

        If more than one spec matches, the most specific one wins (see _specificity).
        """

        for spec in sorted(address_specs, key=_specificity):
            addresses = spec.addresses_for_inverter_model(register_type=register_type, models=inverter_model)
            if addresses is not None:
                return addresses

        return None
