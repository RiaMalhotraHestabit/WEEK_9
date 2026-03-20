import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from groq import Groq
from config import GROQ_API_KEY, MODEL, MAX_TOKENS, AGENTS
from tools import code_executor, file_agent, db_agent

client = Groq(api_key=GROQ_API_KEY)

# BASE AGENT
def run_agent(name: str, user_input: str, context: str = "") -> str:
    """Core function — every agent uses this with their role from config."""
    agent_config = AGENTS[name]
    system_prompt = f"""You are the {name} agent in NEXUS AI.
Your role: {agent_config['role']}
Be concise, specific, and focused only on your role.
Do NOT repeat what other agents already said."""

    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "user", "content": f"Context from previous agents:\n{context}"})
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=agent_config["temperature"],
        max_tokens=MAX_TOKENS,
    )
    return response.choices[0].message.content.strip()

# 9 AGENTS
def orchestrator(query: str, context: str = "") -> str:
    return run_agent("Orchestrator", query, context)

def planner(query: str, context: str = "") -> str:
    return run_agent("Planner", query, context)

def researcher(query: str, context: str = "", filepath: str = None) -> str:
    """
    Domain Expert — gathers facts and background knowledge.
    Uses FileAgent tool if a file is mentioned in the query.
    """
    reasoning = run_agent("Researcher", query, context)
    # Use FileAgent if query mentions a file
    file_keywords = [".csv", ".txt", "file", "read", "load"]
    if filepath:
        result = file_agent.run(task=f"read {filepath}")
        file_data = result.get("analysis", {})
        if file_data:
            return f"{reasoning}\n\n[File Data]: {file_data}"
    elif any(k in query.lower() for k in file_keywords):
        result = file_agent.run(task=query)
        file_data = result.get("analysis", {})
        if file_data:
            return f"{reasoning}\n\n[File Data]: {file_data}"

    return reasoning

def coder(query: str, context: str = "", raw_data: dict = {}) -> str:
    """
    Developer — writes and executes Python code via CodeAgent tool.
    Always calls code_executor for coding or computation tasks.
    """
    reasoning = run_agent("Coder", query, context)

    # Use CodeAgent tool for coding/computation tasks
    code_keywords = ["calculate", "compute", "analyze", "code", "script","sort", "search", "algorithm", "function", "data"]
    if any(k in query.lower() for k in code_keywords):
        exec_result = code_executor.run(task=query, raw_data=raw_data)
        execution   = exec_result.get("execution", {})
        if execution.get("status") == "success":
            return f"{reasoning}\n\n[Code Output]: {execution.get('result', '')}"
        elif execution.get("status") == "error":
            return f"{reasoning}\n\n[Code Error]: {execution.get('stderr', '')}"

    return reasoning

def analyst(query: str, context: str = "", raw_data: dict = {}) -> str:
    """
    Data Scientist — analyzes outputs and derives insights.
    Uses DBAgent tool for SQL queries when data analysis is needed.
    """
    reasoning = run_agent("Analyst", query, context)
    # Use DBAgent tool for data querying tasks
    db_keywords = ["revenue", "sales", "total", "average", "highest","lowest", "count", "query", "database", "sql"]
    if any(k in query.lower() for k in db_keywords):
        if raw_data and "data" in raw_data:
            db_agent.setup_database()
            db_agent.load_csv_into_db(raw_data["data"])
        db_result = db_agent.run(query)
        rows = db_result.get("result", {}).get("rows", [])
        if rows:
            return f"{reasoning}\n\n[DB Query Result]: {rows}"
    return reasoning

def critic(query: str, context: str = "") -> str:
    """Reviewer — finds weaknesses, gaps, and errors."""
    return run_agent("Critic", query, context)

def optimizer(query: str, context: str = "") -> str:
    """Improver — fixes issues raised by Critic."""
    return run_agent("Optimizer", query, context)

def validator(query: str, context: str = "") -> str:
    """QA Engineer — checks correctness and completeness."""
    return run_agent("Validator", query, context)

def reporter(query: str, context: str = "") -> str:
    """Writer — compiles everything into a clean final report."""
    return run_agent("Reporter", query, context)