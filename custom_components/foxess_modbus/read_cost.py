"""Works out what a read costs on a connection, by watching how long reads take"""

from dataclasses import dataclass

# A Modbus read can cover at most 125 registers, so bridging further than that is never possible
MAX_MODBUS_READ = 125

# How much of the history to keep, as the weight the newest sample leaves the ones before it. 0.995
# leaves an effective window of a couple of hundred reads, long enough to be steady and short enough
# to follow a link whose speed changes
_DECAY = 0.995

# Enough samples, and enough spread of read sizes among them, to tell the two costs apart. Reads which
# are all the same size say nothing about which part of the cost is which
_MIN_SAMPLES = 20.0
_MIN_SIZE_VARIANCE = 4.0

# A sample this much worse than expected was something other than a plain read - a retry, or a
# reconnection - and says nothing about what a read costs
_OUTLIER_FACTOR = 3.0


@dataclass(frozen=True)
class ReadCost:
    """What one read costs: a part which doesn't depend on its size, and a part for each register"""

    fixed_seconds: float
    per_register_seconds: float

    @property
    def worthwhile_bridge(self) -> int:
        """How many unwanted registers are worth reading in order to save a whole round trip.

        Reading registers nobody asked for costs time on the wire, and saves the fixed cost of a
        second read. Bridging pays while the registers in the gap cost less than that fixed part.
        """
        if self.per_register_seconds <= 0:
            # Registers are free, which is close to true on a socket: bridge as far as allowed
            return MAX_MODBUS_READ
        return min(int(self.fixed_seconds / self.per_register_seconds), MAX_MODBUS_READ)


class ReadCostEstimator:
    """Learns what a read costs on this connection.

    Whether to read across the gap between two registers we want is a trade: the registers in
    between cost time on the wire, and save the cost of a second round trip. Which way it goes
    depends entirely on the link. A 9600 baud serial line spends about 2ms on a register, so only a
    small gap is worth crossing; a socket spends so little that crossing almost any gap wins. Since
    the difference is this large, and a gateway doesn't say what speed its serial side runs at, the
    numbers are measured rather than assumed.

    This fits `duration = fixed + per_register * count` by least squares over recent reads, with
    older ones decaying away.
    """

    def __init__(self) -> None:
        self._weight = 0.0
        self._sum_x = 0.0
        self._sum_y = 0.0
        self._sum_xx = 0.0
        self._sum_xy = 0.0
        self._cost: ReadCost | None = None

    @property
    def cost(self) -> ReadCost | None:
        """What a read costs, or None until enough varied reads have been seen to tell"""
        return self._cost

    def record(self, num_registers: int, seconds: float) -> None:
        """Add a read which completed normally"""
        if num_registers <= 0 or seconds <= 0:
            return

        # A read which took far longer than the fit expects was something other than a plain read
        if self._cost is not None:
            expected = self._cost.fixed_seconds + self._cost.per_register_seconds * num_registers
            if expected > 0 and seconds > expected * _OUTLIER_FACTOR:
                return

        self._weight = self._weight * _DECAY + 1.0
        self._sum_x = self._sum_x * _DECAY + num_registers
        self._sum_y = self._sum_y * _DECAY + seconds
        self._sum_xx = self._sum_xx * _DECAY + num_registers * num_registers
        self._sum_xy = self._sum_xy * _DECAY + num_registers * seconds

        self._cost = self._fit()

    def _fit(self) -> ReadCost | None:
        if self._weight < _MIN_SAMPLES:
            return None

        mean_x = self._sum_x / self._weight
        # The spread of read sizes. Without it the line through them isn't pinned down, and the two
        # costs can't be told apart
        variance = self._sum_xx / self._weight - mean_x * mean_x
        if variance < _MIN_SIZE_VARIANCE:
            return None

        covariance = self._sum_xy / self._weight - mean_x * (self._sum_y / self._weight)
        per_register = covariance / variance
        fixed = self._sum_y / self._weight - per_register * mean_x

        # Noise can put either part slightly below zero, which means too small to measure, not negative
        return ReadCost(fixed_seconds=max(fixed, 0.0), per_register_seconds=max(per_register, 0.0))
