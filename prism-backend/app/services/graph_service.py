from app.db.neo4j_client import query_graph
from app.utils.llm_client import get_llm_response
import json
from typing import List, Dict, Any


async def extract_relations(text: str) -> List[Dict[str, Any]]:
    """
    Uses LLM to extract knowledge triplets from text.
    Example: "I live in Delhi" -> {"head": "User", "type": "LIVES_IN", "tail": "Delhi"}
    """
    system_prompt = """
    You are a Knowledge Graph extractor.
    Extract key relationships from the user's message.
    Return a list of JSON objects: {"head": "Entity1", "type": "RELATIONSHIP", "tail": "Entity2"}
    
    Rules:
    - "head" should usually be "User" if the user talks about themselves.
    - "type" should be uppercase (e.g., LIKES, WORKS_AT, LIVES_IN).
    - If no clear fact is present, return empty list [].
    
    Example Input: "I love coding in Python"
    Example Output: [{"head": "User", "type": "LIKES", "tail": "Coding"}, {"head": "User", "type": "KNOWS", "tail": "Python"}]
    """
    
    response = await get_llm_response(prompt=text, system_prompt=system_prompt)
    
    try:
        # Clean potential markdown
        cleaned = response.replace("```json", "").replace("```", "").strip()
        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1
        return json.loads(cleaned[start:end])
    except Exception:
        return []


async def _extract_name_from_text(text: str) -> str:
    """
    Very lightweight name extractor for patterns like:
      - "Hello, this is Rathod"
      - "Hi, my name is Rathod"
    """
    lower = text.lower()
    name_part = ""
    if "my name is" in lower:
        name_part = text[lower.find("my name is") + len("my name is") :]
    elif "this is " in lower:
        name_part = text[lower.find("this is ") + len("this is ") :]

    name_part = name_part.strip().strip(".,!")
    # Take only the first few tokens to avoid grabbing whole sentences
    tokens = name_part.split()
    if not tokens:
        return ""
    # Simple heuristic: one or two tokens is usually enough for a name
    candidate = " ".join(tokens[:2])
    return candidate.strip()


async def save_knowledge(user_id: str, text: str):
    """
    Extracts facts and merges them into the Graph.
    Special handling for names: store per-user name on a dedicated User node.
    """
    # 1) Name handling (high priority, low latency)
    print(f"[Graph] save_knowledge called for user_id={user_id} text_snippet={text[:80]}")
    lower = (text or "").lower()
    if "my name is" in lower or "this is " in lower:
        extracted_name = await _extract_name_from_text(text)
        if extracted_name:
            try:
                # MERGE (u:User {id: $user_id}) SET u.name = $extracted_name
                name_query = """
                MERGE (u:User {id: $user_id})
                SET u.name = $name
                """
                await query_graph(name_query, {"user_id": user_id, "name": extracted_name})
                print(f"✅ Saved user name to Neo4j: {user_id} -> {extracted_name}")
            except Exception as e:
                print(f"Graph Name Save Error: {e}")

    # 2) Generic relation extraction (existing behavior)
    relations = await extract_relations(text)
    if not relations:
        return

    print(f"🕸️ Saving to Graph: {relations}")
    
    # Track if Neo4j save succeeds for MongoDB fallback
    neo4j_failed = False

    for rel in relations:
        try:
            rel_type = (rel.get("type") or "RELATED_TO").upper()
            head = rel.get("head") or "User"
            tail = rel.get("tail") or ""
            if not tail:
                continue

            params = {"user_id": user_id, "head": head, "tail": tail}

            # 🧠 MEMORY HARDENING - Fact Updater (idempotent MERGE, no duplicates)
            # If the relationship is user-scoped, always anchor on User{id}
            if rel_type == "LIVES_IN":
                # Clear old LIVES_IN relationships before setting the new city
                await query_graph(
                    "MATCH (u:User {id: $user_id})-[r:LIVES_IN]->() DELETE r",
                    {"user_id": user_id}
                )

            if head.lower() == "user":
                query = f"""
                MERGE (u:User {{id: $user_id}})
                MERGE (t:Entity {{name: $tail}})
                MERGE (u)-[:{rel_type}]->(t)
                """
                await query_graph(query, params)
            else:
                # Fallback for non-user heads: still use MERGE to avoid duplicates
                query = f"""
                MERGE (h:Entity {{name: $head}})
                MERGE (t:Entity {{name: $tail}})
                MERGE (h)-[:{rel_type}]->(t)
                """
                await query_graph(query, params)
        except Exception as e:
            print(f"Graph Write Error: {e}")
            neo4j_failed = True
    
    # MongoDB fallback: Save extracted facts when Neo4j fails
    if neo4j_failed:
        try:
            from app.db.mongo_client import memory_collection
            
            # Prepare structured data from relations
            update_data = {}
            graph_facts = []
            
            for rel in relations:
                rel_type = (rel.get("type") or "RELATED_TO").upper()
                tail = rel.get("tail") or ""
                
                if not tail:
                    continue
                
                # Store name
                if rel_type == "NAME":
                    update_data["name"] = tail
                    graph_facts.append(f"User Name: {tail}")
                
                # Store likes/preferences
                elif rel_type == "LIKES":
                    if "interests" not in update_data:
                        update_data["interests"] = []
                    update_data["interests"].append(tail)
                    graph_facts.append(f"User LIKES {tail}")
                
                # Store other relationships
                else:
                    graph_facts.append(f"User {rel_type} {tail}")
            
            # Save to MongoDB
            if update_data or graph_facts:
                await memory_collection.update_one(
                    {"userId": user_id},
                    {
                        "$set": update_data,
                        "$addToSet": {"graph_facts": {"$each": graph_facts}}
                    },
                    upsert=True
                )
                print(f"✅ MongoDB fallback: Saved {len(graph_facts)} facts for user {user_id}")
        except Exception as mongo_err:
            print(f"❌ MongoDB fallback save failed: {mongo_err}")


async def retrieve_knowledge(user_id: str) -> str:
    """
    Fetches everything the graph knows about this specific user.
    Returns empty string if Neo4j is unavailable (fallback chain handles it).
    """
    facts: List[str] = []

    # 1) Fetch user node with name (permanent identity)
    try:
        name_query = """
        MATCH (u:User {id: $user_id})
        RETURN u.name AS name
        LIMIT 1
        """
        name_results = await query_graph(name_query, {"user_id": user_id})
        if name_results:
            name_row = name_results[0]
            name_value = name_row.get("name") or name_row.get("u.name")
            if name_value:
                # Clean up any trailing commas or extra characters
                name_value = name_value.strip().rstrip(',')
                facts.append(f"User Name: {name_value}")
    except Exception:
        pass  # Silent fail, fallback chain handles it

    # 2) Fetch generic relationships for this user
    try:
        rel_query = """
        MATCH (u:User {id: $user_id})-[r]->(t)
        RETURN type(r) AS relation, t.name AS target
        LIMIT 20
        """
        rel_results = await query_graph(rel_query, {"user_id": user_id})
        for row in rel_results or []:
            relation = row.get("relation") or row.get("type(r)")
            target = row.get("target") or row.get("t.name")
            if relation and target:
                facts.append(f"User {relation} {target}")
    except Exception:
        pass  # Silent fail, fallback chain handles it

    # 3) Fetch from Entity nodes (User)-[:LIKES]->(:Entity)
    try:
        entity_query = """
        MATCH (:User {id: $user_id})-[:RELATED_TO|LIKES|KNOWS|ENJOYS]->(e:Entity)
        RETURN e.name AS entity
        LIMIT 20
        """
        entity_results = await query_graph(entity_query, {"user_id": user_id})
        for row in entity_results or []:
            entity = row.get("entity") or row.get("e.name")
            if entity:
                facts.append(f"User likes {entity}")
    except Exception:
        pass  # Silent fail

    facts_str = "\n".join(facts)
    if facts_str:
        print(f"[Graph] Retrieved {len(facts)} facts for user {user_id[:8]}...")
    return facts_str