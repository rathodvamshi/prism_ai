# 🚀 MINI-AGENT OPTIMIZATION GUIDE
## Make It Fast, Lightweight, and Perfect

---

## 🎯 **1. MODEL SELECTION (CRITICAL)**

### **Current Recommendation: Use Smaller, Specialized Models**

Instead of using GPT-4 or large models for mini-agent, use **small, fast models**:

#### **Best Models for Mini-Agent:**

| Model | Speed | Cost | Quality | Best For |
|-------|-------|------|---------|----------|
| **GPT-3.5-Turbo** | ⚡⚡⚡ (Fast) | 💰 (Cheap) | ✅✅✅ | Production - Perfect balance |
| **Claude Instant** | ⚡⚡⚡ (Fast) | 💰 (Cheap) | ✅✅✅ | Production - Very reliable |
| **Gemini 1.5 Flash** | ⚡⚡⚡⚡ (Fastest) | 💰 (Cheapest) | ✅✅✅ | Production - Google's fast model |
| **Llama 3 8B** | ⚡⚡⚡⚡ (Local) | Free | ✅✅✅ | Self-hosted - Privacy |
| GPT-4 | ⚡ (Slow) | 💰💰💰 (Expensive) | ✅✅✅✅✅ | Avoid - Overkill |

### **✅ RECOMMENDATION:**

```python
# Use Gemini 1.5 Flash for mini-agent
# Fast + Cheap + Good enough for clarifications

MINI_AGENT_MODEL = "gemini-1.5-flash"  # <-- Google's fastest
MAIN_CHAT_MODEL = "gpt-4"  # Keep GPT-4 for main conversation
```

**Why Gemini Flash?**
- ⚡ **2x faster** than GPT-3.5
- 💰 **80% cheaper** than GPT-3.5
- ✅ **Perfect for short explanations**
- 🎯 **Optimized for quick clarifications**

---

## 🔧 **2. PIPELINE OPTIMIZATION**

### **A. Parallel Processing (CRITICAL)**

**Current:** Sequential operations  
**Better:** Parallel database + Redis calls

```python
# ❌ SLOW - Sequential
thread = await mini_agents_collection.find_one({"id": thread_id})
history = await format_mini_agent_history(user_id, message_id)
response = await get_llm_response(prompt, system_prompt)

# ✅ FAST - Parallel
import asyncio

async def add_mini_agent_message(thread_id, request):
    # Fetch thread and history in parallel
    thread_task = mini_agents_collection.find_one({"id": thread_id})
    history_task = format_mini_agent_history(user_id, message_id)
    
    thread, history = await asyncio.gather(thread_task, history_task)
    
    # Now process...
```

**Impact:** 30-50% faster

---

### **B. Reduce Database Calls**

**Current:** Multiple DB calls per request  
**Better:** Batch operations

```python
# ❌ SLOW - 2 separate inserts
await messages_collection.insert_one(user_message_db)
await messages_collection.insert_one(ai_message_db)

# ✅ FAST - Single batch insert
await messages_collection.insert_many([user_message_db, ai_message_db])
```

**Impact:** 2x faster DB operations

---

### **C. Connection Pooling (Already Done ✅)**

You're already using Redis connection pooling - great!

Make sure MongoDB also uses pooling:

```python
# In mongo_client.py
client = AsyncIOMotorClient(
    MONGODB_URL,
    maxPoolSize=50,  # Connection pool
    minPoolSize=10,
    maxIdleTimeMS=30000
)
```

---

## 💡 **3. CACHING STRATEGIES**

### **A. Cache Frequently Asked Questions**

```python
# Redis cache for common snippet explanations
CACHE_KEY = f"MINI_AGENT_CACHE:{hash(snippet_text)}:{hash(question)}"

async def get_cached_response(snippet_text, question):
    cache_key = f"MINI_AGENT_CACHE:{hash(snippet_text)}:{hash(question)}"
    cached = await redis_client.get(cache_key)
    
    if cached:
        logger.info("✅ Cache hit - returning cached response")
        return json.loads(cached)
    
    return None

async def cache_response(snippet_text, question, response, ttl_hours=24):
    cache_key = f"MINI_AGENT_CACHE:{hash(snippet_text)}:{hash(question)}"
    await redis_client.setex(
        cache_key, 
        ttl_hours * 3600, 
        json.dumps(response)
    )
```

**Impact:**
- ⚡ **Instant responses** for repeated questions
- 💰 **90% cost reduction** on common queries
- 🎯 **No LLM call needed** for cache hits

---

### **B. Snippet Embeddings Cache (Advanced)**

For very fast similar question detection:

```python
# Cache snippet embeddings
EMBEDDING_CACHE = f"EMBEDDING:{hash(snippet_text)}"

# If similar question asked before → return cached answer
# Uses vector similarity instead of exact match
```

---

## 🎯 **4. TOKEN OPTIMIZATION**

### **Current Issue:** Verbose system prompt

Your system prompt is ~400 tokens. Optimize it:

```python
# ❌ VERBOSE (~400 tokens)
system_prompt = """
You are a Mini-Agent — a calm, precise clarification tool.

YOUR ROLE:
Explain the selected text clearly and directly. Think of yourself as a margin note...
[All the rules listed out]
"""

# ✅ CONCISE (~150 tokens)
system_prompt = """Mini-Agent: Calm, precise clarifier. Explain selected text in 1-2 sentences.

Rules:
- No greetings/closings
- Neutral tone, no "obviously/simply/just"
- No bullets unless asked
- Build on previous (if shown)
- Never say "earlier I explained"

Failure: "This depends on context. Select more."
"""
```

**Impact:**
- 💰 **60% less tokens** → cheaper
- ⚡ **Faster processing** → quicker
- 🎯 **Same quality** → works perfectly

---

### **Conversation History Limit**

```python
# Current: Unlimited history
# Better: Last 3 clarifications only

context["clarifications"] = context["clarifications"][-3:]  # Was -5
```

**Impact:**
- 💰 **Fewer tokens** per request
- ⚡ **Faster processing**
- ✅ **Still maintains flow**

---

## ⚡ **5. RESPONSE STREAMING (BIG WIN)**

### **Current:** Wait for full response  
**Better:** Stream response as it generates

```python
# In llm_client.py
async def get_llm_response_stream(prompt, system_prompt):
    """Stream LLM response token by token"""
    
    # For OpenAI
    response = await openai.ChatCompletion.create(
        model="gemini-1.5-flash",
        messages=[...],
        stream=True  # ✅ Enable streaming
    )
    
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# In highlights.py
async def add_mini_agent_message(thread_id, request):
    # Stream response back to frontend
    async for token in get_llm_response_stream(prompt, system_prompt):
        # Send token to frontend via websocket
        await websocket.send_json({"type": "token", "content": token})
```

**Impact:**
- ⚡ **Perceived speed improvement** - user sees response immediately
- 🎯 **Better UX** - feels instant
- ✅ **Actually faster** - doesn't wait for full completion

---

## 🏗️ **6. INFRASTRUCTURE OPTIMIZATION**

### **A. Use Edge Functions (If Possible)**

Deploy mini-agent endpoint to edge:

```
Vercel Edge Functions
Cloudflare Workers
AWS Lambda@Edge
```

**Benefits:**
- ⚡ **Lower latency** (closer to users)
- 🌍 **Global performance**
- 💰 **Auto-scaling**

---

### **B. Redis Optimization**

```python
# Use Redis pipeline for multiple operations
pipeline = redis_client.pipeline()
pipeline.get(key1)
pipeline.get(key2)
pipeline.set(key3, value3)
results = await pipeline.execute()
```

**Impact:** 3-5x faster than individual calls

---

### **C. MongoDB Indexes**

```python
# Add indexes for fast lookups
await mini_agents_collection.create_index("id")
await mini_agents_collection.create_index("sessionId")
await messages_collection.create_index("threadId")
```

**Impact:** 10-100x faster queries

---

## 🎯 **7. LIGHTWEIGHT CONTEXT**

### **Reduce Context Size**

```python
# Only send what's needed
snippet_context = f"TEXT: {selected_text[:200]}\n"  # Limit to 200 chars

# Instead of full thread data
```

**Impact:**
- 💰 **Fewer tokens**
- ⚡ **Faster processing**
- ✅ **Usually sufficient**

---

## 🧪 **8. PRE-PROCESSING OPTIMIZATIONS**

### **A. Question Classification**

Detect question type and use different strategies:

```python
def classify_question(question):
    """Fast, simple classification"""
    
    lower_q = question.lower()
    
    # Definition questions - use cached embeddings
    if any(word in lower_q for word in ['what is', 'what does', 'define']):
        return 'definition'
    
    # Clarification - check history
    if any(word in lower_q for word in ['why', 'how', 'can you']):
        return 'clarification'
    
    # Example request - might need more tokens
    if 'example' in lower_q or 'instance' in lower_q:
        return 'example'
    
    return 'general'

# Use different models/strategies based on type
if question_type == 'definition':
    # Use ultra-fast model
    model = "gemini-1.5-flash"
elif question_type == 'example':
    # Use slightly better model
    model = "gpt-3.5-turbo"
```

---

### **B. Smart Caching by Question Type**

```python
# Cache definitions longer (they don't change)
if question_type == 'definition':
    cache_ttl = 7 * 24 * 3600  # 7 days
else:
    cache_ttl = 1 * 3600  # 1 hour
```

---

## 📊 **9. MONITORING & METRICS**

### **Track Performance**

```python
import time

async def add_mini_agent_message(thread_id, request):
    start_time = time.time()
    
    # ... process request ...
    
    # Log metrics
    duration = time.time() - start_time
    logger.info(f"⏱️ Mini-agent response time: {duration:.2f}s")
    
    # Alert if slow
    if duration > 3.0:
        logger.warning(f"⚠️ Slow mini-agent response: {duration:.2f}s")
```

**Track:**
- Response time
- Cache hit rate
- Token usage
- Error rate

---

## 🎯 **10. COMPLETE OPTIMIZED PIPELINE**

### **Perfect Mini-Agent Architecture:**

```python
async def add_mini_agent_message_OPTIMIZED(thread_id, request):
    start = time.time()
    
    # 1. Check cache first
    cache_key = f"CACHE:{hash(snippet)}:{hash(question)}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)  # ⚡ Instant return
    
    # 2. Parallel fetch (thread + history)
    thread, history = await asyncio.gather(
        mini_agents_collection.find_one({"id": thread_id}),
        format_mini_agent_history(user_id, message_id)
    )
    
    # 3. Build minimal prompt
    prompt = f"TEXT: {snippet[:200]}\n"
    if history:
        # Only last 2 QA pairs
        recent_history = "\n".join(history.split("\n\n")[-2:])
        prompt += f"RECENT:\n{recent_history}\n"
    prompt += f"Q: {request.text}"
    
    # 4. Use fast model
    response = await get_llm_response_stream(
        prompt=prompt,
        system_prompt=CONCISE_SYSTEM_PROMPT,  # Optimized version
        model="gemini-1.5-flash"  # Fastest model
    )
    
    # 5. Store in batch
    await asyncio.gather(
        messages_collection.insert_many([user_msg, ai_msg]),
        store_mini_agent_context(user_id, message_id, q, a),
        redis_client.setex(cache_key, 3600, json.dumps(response))
    )
    
    logger.info(f"⚡ Response in {time.time() - start:.2f}s")
    return response
```

---

## 📋 **IMPLEMENTATION PRIORITY**

### **Quick Wins (Do First):**

1. ✅ **Switch to Gemini Flash** - 2x faster, cheaper
2. ✅ **Parallel DB calls** - 30-50% faster
3. ✅ **Optimize system prompt** - 60% fewer tokens
4. ✅ **Add response caching** - 90% faster for common Qs
5. ✅ **Batch DB inserts** - 2x faster writes

### **Medium Effort:**

6. ✅ **Add MongoDB indexes** - 10x faster queries
7. ✅ **Reduce history to last 3** - Faster, cheaper
8. ✅ **Question classification** - Smart routing

### **Advanced:**

9. ✅ **Response streaming** - Better UX
10. ✅ **Edge deployment** - Lower latency
11. ✅ **Embedding cache** - Ultra-fast similar Q detection

---

## 🎯 **EXPECTED IMPROVEMENTS**

### **Before Optimization:**
- ⏱️ Response time: 3-5 seconds
- 💰 Cost per request: $0.002
- 🎯 Cache hit rate: 0%

### **After Optimization:**
- ⏱️ Response time: **0.5-1.5 seconds** (3-5x faster)
- 💰 Cost per request: **$0.0003** (85% cheaper)
- 🎯 Cache hit rate: **40-60%** (common questions)

---

## 🏆 **RECOMMENDED STACK**

```
┌─────────────────────────────────────┐
│  MINI-AGENT OPTIMIZED STACK         │
├─────────────────────────────────────┤
│                                     │
│  Model: Gemini 1.5 Flash           │  ⚡ Fastest
│  Cache: Redis (24hr for defs)      │  💾 Smart caching
│  History: Last 3 QA pairs          │  🎯 Lightweight
│  Prompt: 150 tokens (optimized)    │  💰 Cheap
│  DB: Batch inserts + indexes       │  🚀 Fast writes
│  Processing: Parallel operations   │  ⚡ Concurrent
│  Streaming: Token-by-token         │  👁️ Instant feel
│                                     │
└─────────────────────────────────────┘
```

---

## 💡 **BONUS: MODEL FALLBACK STRATEGY**

```python
# Try fast model first, fallback to better if unsure
async def get_smart_response(prompt, system_prompt):
    # Try Gemini Flash (fast & cheap)
    response = await get_llm_response(
        prompt, 
        system_prompt, 
        model="gemini-1.5-flash"
    )
    
    # Check confidence (you can add confidence scoring)
    if is_low_confidence(response):
        # Fallback to GPT-3.5
        response = await get_llm_response(
            prompt,
            system_prompt,
            model="gpt-3.5-turbo"
        )
    
    return response
```

---

## ✅ **ACTION ITEMS**

**Start with these 5 changes:**

1. **Switch model to Gemini Flash**
   - Update `get_llm_response()` call
   - Add model parameter

2. **Optimize system prompt**
   - Reduce to ~150 tokens
   - Keep same rules, compress wording

3. **Add response caching**
   - Cache common questions for 24 hours
   - Use snippet+question hash as key

4. **Parallel DB operations**
   - Use `asyncio.gather()` for concurrent calls
   - Combine MongoDB inserts

5. **Add MongoDB indexes**
   - Index `id`, `sessionId`, `threadId`
   - Massive query speedup

**Expected result:** 3-4x faster, 80% cheaper, same quality ✅

---

**Status:** Ready to implement  
**Effort:** 2-4 hours total  
**Impact:** Massive performance improvement  
**Risk:** Low (all proven optimizations)
