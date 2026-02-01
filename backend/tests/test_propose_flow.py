"""Tests for propose event flow (initial check rejection, traction gate, period)."""
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

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


def test_propose_event_without_window_uses_default():
    """Omitting windowMinutes uses default (1h). Agent says build index -> index build runs -> accepted."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok", "should_build_index": True}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["test"],
                "exclusions": [],
                "window_minutes": 60,
                "market_type": "1h",
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index_via_gemini", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = (100.0, {"Gemini (6mo)": 100.0})
                with patch("agent.propose_agent.should_accept_event", return_value={"accept": True, "reason": "ok"}):
                    r = client.post("/events", json={"name": "Test"})
    assert r.status_code == 201
    assert r.json()["status"] == "open"


def test_propose_event_missing_name_returns_400():
    """Missing or empty name returns 400."""
    r = client.post(
        "/events",
        json={"name": ""},
    )
    assert r.status_code == 400


def test_propose_event_initial_check_rejection_returns_rejected():
    """When initial reasonability check fails (e.g. 'some mess'), event is rejected and not stored."""
    with patch("agent.propose_agent.initial_reasonability_check") as mock_check:
        mock_check.return_value = {"pass": False, "reason": "No relevant results; input appears to be nonsense."}
        r = client.post(
            "/events",
            json={"name": "some mess"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert data["name"] == "some mess"
    assert "rejectReason" in data


def test_propose_event_valid_window_accepted():
    """Valid marketType/window is accepted. Agent says build index -> index build runs -> accepted."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok", "should_build_index": True}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["test"],
                "exclusions": [],
                "window_minutes": 60,
                "market_type": "1h",
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index_via_gemini", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = (100.0, {"Gemini (6mo)": 100.0})
                with patch("agent.propose_agent.should_accept_event", return_value={"accept": True, "reason": "ok"}):
                    r = client.post(
                        "/events",
                        json={"name": "Cursor Hackathon"},
                    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"
    assert data["name"] == "Cursor Hackathon"


def test_propose_event_no_traction_rejected():
    """When agent returns should_build_index false, event is rejected without running index build (no HN fetch)."""
    with patch("agent.propose_agent.initial_reasonability_check") as mock_check:
        mock_check.return_value = {
            "pass": True,
            "reason": "Not enough traction to build the index yet.",
            "should_build_index": False,
        }
        with patch("backend.src.routes.events.build_index_via_gemini", new_callable=AsyncMock) as mock_build:
            r = client.post("/events", json={"name": "Obscure Event"})
            mock_build.assert_not_called()
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert "rejectReason" in data


def test_propose_event_build_index_completes_with_mocked_gemini():
    """Propose flow runs build_index_via_gemini (mocked) when agent says should_build_index -> open."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok", "should_build_index": True}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["cursor hackathon"],
                "exclusions": [],
                "window_minutes": 60,
                "market_type": "1h",
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index_via_gemini", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = (100.0, {"Gemini (6mo)": 100.0})
                with patch("agent.propose_agent.should_accept_event", return_value={"accept": True, "reason": "ok"}):
                    r = client.post("/events", json={"name": "Cursor Hackathon"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"


def test_propose_event_outcome_style_rejected():
    """Outcome-style name (e.g. '100 stars by Friday') is rejected with suggestion."""
    r = client.post(
        "/events",
        json={"name": "Will this repo get 100 GitHub stars by Friday?"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert "rejectReason" in data
    assert "outcome" in data["rejectReason"].lower() or "attention" in data["rejectReason"].lower()


def test_propose_event_demo_accepted():
    """Demo event is accepted without reasonability/traction; 2-min window, synthetic index."""
    r = client.post(
        "/events",
        json={"name": "Any Demo Topic", "demo": True},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"
    assert data["demo"] is True
    assert data["name"] == "Any Demo Topic"
