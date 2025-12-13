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

async def search_web(query: str, max_results: int = 3) -> str:
    """
    Searches DuckDuckGo and returns a summary string.
    """
    print(f"🔎 Searching web for: {query}")
    
    try:
        if DDGS is None:
            return "Web search is unavailable: missing ddgs/duckduckgo_search package."
        # 1. Perform the search (Synchronous function run in async wrapper if needed, 
        # but for low traffic, direct call is okay)
        results = DDGS().text(keywords=query, max_results=max_results)
        
        if not results:
            return "No web results found."

        # 2. Format results into a single string for the LLM
        formatted_results = ""
        for i, res in enumerate(results, 1):
            formatted_results += f"Result {i}:\nTitle: {res['title']}\nSnippet: {res['body']}\nURL: {res['href']}\n\n"
            
        return formatted_results

    except Exception as e:
        print(f"Search Error: {e}")
        return "I tried to search the web, but an error occurred."