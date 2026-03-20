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
    lesson_id = str(uuid.uuid4())
    doc = f"{topic} {problem} {resolution}"
    meta = {
        "topic": topic,
        "problem": problem,
        "resolution": resolution,
        "tags": json.dumps(tags or []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _col(chroma_dir).add(ids=[lesson_id], documents=[doc], metadatas=[meta])
    return {"id": lesson_id, **meta, "tags": tags or []}


def search(chroma_dir: str, query: str, k: int = 5) -> list[dict]:
    col = _col(chroma_dir)
    if col.count() == 0:
        return []
    results = col.query(query_texts=[query], n_results=min(k, col.count()))
    lessons = []
    for i, mid in enumerate(results["ids"][0]):
        m = results["metadatas"][0][i]
        lessons.append({
            "id": mid,
            "topic": m["topic"],
            "problem": m["problem"],
            "resolution": m["resolution"],
            "tags": json.loads(m["tags"]),
            "score": 1 - results["distances"][0][i],  # chroma returns L2 distance
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
