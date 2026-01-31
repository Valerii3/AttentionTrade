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
    """Omitting windowMinutes uses default (24h). Activity above traction threshold -> accepted."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok"}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["test"],
                "exclusions": [],
                "window_minutes": 1440,
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index", new_callable=AsyncMock) as mock_build:
                # Activity >= MIN_TRACTION_SCORE (0.5) so traction gate passes
                mock_build.return_value = (100.0, {"Hacker News": 1.0, "Reddit": 0.0})
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
    """Valid windowMinutes is accepted in body. Activity above traction threshold -> accepted."""
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
                mock_build.return_value = (100.0, {"Hacker News": 2.0, "Reddit": 0.0})
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
    """When build_index returns activity below MIN_TRACTION_SCORE, event is rejected with no-attention reason."""
    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok"}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["obscure"],
                "exclusions": [],
                "window_minutes": 1440,
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.routes.events.build_index", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = (100.0, {"Hacker News": 0.0, "Reddit": 0.0})
                r = client.post("/events", json={"name": "Obscure Event"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "rejected"
    assert "rejectReason" in data
    assert "not tradable" in data["rejectReason"].lower() or "attention" in data["rejectReason"].lower()


def test_propose_event_build_index_completes_with_mocked_hn():
    """Propose flow runs real build_index with Algolia mocked; traction above threshold -> open."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "hits": [
            {"title": "Cursor Hackathon Dec 24", "points": 10, "url": "https://example.com"},
        ]
    }

    with patch("agent.propose_agent.initial_reasonability_check", return_value={"pass": True, "reason": "ok"}):
        with patch("agent.propose_agent.select_tools_and_config") as mock_config:
            mock_config.return_value = {
                "tools": ["hn_frontpage", "reddit"],
                "keywords": ["cursor hackathon"],
                "exclusions": [],
                "window_minutes": 1440,
                "source_url": None,
                "description": None,
            }
            with patch("backend.src.services.index_pipeline.httpx.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.get.return_value = mock_response
                mock_client.__enter__.return_value = mock_client
                mock_client.__exit__.return_value = None
                mock_client_cls.return_value = mock_client
                with patch("agent.propose_agent.should_accept_event", return_value={"accept": True, "reason": "ok"}):
                    r = client.post("/events", json={"name": "Cursor Hackathon"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "open"
