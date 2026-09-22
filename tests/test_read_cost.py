"""Tests for working out what a read costs on a connection"""

import pytest

from custom_components.foxess_modbus.read_cost import MAX_MODBUS_READ
from custom_components.foxess_modbus.read_cost import ReadCost
from custom_components.foxess_modbus.read_cost import ReadCostEstimator

# Roughly what a 9600 baud serial line behind a gateway measures at
_FIXED = 0.0192
_PER_REGISTER = 0.00204

# A spread of read sizes, like a real poll produces
_SIZES = [1, 2, 4, 6, 10, 11, 12, 16, 18, 19, 20]


def _feed(estimator: ReadCostEstimator, count: int = 10) -> None:
    for _ in range(count):
        for size in _SIZES:
            estimator.record(size, _FIXED + _PER_REGISTER * size)


def test_says_nothing_until_it_has_seen_enough() -> None:
    estimator = ReadCostEstimator()
    assert estimator.cost is None

    for size in _SIZES:
        estimator.record(size, _FIXED + _PER_REGISTER * size)

    # 11 reads isn't enough to fit a line through with any confidence
    assert estimator.cost is None


def test_says_nothing_when_every_read_is_the_same_size() -> None:
    """Reads which are all one size can't say which part of the cost is which"""
    estimator = ReadCostEstimator()
    for _ in range(200):
        estimator.record(20, _FIXED + _PER_REGISTER * 20)

    assert estimator.cost is None


def test_recovers_the_two_costs() -> None:
    estimator = ReadCostEstimator()
    _feed(estimator)

    cost = estimator.cost
    assert cost is not None
    assert cost.fixed_seconds == pytest.approx(_FIXED, abs=1e-4)
    assert cost.per_register_seconds == pytest.approx(_PER_REGISTER, abs=1e-5)


def test_a_slow_line_is_only_worth_crossing_a_small_gap() -> None:
    estimator = ReadCostEstimator()
    _feed(estimator)

    cost = estimator.cost
    assert cost is not None
    # 19.2ms buys about nine registers at 2.04ms each
    assert cost.worthwhile_bridge == 9


def test_a_socket_is_worth_crossing_any_gap() -> None:
    """Registers cost so little on a socket that saving a round trip always wins"""
    estimator = ReadCostEstimator()
    for _ in range(10):
        for size in _SIZES:
            estimator.record(size, 0.002)

    cost = estimator.cost
    assert cost is not None
    assert cost.worthwhile_bridge == MAX_MODBUS_READ


def test_a_read_which_stalled_is_not_evidence() -> None:
    """A retry or a reconnection says nothing about what a plain read costs"""
    estimator = ReadCostEstimator()
    _feed(estimator)
    before = estimator.cost
    assert before is not None

    for _ in range(20):
        estimator.record(10, 5.0)

    after = estimator.cost
    assert after is not None
    assert after.fixed_seconds == pytest.approx(before.fixed_seconds, abs=1e-4)


def test_it_follows_a_link_which_changes() -> None:
    estimator = ReadCostEstimator()
    _feed(estimator)

    # The same link, now at twice the speed
    for _ in range(80):
        for size in _SIZES:
            estimator.record(size, _FIXED / 2 + (_PER_REGISTER / 2) * size)

    cost = estimator.cost
    assert cost is not None
    assert cost.per_register_seconds == pytest.approx(_PER_REGISTER / 2, abs=2e-5)


def test_nonsense_samples_are_ignored() -> None:
    estimator = ReadCostEstimator()
    _feed(estimator)
    before = estimator.cost

    estimator.record(0, 0.01)
    estimator.record(10, 0.0)
    estimator.record(-1, 0.01)

    assert estimator.cost == before


def test_free_registers_mean_any_gap_is_worth_crossing() -> None:
    assert ReadCost(fixed_seconds=0.02, per_register_seconds=0.0).worthwhile_bridge == MAX_MODBUS_READ


def test_a_bridge_is_never_longer_than_a_read_can_be() -> None:
    cost = ReadCost(fixed_seconds=10.0, per_register_seconds=0.000001)
    assert cost.worthwhile_bridge == MAX_MODBUS_READ
