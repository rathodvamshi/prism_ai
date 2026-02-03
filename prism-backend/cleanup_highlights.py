"""
Highlight Cleanup Script

Removes duplicate highlights from the database based on:
- Same messageId + overlapping/identical indexes
- Keeps the most recent highlight in case of duplicates
"""

import asyncio
import os
import sys
from datetime import datetime
from collections import defaultdict

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")

async def cleanup_duplicate_highlights():
    """Remove duplicate highlights from database."""
    print("🧹 Starting highlight cleanup...")
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.prism_studio
    highlights_collection = db.message_highlights
    
    try:
        # Get all highlights
        all_highlights = await highlights_collection.find({}).to_list(length=None)
        print(f"📊 Found {len(all_highlights)} total highlights")
        
        # Group by messageId
        by_message = defaultdict(list)
        for h in all_highlights:
            by_message[h.get("messageId")].append(h)
        
        duplicates_removed = 0
        messages_with_duplicates = 0
        
        for message_id, highlights in by_message.items():
            if len(highlights) <= 1:
                continue
            
            # Sort by createdAt (newest first) to keep most recent
            highlights.sort(key=lambda x: x.get("createdAt", datetime.min), reverse=True)
            
            # Find duplicates (same or overlapping indexes)
            seen_ranges = []
            to_delete = []
            
            for h in highlights:
                start = h.get("startIndex", 0)
                end = h.get("endIndex", 0)
                text = h.get("text", "")
                highlight_id = h.get("highlightId", str(h.get("_id")))
                
                # Check if this range overlaps significantly with any seen range
                is_duplicate = False
                for seen_start, seen_end, seen_text in seen_ranges:
                    # Check for identical or very similar highlights
                    if (start == seen_start and end == seen_end) or text == seen_text:
                        is_duplicate = True
                        break
                    
                    # Check for significant overlap (>50%)
                    overlap_start = max(start, seen_start)
                    overlap_end = min(end, seen_end)
                    if overlap_end > overlap_start:
                        overlap_len = overlap_end - overlap_start
                        min_len = min(end - start, seen_end - seen_start)
                        if min_len > 0 and overlap_len / min_len > 0.5:
                            is_duplicate = True
                            break
                
                if is_duplicate:
                    to_delete.append(h)
                else:
                    seen_ranges.append((start, end, text))
            
            # Delete duplicates
            if to_delete:
                messages_with_duplicates += 1
                for h in to_delete:
                    _id = h.get("_id")
                    if _id:
                        await highlights_collection.delete_one({"_id": _id})
                        duplicates_removed += 1
                        print(f"  🗑️ Removed duplicate: {h.get('text', '')[:30]}... in message {message_id}")
        
        print(f"\n✅ Cleanup complete!")
        print(f"   - Messages with duplicates: {messages_with_duplicates}")
        print(f"   - Duplicates removed: {duplicates_removed}")
        print(f"   - Remaining highlights: {len(all_highlights) - duplicates_removed}")
        
    finally:
        client.close()

async def show_highlight_stats():
    """Show statistics about highlights in the database."""
    print("📊 Highlight Statistics\n")
    
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.prism_studio
    highlights_collection = db.message_highlights
    
    try:
        total = await highlights_collection.count_documents({})
        print(f"Total highlights: {total}")
        
        # Group by session
        pipeline = [
            {"$group": {"_id": "$sessionId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        by_session = await highlights_collection.aggregate(pipeline).to_list(length=None)
        
        print(f"\nTop 10 sessions by highlight count:")
        for s in by_session:
            print(f"  - {s['_id']}: {s['count']} highlights")
        
        # Find potential duplicates
        pipeline = [
            {"$group": {
                "_id": {"messageId": "$messageId", "text": "$text"},
                "count": {"$sum": 1}
            }},
            {"$match": {"count": {"$gt": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        duplicates = await highlights_collection.aggregate(pipeline).to_list(length=None)
        
        print(f"\nPotential duplicates (same text in same message):")
        for d in duplicates:
            print(f"  - Message {d['_id']['messageId'][:8]}...: '{d['_id']['text'][:30]}...' appears {d['count']} times")
        
    finally:
        client.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cleanup duplicate highlights")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--clean", action="store_true", help="Remove duplicates")
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(show_highlight_stats())
    elif args.clean:
        asyncio.run(cleanup_duplicate_highlights())
    else:
        print("Usage:")
        print("  python cleanup_highlights.py --stats   # Show statistics")
        print("  python cleanup_highlights.py --clean   # Remove duplicates")
