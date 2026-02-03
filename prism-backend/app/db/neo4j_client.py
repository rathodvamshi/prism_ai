"""
🔗 GRAPH MEMORY (Neo4j)

Store relationships between user → interests → habits → tasks.

Simple example graph:
(User) ---likes---> (Fitness)  
(User) ---likes---> (AI)
(User) ---hasTask--> (Finish Assignment)

Why this helps?
- "Your interests are AI & Fitness."
- "You have 5 pending tasks."  
- "Since you like fitness, try XYZ."

🟢 Rule: Neo4j uses MERGE, not CREATE to avoid duplicates
"""

from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Driver with error handling
def create_neo4j_driver():
    """Create Neo4j driver with proper error handling and optimized connection settings"""
    try:
        if not settings.NEO4J_URI or settings.NEO4J_URI == "neo4j://localhost:7687":
            # Check if it's actually localhost or just default
            if "localhost" in settings.NEO4J_URI and not settings.is_development:
                 logger.warning("⚠️ Neo4j URI is set to localhost in non-dev environment.")
            
            if not settings.NEO4J_URI:
                logger.warning("Neo4j URI not configured, using None driver")
                return None
        
        # Enhanced connection settings for Neo4j Aura
        return AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,       # Keep connections alive for 1 hour
            max_connection_pool_size=50,        # Increase pool size
            connection_timeout=60,              # 60 second timeout for Neo4j Aura
            connection_acquisition_timeout=60,  # 60s to acquire connection from pool
            keep_alive=True,                    # Enable TCP keepalive
            resolver=None                       # Use default DNS resolver
        )
    except Exception as e:
        logger.error(f"Failed to create Neo4j driver: {e}")
        return None

class Neo4jClient:
    """
    🔌 SINGLETON Neo4j client with connection pooling.
    """
    
    _instance = None
    _initialized = False
    _failure_logged = False  # 🔇 Log failure only once to reduce noise
    
    def __new__(cls):
        """Enforce singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Neo4j driver only once"""
        if not self._initialized:
            self._driver = create_neo4j_driver()
            self._connection_verified = False
            Neo4jClient._initialized = True
            if self._driver:
                logger.info("✅ Neo4j singleton driver initialized with connection pool")
                logger.info("   Max pool size: 50 connections")
    
    @property
    def is_available(self) -> bool:
        """Check if Neo4j is available"""
        return self._driver is not None
    
    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connection is working (logs failure only once)"""
        if not self._driver:
            if not Neo4jClient._failure_logged:
                logger.warning("⚠️ Neo4j driver not initialized - graph features disabled")
                Neo4jClient._failure_logged = True
            return False
        
        try:
            await self._driver.verify_connectivity()
            self._connection_verified = True
            Neo4jClient._failure_logged = False  # Reset on success
            logger.info("✅ Neo4j connection verified successfully")
            return True
        except Exception as e:
            # 🔇 Log failure only ONCE to reduce log noise
            if not Neo4jClient._failure_logged:
                if "getaddrinfo failed" in str(e):
                    logger.warning(f"⚠️ Neo4j unavailable (DNS failed) - graph features disabled")
                    logger.debug(f"   URI: {settings.NEO4J_URI}")
                else:
                    logger.warning(f"⚠️ Neo4j unavailable: {type(e).__name__} - graph features disabled")
                Neo4jClient._failure_logged = True
            return False
    
    async def close(self):
        """Close Neo4j driver"""
        if self._driver:
            await self._driver.close()
    
    async def query(self, query: str, parameters: dict = None, max_retries: int = 2):
        """Execute Cypher query with silent retry logic for connection issues"""
        if not self._driver:
            return []
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with self._driver.session() as session:
                    result = await session.run(query, parameters)
                    return [record.data() async for record in result]
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    # Quick retry with minimal backoff
                    await asyncio.sleep(0.2 * (attempt + 1))
                    continue
        
        # Only log once if all retries fail (reduces noise)
        if last_error:
            logger.debug(f"Neo4j query unavailable after {max_retries} attempts: {last_error}")
        return []

# Global Neo4j client instance
neo4j_client = Neo4jClient()

# Export driver for backward compatibility
driver = neo4j_client._driver

def get_neo4j_driver():
    """Get the Neo4j driver instance for direct use"""
    return neo4j_client._driver

async def close_neo4j():
    await neo4j_client.close()

async def query_graph(query: str, parameters: dict = None):
    """
    Runs a Cypher query and returns the results.
    """
    return await neo4j_client.query(query, parameters)

class GraphMemoryService:
    """
    Perfect Graph Memory Service for PRISM AI.
    Stores user relationships and enables intelligent AI behavior.
    """
    
    async def create_user_node(self, user_id: str, email: str, name: str) -> bool:
        """
        Create or update user node in graph.
        🟢 Rule: Uses MERGE to avoid duplicates
        """
        if not neo4j_client.is_available:
            return False

        query = """
        MERGE (u:User {id: $user_id})
        SET u.email = $email,
            u.name = $name,
            u.createdAt = $timestamp,
            u.updatedAt = $timestamp
        RETURN u
        """
        
        try:
            await query_graph(query, {
                "user_id": user_id,
                "email": email, 
                "name": name,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ User node created/updated: {email}")
            return True
        except Exception as e:
            print(f"❌ Error creating user node: {e}")
            return False

    async def add_dynamic_relationship(self, user_id: str, target: str, relationship_type: str, target_label: str = "Entity") -> bool:
        """
        Add a dynamic relationship between User and an Entity.
        Allows flexible types like DISLIKES, KNOWS, LIVES_IN, etc.
        """
        if not neo4j_client.is_available:
            return False

        # Sanitize relationship type (uppercase, alphanumeric + underscore)
        safe_rel_type = "".join(c for c in relationship_type.upper() if c.isalnum() or c == '_')
        if not safe_rel_type:
            safe_rel_type = "RELATED_TO"
            
        safe_label = "".join(c for c in target_label if c.isalnum())
        if not safe_label:
            safe_label = "Entity"

        query = f"""
        MERGE (u:User {{id: $user_id}})
        MERGE (t:{safe_label} {{name: $target}})
        MERGE (u)-[r:{safe_rel_type}]->(t)
        SET r.createdAt = $timestamp,
            r.updatedAt = $timestamp,
            r.source = 'holographic_extractor'
        RETURN u, r, t
        """
        
        try:
            await query_graph(query, {
                "user_id": user_id,
                "target": target,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ Dynamic relationship added: {user_id} -[{safe_rel_type}]-> {target}")
            return True
        except Exception as e:
            print(f"❌ Error adding dynamic relationship: {e}")
            return False

    async def add_user_interest(self, user_id: str, interest: str, category: str = "interest") -> bool:
        """
        Add interest/hobby relationship for user.
        Example: (User) ---LIKES---> (AI)
        """
        if not neo4j_client.is_available:
            return False

        query = """
        MERGE (u:User {id: $user_id})
        MERGE (i:Interest {name: $interest, category: $category})
        MERGE (u)-[r:LIKES]->(i)
        SET r.createdAt = $timestamp,
            r.strength = COALESCE(r.strength, 0) + 1
        RETURN u, i, r
        """
        
        try:
            await query_graph(query, {
                "user_id": user_id,
                "interest": interest.lower(),
                "category": category,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ Interest added: {user_id} likes {interest}")
            return True
        except Exception as e:
            print(f"❌ Error adding interest: {e}")
            return False

    async def add_interest_relationship(self, user_id: str, interest: str, category: str = "interest") -> bool:
        """
        Backwards-compatible alias for adding an interest relationship.
        Matches older callers expecting `add_interest_relationship`.
        """
        return await self.add_user_interest(user_id, interest, category)
    
    async def add_user_task(self, user_id: str, task_id: str, title: str, status: str = "pending") -> bool:
        """
        Add task relationship for user.
        Example: (User) ---HAS_TASK---> (Task)
        """
        if not neo4j_client.is_available:
            return False

        query = """
        MERGE (u:User {id: $user_id})
        MERGE (t:Task {taskId: $task_id})
        SET t.title = $title,
            t.status = $status,
            t.createdAt = $timestamp
        MERGE (u)-[r:HAS_TASK]->(t)
        SET r.createdAt = $timestamp
        RETURN u, t, r
        """
        
        try:
            await query_graph(query, {
                "user_id": user_id,
                "task_id": task_id,
                "title": title,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ Task relationship added: {task_id}")
            return True
        except Exception as e:
            print(f"❌ Error adding task: {e}")
            return False
    
    async def update_task_status(self, user_id: str, task_id: str, status: str) -> bool:
        """Update task status in graph"""
        if not neo4j_client.is_available:
            return False

        query = """
        MATCH (u:User {id: $user_id})-[:HAS_TASK]->(t:Task {taskId: $task_id})
        SET t.status = $status,
            t.updatedAt = $timestamp
        RETURN t
        """
        
        try:
            result = await query_graph(query, {
                "user_id": user_id,
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if result:
                print(f"✅ Task status updated: {task_id} -> {status}")
                return True
            return False
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            return False
    
    async def get_user_interests(self, user_id: str) -> List[str]:
        """Get all interests/hobbies for a user"""
        if not neo4j_client.is_available:
            return []

        query = """
        MATCH (u:User {id: $user_id})-[:LIKES]->(i:Interest)
        RETURN i.name as interest, i.category as category
        ORDER BY i.name
        """
        
        try:
            result = await query_graph(query, {"user_id": user_id})
            interests = [record["interest"] for record in result]
            print(f"✅ Found {len(interests)} interests for user {user_id}")
            return interests
        except Exception as e:
            print(f"❌ Error getting interests: {e}")
            return []
    
    async def get_user_tasks(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks for user, optionally filtered by status"""
        if not neo4j_client.is_available:
            return []

        base_query = "MATCH (u:User {id: $user_id})-[:HAS_TASK]->(t:Task)"
        
        if status:
            query = f"{base_query} WHERE t.status = $status RETURN t ORDER BY t.createdAt DESC"
            params = {"user_id": user_id, "status": status}
        else:
            query = f"{base_query} RETURN t ORDER BY t.createdAt DESC"
            params = {"user_id": user_id}
        
        try:
            result = await query_graph(query, params)
            tasks = []
            for record in result:
                task_data = record["t"]
                tasks.append({
                    "taskId": task_data.get("taskId"),
                    "title": task_data.get("title"),
                    "status": task_data.get("status"),
                    "createdAt": task_data.get("createdAt")
                })
            
            print(f"✅ Found {len(tasks)} tasks for user {user_id}")
            return tasks
        except Exception as e:
            print(f"❌ Error getting tasks: {e}")
            return []
    
    async def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete user summary from graph.
        Perfect for AI context building.
        """
        if not neo4j_client.is_available:
            return {}

        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[:LIKES]->(i:Interest)
        OPTIONAL MATCH (u)-[:HAS_TASK]->(t:Task)
        
        RETURN u.name as name,
               u.email as email,
               collect(DISTINCT i.name) as interests,
               collect(DISTINCT {
                   taskId: t.taskId, 
                   title: t.title, 
                   status: t.status
               }) as tasks
        """
        
        try:
            result = await query_graph(query, {"user_id": user_id})
            
            if result:
                data = result[0]
                
                # Count tasks by status
                tasks = [t for t in data.get("tasks", []) if t.get("taskId")]
                pending_tasks = len([t for t in tasks if t.get("status") == "pending"])
                completed_tasks = len([t for t in tasks if t.get("status") == "completed"])
                
                summary = {
                    "name": data.get("name", "Unknown"),
                    "email": data.get("email", ""),
                    "interests": [i for i in data.get("interests", []) if i],
                    "total_tasks": len(tasks),
                    "pending_tasks": pending_tasks,
                    "completed_tasks": completed_tasks,
                    "recent_tasks": tasks[:5]  # Last 5 tasks
                }
                
                print(f"✅ Generated user summary for {user_id}")
                return summary
            
            return {}
        except Exception as e:
            print(f"❌ Error getting user summary: {e}")
            return {}

    async def update_user_name(self, user_id: str, name: str) -> bool:
        """
        Update or create the user's node and set the name property.
        """
        if not neo4j_client.is_available:
            return False

        query = """
        MERGE (u:User {id: $user_id})
        SET u.name = $name,
            u.updatedAt = $timestamp
        RETURN u
        """
        try:
            await query_graph(query, {
                "user_id": user_id,
                "name": name,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ User name set for {user_id} -> {name}")
            return True
        except Exception as e:
            print(f"❌ Error updating user name: {e}")
            return False

    async def add_user_property(self, user_id: str, key: str, value: Any) -> bool:
        """
        Add or update a primitive property directly on the User node.
        Example: key="location", value="New York" sets u.location = "New York".
        """
        if not neo4j_client.is_available:
            return False

        # Safely interpolate property key by restricting to alphanumeric and underscore
        safe_key = "".join(ch for ch in key if ch.isalnum() or ch == "_")
        if not safe_key:
            return False
        query = f"""
        MERGE (u:User {{id: $user_id}})
        SET u.{safe_key} = $value,
            u.updatedAt = $timestamp
        RETURN u
        """
        try:
            await query_graph(query, {
                "user_id": user_id,
                "value": value,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"✅ User property set: {user_id}.{safe_key} -> {value}")
            return True
        except Exception as e:
            print(f"❌ Error setting user property {safe_key}: {e}")
            return False
    
    async def find_related_interests(self, user_id: str, limit: int = 5) -> List[str]:
        """
        Find interests related to user's current interests.
        Useful for recommendations.
        """
        if not neo4j_client.is_available:
            return []

        query = """
        MATCH (u:User {id: $user_id})-[:LIKES]->(userInterest:Interest)
        MATCH (otherUser:User)-[:LIKES]->(userInterest)
        MATCH (otherUser)-[:LIKES]->(relatedInterest:Interest)
        WHERE NOT (u)-[:LIKES]->(relatedInterest)
        
        RETURN relatedInterest.name as suggestion, 
               count(*) as frequency
        ORDER BY frequency DESC
        LIMIT $limit
        """
        
        try:
            result = await query_graph(query, {"user_id": user_id, "limit": limit})
            suggestions = [record["suggestion"] for record in result]
            print(f"✅ Found {len(suggestions)} interest suggestions for {user_id}")
            return suggestions
        except Exception as e:
            print(f"❌ Error finding related interests: {e}")
            return []
    
    async def delete_user_graph_data(self, user_id: str) -> bool:
        """Delete all graph data for a user"""
        if not neo4j_client.is_available:
            return False

        query = """
        MATCH (u:User {id: $user_id})
        OPTIONAL MATCH (u)-[r]->(n)
        DELETE r, u, n
        """
        
        try:
            await query_graph(query, {"user_id": user_id})
            print(f"✅ Deleted graph data for user: {user_id}")
            return True
        except Exception as e:
            print(f"[Neo4j] Error deleting user graph data: {e}")
            return False

async def create_user_in_graph(user_id: str, email: str, name: str) -> bool:
    """Simple function to create user in graph"""
    return await graph_memory.create_user_node(user_id, email, name)

async def add_interest_to_user(user_id: str, interest: str, category: str = "interest") -> bool:
    """Simple function to add interest to user"""
    return await graph_memory.add_user_interest(user_id, interest, category)

async def add_task_to_user(user_id: str, task_id: str, title: str, status: str = "pending") -> bool:
    """Simple function to add task to user"""
    return await graph_memory.add_user_task(user_id, task_id, title, status)

async def get_user_context_summary(user_id: str) -> str:
    """Get formatted user context summary for AI"""
    summary = await graph_memory.get_user_summary(user_id)
    
    if not summary:
        return "No user context available."
    
    context_parts = [
        f"User: {summary.get('name', 'Unknown')}",
    ]
    
    if summary.get('interests'):
        interests_str = ", ".join(summary['interests'])
        context_parts.append(f"Interests: {interests_str}")
    
    if summary.get('total_tasks', 0) > 0:
        context_parts.append(f"Tasks: {summary['pending_tasks']} pending, {summary['completed_tasks']} completed")
    
    return " | ".join(context_parts)

# 🎀 PINECONE CLIENT PLACEHOLDER (Vector Memory)
# TODO: Implement when Pinecone is available

class PineconeClient:
    """Pinecone client for vector memory operations (placeholder)"""
    
    def __init__(self):
        # TODO: Initialize Pinecone client when available
        pass
    
    async def get_user_memories(self, user_id: str) -> list:
        """Get vector memories for user"""
        # TODO: Implement Pinecone query
        return []
    
    async def add_memory(self, user_id: str, memory_text: str) -> bool:
        """Add vector memory to Pinecone"""
        # TODO: Implement Pinecone upsert
        return True
    
    async def search_similar_memories(self, user_id: str, query: str, top_k: int = 5) -> list:
        """Search for similar memories"""
        # TODO: Implement semantic search
        return []

# 🧠 ADVANCED NEO4J CLIENT FOR AI MEMORY MANAGEMENT

class AdvancedNeo4jClient:
    """Neo4j client with advanced memory management for AI model integration"""
    
    def __init__(self):
        self.driver = neo4j_client._driver  # Use the wrapper client's driver
        self.graph_memory = graph_memory
        self.neo4j_client = neo4j_client  # Reference to wrapper
    
    # USER RELATIONSHIPS OPERATIONS
    async def get_user_relationships(self, user_id: str) -> list:
        """Get all relationships for a user from the graph"""
        try:
            query = """
            MATCH (u:User {id: $user_id})-[r]->(n)
            RETURN type(r) as relationship, n.title as target, n.name as target_name,
                   labels(n) as target_labels, r.createdAt as created_at
            ORDER BY r.createdAt DESC
            """
            
            result = await query_graph(query, {"user_id": user_id})
            return result if result else []
        except Exception as e:
            print(f"Error getting user relationships: {e}")
            return []
    
    async def get_user_interests(self, user_id: str) -> list:
        """Get user interests and their connections from the graph"""
        try:
            query = """
            MATCH (u:User {id: $user_id})-[:LIKES|INTERESTED_IN]->(i:Interest)
            RETURN i.name as interest, i.category as category, i.strength as strength
            ORDER BY i.strength DESC
            """
            
            result = await query_graph(query, {"user_id": user_id})
            return result if result else []
        except Exception as e:
            print(f"Error getting user interests: {e}")
            return []
    
    async def merge_user_relationship(self, user_id: str, relation_type: str, target_value: str) -> bool:
        """Create or update a relationship using MERGE (prevents duplicates)"""
        try:
            # Determine target node type based on relation type
            if relation_type in ["LIKES", "INTERESTED_IN", "FAVORITE_LANGUAGE"]:
                target_label = "Interest"
                target_property = "name"
            elif relation_type in ["LIVES_IN", "WORKS_AT"]:
                target_label = "Location"
                target_property = "name"
            elif relation_type in ["HAS_SKILL", "LEARNING"]:
                target_label = "Skill"
                target_property = "name"
            else:
                target_label = "Entity"
                target_property = "name"
            
            query = f"""
            MERGE (u:User {{id: $user_id}})
            MERGE (t:{target_label} {{{target_property}: $target_value}})
            MERGE (u)-[r:{relation_type}]->(t)
            SET r.createdAt = CASE WHEN r.createdAt IS NULL THEN $timestamp ELSE r.createdAt END,
                r.updatedAt = $timestamp,
                r.strength = COALESCE(r.strength, 1) + 0.1
            RETURN u, r, t
            """
            
            result = await query_graph(query, {
                "user_id": user_id,
                "target_value": target_value,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return len(result) > 0
        except Exception as e:
            print(f"Error merging user relationship: {e}")
            return False
    
    # ADVANCED QUERY OPERATIONS
    async def get_related_interests(self, user_id: str, interest: str) -> list:
        """Find interests related to a specific user interest"""
        try:
            query = """
            MATCH (u:User {id: $user_id})-[:LIKES|INTERESTED_IN]->(i:Interest {name: $interest})
            MATCH (i)-[r]-(related:Interest)
            WHERE NOT (u)-[:LIKES|INTERESTED_IN]->(related)
            RETURN related.name as suggestion, type(r) as relationship_type, related.category as category
            LIMIT 5
            """
            
            result = await query_graph(query, {
                "user_id": user_id,
                "interest": interest
            })
            return result if result else []
        except Exception as e:
            print(f"Error getting related interests: {e}")
            return []
    
    async def get_user_path_to_goal(self, user_id: str, goal: str) -> list:
        """Find path from user's interests to a specific goal"""
        try:
            query = """
            MATCH path = shortestPath((u:User {id: $user_id})-[*..4]-(g:Goal {name: $goal}))
            RETURN [n in nodes(path) | n.name] as path_nodes,
                   [r in relationships(path) | type(r)] as relationships
            """
            
            result = await query_graph(query, {
                "user_id": user_id,
                "goal": goal
            })
            return result if result else []
        except Exception as e:
            print(f"Error getting path to goal: {e}")
            return []
    
    # MEMORY STRENGTH OPERATIONS
    async def strengthen_relationship(self, user_id: str, relation_type: str, target: str, increment: float = 0.1) -> bool:
        """Increase the strength of a relationship (for frequently accessed memories)"""
        try:
            query = """
            MATCH (u:User {id: $user_id})-[r]->(t)
            WHERE type(r) = $relation_type AND (t.name = $target OR t.title = $target)
            SET r.strength = COALESCE(r.strength, 1) + $increment,
                r.lastAccessed = $timestamp
            RETURN r.strength as new_strength
            """
            
            result = await query_graph(query, {
                "user_id": user_id,
                "relation_type": relation_type,
                "target": target,
                "increment": increment,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return len(result) > 0
        except Exception as e:
            print(f"Error strengthening relationship: {e}")
            return False
    
    # CLEANUP OPERATIONS
    async def remove_weak_relationships(self, user_id: str, threshold: float = 0.5) -> bool:
        """Remove relationships below a certain strength threshold"""
        try:
            query = """
            MATCH (u:User {id: $user_id})-[r]-(n)
            WHERE r.strength < $threshold
            DELETE r
            RETURN count(r) as removed_count
            """
            
            result = await query_graph(query, {
                "user_id": user_id,
                "threshold": threshold
            })
            
            return True
        except Exception as e:
            print(f"Error removing weak relationships: {e}")
            return False

# Create global instances
neo4j_client = Neo4jClient()
graph_memory = GraphMemoryService()
