from unittest.mock import patch

from mcp_kb import server, local_store


def test_cloud_configured_false(no_cloud):
    assert server._cloud_configured() is False


def test_cloud_configured_true():
    import mcp_kb.config as cfg
    cfg.GATEWAY_URL = "https://gw"
    cfg.CLIENT_ID = "cid"
    cfg.CLIENT_SECRET = "csec"
    cfg.TOKEN_URL = "https://tok"
    assert server._cloud_configured() is True


def test_add_lesson_local_only(chroma_dir, no_cloud):
    import mcp_kb.config as cfg
    cfg.CHROMA_DIR = chroma_dir
    result = server.add_lesson("test", "problem", "resolution")
    assert result["id"]
    assert result["topic"] == "test"
    assert "cloud_synced" not in result


def test_add_lesson_cloud_sync(chroma_dir):
    import mcp_kb.config as cfg
    cfg.CHROMA_DIR = chroma_dir
    cfg.GATEWAY_URL = "https://gw"
    cfg.CLIENT_ID = "cid"
    cfg.CLIENT_SECRET = "csec"
    cfg.TOKEN_URL = "https://tok"
    with patch("mcp_kb.cloud_client.write_lesson", return_value={"id": "x"}):
        result = server.add_lesson("test", "problem", "resolution")
        assert result["cloud_synced"] is True


def test_add_lesson_cloud_failure(chroma_dir):
    import mcp_kb.config as cfg
    cfg.CHROMA_DIR = chroma_dir
    cfg.GATEWAY_URL = "https://gw"
    cfg.CLIENT_ID = "cid"
    cfg.CLIENT_SECRET = "csec"
    cfg.TOKEN_URL = "https://tok"
    with patch("mcp_kb.cloud_client.write_lesson", side_effect=RuntimeError("fail")):
        result = server.add_lesson("test", "problem", "resolution")
        assert result["cloud_synced"] is False
        assert "fail" in result["cloud_error"]


def test_search_lessons_empty(chroma_dir, no_cloud):
    import mcp_kb.config as cfg
    cfg.CHROMA_DIR = chroma_dir
    result = server.search_lessons("anything")
    assert result["count"] == 0


def test_search_lessons_with_results(chroma_dir, no_cloud):
    import mcp_kb.config as cfg
    cfg.CHROMA_DIR = chroma_dir
    local_store.add(chroma_dir, "docker", "container crash", "restart daemon")

    with patch("mcp_kb.server._filter_relevant", side_effect=lambda q, r: r):
        result = server.search_lessons("docker container")
        assert result["count"] >= 1
        assert result["results"][0]["topic"] == "docker"


def test_sync_no_cloud(no_cloud):
    result = server.sync()
    assert "error" in result


def test_filter_relevant_high_scores():
    results = [{"topic": "a", "problem": "b", "score": 0.8}]
    filtered = server._filter_relevant("query", results)
    assert len(filtered) == 1


def test_summarize_mocked():
    with patch("mcp_kb.server._llm_call", return_value="Summary text"):
        result = server._summarize("query", [{"topic": "t", "problem": "p", "resolution": "r"}])
        assert result == "Summary text"
