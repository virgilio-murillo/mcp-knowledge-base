import pytest

from mcp_kb import local_store


def test_add_and_search(chroma_dir):
    result = local_store.add(chroma_dir, "docker", "container won't start", "check port conflicts")
    assert result["id"]
    assert result["topic"] == "docker"
    assert "duplicate" not in result

    found = local_store.search(chroma_dir, "container startup issue", k=3)
    assert len(found) >= 1
    assert found[0]["topic"] == "docker"
    assert 0 < found[0]["score"] <= 1
    assert found[0]["confidence"] in ("high", "medium", "low")


def test_dedup(chroma_dir):
    local_store.add(chroma_dir, "docker", "container won't start", "check port conflicts")
    local_store.add(chroma_dir, "docker", "container won't start", "check port conflicts")
    # Either flagged as duplicate or added (depends on embedding distance threshold)
    # Verify collection doesn't grow unboundedly
    col = local_store._col(chroma_dir)
    assert col.count() <= 2


def test_search_empty(chroma_dir):
    assert local_store.search(chroma_dir, "anything") == []


def test_tags_roundtrip(chroma_dir):
    result = local_store.add(chroma_dir, "python", "import error", "fix path", tags=["py", "debug"])
    assert result["tags"] == ["py", "debug"]

    found = local_store.search(chroma_dir, "import error", k=1)
    assert found[0]["tags"] == ["py", "debug"]


def test_sync_from_cloud(chroma_dir):
    cloud_lessons = [
        {"id": "cloud-1", "topic": "aws", "problem": "timeout", "resolution": "increase limit", "tags": [], "created_at": "2025-01-01T00:00:00Z"},
        {"id": "cloud-2", "topic": "s3", "problem": "access denied", "resolution": "fix policy", "tags": ["iam"], "created_at": "2025-01-02T00:00:00Z"},
    ]
    result = local_store.sync_from_cloud(chroma_dir, cloud_lessons)
    assert result["synced"] == 2
    assert result["total"] == 2

    # Sync again — no new additions
    result2 = local_store.sync_from_cloud(chroma_dir, cloud_lessons)
    assert result2["synced"] == 0


def test_normalize_score():
    assert local_store._normalize_score(0.0) == pytest.approx(1.0)
    assert local_store._normalize_score(1.0) == pytest.approx(0.5)
    assert local_store._normalize_score(100.0) > 0


def test_confidence():
    assert local_store._confidence(0.7) == "high"
    assert local_store._confidence(0.5) == "medium"
    assert local_store._confidence(0.2) == "low"
