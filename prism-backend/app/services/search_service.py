import json
from typing import Literal

from app.db.redis_client import redis_client

try:
    # Preferred: renamed package
    from ddgs import DDGS
except ImportError:
    try:
        # Fallback: legacy package name
        from duckduckgo_search import DDGS  # type: ignore
        print("RuntimeWarning: `ddgs` not found, using legacy `duckduckgo_search`. Consider installing `ddgs`.")
    except ImportError:
        DDGS = None  # type: ignore
        print("ImportError: Neither `ddgs` nor `duckduckgo_search` is installed. Web search will be disabled.")


def _format_results(results):
    formatted_results = ""
    for i, res in enumerate(results, 1):
        title = res.get("title")
        snippet = res.get("body") or res.get("snippet") or res.get("description")
        href = res.get("href") or res.get("url")
        formatted_results += f"Result {i}:\nTitle: {title}\nSnippet: {snippet}\nURL: {href}\n\n"
    return formatted_results


async def search_web(
    query: str,
    *,
    mode: Literal["quick", "deep"] = "quick",
    max_results: int = 5,
    cache_ttl_seconds: int = 900,
) -> str:
    """
    Searches DuckDuckGo with caching.
    - quick: fast facts (few results, cached)
    - deep: more results for richer analysis (still cached)
    """
    print(f"🔎 Searching web ({mode}) for: {query}")

    if DDGS is None:
        return "Web search is unavailable: missing ddgs/duckduckgo_search package."

    # Cache first
    cache_key = f"WEB_SEARCH_CACHE:{mode}:{query}"
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            return cached
    except Exception:
        pass

    results_count = 3 if mode == "quick" else max_results
    try:
        results = DDGS().text(keywords=query, max_results=results_count)
        if not results:
            return "No web results found."

        formatted_results = _format_results(results)

        # Cache the formatted string
        try:
            await redis_client.set(cache_key, formatted_results, ex=cache_ttl_seconds)
        except Exception:
            pass

        return formatted_results

    except Exception as e:
        print(f"Search Error: {e}")
        return "I tried to search the web, but an error occurred."

