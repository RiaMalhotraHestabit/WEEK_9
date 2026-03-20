# NEXUS AI — System Architecture

## Overview

NEXUS AI is a sequential multi-agent pipeline where each agent receives the output of the previous agent as context. The system is built on a single `run_agent()` base function with role-based specialization controlled entirely through `config.py`.

---

## Pipeline Flow

```
User Query
     │
     ▼
┌─────────────────┐
│   Orchestrator  │  ← Coordinates everything, sets big picture
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Planner     │  ← Breaks query into ordered steps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Researcher    │  ← Gathers facts + background knowledge
└────────┬────────┘
         │ (+ FileAgent tool if CSV/file mentioned)
         ▼
┌─────────────────┐
│     Coder       │  ← Writes + executes Python code
└────────┬────────┘
         │ (+ CodeExecutor tool for computation tasks)
         ▼
┌─────────────────┐
│    Analyst      │  ← Analyzes outputs, derives insights
└────────┬────────┘
         │ (+ DBAgent tool for SQL queries)
         ▼
┌─────────────────┐
│     Critic      │  ← Reviews ALL previous outputs, finds gaps
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Optimizer     │  ← Fixes issues raised by Critic
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validator     │  ← QA check — approves or flags issues
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Reporter     │  ← Compiles everything into final report
└────────┬────────┘
         │
         ▼
   Final Report
   + trace.json
```

---

## Agent Communication Protocol

Agents communicate via **context injection** — each agent's output is passed as context to the next agent through the `run_agent()` base function:

```python
messages = [
    {"role": "system", "content": system_prompt},   # agent's role
    {"role": "user",   "content": f"Context:\n{context}"},  # previous agent output
    {"role": "user",   "content": user_query}        # original query
]
```

This is a **blackboard memory pattern** — all agents read from and write to a shared context that grows through the pipeline.

---

## Core Components

### 1. `main.py` — Pipeline Orchestrator
- Entry point for the system
- Defines the `run()` function that executes all 9 agents in sequence
- Contains `step()` wrapper with **failure recovery** (try/except)
- Handles output modes (Mode 1: final only, Mode 2: full steps)
- Saves full execution trace to `logs/trace.json`

### 2. `agents.py` — Agent Definitions
- Contains all 9 agent functions
- All agents use a single `run_agent()` base function
- Role specialization comes from `config.py` AGENTS registry
- Tool-enabled agents (Researcher, Coder, Analyst) call Day 3 tools

### 3. `config.py` — Central Configuration
- Groq API key and model selection
- All file paths (logs, memory, DB, FAISS)
- Agent registry with role, temperature per agent
- Global settings (MAX_TOKENS, MEMORY_WINDOW, TEMPERATURE)

### 4. `tools/` — External Tool Integrations
| Tool | File | Purpose |
|---|---|---|
| Code Executor | `code_executor.py` | Generates + executes Python via subprocess |
| File Agent | `file_agent.py` | Reads/writes .txt and .csv files |
| DB Agent | `db_agent.py` | Loads CSV into SQLite, runs SQL queries |

### 5. `memory/` — Memory Systems
| Memory | File | Purpose |
|---|---|---|
| Session Memory | `session_memory.py` | Short-term conversation window |
| Vector Store | `vector_store.py` | FAISS similarity search |
| Long-term DB | `long_term.db` | SQLite persistent storage |

---

## Failure Recovery Architecture

Every agent is wrapped in a `try/except` block inside the `step()` function:

```
Agent Call
    │
    ├── SUCCESS → output logged + passed to next agent
    │
    └── FAILURE → error message logged as output
                  pipeline CONTINUES to next agent
                  error saved in trace.json with status: "error"
```

This ensures the pipeline **never crashes** — even if multiple agents fail, the system completes and saves whatever output was generated.

---

## Tool Calling Architecture

Tools are called conditionally based on keywords in the query:

```
Researcher Agent
    │
    ├── CSV/file keyword detected? → call FileAgent
    │
    └── No file keyword → pure LLM reasoning

Coder Agent
    │
    ├── code/compute keyword detected? → call CodeExecutor
    │
    └── No code keyword → pure LLM reasoning

Analyst Agent
    │
    ├── revenue/SQL keyword detected? → call DBAgent
    │
    └── No DB keyword → pure LLM reasoning
```

---

## Memory Architecture

```
New Query
    │
    ▼
Search FAISS Vector Store
    │
    ▼
Fetch similar past context
    │
    ▼
Inject into agent prompt
    │
    ▼
Generate response with memory
    │
    ▼
Save to SQLite + FAISS
```
---
