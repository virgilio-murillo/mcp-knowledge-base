import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset module-level singletons between tests."""
    import mcp_kb.local_store as ls
    import mcp_kb.cloud_client as cc

    ls._client = None
    ls._collection = None
    cc._token = None
    cc._token_exp = 0
    yield
    ls._client = None
    ls._collection = None
    cc._token = None
    cc._token_exp = 0


@pytest.fixture
def chroma_dir(tmp_path):
    """Provide a temporary ChromaDB directory."""
    return str(tmp_path / "chroma")


@pytest.fixture
def no_cloud():
    """Ensure cloud is not configured."""
    with patch.dict("os.environ", {}, clear=False):
        import mcp_kb.config as cfg
        orig = (cfg.GATEWAY_URL, cfg.CLIENT_ID, cfg.CLIENT_SECRET, cfg.TOKEN_URL)
        cfg.GATEWAY_URL = ""
        cfg.CLIENT_ID = ""
        cfg.CLIENT_SECRET = ""
        cfg.TOKEN_URL = ""
        yield
        cfg.GATEWAY_URL, cfg.CLIENT_ID, cfg.CLIENT_SECRET, cfg.TOKEN_URL = orig
