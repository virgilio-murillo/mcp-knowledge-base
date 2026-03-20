import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import chromadb

_client = None
_collection = None


def _col(chroma_dir: str):
    global _client, _collection
    if _collection is None:
        Path(chroma_dir).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=chroma_dir)
        _collection = _client.get_or_create_collection("lessons")
    return _collection


def add(chroma_dir: str, topic: str, problem: str, resolution: str, tags: list[str] | None = None) -> dict:
    col = _col(chroma_dir)
    # Dedup: check if similar lesson already exists
    if col.count() > 0:
        existing = col.query(query_texts=[f"{topic} {problem}"], n_results=1)
        if existing["distances"][0] and existing["distances"][0][0] < 0.15:
            m = existing["metadatas"][0][0]
            return {"id": existing["ids"][0][0], "duplicate": True, **{k: m[k] for k in ("topic", "problem", "resolution")}, "tags": json.loads(m["tags"])}

    lesson_id = str(uuid.uuid4())
    doc = f"{topic} {problem} {resolution}"
    meta = {
        "topic": topic,
        "problem": problem,
        "resolution": resolution,
        "tags": json.dumps(tags or []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    col.add(ids=[lesson_id], documents=[doc], metadatas=[meta])
    return {"id": lesson_id, **meta, "tags": tags or []}


def _normalize_score(raw_distance: float) -> float:
    """Convert ChromaDB L2 distance to 0-1 similarity score."""
    return max(0.0, 1.0 / (1.0 + raw_distance))


def _confidence(score: float) -> str:
    if score >= 0.6:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


THRESHOLD = 0.45  # minimum normalized score to include


def search(chroma_dir: str, query: str, k: int = 5) -> list[dict]:
    col = _col(chroma_dir)
    if col.count() == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(k, col.count()))
    lessons = []
    for i, mid in enumerate(results["ids"][0]):
        m = results["metadatas"][0][i]
        score = _normalize_score(results["distances"][0][i])
        if score < THRESHOLD:
            continue
        lessons.append({
            "id": mid,
            "topic": m["topic"],
            "problem": m["problem"],
            "resolution": m["resolution"],
            "tags": json.loads(m["tags"]),
            "score": round(score, 3),
            "confidence": _confidence(score),
        })
    return lessons


def sync_from_cloud(chroma_dir: str, lessons: list[dict]):
    col = _col(chroma_dir)
    existing = set(col.get()["ids"]) if col.count() > 0 else set()
    added = 0
    for l in lessons:
        if l["id"] not in existing:
            doc = f"{l['topic']} {l['problem']} {l['resolution']}"
            meta = {
                "topic": l["topic"],
                "problem": l["problem"],
                "resolution": l["resolution"],
                "tags": json.dumps(l.get("tags", [])),
                "created_at": l.get("created_at", ""),
            }
            col.add(ids=[l["id"]], documents=[doc], metadatas=[meta])
            added += 1
    return {"synced": added, "total": col.count()}
