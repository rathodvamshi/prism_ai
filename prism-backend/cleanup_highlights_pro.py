"""
Highlight Cleanup Utility

This script removes duplicate highlights from the database and fixes indexing issues.

Usage:
    python cleanup_highlights_pro.py --stats    # Show statistics
    python cleanup_highlights_pro.py --clean    # Remove duplicates
    python cleanup_highlights_pro.py --fix-indexes  # Fix incorrect indexes
"""

import asyncio
import argparse
from datetime import datetime
from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "prism_ai")


async def get_database():
    """Get database connection"""
    client = AsyncIOMotorClient(MONGODB_URI)
    return client[DATABASE_NAME]


async def cleanup_duplicate_highlights():
    """Remove duplicate highlights from database."""
    print("🧹 Starting enhanced highlight cleanup...")
    
    db = await get_database()
    highlights_collection = db.message_highlights
    
    try:
        # Get all highlights
        all_highlights = await highlights_collection.find({}).to_list(length=None)
        print(f"📊 Found {len(all_highlights)} total highlights")
        
        # Group by message
        by_message = defaultdict(list)
        for h in all_highlights:
            message_id = h.get("messageId")
            if message_id:
                by_message[message_id].append(h)
        
        duplicates_removed = 0
        fixed_indexes = 0
        
        for message_id, highlights in by_message.items():
            if len(highlights) <= 1:
                continue
            
            # Sort by creation time (keep newest)
            highlights.sort(key=lambda x: x.get("createdAt", datetime.min), reverse=True)
            
            # Track seen highlights (by text + range)
            seen = set()
            
            for h in highlights:
                start = h.get("startIndex", 0)
                end = h.get("endIndex", 0)
                text = h.get("text", "").strip()
                _id = h.get("_id")
                highlight_id = h.get("highlightId", str(_id))
                
                # Create signature for duplicate detection
                signature = f"{text}|{start}|{end}"
                
                # Check for exact duplicates
                if signature in seen:
                    # Delete this duplicate
                    await highlights_collection.delete_one({"_id": _id})
                    duplicates_removed += 1
                    print(f"   🗑️ Removed exact duplicate: {highlight_id}")
                    continue
                
                # Check for overlapping duplicates with same text
                is_duplicate = False
                for seen_sig in seen:
                    seen_text, seen_start, seen_end = seen_sig.split("|")
                    seen_start = int(seen_start)
                    seen_end = int(seen_end)
                    
                    # Check overlap
                    ranges_overlap = (start < seen_end and seen_start < end)
                    text_match = seen_text == text
                    
                    if ranges_overlap and text_match:
                        # This is a near-duplicate
                        await highlights_collection.delete_one({"_id": _id})
                        duplicates_removed += 1
                        print(f"   🔄 Removed overlapping duplicate: {highlight_id}")
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen.add(signature)
                    
                    # Fix invalid indexes (startIndex >= endIndex)
                    if start >= end:
                        # Try to fix by using text length
                        if text:
                            new_end = start + len(text)
                            await highlights_collection.update_one(
                                {"_id": _id},
                                {"$set": {"endIndex": new_end}}
                            )
                            fixed_indexes += 1
                            print(f"   🔧 Fixed invalid index: {highlight_id} [{start}:{end}] -> [{start}:{new_end}]")
        
        print(f"\n✅ Cleanup complete!")
        print(f"   - Duplicates removed: {duplicates_removed}")
        print(f"   - Indexes fixed: {fixed_indexes}")
        print(f"   - Remaining highlights: {len(all_highlights) - duplicates_removed}")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        raise


async def show_highlight_stats():
    """Show statistics about highlights in the database."""
    print("📊 Highlight Statistics\n")
    
    db = await get_database()
    highlights_collection = db.message_highlights
    
    try:
        total = await highlights_collection.count_documents({})
        print(f"Total highlights: {total}")
        
        # Count by session
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
                "_id": {"messageId": "$messageId", "text": "$text", "start": "$startIndex", "end": "$endIndex"},
                "count": {"$sum": 1},
                "ids": {"$push": "$highlightId"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = await highlights_collection.aggregate(pipeline).to_list(length=None)
        print(f"\nPotential duplicates found: {len(duplicates)}")
        if duplicates:
            print("Sample duplicates:")
            for dup in duplicates[:5]:
                print(f"  - Message: {dup['_id']['messageId'][:20]}... Count: {dup['count']}")
        
        # Find invalid indexes
        invalid_indexes = await highlights_collection.count_documents({
            "$expr": {"$gte": ["$startIndex", "$endIndex"]}
        })
        print(f"\nHighlights with invalid indexes (start >= end): {invalid_indexes}")
        
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        raise


async def fix_highlight_indexes():
    """Fix highlights with incorrect indexes."""
    print("🔧 Fixing highlight indexes...")
    
    db = await get_database()
    highlights_collection = db.message_highlights
    
    try:
        # Find highlights with invalid indexes
        invalid = await highlights_collection.find({
            "$expr": {"$gte": ["$startIndex", "$endIndex"]}
        }).to_list(length=None)
        
        print(f"Found {len(invalid)} highlights with invalid indexes")
        
        fixed = 0
        for h in invalid:
            text = h.get("text", "")
            start = h.get("startIndex", 0)
            
            if text:
                # Fix by using text length
                new_end = start + len(text)
                await highlights_collection.update_one(
                    {"_id": h["_id"]},
                    {"$set": {"endIndex": new_end}}
                )
                fixed += 1
                print(f"  ✅ Fixed: {h.get('highlightId')} [{start}:{h.get('endIndex')}] -> [{start}:{new_end}]")
        
        print(f"\n✅ Fixed {fixed} highlights")
        
    except Exception as e:
        print(f"❌ Error fixing indexes: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup and fix highlights")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--clean", action="store_true", help="Remove duplicates")
    parser.add_argument("--fix-indexes", action="store_true", help="Fix invalid indexes")
    
    args = parser.parse_args()
    
    if args.stats:
        asyncio.run(show_highlight_stats())
    elif args.clean:
        asyncio.run(cleanup_duplicate_highlights())
    elif args.fix_indexes:
        asyncio.run(fix_highlight_indexes())
    else:
        print("Usage:")
        print("  python cleanup_highlights_pro.py --stats        # Show statistics")
        print("  python cleanup_highlights_pro.py --clean        # Remove duplicates")
        print("  python cleanup_highlights_pro.py --fix-indexes  # Fix invalid indexes")
