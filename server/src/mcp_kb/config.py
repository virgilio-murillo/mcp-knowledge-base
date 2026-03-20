import os
from pathlib import Path

GATEWAY_URL = os.environ.get("MCP_KB_GATEWAY_URL", "")
CLIENT_ID = os.environ.get("MCP_KB_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MCP_KB_CLIENT_SECRET", "")
TOKEN_URL = os.environ.get("MCP_KB_TOKEN_URL", "")
CHROMA_DIR = os.environ.get("MCP_KB_CHROMA_DIR", str(Path.home() / ".mcp-kb" / "chroma"))
