import os
import sys
import json
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from config import LOGS_DIR, TRACE_FILE
import agents as ag

# LOGGING
def save_trace(trace: dict):
    """Save full execution trace to logs/trace.json."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(TRACE_FILE, "w") as f:
        json.dump(trace, f, indent=2)
    print(f"\n[NEXUS] Trace saved → {TRACE_FILE}")

def print_step(step: int, agent: str, output: str):
    """Print agent output in a clean formatted block."""
    print(f"\n{'─'*60}")
    print(f"  Step {step} | {agent}")
    print(f"{'─'*60}")
    print(output)

# NEXUS AI PIPELINE
def run(query: str, verbose: bool=False) -> dict:
    print(f"\n{'='*60}")
    print(f"  NEXUS AI")
    print(f"  Query: {query}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    trace = {"query": query, "timestamp": datetime.now().isoformat(), "steps": []}

    #Failure Recovery Wrapper 
    def step(num: int, name: str, fn, *args, **kwargs) -> str:
        """
        Run an agent with failure recovery.
        If an agent crashes, log the error and continue pipeline.
        """
        print(f"\n[NEXUS] Running {name}...")
        try:
            output = fn(*args, **kwargs)
        except Exception as e:
            output = f"[{name} FAILED]: {str(e)} — skipping this step."
            print(f"[NEXUS WARNING] {name} failed: {e} — continuing pipeline...")

        if verbose:
            print_step(num, name, output)
        trace["steps"].append({
            "step"  : num,
            "agent" : name,
            "output": output,
            "status": "error" if "FAILED" in output else "success"
        })
        return output

    orch_out = step(1, "Orchestrator", ag.orchestrator, query)
    plan_out = step(2, "Planner", ag.planner, query, context=orch_out)
    filepath = None
    if ".csv" in query.lower():
        import re
        match = re.search(r'\b\w+\.csv\b', query, re.IGNORECASE)
        filepath = match.group(0) if match else None

    research_out = step(3, "Researcher", ag.researcher,query, context=plan_out, filepath=filepath)
    coder_out = step(4, "Coder", ag.coder,query, context=research_out)
    analyst_out = step(5, "Analyst", ag.analyst,query, context=coder_out)
    combined = f"Plan:\n{plan_out}\n\nResearch:\n{research_out}\n\nAnalysis:\n{analyst_out}"
    critic_out = step(6, "Critic", ag.critic,query, context=combined)
    optimizer_out = step(7, "Optimizer", ag.optimizer,query, context=f"Critic feedback:\n{critic_out}\n\nOriginal output:\n{combined}")
    validator_out = step(8, "Validator", ag.validator,query, context=optimizer_out)
    full_context = f"""
Query: {query}
Plan: {plan_out}
Research: {research_out}
Code Output: {coder_out}
Analysis: {analyst_out}
Optimized: {optimizer_out}
Validation: {validator_out}
"""
    final_report = step(9, "Reporter", ag.reporter, query, context=full_context)

    # Final Output 
    print(f"\n{'='*60}")
    print("  NEXUS AI — FINAL REPORT")
    print(f"{'='*60}")
    print(final_report)
    print(f"{'='*60}\n")
    trace["final_report"] = final_report
    trace["completed"]    = datetime.now().isoformat()
    save_trace(trace)

    return trace

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS AI — Autonomous Multi-Agent System")
    print("  Powered by Groq + LLaMA 3.3")
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

        # Auto-process any query through the full pipeline
        print("\nOutput mode:")
        print("  [1] Final report only (clean)")
        print("  [2] Full step-by-step output")
        mode = input("Choose (1 or 2): ").strip()
        verbose = mode == "2"

        # Auto-process any query through the full pipeline
        run(query, verbose=verbose)
        
        print("\n" + "=" * 60)
        again = input("Run another query? (yes/no): ").strip().lower()
        if again not in ["yes", "y"]:
            print("\n[NEXUS] Goodbye!\n")
            break