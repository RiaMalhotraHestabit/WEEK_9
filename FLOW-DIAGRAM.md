# Day 2 — Multi-Agent Orchestration Pipeline (Interactive)

## Objective

The goal of this pipeline is to process a **user-provided query** using a 4-agent architecture:

1. **Planner / Orchestrator** – Breaks down the query into numbered tasks dynamically.
2. **Worker Agents** – Execute tasks in parallel and produce individual outputs.
3. **Reflection Agent** – Refines and merges worker outputs into a coherent response.
4. **Validator Agent** – Checks the final answer for factual accuracy and clarity.

This architecture supports **dynamic task allocation**, **parallel execution**, and produces a **high-quality final answer** for any query.

---

## Flow Diagram

```
User Query (interactive input)
    │
    ▼
Orchestrator / Planner
    - Breaks query into numbered tasks
    │
    ▼
Worker Agents (parallel)
    - Each worker executes its assigned task
    - Outputs numbered for clarity
    │
    ▼
Reflection Agent
    - Combines all worker outputs
    - Improves clarity, flow, and coherence
    │
    ▼
Validator Agent
    - Checks for factual/logical errors
    - Returns final clean answer
    │
    ▼
Final Answer
```

---

## Commands to Run

1. Activate your virtual environment:

```bash
source .venv/bin/activate
```

2. Run the interactive pipeline:

```bash
python main_day2.py
```

* The program will **prompt the user** to enter a query.
* Workers, reflection, and validation happen automatically.

---

## Sample Interactive Output

```bash
Enter your query: Explain how electric vehicles reduce pollution?
```

![final-output](screenshots/day2/final_output.png)