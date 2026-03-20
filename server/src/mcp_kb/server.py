from mcp.server.fastmcp import FastMCP

from . import config, local_store, cloud_client

mcp = FastMCP("mcp-knowledge-base")

SUMMARY_THRESHOLD = 10


def _cloud_configured() -> bool:
    return all([config.GATEWAY_URL, config.CLIENT_ID, config.CLIENT_SECRET, config.TOKEN_URL])


def _summarize(query: str, results: list[dict]) -> str:
    """Use Bedrock to summarize many results into actionable advice."""
    try:
        import boto3
        client = boto3.client("bedrock-runtime", region_name=config.BEDROCK_REGION)
        lessons_text = "\n\n".join(
            f"**{r['topic']}** (confidence: {r.get('confidence', '?')}, score: {r.get('score', '?')})\n"
            f"Problem: {r['problem'][:200]}\nResolution: {r['resolution'][:300]}"
            for r in results
        )
        resp = client.converse(
            modelId=config.SUMMARY_MODEL,
            messages=[{"role": "user", "content": [{"text":
                f"A user searched a knowledge base for: \"{query}\"\n\n"
                f"Here are {len(results)} matching lessons:\n\n{lessons_text}\n\n"
                f"Synthesize these into a concise, actionable summary. Group related lessons. "
                f"Highlight the most relevant ones for the query. Be direct and practical."
            }]}],
            inferenceConfig={"maxTokens": 1024},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"(Summary unavailable: {e})"


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

    output = {"results": results, "count": len(results), "query": query}
    if len(results) > SUMMARY_THRESHOLD:
        output["summary"] = _summarize(query, results)
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
