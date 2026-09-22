"""Defines RegisterType"""  # noqa: A005

from enum import Enum
from enum import Flag
from enum import IntEnum
from enum import StrEnum
from typing import TYPE_CHECKING
from typing import Callable
from typing import NotRequired
from typing import TypeAlias
from typing import TypedDict

if TYPE_CHECKING:
    from ..client.modbus_client import ModbusClient
    from ..modbus_controller import ModbusController


class RegisterType(Enum):
    """The different register types exposed by inverters"""

    INPUT = 1
    HOLDING = 2


class ConnectionType(StrEnum):
    # NOTE: Values match those stored in config
    AUX = "AUX"
    LAN = "LAN"


class InverterModel(StrEnum):
    """
    Inverter models are detected during auto-connection (during the config flow) and stored in config
    as config[INVERTER_BASE].
    """

    H1_G1 = "H1"  # Can't change the value, as it's set in people's configs
    H1_G2 = "H1_G2"

    P1 = "P1"

    AC1 = "AC1"
    AC1_G2 = "AC1_G2"
    AIO_H1 = "AIO-H1"
    AIO_AC1 = "AIO-AC1"

    KH = "KH"

    H3 = "H3"
    AC3 = "AC3"
    AIO_H3 = "AIO-H3"
    KUARA_H3 = "KUARA-H3"
    SK_HWR = "SK-HWR"
    SK_HWR_SMART = "SK-HWR-SMART"
    STAR_H3 = "STAR-H3"
    SOLAVITA_SP = "SOLAVITA-SP"
    ATRONIX_AX = "ATRONIX_AX"
    ENPAL_IX = "ENPAL_IX"
    ONE_KOMMA_FIVE = "1KOMMA5"

    H3_PRO = "H3_PRO"
    H3_SMART = "H3_SMART"

    P3_SMART = "P3_SMART"
    EVO = "EVO"


class _BitAllocator:
    """
    Drop-in replacement for auto() which returns actual ints, allowing | composition during Flag class body
    execution.

    Each instance maintains its own counter, so multiple Flag classes are fully isolated.
    """

    def __init__(self) -> None:
        self._n = -1

    def __call__(self) -> int:
        self._n += 1
        return 1 << self._n

    def __repr__(self) -> str:
        return f"_BitAllocator(next={self._n + 1})"


class Inv(Flag):
    """
    An InverterModel and connection type (and, maybe in the future, things like manager version) are together mapped to
    an Inv, in inverter_profiles. This Inv is then used as a key in entity_descriptions to identify the register
    address(es) and register type (Input, Holding) to use
    """

    _ignore_ = ["_b"]  # noqa: RUF012
    _b = _BitAllocator()

    H1_LAN = _b()
    H1_G1 = _b()
    H1_G2_PRE144 = _b()
    H1_G2_144 = _b()
    H1_G2_SET = H1_G2_PRE144 | H1_G2_144

    KH_PRE119 = _b()
    KH_PRE133 = _b()
    KH_133 = _b()
    KH_SET = KH_PRE119 | KH_PRE133 | KH_133

    H3_PRE180 = _b()
    H3_180 = _b()
    H3_193 = _b()
    AIO_H3_PRE101 = _b()
    AIO_H3_101 = _b()
    KUARA_H3 = _b()
    H3_SET = H3_PRE180 | H3_180 | H3_193 | AIO_H3_PRE101 | AIO_H3_101 | KUARA_H3

    H3_PRO_PRE122 = _b()
    H3_PRO_122 = _b()
    # H3 >= 1.93 speaks the Pro register map, so it's a member here and inherits every Pro register. The
    # few registers which differ keep an explicit Inv.H3_193 spec, which wins on specificity
    H3_PRO_SET = H3_PRO_PRE122 | H3_PRO_122 | H3_193
    # ...but it's still H3 hardware, with two PV strings and one battery. Registers describing hardware only
    # a real H3 Pro has (PV3+, the second and third BMS banks) use this instead
    H3_PRO_HW = H3_PRO_SET & ~H3_193

    H3_SMART = _b()

    EVO = _b()

    ALL = H1_LAN | H1_G1 | H1_G2_SET | KH_SET | H3_SET | H3_PRO_SET | H3_SMART | EVO


class RegisterPollType(IntEnum):
    """Describes when a register should be polled"""

    # These must be ordered from least frequent to most frequent
    ON_CONNECTION = 0
    # For things which drift rather than change: a battery's full-charge energy, the limits its BMS is
    # asking for. Reading them once per connection would leave them stale for as long as the connection
    # lasts, and every poll spends a read on something which moves over months
    SLOWLY = 1
    PERIODICALLY = 2


class HassDataEntry(TypedDict):
    controllers: list["ModbusController"]
    modbus_clients: list["ModbusClient"]
    unload: NotRequired[Callable[[], None]]


HassData: TypeAlias = dict[str, HassDataEntry]
