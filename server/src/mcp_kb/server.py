from mcp.server.fastmcp import FastMCP

from . import config, local_store, cloud_client

mcp = FastMCP("mcp-knowledge-base")


def _cloud_configured() -> bool:
    return all([config.GATEWAY_URL, config.CLIENT_ID, config.CLIENT_SECRET, config.TOKEN_URL])


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
def search_lessons(query: str, k: int = 5) -> list[dict]:
    """Search lessons learned using semantic similarity. Searches local cache first, falls back to cloud."""
    results = local_store.search(config.CHROMA_DIR, query, k)
    if results:
        return results
    if _cloud_configured():
        try:
            return cloud_client.search_lessons(
                config.GATEWAY_URL, config.TOKEN_URL, config.CLIENT_ID, config.CLIENT_SECRET,
                query=query, k=k,
            )
        except Exception:
            pass
    return []


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
