"""Tests for initial reasonability check (Gemini + Google Search–style tool)."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

# Project root on path (run from project root: pytest backend/tests)
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from agent.propose_agent import initial_reasonability_check


def test_initial_reasonability_check_no_api_key_passes():
    """When GEMINI_API_KEY is not set, check passes (skip)."""
    env_orig = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ.pop("GEMINI_API_KEY", None)
        result = initial_reasonability_check("anything", None, None, lambda q: "")
        assert result["pass"] is True
        assert "reason" in result
    finally:
        if env_orig is not None:
            os.environ["GEMINI_API_KEY"] = env_orig


def test_initial_reasonability_check_mess_with_empty_search_rejects():
    """When input is nonsense and search returns no results, Gemini rejects (mock)."""
    mock_response_query = MagicMock()
    mock_response_query.text = "asdfkj random gibberish xyz"
    mock_response_judge = MagicMock()
    mock_response_judge.text = json.dumps({"pass": False, "reason": "No relevant results; input appears to be nonsense."})

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [mock_response_query, mock_response_judge]
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    env_orig = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = "test-key"
        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            search_results: list[str] = []

            def capture_search(q: str) -> str:
                search_results.append(q)
                return ""

            result = initial_reasonability_check("some mess", None, None, capture_search)
    finally:
        if env_orig is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = env_orig

    assert result["pass"] is False
    assert "reason" in result and len(result["reason"]) > 0
    assert "nonsense" in result["reason"].lower() or "no" in result["reason"].lower() or "reject" in result["reason"].lower()


def test_initial_reasonability_check_with_similar_results_passes():
    """When search returns relevant results, Gemini can pass (mock)."""
    mock_response_query = MagicMock()
    mock_response_query.text = "Cursor Hackathon 2024"
    mock_response_judge = MagicMock()
    mock_response_judge.text = json.dumps({"pass": True, "reason": "Found relevant discussion of Cursor Hackathon."})

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [mock_response_query, mock_response_judge]
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client
    mock_google = MagicMock()
    mock_google.genai = mock_genai

    env_orig = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = "test-key"
        with patch.dict(sys.modules, {"google": mock_google, "google.genai": mock_genai}):
            result = initial_reasonability_check(
                "Cursor Hackathon Dec 24",
                None,
                None,
                lambda q: "Cursor Hackathon 2024 announced...",
            )
    finally:
        if env_orig is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = env_orig

    assert result["pass"] is True
    assert "reason" in result
