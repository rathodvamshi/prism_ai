from app.db.neo4j_client import query_graph
from app.utils.llm_client import get_llm_response
import json

async def extract_relations(text: str):
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
        start = cleaned.find('[')
        end = cleaned.rfind(']') + 1
        return json.loads(cleaned[start:end])
    except:
        return []

async def save_knowledge(user_id: str, text: str):
    """
    Extracts facts and merges them into the Graph.
    """
    relations = await extract_relations(text)
    
    if not relations:
        return
        
    print(f"🕸️ Saving to Graph: {relations}")

    for rel in relations:
        # Cypher Query: Merge nodes and relationships so we don't create duplicates
        cypher = """
        MERGE (h:Entity {name: $head_name})
        MERGE (t:Entity {name: $tail_name})
        MERGE (h)-[r:RELATIONSHIP {type: $rel_type}]->(t)
        """
        # Note: Dynamic relationship types in Cypher are tricky, 
        # so for simplicity in this baby-level version, we treat relation 'type' as a property 
        # or we use APOC. But let's stick to a generic relationship with a type property for safety.
        
        # Better simple approach for beginners:
        # (User)-[:KNOWS]->(Python)
        
        query = f"""
        MERGE (h:Entity {{name: $head}})
        MERGE (t:Entity {{name: $tail}})
        MERGE (h)-[:{rel['type'].upper()}]->(t)
        """
        
        try:
            await query_graph(query, {"head": rel['head'], "tail": rel['tail']})
        except Exception as e:
            print(f"Graph Write Error: {e}")

async def retrieve_knowledge(user_id: str) -> str:
    """
    Fetches everything the graph knows about the 'User'.
    """
    query = """
    MATCH (u:Entity {name: 'User'})-[r]->(t:Entity)
    RETURN u.name, type(r) as relation, t.name
    LIMIT 10
    """
    results = await query_graph(query)
    
    if not results:
        return ""
        
    facts = [f"User {r['relation']} {r['t.name']}" for r in results]
    return "\n".join(facts)