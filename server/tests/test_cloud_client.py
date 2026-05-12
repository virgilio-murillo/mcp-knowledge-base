import json
import time
from unittest.mock import patch, MagicMock

from mcp_kb import cloud_client


def _mock_token_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 3600}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_get_token():
    with patch("mcp_kb.cloud_client.httpx.post", return_value=_mock_token_response()) as mock_post:
        token = cloud_client._get_token("https://token.url", "cid", "csec")
        assert token == "tok123"
        mock_post.assert_called_once()


def test_token_caching():
    cloud_client._token = "cached"
    cloud_client._token_exp = time.time() + 600
    token = cloud_client._get_token("https://token.url", "cid", "csec")
    assert token == "cached"


def _mock_tool_response(body):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "result": {"content": [{"text": json.dumps({"body": json.dumps(body)})}]}
    }
    return mock_resp


def test_write_lesson():
    cloud_client._token = "tok"
    cloud_client._token_exp = time.time() + 600
    with patch("mcp_kb.cloud_client.httpx.post", return_value=_mock_tool_response({"id": "x", "status": "stored"})):
        result = cloud_client.write_lesson("https://gw", "https://tok", "cid", "csec", topic="t", problem="p", resolution="r")
        assert result["id"] == "x"


def test_sync_lessons():
    cloud_client._token = "tok"
    cloud_client._token_exp = time.time() + 600
    lessons = [{"id": "1", "topic": "a", "problem": "b", "resolution": "c"}]
    with patch("mcp_kb.cloud_client.httpx.post", return_value=_mock_tool_response({"lessons": lessons})):
        result = cloud_client.sync_lessons("https://gw", "https://tok", "cid", "csec")
        assert len(result) == 1
        assert result[0]["id"] == "1"
