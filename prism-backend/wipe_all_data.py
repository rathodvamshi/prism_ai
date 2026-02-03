import asyncio
import os
import logging
import sys
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WipeAllData")

async def wipe_mongo():
    logger.info("🗑️  [MongoDB] Starting wipe...")
    try:
        from app.db.mongo_client import _build_client
        client = _build_client()
        
        # 1. Wipe database from URI
        # Handle simple URI parsing
        uri_db_name = None
        try:
             # Typical URI: mongodb://host:port/dbname?options
             path = settings.MONGO_URI.split('/')[-1]
             uri_db_name = path.split('?')[0]
        except:
             pass

        if uri_db_name:
            await client.drop_database(uri_db_name)
            logger.info(f"    ✅ Dropped database from URI: {uri_db_name}")
            
        # 2. Wipe 'prism_db' explicitly used in app/db/mongo_client.py
        # Check if it's different to avoid double log (though drop is idempotent)
        if uri_db_name != "prism_db":
            await client.drop_database("prism_db")
            logger.info(f"    ✅ Dropped database: prism_db")
             
        client.close()
    except Exception as e:
        logger.error(f"    ❌ [MongoDB] Failed: {e}")

async def wipe_redis():
    logger.info("🗑️  [Redis] Starting wipe...")
    try:
        from app.db.redis_client import create_redis_client
        client = create_redis_client()
        # FLUSHALL wipes all keys in all databases (0, 1, 2...)
        # This is the truest 'start fresh' for Redis
        await client.flushall() 
        await client.aclose()
        logger.info("    ✅ Flushed ALL Redis databases (FLUSHALL)")
    except Exception as e:
        logger.error(f"    ❌ [Redis] Failed: {e}")

async def wipe_neo4j():
    logger.info("🗑️  [Neo4j] Starting wipe...")
    try:
        from app.db.neo4j_client import create_neo4j_driver
        driver = create_neo4j_driver()
        if driver:
            async with driver.session() as session:
                # Delete all nodes and relationships
                result = await session.run("MATCH (n) DETACH DELETE n")
                consume = await result.consume()
                counters = consume.counters
                logger.info(f"    ✅ Deleted {counters.nodes_deleted} nodes, {counters.relationships_deleted} relationships")
            await driver.close()
        else:
             logger.warning("    ⚠️ Neo4j driver not initialized (check credentials)")
    except Exception as e:
        logger.error(f"    ❌ [Neo4j] Failed: {e}")

async def wipe_pinecone():
    logger.info("🗑️  [Pinecone] Starting wipe...")
    try:
        if not settings.PINECONE_API_KEY:
            logger.warning("    ⚠️ PINECONE_API_KEY not set. Skipping.")
            return

        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index_name = settings.PINECONE_INDEX_NAME or "prism-memory"
        
        indexes = pc.list_indexes()
        # Handle different Pinecone client versions response formats
        existing_names = [i.name if hasattr(i, 'name') else i for i in indexes]
        
        if index_name in existing_names:
            logger.info(f"    found index '{index_name}', wiping vectors...")
            index = pc.Index(index_name)
            
            # Method 1: Delete all namespaces (Fastest for just data)
            stats = index.describe_index_stats()
            # .namespaces gives a dict of namespace -> stats
            # Handle case where namespaces might be None or empty
            namespaces = list(stats.namespaces.keys()) if stats.namespaces else []
            
            # Helper to delete namespace
            def delete_ns(ns_name):
                 try:
                    index.delete(delete_all=True, namespace=ns_name)
                    logger.info(f"    ✅ Deleted namespace: '{ns_name}'")
                 except Exception as ns_e:
                    logger.error(f"    ❌ Failed to delete namespace '{ns_name}': {ns_e}")

            if not namespaces and stats.total_vector_count == 0:
                 logger.info("    Index is already empty.")
                 return

            for ns in namespaces:
                delete_ns(ns)
            
            # 🟢 ALWAYS try to delete default namespace "" explicitly just in case stats didn't show it 
            # or if vectors exist outside named namespaces.
            # Pinecone treats "" as default namespace.
            if "" not in namespaces:
                 delete_ns("")

            logger.info(f"    ✅ Pinecone wipe complete.")
        else:
            logger.warning(f"    ⚠️ Index '{index_name}' not found. Nothing to wipe.")
            
    except Exception as e:
        logger.error(f"    ❌ [Pinecone] Failed: {e}")

async def main():
    print("\n⚠️  WARNING: THIS WILL DELETE ALL DATA IN: MONGODB, REDIS, NEO4J, AND PINECONE. ⚠️")
    print("This cannot be undone.")
    
    # Allow passing 'force' argument to skip prompt
    # Also ignore case for argument
    force = False
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["yes", "force", "true", "y"]:
        force = True

    if force:
        print("Force mode: Skipping confirmation.")
    else:
        try:
            choice = input("Type 'yes' to wipe everything: ")
            if choice.lower() != 'yes':
                print("Aborted.")
                return
        except Exception:
             # If input fails (non-interactive), assume safe abort unless forced
             print("Input failed (non-interactive shell?). Run with 'python wipe_all_data.py yes' to force.")
             return

    await asyncio.gather(
        wipe_mongo(),
        wipe_redis(),
        wipe_neo4j(),
        wipe_pinecone()
    )
    
    print("\n✨ All systems wiped successfully. Fresh start ready! ✨\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
