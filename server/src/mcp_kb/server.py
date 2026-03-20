from mcp.server.fastmcp import FastMCP

from . import config, local_store, cloud_client

mcp = FastMCP("mcp-knowledge-base")

SUMMARY_THRESHOLD = 10
RELEVANCE_THRESHOLD = 0.6  # above this, skip LLM filter


def _cloud_configured() -> bool:
    return all([config.GATEWAY_URL, config.CLIENT_ID, config.CLIENT_SECRET, config.TOKEN_URL])


def _bedrock_client():
    import boto3
    return boto3.client("bedrock-runtime", region_name=config.BEDROCK_REGION)


def _llm_call(client, messages: list[dict], max_tokens: int = 1024) -> str | None:
    for model_id in config.SUMMARY_MODELS:
        try:
            resp = client.converse(
                modelId=model_id, messages=messages,
                inferenceConfig={"maxTokens": max_tokens},
            )
            return resp["output"]["message"]["content"][0]["text"]
        except Exception:
            continue
    return None


def _filter_relevant(query: str, results: list[dict]) -> list[dict]:
    """Use LLM to filter out irrelevant results from borderline matches."""
    # Split: high-confidence pass through, borderline get LLM-checked
    high = [r for r in results if r.get("score", 0) >= RELEVANCE_THRESHOLD]
    borderline = [r for r in results if r.get("score", 0) < RELEVANCE_THRESHOLD]
    if not borderline:
        return high

    listing = "\n".join(
        f"{i}: {r['topic']} — {r['problem'][:100]}" for i, r in enumerate(borderline)
    )
    text = _llm_call(_bedrock_client(), [{"role": "user", "content": [{"text":
        f"Query: \"{query}\"\n\nWhich of these knowledge base results are relevant or even partially related?\n\n"
        f"{listing}\n\nOnly remove results about a completely different technology or domain. "
        f"Keep anything tangentially related. Return ONLY the numbers of results to keep, comma-separated. "
        f"If none are relevant at all, return \"none\"."
    }]}], max_tokens=100)
    if not text or "none" in text.lower():
        return high

    import re
    keep = set()
    for m in re.finditer(r'\d+', text):
        keep.add(int(m.group()))
    return high + [r for i, r in enumerate(borderline) if i in keep]


def _summarize(query: str, results: list[dict]) -> str | None:
    """Use Bedrock to summarize many results into actionable advice."""
    lessons_text = "\n\n".join(
        f"**{r['topic']}** (confidence: {r.get('confidence', '?')}, score: {r.get('score', '?')})\n"
        f"Problem: {r['problem'][:200]}\nResolution: {r['resolution'][:300]}"
        for r in results
    )
    return _llm_call(_bedrock_client(), [{"role": "user", "content": [{"text":
        f"A user searched a knowledge base for: \"{query}\"\n\n"
        f"Here are {len(results)} matching lessons:\n\n{lessons_text}\n\n"
        f"Synthesize these into a concise, actionable summary. Group related lessons. "
        f"Highlight the most relevant ones for the query. Be direct and practical."
    }]}])


@mcp.tool()
def add_lesson(topic: str, problem: str, resolution: str, tags: list[str] | None = None) -> dict:
    """Store a new lesson learned (debugging tip, solution, or pattern)."""
    lesson = local_store.add(config.CHROMA_DIR, topic, problem, resolution, tags)
    if _cloud_configured():
        try:
            cloud_client.write_lesson(
                config.GATEWAY_URL, config.TOKEN_URL, config.CLIENT_ID, config.CLIENT_SECRET,
                topic=topic, problem=problem, resolution=resolution, tags=tags or [],
            )
            lesson["cloud_synced"] = True
        except Exception as e:
            lesson["cloud_synced"] = False
            lesson["cloud_error"] = str(e)
    return lesson


@mcp.tool()
def search_lessons(query: str, k: int = 10) -> dict:
    """Search lessons learned using semantic similarity. Returns multiple results with confidence labels. When more than 10 results match, includes an AI-generated summary."""
    results = local_store.search(config.CHROMA_DIR, query, k)
    if not results and _cloud_configured():
        try:
            results = cloud_client.search_lessons(
                config.GATEWAY_URL, config.TOKEN_URL, config.CLIENT_ID, config.CLIENT_SECRET,
                query=query, k=k,
            )
        except Exception:
            pass
    if not results:
        return {"results": [], "count": 0, "message": "No relevant lessons found", "query": query}

    results = _filter_relevant(query, results)
    if not results:
        return {"results": [], "count": 0, "message": "No relevant lessons found", "query": query}

    output = {"results": results, "count": len(results), "query": query}
    if len(results) > SUMMARY_THRESHOLD:
        summary = _summarize(query, results)
        if summary:
            output["summary"] = summary
    return output


@mcp.tool()
def sync() -> dict:
    """Sync local cache from cloud. Downloads all lessons and adds missing ones to local ChromaDB."""
    if not _cloud_configured():
        return {"error": "Cloud not configured"}
    try:
        lessons = cloud_client.sync_lessons(
            config.GATEWAY_URL, config.TOKEN_URL, config.CLIENT_ID, config.CLIENT_SECRET,
        )
        return local_store.sync_from_cloud(config.CHROMA_DIR, lessons)
    except Exception as e:
        return {"error": str(e)}


def main():
    mcp.run(transport="stdio")
