import os
from pathlib import Path

GATEWAY_URL = os.environ.get("MCP_KB_GATEWAY_URL", "")
CLIENT_ID = os.environ.get("MCP_KB_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("MCP_KB_CLIENT_SECRET", "")
TOKEN_URL = os.environ.get("MCP_KB_TOKEN_URL", "")
CHROMA_DIR = os.environ.get("MCP_KB_CHROMA_DIR", str(Path.home() / ".mcp-kb" / "chroma"))
BEDROCK_REGION = os.environ.get("MCP_KB_BEDROCK_REGION", "us-west-2")
SUMMARY_MODELS = [
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0",  # global inference, newest
    "us.amazon.nova-pro-v1:0",                        # Amazon fallback
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",    # cheap fallback
]
