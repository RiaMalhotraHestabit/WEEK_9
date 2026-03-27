import os
import json
import csv
from groq import Groq
from torch import Use
from tools import file_agent
from tools import code_executor
from tools import db_agent
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_3"))

ORCHESTRATOR_PROMPT = """You are an Orchestrator Agent. You receive a user query and create an execution plan as JSON:
{
  "plan": [
    {"step": 1, "agent": "FileAgent",  "task": "exact instruction for file agent"},
    {"step": 2, "agent": "DBAgent",    "task": "what to query"},
    {"step": 3, "agent": "CodeAgent",  "task": "what to compute"}
  ],
  "final_goal": "what the final answer should contain"
}
Available agents: FileAgent (reads .csv/.txt files and also generates and writes any content like poems/stories/notes to files), DBAgent (SQLite queries), CodeAgent (Python execution, data analysis only).
CRITICAL RULES for FileAgent tasks:
- For READ: task must be exactly "read <filename>" e.g. "read sales.csv"
- For WRITE: ALWAYS preserve the EXACT original content from the user query word for word.
  GOOD: "write Hello from File Agent to output.txt"
  BAD:  "write content to output.txt"
- NEVER paraphrase, summarize, or rephrase the content to be written.

Respond ONLY with valid JSON."""


def create_sample_csv(path: str = "sales.csv"):
    #Create a sample sales.csv if it doesn't exist.
    if os.path.exists(path):
        return path
    rows = [
        ["date", "product", "region", "units_sold", "revenue"],
        ["2024-01-01", "Laptop", "North", 12, 14400],
        ["2024-01-02", "Phone",  "South", 25, 12500],
        ["2024-01-03", "Tablet", "East",  8,  4000],
        ["2024-01-04", "Laptop", "West",  19, 22800],
        ["2024-01-05", "Phone",  "North", 31, 15500],
        ["2024-01-06", "Tablet", "South", 14, 7000],
        ["2024-01-07", "Laptop", "East",  7,  8400],
        ["2024-01-08", "Phone",  "West",  22, 11000],
        ["2024-01-09", "Tablet", "North", 10, 5000],
        ["2024-01-10", "Laptop", "South", 15, 18000],
    ]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"[Orchestrator] Created {path}")
    return path


def plan_execution(user_query: str) -> dict:
    #Use Groq to plan which agents to call.
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": ORCHESTRATOR_PROMPT},
            {"role": "user", "content": user_query},
        ],
        temperature=0.1,
        max_tokens=512,
    )
    raw = response.choices[0].message.content.strip()
    try:
        clean = raw
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:])
            if clean.endswith("```"):
                clean = clean[:-3]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return {
            "plan": [
                {"step": 1, "agent": "FileAgent",  "task": "Read sales.csv"},
                {"step": 2, "agent": "DBAgent",    "task": "What is total revenue and units sold by product?"},
                {"step": 3, "agent": "CodeAgent",  "task": "Generate top 5 business insights from the sales data"},
            ],
            "final_goal": "Top 5 insights from the sales data",
        }


def synthesize_final_answer(user_query: str, all_results: list) -> str:
    #Use Groq to synthesize all agent outputs into a final answer.
    context = json.dumps(all_results, indent=2)[:3000]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a senior data analyst. Given agent results, write a clear, concise final answer for the user. Use bullet points for insights."},
            {"role": "user", "content": f"User asked: {user_query}\n\nAgent results:\n{context}\n\nWrite the final answer:"},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()

def run(user_query: str, csv_path: str = "sales.csv") -> dict:
    #Main orchestrator pipeline.
    print(f"\n{'='*60}")
    print(f"[Orchestrator] Query: {user_query}")
    print(f"{'='*60}")

    # Ensure CSV exists
    create_sample_csv(csv_path)

    #Step-1: Plan
    print("\n[Orchestrator] Planning execution...")
    plan = plan_execution(user_query)
    print(f"[Orchestrator] Plan:\n{json.dumps(plan, indent=2)}")

    all_results = []
    file_raw_data = None

    #Step-2: Execute each agent in the plan
    for step in plan.get("plan", []):
        agent_name = step["agent"]
        task = step["task"]
        print(f"\n[Orchestrator] → Step {step['step']}: {agent_name} — {task}")

        if agent_name == "FileAgent":
            prior_output = None
            for prev in all_results:
                if prev["agent"] == "CodeAgent":
                    exec_result = prev["result"]
                    if isinstance(exec_result.get("result"), dict):
                        prior_output = exec_result["result"].get("output") or exec_result["result"].get("result")
                    elif isinstance(exec_result.get("result"), str):
                        prior_output = exec_result["result"]
                    else:
                        prior_output = exec_result.get("output")
                    break

            result = file_agent.run(task=task, write_content=prior_output)
            file_raw_data = result.get("raw_data", {})

            if "error" in result:
                all_results.append({
                    "step": step["step"],
                    "agent": agent_name,
                    "result": result
                })
            elif result.get("operation") == "write":
                all_results.append({
                    "step": step["step"],
                    "agent": agent_name,
                    "result": result.get("write_result", {})
                })
            else:
                all_results.append({
                    "step": step["step"],
                    "agent": agent_name,
                    "result": result.get("analysis", {})
                })
        elif agent_name == "DBAgent":
            if file_raw_data and "data" in file_raw_data:
                db_agent.setup_database()
                db_agent.load_csv_into_db(file_raw_data["data"])

            result = db_agent.run(user_query)
            all_results.append({
                "step": step["step"],
                "agent": agent_name,
                "result": result.get("result", {})
            })

        elif agent_name == "CodeAgent":
            data_to_analyze = file_raw_data if file_raw_data else {}
            result = code_executor.run(task=task, raw_data=data_to_analyze)
            all_results.append({"step": step["step"], "agent": agent_name, "result": result.get("execution", {})})

    #Step-3: Synthesize
    print(f"\n[Orchestrator] Synthesizing final answer...")
    final_answer = synthesize_final_answer(user_query, all_results)

    print(f"\n{'='*60}")
    print("FINAL ANSWER:")
    print(f"{'='*60}")
    print(final_answer)
    print(f"{'='*60}\n")

    return {
        "query": user_query,
        "plan": plan,
        "agent_results": all_results,
        "final_answer": final_answer,
    }

if __name__ == "__main__":
    query = input("Enter your Query: ")
    result = run(query)
    # Save the full trace
    with open("execution_trace.json", "w") as f:
        json.dump(result, f, indent=2)
    print("[Orchestrator] Full trace saved to execution_trace.json")