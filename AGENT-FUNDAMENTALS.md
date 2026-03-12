# Agent Fundamentals – Day 1

## Overview

A simple multi-agent pipeline built with **AutoGen** and a local **Phi-3** model via **Ollama**. Three specialized agents collaborate to answer a user query.

---

## Agents

| Agent | Role |
|---|---|
| Research Agent | Generates detailed notes on the topic |
| Summarizer Agent | Condenses notes into a short summary |
| Answer Agent | Produces the final user-facing response |

**Flow:** `User → Research → Summarizer → Answer → Output`

---

## Key Concepts

- **Agent Loop:** Perception → Reasoning → Action
- **Message Passing:** Each agent processes the previous agent's output
- **Role Isolation:** Strict separation of responsibilities for modularity

---

## Project Structure

```
WEEK_9/
├── agents/
│   ├── research_agent.py
│   ├── summarizer_agent.py
│   └── answer_agent.py
├── model_client.py       # Connects to Ollama (phi3, localhost:11434)
├── main.py               # Entry point & pipeline coordinator
└── AGENT-FUNDAMENTALS.md
```

---

## Setup & Run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install autogen-agentchat autogen-ext openai
ollama serve
ollama pull phi3
python main.py
```

---

## output

![final_results](screenshots/day1/final_result.png)

## Takeaways

- Agents can collaborate to solve tasks more effectively than a single model call
- Local LLMs (Ollama) enable fully offline AI systems
- This architecture extends naturally to memory, RAG, and task planning