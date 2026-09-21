"""Sub-devices which hang off the inverter in Home Assistant's device registry.

Everything used to sit on a single "FoxESS - Modbus" device, which put the battery's own readings next to
the inverter's. A battery stack is a separate piece of hardware with its own BMS, firmware and serial
number, so it gets its own device.

An entity is assigned to a sub-device by key, which is what Home Assistant derives its unique id from and
so is already the stable identifier for an entity. Entities without an assignment stay on the inverter.
"""

from dataclasses import dataclass
from typing import Iterable
from typing import Iterator
from typing import TypeVar

# Entity descriptions, which all carry a key, but which don't share a base class that declares one
_T = TypeVar("_T")


@dataclass(frozen=True)
class SubDevice:
    """A device which appears underneath the inverter in the device registry.

    `path` is appended to the inverter's own identifier to give this device a stable identity, so renaming
    one doesn't orphan it and its history.
    """

    path: tuple[str, ...]
    name: str
    parent: "SubDevice | None" = None


# The battery as the inverter sees it. Inverters which report each BMS separately (Pro hardware, Smart)
# get one device per BMS as well. The modules within a stack don't: they report nothing but a serial
# number, which sits on the battery they belong to.
BATTERY = SubDevice(path=("battery",), name="Battery")
BMS = {index: SubDevice(path=("bms", str(index)), name=f"Battery {index}") for index in (1, 2)}


_DEVICES: dict[str, SubDevice] = {}


def assign_device(key: str, device: SubDevice) -> None:
    """Put the entity with the given key on the given sub-device"""
    _DEVICES[key] = device


def on_device(device: SubDevice, descriptions: Iterable[_T]) -> Iterator[_T]:
    """Put every entity description which passes through here on the given sub-device"""
    for description in descriptions:
        assign_device(getattr(description, "key"), device)  # noqa: B009
        yield description


def device_for_key(key: str) -> SubDevice | None:
    """The sub-device the entity with the given key belongs to, or None if it belongs to the inverter"""
    return _DEVICES.get(key)
