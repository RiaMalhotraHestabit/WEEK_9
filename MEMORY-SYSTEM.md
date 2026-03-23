# MEMORY-SYSTEM.md — Day 4

## Overview

A 3-layer persistent memory system built with AutoGen, FAISS, and SQLite.
The agent recalls relevant context from past sessions and uses it to give
accurate, personalized responses across multiple conversations.

---

## Architecture

```
New Query
    │
    ▼
┌─────────────────────────────────────────┐
│           Memory Recall Phase           │
│                                         │
│  1. FAISS vector search (semantic)      │
│  2. SQLite fetch (recent log)           │
│  3. Session window (current session)    │
└──────────────────┬──────────────────────┘
                   │
                   ▼
        Inject into system prompt
                   │
                   ▼
         AutoGen AssistantAgent
         (llama-3.3-70b-versatile)
                   │
                   ▼
              Single Reply
                   │
                   ▼
┌─────────────────────────────────────────┐
│            Memory Store Phase           │
│                                         │
│  1. Summarizer extracts key facts       │
│  2. Summary → FAISS vector store        │
│  3. Full reply → SQLite long_term.db    │
│  4. Full reply → Session rolling window │
└─────────────────────────────────────────┘
```

---

## Memory Layers

---

## Memory Types: Episodic vs Semantic

- **Episodic Memory (SQLite):**  
  Stores exact past events (conversation logs).  
  Example: "User asked about AI startups yesterday."

- **Semantic Memory (FAISS):**  
  Stores extracted meaning and facts from conversations.  
  Example: "User is interested in AI startups."

### In this system:
- SQLite → Episodic memory (full history)
- FAISS → Semantic memory (compressed knowledge)

---

## Memory Layers

### 1. Session Memory — `session_memory.py`

- Type: Short-term, in-memory rolling window  
- Scope: Current session only (resets on restart)  
- Capacity: Last 10 messages (configurable)  
- Purpose: Maintains conversational continuity  

**Key methods:**
- `add(role, content)`
- `get_history()`
- `clear()`

---

### 2. Long-Term Memory — `long_term_memory.py` → `long_term.db`

- Type: Persistent SQLite database  
- Scope: Survives across sessions  

**Purpose:**
- Stores complete conversation history (audit log)
- Provides recent context for prompt injection  

**Key methods:**
- `add(role, content)`
- `get_recent(limit)`

---

### 3. Vector Memory — `vector_store.py` → `faiss.index`

- Type: FAISS (L2 similarity search)  
- Embedding model: `all-MiniLM-L6-v2` (384-dim)  
- Scope: Persistent (saved to disk)  

**Purpose:**
- Semantic similarity search  
- Retrieves relevant past context even without keyword match  

**What is stored:**
- User queries (raw)
- Assistant responses (summarized)

**Key methods:**
- `add(text)`
- `search(query, top_k)`
- `save()`

---

## Context Injection Strategy

At every user query:

- Top-3 similar memories are retrieved from FAISS  
- Last 5 messages are fetched from SQLite  
- Last 10 messages are included from session memory  

These are combined into the system prompt before generating a response.

---

## Summarizer Agent

A lightweight secondary agent extracts key facts from responses before storing them in FAISS.

**Why this is important:**
- Raw responses are verbose → poor embeddings  
- Summaries are dense → better semantic retrieval  

**Example:**

- Raw response:  
  "Hello Ria, you mentioned you're working on a RAG system..."

- Stored summary:  
  "User is working on a RAG system."

---

## File Structure

```
memory/
  session_memory.py       short-term rolling window (in-memory)
  vector_store.py         FAISS semantic vector store
  long_term_memory.py     SQLite permanent log
  long_term.db            auto-created on first run
  faiss.index             auto-created on first run
  faiss_metadata.json     auto-created on first run
day4_main.py              AutoGen entry point — run this
```

---

## How to Run

```bash
python day4_main.py
```

### Terminal Commands

| Command | Action |
|---|---|
| `clear` | Wipe session memory only |
| `exit` | Save FAISS and quit |

---

## Tech Stack

| Component | Library |
|---|---|
| Agent framework | AutoGen (`autogen-agentchat`) |
| LLM | `llama-3.3-70b-versatile` via Groq |
| Vector store | FAISS (`faiss-cpu`) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Long-term store | SQLite (built-in Python `sqlite3`) |
| Environment | `python-dotenv` |

---
