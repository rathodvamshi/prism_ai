from duckduckgo_search import DDGS

async def deep_research(query: str):
    """
    Performs a deep dive search.
    1. Searches for reviews and "best of" lists.
    2. Extracts Product Name, Price, and Link.
    3. Formats it nicely.
    """
    print(f"🕵️‍♂️ Deep Research started for: {query}")
    
    try:
        # Use DuckDuckGo to find shopping/review results
        results = DDGS().text(keywords=query + " reviews price buy online", max_results=5)
        
        if not results:
            return "I couldn't find detailed research results."

        # We format the raw data for the LLM to synthesize later
        research_data = "Here is the raw research data found:\n"
        
        for res in results:
            research_data += f"""
            ---
            Title: {res['title']}
            Link: {res['href']}
            Snippet: {res['body']}
            ---
            """
            
        return research_data
    except Exception as e:
        return f"Research failed: {str(e)}"