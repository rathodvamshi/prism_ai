"""
🧠 PENDING / DRAFT MEMORY SERVICE

Core rules implemented here:
- Never drop memory when Neo4j / Redis / Pinecone fails
- Always store as pending draft when a write fails
- Read pending memory first (fast) before slower systems
- Background sync auto-heals when connections are back
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db.mongo_client import db  # reuse main DB client
from app.db.redis_client import redis_client
from app.db.neo4j_client import AdvancedNeo4jClient

logger = logging.getLogger(__name__)

# Mongo collection dedicated to pending / draft memories
pending_memory_collection = db.pending_memory


async def _ensure_indexes():
    """
    Create indexes for fast scans.
    This is light-weight and safe to call multiple times.
    """
    try:
        await pending_memory_collection.create_index("user_id")
        await pending_memory_collection.create_index("status")
        await pending_memory_collection.create_index("targets")
    except Exception as e:
        logger.warning(f"PendingMemory: index creation failed (non‑fatal): {e}")


async def save_draft_memory(
    user_id: str,
    memory_type: str,
    value: Any,
    source: str,
    targets: Optional[List[str]] = None,
) -> None:
    """
    Save pending memory in Mongo + Redis.

    Example document:
    {
      "user_id": "123",
      "type": "USER_NAME",
      "value": "Vamshi",
      "source": "chat",
      "targets": ["neo4j"],
      "status": "pending_sync",
      "created_at": "...",
      "last_error": "Neo4j timeout"
    }
    """
    await _ensure_indexes()

    doc: Dict[str, Any] = {
        "user_id": user_id,
        "type": memory_type,
        "value": value,
        "source": source,
        "targets": targets or [],
        "status": "pending_sync",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    try:
        await pending_memory_collection.insert_one(doc)
    except Exception as e:
        # As a last resort, keep it in Redis emergency storage
        logger.error(f"PendingMemory: failed to write draft to Mongo, falling back to Redis: {e}")
        key = f"PENDING_MEMORY_FALLBACK:{user_id}:{memory_type}:{datetime.utcnow().timestamp()}"
        try:
            await redis_client.set(
                key,
                json.dumps(
                    {
                        "user_id": user_id,
                        "type": memory_type,
                        "value": value,
                        "source": source,
                        "targets": targets or [],
                        "status": "pending_sync",
                    }
                ),
                ex=24 * 3600,
            )
        except Exception as re:
            logger.error(f"PendingMemory: Redis fallback also failed (memory kept only in process logs): {re}")

    # Also cache a fast lookup copy in Redis for read‑priority layer
    try:
        cache_key = f"PENDING_MEMORY_CACHE:{user_id}"
        # We store a small append‑only list; no strong consistency needed
        entry = {
            "type": memory_type,
            "value": value,
            "source": source,
            "targets": targets or [],
            "status": "pending_sync",
            "ts": datetime.utcnow().isoformat(),
        }
        existing_raw = await redis_client.get(cache_key)
        items: List[Dict[str, Any]] = []
        if existing_raw:
            try:
                items = json.loads(existing_raw)
            except Exception:
                items = []
        items.append(entry)
        # Keep only last 50 drafts per user for speed
        items = items[-50:]
        await redis_client.set(cache_key, json.dumps(items), ex=24 * 3600)
    except Exception as e:
        logger.warning(f"PendingMemory: failed to update Redis cache (non‑fatal): {e}")


async def get_draft_memories(
    user_id: str,
    memory_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Read pending / draft memories for a user.
    Priority: Redis cache (fast) → Mongo (authoritative).
    """
    cache_key = f"PENDING_MEMORY_CACHE:{user_id}"
    drafts: List[Dict[str, Any]] = []

    # 1) Fast path: Redis cache
    try:
        cached = await redis_client.get(cache_key)
        if cached:
            items = json.loads(cached)
            if memory_type:
                items = [it for it in items if it.get("type") == memory_type]
            drafts.extend(items)
    except Exception as e:
        logger.warning(f"PendingMemory: Redis cache read failed (falling back to Mongo): {e}")

    # 2) Authoritative: Mongo
    try:
        query: Dict[str, Any] = {"user_id": user_id, "status": "pending_sync"}
        if memory_type:
            query["type"] = memory_type
        cursor = pending_memory_collection.find(query).limit(100)
        async for doc in cursor:
            # Merge Mongo docs on top (they are canonical)
            drafts.append(
                {
                    "id": str(doc.get("_id")),
                    "type": doc.get("type"),
                    "value": doc.get("value"),
                    "source": doc.get("source"),
                    "targets": doc.get("targets") or [],
                    "status": doc.get("status"),
                    "created_at": doc.get("created_at"),
                }
            )
    except Exception as e:
        logger.error(f"PendingMemory: Mongo read failed for drafts: {e}")

    return drafts


async def sync_pending_graph_memories(
    *,
    per_item_timeout_seconds: float = 5.0,
    max_items: int = 100,
) -> None:
    """
    Background auto‑healing job:
    - Finds all pending memories that target Neo4j
    - Tries to write them to Neo4j with per‑item timeouts
    - Marks as synced (or keeps as pending on failure)
    """
    await _ensure_indexes()

    neo4j_client_adv = AdvancedNeo4jClient()

    try:
        # Quick check: if Neo4j is not available, just exit fast
        if not neo4j_client_adv.neo4j_client.is_available:
            logger.info("PendingMemory: Neo4j not available, skipping sync cycle")
            return
    except Exception as e:
        logger.warning(f"PendingMemory: Neo4j availability check failed, skipping sync: {e}")
        return

    query = {
        "status": "pending_sync",
        "targets": {"$in": ["neo4j"]},
    }

    cursor = pending_memory_collection.find(query).limit(max_items)

    async for doc in cursor:
        doc_id = doc.get("_id")
        user_id = doc.get("user_id")
        memory_type = doc.get("type")
        value = doc.get("value")

        # Only graph‑style memories are handled here (interests, relations, etc.)
        try:
            if memory_type in ("USER_INTEREST", "INTEREST", "HOBBY"):
                async def apply_interest() -> bool:
                    return await neo4j_client_adv.merge_user_relationship(
                        user_id=user_id,
                        relation_type="LIKES",
                        target_value=str(value),
                    )

                success = await asyncio.wait_for(
                    apply_interest(),
                    timeout=per_item_timeout_seconds,
                )
            elif memory_type == "USER_NAME":
                # USER_NAME is typically stored in Mongo profile; we still create/update a user node
                async def apply_name() -> bool:
                    # This is a soft operation, only to make sure graph node exists
                    try:
                        from app.db.neo4j_client import create_user_in_graph
                    except Exception:
                        return False
                    return await create_user_in_graph(user_id, email="", name=str(value))

                success = await asyncio.wait_for(
                    apply_name(),
                    timeout=per_item_timeout_seconds,
                )
            else:
                # Unknown type – skip but keep in pending for now
                logger.info(f"PendingMemory: skipping unsupported graph memory type={memory_type}")
                continue

            if success:
                await pending_memory_collection.update_one(
                    {"_id": doc_id},
                    {
                        "$set": {
                            "status": "synced",
                            "synced_at": datetime.utcnow(),
                        }
                    },
                )
                logger.info(
                    f"PendingMemory: synced draft for user={user_id}, type={memory_type}, value={value}"
                )
            else:
                logger.warning(
                    f"PendingMemory: Neo4j sync returned False for user={user_id}, type={memory_type}"
                )
        except asyncio.TimeoutError:
            logger.warning(
                f"PendingMemory: Neo4j sync timeout for user={user_id}, type={memory_type}"
            )
        except Exception as e:
            logger.error(
                f"PendingMemory: error while syncing draft to Neo4j for user={user_id}, type={memory_type}: {e}"
            )


