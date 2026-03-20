import json
import time
import httpx

_token = None
_token_exp = 0


def _get_token(token_url: str, client_id: str, client_secret: str) -> str:
    global _token, _token_exp
    if _token and time.time() < _token_exp - 60:
        return _token
    resp = httpx.post(
        token_url,
        data={"grant_type": "client_credentials", "scope": "mcp-kb/tools"},
        auth=(client_id, client_secret),
    )
    resp.raise_for_status()
    data = resp.json()
    _token = data["access_token"]
    _token_exp = time.time() + data.get("expires_in", 3600)
    return _token


def _call_tool(gateway_url: str, token: str, tool_name: str, arguments: dict) -> dict:
    resp = httpx.post(
        gateway_url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if "error" in result:
        raise RuntimeError(result["error"]["message"])
    text = result["result"]["content"][0]["text"]
    inner = json.loads(text)
    return json.loads(inner["body"]) if isinstance(inner, dict) and "body" in inner else inner


def write_lesson(gateway_url: str, token_url: str, client_id: str, client_secret: str, **kwargs) -> dict:
    token = _get_token(token_url, client_id, client_secret)
    return _call_tool(gateway_url, token, "write-lesson___write_lesson", kwargs)


def search_lessons(gateway_url: str, token_url: str, client_id: str, client_secret: str, query: str, k: int = 5) -> list:
    token = _get_token(token_url, client_id, client_secret)
    return _call_tool(gateway_url, token, "search-lessons___search_lessons", {"query": query, "k": k}).get("results", [])


def sync_lessons(gateway_url: str, token_url: str, client_id: str, client_secret: str) -> list:
    token = _get_token(token_url, client_id, client_secret)
    return _call_tool(gateway_url, token, "sync-lessons___sync_lessons", {}).get("lessons", [])
