"""Tests for event period conversion (1h / 8h / 24h / 1w)."""
import pytest

from backend.src.constants import EVENT_PERIODS, period_to_minutes


def test_period_to_minutes_1h():
    assert period_to_minutes("1h") == 60


def test_period_to_minutes_8h():
    assert period_to_minutes("8h") == 480


def test_period_to_minutes_24h():
    assert period_to_minutes("24h") == 1440


def test_period_to_minutes_1w():
    assert period_to_minutes("1w") == 10080


def test_period_to_minutes_invalid_raises():
    with pytest.raises(ValueError, match="Invalid period"):
        period_to_minutes("2d")
    with pytest.raises(ValueError, match="Invalid period"):
        period_to_minutes("")


def test_event_periods_keys():
    assert set(EVENT_PERIODS.keys()) == {"1h", "8h", "24h", "1w"}
    assert EVENT_PERIODS["1h"] == 60
    assert EVENT_PERIODS["8h"] == 480
    assert EVENT_PERIODS["24h"] == 1440
    assert EVENT_PERIODS["1w"] == 10080
