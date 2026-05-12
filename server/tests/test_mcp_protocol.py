"""MCP protocol compliance tests — starts the server over stdio and validates JSON-RPC 2.0."""
import json
import subprocess
import sys
import os
import time

import pytest

pytestmark = pytest.mark.integration


def _send(proc, request: dict):
    """Send a JSON-RPC request as newline-delimited JSON."""
    proc.stdin.write(json.dumps(request) + "\n")
    proc.stdin.flush()


def _recv(proc, timeout=10) -> dict:
    """Read a JSON-RPC response, skipping notifications."""
    import select

    deadline = time.time() + timeout
    while time.time() < deadline:
        remaining = deadline - time.time()
        ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.5))
        if not ready:
            continue
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Server closed stdout")
        data = json.loads(line)
        if "id" in data:
            return data
    raise TimeoutError("No response within timeout")


def _init(proc):
    """Perform MCP initialize handshake."""
    _send(proc, {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "test", "version": "0.1"}},
    })
    resp = _recv(proc)
    _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    return resp


@pytest.fixture
def mcp_server(tmp_path):
    """Start the MCP server as a subprocess."""
    env = os.environ.copy()
    env["MCP_KB_CHROMA_DIR"] = str(tmp_path / "chroma")
    env["MCP_KB_GATEWAY_URL"] = ""
    env["MCP_KB_CLIENT_ID"] = ""
    env["MCP_KB_CLIENT_SECRET"] = ""
    env["MCP_KB_TOKEN_URL"] = ""

    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_kb"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env,
        cwd=os.path.dirname(os.path.dirname(__file__)),
    )
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_initialize(mcp_server):
    resp = _init(mcp_server)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "serverInfo" in resp["result"]


def test_tools_list(mcp_server):
    _init(mcp_server)
    _send(mcp_server, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    resp = _recv(mcp_server)
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {"add_lesson", "search_lessons", "sync"}


def test_tools_call_add_and_search(mcp_server):
    _init(mcp_server)

    _send(mcp_server, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
          "params": {"name": "add_lesson", "arguments": {"topic": "test", "problem": "p", "resolution": "r"}}})
    resp = _recv(mcp_server)
    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["topic"] == "test"

    _send(mcp_server, {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
          "params": {"name": "search_lessons", "arguments": {"query": "test"}}})
    resp = _recv(mcp_server)
    assert "result" in resp
