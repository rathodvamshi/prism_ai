"""
🧭 DEEP RESEARCH ORCHESTRATOR

This service connects the "Map" (DuckDuckGo) to the "Eyes" (Scraper) and compiles the report.
Orchestrates the research flow: Search -> Parallel Scrape -> Synthesize
"""

import asyncio
import hashlib
from duckduckgo_search import DDGS
from app.services.scraper_service import scrape_dynamic_url
from app.db.redis_client import redis_client
import logging

logger = logging.getLogger(__name__)


async def deep_research(query: str):
    """
    Orchestrates the research flow: Search -> Parallel Scrape -> Synthesize
    
    Args:
        query: The search query
        
    Returns:
        str: Formatted research report with sources, images, and content
    """
    print(f"🧭 [Research] Starting Mission: {query}")
    
    # 1. CACHE CHECK (hash query to create stable key)
    normalized = (query or "").strip().lower()
    query_hash = hashlib.md5(normalized.encode()).hexdigest()
    cache_key = f"research:{query_hash}"

    try:
        cached_result = await redis_client.get(cache_key)
        if cached_result:
            print(f"⚡ Cache Hit for Deep Research: {query}")
            return cached_result.decode('utf-8') if isinstance(cached_result, bytes) else cached_result
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
        cached_result = None
    
    # 1. SEARCH: Get Top 3-4 Targets
    # We fetch 4 links assuming 1 might fail/timeout
    try:
        results = list(DDGS().text(keywords=query, max_results=4))
    except Exception as e:
        print(f"⚠️ Search Error: {e}")
        logger.error(f"DuckDuckGo search failed: {e}")
        return "I couldn't access the search engine right now."
        
    if not results: 
        return "No relevant search results found."
        
    # 2. PREPARE TASKS
    tasks = []
    for r in results:
        # Pass each URL to the scraper
        url = r.get('href') if isinstance(r, dict) else r
        if url:
            tasks.append(scrape_dynamic_url(url))

    # 3. EXECUTE: Visit all sites in PARALLEL
    # This is fast. Total time = time of slowest site (~3-5s total)
    scraped_data = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. FILTER & FORMAT
    valid_data = []
    for d in scraped_data:
        if isinstance(d, Exception):
            logger.warning(f"Scraping task raised exception: {d}")
            continue
        if d:  # d is not None
            valid_data.append(d)
    
    if not valid_data:
        urls = [r.get('href') if isinstance(r, dict) else r for r in results]
        return f"I tried to read the websites, but they blocked access. Here are the links: {', '.join(urls)}"

    # 5. FORMAT REPORT
    report = f"Deep Research Results for '{query}':\n\n"
    
    for idx, item in enumerate(valid_data, 1):
        report += f"""
=== SOURCE {idx}: {item['title']} ===
URL: {item['source']}
IMAGE: {item['image'] if item.get('image') else 'No image available'}
DATA: {item['content']}
================================
"""
    
    # 6. SAVE TO REDIS (TTL: 24 hours) - ignore failures silently
    try:
        await redis_client.set(cache_key, report, ex=86400)
    except Exception as e:
        logger.warning(f"Failed to cache research result: {e}")
    
    return report
