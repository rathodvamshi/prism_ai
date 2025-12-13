from youtubesearchpython import VideosSearch
import json

async def play_video(query: str):
    """
    Searches YouTube and returns the best video link + metadata.
    """
    print(f"🎵 Searching YouTube for: {query}")
    
    try:
        videosSearch = VideosSearch(query, limit=1)
        results = videosSearch.result()
        
        if not results['result']:
            return "No video found."

        video = results['result'][0]
        
        return json.dumps({
            "action": "play_video",
            "title": video['title'],
            "link": video['link'],
            "duration": video['duration'],
            "thumbnail": video['thumbnails'][0]['url'],
            "channel": video['channel']['name']
        })
    except Exception as e:
        return f"YouTube Error: {str(e)}"