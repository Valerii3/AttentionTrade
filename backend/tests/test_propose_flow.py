"""Tests for propose event flow (initial check rejection, period)."""
import sys
import os
from unittest.mock import AsyncMock, patch

import pytest

# Project root on path
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from fastapi.testclient import TestClient
    from backend.src.main import app
except ImportError as e:
    pytest.skip(
        f"Backend dependencies not installed (e.g. aiosqlite). Run: pip install -r backend/requirements.txt. {e!s}",
        allow_module_level=True,
    )

client = TestClient(app)


def test_propose_event_invalid_period_returns_400():
    """Invalid period returns 400."""
    r = client.post(
        "/events",
        json={"name": "Test", "period": "2d"},
    )
    assert r.status_code == 400


def test_propose_event_missing_name_returns_400():
    """Missing or empty name returns 400."""
    r = client.post(
        "/events",
        json={"name": "", "period": "1h"},
    )
    assert r.status_code == 400


def test_propose_event_initial_check_rejection_returns_rejected():
    """When initial reasonability check fails (e.g. 'some mess'), event is rejected."""
    with patch("agent.propose_agent.initial_reasonability_check") as mock_check:
        mock_check.return_value = {"pass": False, "reason": "No relevant results; input appears to be nonsense."}
        r = client.post(
            "/events",
            json={"name": "some mess", "period": "1h"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert data["name"] == "some mess"


def test_propose_event_valid_period_1h():
    """Valid period 1h is accepted in body."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok"}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["test"],
                "exclusions": [],
                "window_minutes": 60,
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = (100.0, {"Hacker News": 0.0, "Reddit": 0.0})
                with patch("agent.propose_agent.should_accept_event", return_value={"accept": True, "reason": "ok"}):
                    r = client.post(
                        "/events",
                        json={"name": "Cursor Hackathon", "period": "1h"},
                    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"
    assert data["name"] == "Cursor Hackathon"
