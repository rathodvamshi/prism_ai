# 🤖 How Mini-Agent Works - Simple Explanation

## What is Mini-Agent (Sub-Brain)?

**Mini-Agent** is like a **focused AI assistant** that helps you understand specific parts of your conversation. Think of it as having a mini expert that only focuses on ONE piece of text you select!

---

## 📝 Simple Flow

### 1️⃣ **You Select Text**
```
You highlight some text in a message, for example:
"Machine learning is a subset of artificial intelligence"
```

### 2️⃣ **You Ask a Question**
```
You might ask: "What does subset mean here?"
```

### 3️⃣ **Mini-Agent Responds**
```
Mini-Agent gives you a focused answer about THAT specific text!
```

---

## 🔧 What Powers the Mini-Agent?

### **The Technology:**

**Mini-Agent uses an LLM (Large Language Model)** - the same kind of AI that powers ChatGPT, Claude, etc.

### **Specifically:**
- **Function:** `get_llm_response()` (from `llm_client.py`)
- **Model:** Whatever LLM you have configured (could be OpenAI, Gemini, etc.)
- **Location:** Backend file `highlights.py` (lines 359-369)

---

## 🎯 How It Generates Responses

### **Step-by-Step Process:**

#### **1. Gather Context**
```python
# Gets the text you selected
snippet_context = "CONTEXT SNIPPET: [your selected text]"
```

#### **2. Special Instructions**
```python
system_prompt = """
You are a 'Mini-Agent' focused exclusively on explaining 
the specific text snippet provided below.
Your goal is to resolve the user's doubt about THIS 
specific part of the message.
Keep your response SHORT, SWEET, and DIRECT. No fluff.
"""
```

#### **3. Combine Everything**
```python
# Sends to AI:
prompt = f"{snippet_context}\n\nUSER QUESTION: {your_question}"
```

#### **4. Get AI Response**
```python
ai_response = await get_llm_response(
    prompt=prompt,
    system_prompt=system_prompt
)
```

#### **5. Send to You**
```python
# Returns the response to display in UI
return ai_response
```

---

## 🌟 Key Features

### **1. Context-Aware**
✅ Always includes the text snippet you selected
✅ AI knows exactly what you're asking about

### **2. Focused Answers**
✅ Told to be "SHORT, SWEET, and DIRECT"
✅ No rambling or unnecessary information

### **3. Isolated from Main Chat**
✅ Doesn't see your entire conversation
✅ Only focuses on the selected snippet
✅ Won't get confused by unrelated messages

### **4. Smart Fallbacks**
✅ If AI fails to respond → shows fallback message
✅ Logs all responses for debugging
✅ Never shows empty bubbles

---

## 📊 Example

### **You Select:**
> "Python is an interpreted, high-level programming language"

### **You Ask:**
> "What does interpreted mean?"

### **What Mini-Agent Sees:**
```
CONTEXT SNIPPET:
Python is an interpreted, high-level programming language

USER QUESTION: What does interpreted mean?
```

### **Mini-Agent Responds:**
> "In this context, 'interpreted' means Python code runs line-by-line 
> through an interpreter, rather than being compiled into machine code first. 
> This makes Python slower but easier to test and debug."

---

## 🎨 Visual Representation

```
┌─────────────────────────────────────────┐
│  Main Conversation                      │
│  ┌───────────────────────────────────┐  │
│  │ "Python is an interpreted..."     │◄─── You select this
│  └───────────────────────────────────┘  │
│                                         │
│  [Select] → Opens Mini-Agent            │
└─────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────┐
│  🧠 Sub-Brain (Mini-Agent)               │
│  ↴ "Python is an interpreted..."        │ ← Shows snippet
│    What does interpreted mean?          │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ In this context, "interpreted"  │   │
│  │ means Python code runs line-    │   │ ← AI Response
│  │ by-line through an interpreter  │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## 🔑 Key Differences from Main Chat

| Aspect | Main Chat | Mini-Agent |
|--------|-----------|------------|
| **Context** | Full conversation history | Only selected text snippet |
| **Purpose** | General conversation | Explain specific text |
| **Style** | Can be detailed | Short & focused |
| **Memory** | Remembers everything | Only sees snippet |

---

## 💡 In Simple Terms

**Think of it like this:**

- **Main Chat** = Talking to a knowledgeable friend about anything
- **Mini-Agent** = Asking a teacher to explain ONE specific sentence

The Mini-Agent is:
1. 🎯 **Focused** - Only cares about the text you selected
2. ⚡ **Fast** - Gives quick, concise answers
3. 🧩 **Isolated** - Won't get confused by your main conversation
4. 💡 **Helpful** - Perfect for clarifying confusing parts

---

## 🛠️ Technical Summary

```javascript
// Frontend (User clicks selected text)
→ Opens Mini-Agent panel
→ Shows selected text
→ User types question

// Backend receives request:
{
  threadId: "mini_agent_123",
  text: "What does interpreted mean?",
  selectedText: "Python is an interpreted..."
}

// Backend processes:
1. Fetches the selected text (snippet)
2. Creates focused prompt with snippet context
3. Sends to LLM (AI model)
4. Gets response
5. Returns to frontend

// Frontend displays:
✅ User question
✅ AI answer (focused on snippet)
```

---

## ✨ The Magic Ingredient

**The secret sauce is the `system_prompt`:**

It tells the AI:
- ✅ You are a MINI-AGENT (not a general chatbot)
- ✅ Focus ONLY on this snippet
- ✅ Be SHORT and DIRECT
- ✅ Resolve the user's specific doubt

This is what makes Mini-Agent different from just asking in main chat!

---

## 🎯 Bottom Line

**Mini-Agent = Laser-Focused AI Assistant**

- **Uses:** Same LLM technology as main chat
- **Difference:** Specialized instructions + limited context
- **Result:** Perfect for quick clarifications about specific text
- **Power:** LLM (OpenAI/Gemini/etc.) with focused prompting

**It's not a separate AI - it's your MAIN AI wearing a "focus hat"!** 🎩
