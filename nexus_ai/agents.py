"""
agents.py — NEXUS AI
─────────────────────────────────────────────────────────────
Every agent is an AutoGen 0.4.x AssistantAgent backed by
Groq (llama-3.3-70b-versatile) via the OpenAI-compatible endpoint.

Key design decisions
────────────────────
• One reusable factory  →  make_agent(name)  creates any agent
• One async runner      →  run_agent(name, user_input, context)
  wraps the async AutoGen call so main.py can stay synchronous
• Tool hooks for Researcher, Coder, Analyst are preserved
  (file_agent / code_executor / db_agent) exactly as before
"""

import os
import sys
import asyncio
import threading

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# AutoGen 0.4.x imports
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

from config import (
    GROQ_API_KEY, MODEL, MAX_TOKENS, AGENTS,
    AUTOGEN_MODEL_CLIENT_CONFIG,
)

# ─────────────────────────────────────────────
#  PERSISTENT EVENT LOOP
#  Fixes: RuntimeError('Event loop is closed')
#  Root cause: asyncio.run() tears down the loop after each call,
#  but httpx async clients try to close AFTER the loop is gone.
#  Solution: one long-lived background loop that never closes.
# ─────────────────────────────────────────────
_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()

def _start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

_loop_thread = threading.Thread(target=_start_loop, args=(_loop,), daemon=True)
_loop_thread.start()

# ── optional tool imports (graceful fallback if not present) ──
try:
    from tools import code_executor, file_agent, db_agent
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    print("[NEXUS WARNING] tools module not found — tool steps will be skipped.")


# ─────────────────────────────────────────────
#  GROQ CLIENT (OpenAI-compatible)
# ─────────────────────────────────────────────
def _make_model_client(temperature: float) -> OpenAIChatCompletionClient:
    """Create a per-agent Groq client with the right temperature."""
    return OpenAIChatCompletionClient(
        model      = MODEL,
        api_key    = GROQ_API_KEY,
        base_url   = "https://api.groq.com/openai/v1",
        temperature= temperature,
        max_tokens = MAX_TOKENS,
        model_info={                        # required by AutoGen 0.4.x
            "vision"            : False,
            "function_calling"  : False,
            "json_output"       : False,
            "structured_output" : False,    # suppress UserWarning
            "family"            : "llama",
        },
    )


# ─────────────────────────────────────────────
#  AGENT FACTORY
# ─────────────────────────────────────────────
def make_agent(name: str) -> AssistantAgent:
    """
    Build and return an AutoGen AssistantAgent for the given NEXUS role.
    Each call creates a fresh agent (stateless — context is passed explicitly).
    """
    cfg    = AGENTS[name]
    client = _make_model_client(cfg["temperature"])
    return AssistantAgent(
        name          = name.lower().replace(" ", "_"),
        model_client  = client,
        system_message= cfg["role"],
    )


# ─────────────────────────────────────────────
#  ASYNC CORE RUNNER
# ─────────────────────────────────────────────
async def _async_run_agent(name: str, user_input: str, context: str = "") -> str:
    """
    Core async function that drives one AssistantAgent turn.
    Context from previous agents is prepended to the user message.
    """
    agent = make_agent(name)

    # Build the user message — prepend context if available
    if context:
        full_message = (
            f"Context from previous agents:\n{context}\n\n"
            f"Your task:\n{user_input}"
        )
    else:
        full_message = user_input

    # AutoGen 0.4.x: on_messages takes a list of ChatMessage
    response = await agent.on_messages(
        messages     = [TextMessage(content=full_message, source="user")],
        cancellation_token=None,
    )
    # response.chat_message.content holds the reply text
    return response.chat_message.content.strip()


# ─────────────────────────────────────────────
#  SYNC WRAPPER  (main.py calls these directly)
# ─────────────────────────────────────────────
def _run(name: str, user_input: str, context: str = "") -> str:
    """
    Synchronous wrapper — submits the coroutine to the persistent
    background event loop so the loop is NEVER closed between calls.
    This eliminates the 'Event loop is closed' RuntimeError.
    """
    future = asyncio.run_coroutine_threadsafe(
        _async_run_agent(name, user_input, context),
        _loop,
    )
    return future.result()   # blocks until the agent responds


# ─────────────────────────────────────────────
#  9 PUBLIC AGENT FUNCTIONS
# ─────────────────────────────────────────────

def orchestrator(query: str, context: str = "") -> str:
    """
    Master Coordinator — analyses the query and returns a JSON list
    of agent names that are needed, in execution order.
    """
    return _run("Orchestrator", query, context)


def planner(query: str, context: str = "") -> str:
    """Breaks query into an ordered action plan."""
    return _run("Planner", query, context)


def researcher(query: str, context: str = "", filepath: str = None) -> str:
    """
    Gathers facts and background knowledge.
    Calls file_agent tool if a CSV / file path is present.
    """
    reasoning = _run("Researcher", query, context)

    if not TOOLS_AVAILABLE:
        return reasoning

    file_keywords = [".csv", ".txt", "file", "read", "load"]
    if filepath:
        result    = file_agent.run(task=f"read {filepath}")
        file_data = result.get("analysis", {})
        if file_data:
            return f"{reasoning}\n\n[File Data]: {file_data}"
    elif any(k in query.lower() for k in file_keywords):
        result    = file_agent.run(task=query)
        file_data = result.get("analysis", {})
        if file_data:
            return f"{reasoning}\n\n[File Data]: {file_data}"

    return reasoning


def coder(query: str, context: str = "", raw_data: dict = {}) -> str:
    """
    Writes Python code / system snippets.
    Executes code via code_executor tool for computation tasks.
    """
    reasoning = _run("Coder", query, context)

    if not TOOLS_AVAILABLE:
        return reasoning

    code_keywords = [
        "calculate", "compute", "analyze", "code", "script",
        "sort", "search", "algorithm", "function", "data",
    ]
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
    Analyses data and derives insights.
    Runs SQL queries via db_agent tool when data analysis is needed.
    """
    reasoning = _run("Analyst", query, context)

    if not TOOLS_AVAILABLE:
        return reasoning

    db_keywords = [
        "revenue", "sales", "total", "average", "highest",
        "lowest", "count", "query", "database", "sql",
    ]
    if any(k in query.lower() for k in db_keywords):
        if raw_data and "data" in raw_data:
            db_agent.setup_database()
            db_agent.load_csv_into_db(raw_data["data"])
        db_result = db_agent.run(query)
        rows      = db_result.get("result", {}).get("rows", [])
        if rows:
            return f"{reasoning}\n\n[DB Query Result]: {rows}"

    return reasoning


def critic(query: str, context: str = "") -> str:
    """Reviews all outputs and identifies weaknesses / gaps."""
    return _run("Critic", query, context)


def optimizer(query: str, context: str = "") -> str:
    """Applies Critic feedback to improve previous outputs."""
    return _run("Optimizer", query, context)


def validator(query: str, context: str = "") -> str:
    """Validates final output for correctness and completeness."""
    return _run("Validator", query, context)


def reporter(query: str, context: str = "") -> str:
    """Compiles everything into a clean, structured final report."""
    return _run("Reporter", query, context)