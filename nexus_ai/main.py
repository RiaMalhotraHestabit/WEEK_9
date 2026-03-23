"""
main.py — NEXUS AI
─────────────────────────────────────────────────────────────
AutoGen 0.4.x  |  Groq llama-3.3-70b-versatile
─────────────────────────────────────────────────────────────

Pipeline flow
─────────────
1. Orchestrator   → reads query → returns JSON list of needed agents
2. Smart Selector → parses that list → enforces ordering rules
3. Sequential run → each selected agent runs in order, output fed
                    as context to the next agent
4. Reporter       → always runs last, compiles final report
5. Trace saved    → logs/trace.json

"""

import os
import sys
import json
import re
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config import (
    LOGS_DIR, TRACE_FILE,
    AGENT_ORDER, CRITIC_THRESHOLD,
    ALWAYS_FIRST, ALWAYS_LAST,
)
import agents as ag

# ─────────────────────────────────────────────
#  LOGGING HELPERS
# ─────────────────────────────────────────────

def save_trace(trace: dict):
    """Persist full execution trace to logs/trace.json."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(TRACE_FILE, "w") as f:
        json.dump(trace, f, indent=2)
    print(f"\n[NEXUS] Trace saved → {TRACE_FILE}")


def print_step(step: int, agent: str, output: str):
    """Pretty-print a single agent's output."""
    print(f"\n{'─'*60}")
    print(f"  Step {step} | {agent}")
    print(f"{'─'*60}")
    print(output)


# ─────────────────────────────────────────────
#  SMART AGENT SELECTOR
# ─────────────────────────────────────────────

def select_agents(orchestrator_output: str) -> list[str]:
    """
    Parse the Orchestrator's JSON response and return an ordered,
    validated list of agent names to run.

    Rules enforced:
    • Orchestrator itself is never in the run-list (already ran)
    • Reporter always appears last
    • Critic + Optimizer always travel together
    • Agent order follows AGENT_ORDER from config
    • If parse fails → fallback to full pipeline
    """
    # ── try to extract JSON array from Orchestrator output ──
    selected: list[str] = []
    try:
        # Strip markdown fences if present
        clean = re.sub(r"```[a-z]*", "", orchestrator_output).strip("` \n")
        # Find first [...] block
        match = re.search(r'\[.*?\]', clean, re.DOTALL)
        if match:
            selected = json.loads(match.group(0))
    except (json.JSONDecodeError, AttributeError):
        pass

    # ── fallback: full pipeline ──
    if not selected:
        print("[NEXUS] Orchestrator did not return valid JSON — running full pipeline.")
        selected = [a for a in AGENT_ORDER]  # already excludes Orchestrator

    # ── normalise names (title-case) ──
    valid_names = set(AGENT_ORDER)
    selected    = [s.strip().title() for s in selected if s.strip().title() in valid_names]

    # ── enforce Critic+Optimizer coupling ──
    if "Critic" in selected and "Optimizer" not in selected:
        selected.append("Optimizer")
    if "Optimizer" in selected and "Critic" not in selected:
        selected.insert(selected.index("Optimizer"), "Critic")

    # ── auto-add Critic+Optimizer for non-trivial pipelines ──
    non_report = [a for a in selected if a != "Reporter"]
    if len(non_report) >= CRITIC_THRESHOLD:
        if "Critic" not in selected:
            selected.append("Critic")
        if "Optimizer" not in selected:
            selected.append("Optimizer")

    # ── ensure Reporter is last ──
    if "Reporter" not in selected:
        selected.append("Reporter")
    else:
        selected = [a for a in selected if a != "Reporter"]
        selected.append("Reporter")

    # ── sort by canonical order (preserve Reporter last) ──
    order_index = {name: i for i, name in enumerate(AGENT_ORDER)}
    body        = [a for a in selected if a != "Reporter"]
    body.sort(key=lambda x: order_index.get(x, 99))
    final       = body + ["Reporter"]

    print(f"[NEXUS] Agent pipeline → {' → '.join(final)}")
    return final


# ─────────────────────────────────────────────
#  AGENT DISPATCHER
# ─────────────────────────────────────────────

# Maps agent name → callable from agents.py
AGENT_FN_MAP = {
    "Planner"   : ag.planner,
    "Researcher": ag.researcher,
    "Coder"     : ag.coder,
    "Analyst"   : ag.analyst,
    "Critic"    : ag.critic,
    "Optimizer" : ag.optimizer,
    "Validator" : ag.validator,
    "Reporter"  : ag.reporter,
}


def _dispatch(name: str, query: str, context: str, filepath: str = None) -> str:
    """
    Call the right agent function.
    Researcher gets the optional filepath kwarg.
    """
    fn = AGENT_FN_MAP.get(name)
    if fn is None:
        return f"[{name}] — no handler registered."
    if name == "Researcher" and filepath:
        return fn(query, context=context, filepath=filepath)
    return fn(query, context=context)


# ─────────────────────────────────────────────
#  FAILURE-RECOVERY STEP RUNNER
# ─────────────────────────────────────────────

def safe_step(
    num: int,
    name: str,
    query: str,
    context: str,
    trace: dict,
    verbose: bool,
    filepath: str = None,
) -> str:
    """
    Run one agent with full failure recovery.
    Appends result to trace regardless of success/failure.
    """
    print(f"\n[NEXUS] ▶ Running {name}...")
    try:
        output = _dispatch(name, query, context, filepath)
        status = "success"
    except Exception as e:
        output = f"[{name} FAILED]: {str(e)} — skipping this step."
        status = "error"
        print(f"[NEXUS WARNING] {name} failed: {e} — continuing pipeline...")

    if verbose:
        print_step(num, name, output)

    trace["steps"].append({
        "step"  : num,
        "agent" : name,
        "output": output,
        "status": status,
    })
    return output


# ─────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────

def run(query: str, verbose: bool = False) -> dict:
    """
    Execute the full NEXUS AI pipeline for a given query.

    Returns the complete trace dict (also saved to logs/trace.json).
    """
    print(f"\n{'='*60}")
    print(f"  NEXUS AI")
    print(f"  Query : {query}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    trace = {
        "query"    : query,
        "timestamp": datetime.now().isoformat(),
        "agents"   : [],
        "steps"    : [],
    }

    # ── detect CSV filepath in query ──
    filepath = None
    if ".csv" in query.lower():
        match    = re.search(r'\b[\w./\\-]+\.csv\b', query, re.IGNORECASE)
        filepath = match.group(0) if match else None

    # ── Step 0: Orchestrator decides the pipeline ──
    print(f"\n[NEXUS] ▶ Running Orchestrator...")
    try:
        orch_out = ag.orchestrator(query)
    except Exception as e:
        orch_out = ""
        print(f"[NEXUS WARNING] Orchestrator failed: {e} — falling back to full pipeline.")

    if verbose:
        print_step(0, "Orchestrator", orch_out)

    trace["steps"].append({
        "step"  : 0,
        "agent" : "Orchestrator",
        "output": orch_out,
        "status": "success" if orch_out else "error",
    })

    # ── Smart selection ──
    pipeline = select_agents(orch_out)
    trace["agents"] = pipeline

    # ── Sequential pipeline ──
    context      = f"Orchestrator analysis:\n{orch_out}"   # seed context
    step_counter = 1
    outputs      = {}        # name → output  (for Reporter aggregation)

    for agent_name in pipeline:
        output = safe_step(
            num      = step_counter,
            name     = agent_name,
            query    = query,
            context  = context,
            trace    = trace,
            verbose  = verbose,
            filepath = filepath if agent_name == "Researcher" else None,
        )
        outputs[agent_name] = output

        # ── build rolling context for next agent ──
        # Critic gets a richer combined context
        if agent_name == "Critic":
            context = (
                "All previous outputs:\n"
                + "\n\n".join(f"[{k}]:\n{v}" for k, v in outputs.items()
                              if k not in ("Critic",))
            )
        # Optimizer sees Critic feedback + everything before it
        elif agent_name == "Optimizer":
            context = (
                f"Critic feedback:\n{outputs.get('Critic', '')}\n\n"
                f"Original outputs:\n"
                + "\n\n".join(f"[{k}]:\n{v}" for k, v in outputs.items()
                              if k not in ("Critic", "Optimizer"))
            )
        # Reporter gets the full picture
        elif agent_name == "Reporter":
            context = (
                f"Query: {query}\n\n"
                + "\n\n".join(f"[{k}]:\n{v}" for k, v in outputs.items()
                              if k != "Reporter")
            )
        else:
            # Every other agent just gets the last agent's output as context
            context = output

        step_counter += 1

    # ── Final Output ──
    final_report = outputs.get("Reporter", "[Reporter did not produce output]")

    print(f"\n{'='*60}")
    print("  NEXUS AI — FINAL REPORT")
    print(f"{'='*60}")
    print(final_report)
    print(f"{'='*60}\n")

    trace["final_report"] = final_report
    trace["completed"]    = datetime.now().isoformat()
    save_trace(trace)

    return trace


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS AI — Autonomous Multi-Agent System")
    print("  Powered by AutoGen 0.4.x + Groq LLaMA 3.3")
    print("=" * 60)
    print("""
What can NEXUS AI do?
  * Plan startups, products, and business strategies
  * Design system and backend architectures
  * Analyze data and generate insights
  * Design AI pipelines (RAG, fine-tuning, agents)
  * Answer any technical or strategic question
""")

    while True:
        query = input("Enter your query (or 'exit' to quit): ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("\n[NEXUS] Goodbye!\n")
            break
        if not query:
            print("[NEXUS] Please enter a query.\n")
            continue

        print("\nOutput mode:")
        print("  [1] Final report only (clean)")
        print("  [2] Full step-by-step output")
        mode    = input("Choose (1 or 2): ").strip()
        verbose = mode == "2"

        run(query, verbose=verbose)

        print("\n" + "=" * 60)
        again = input("Run another query? (yes/no): ").strip().lower()
        if again not in ["yes", "y"]:
            print("\n[NEXUS] Goodbye!\n")
            break