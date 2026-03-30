import os
import sys
import asyncio
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from config import (GROQ_API_KEY, MODEL, MAX_TOKENS, AGENTS)

_loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()

def _start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

_loop_thread = threading.Thread(target=_start_loop, args=(_loop,), daemon=True)
_loop_thread.start()

# optional tool imports (graceful fallback if not present)
try:
    from tools import code_executor, file_agent, db_agent
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    print("[NEXUS WARNING] tools module not found — tool steps will be skipped.")

# GROQ CLIENT (OpenAI-compatible)
def _make_model_client(temperature: float) -> OpenAIChatCompletionClient:
    return OpenAIChatCompletionClient(
        model      = MODEL,
        api_key    = GROQ_API_KEY,
        base_url   = "https://api.groq.com/openai/v1",
        temperature= temperature,
        max_tokens = MAX_TOKENS,
        model_info={                        # required by AutoGen
            "vision"            : False,
            "function_calling"  : False,
            "json_output"       : False,
            "structured_output" : False,    # suppress UserWarning
            "family"            : "llama",
        },
    )
def make_agent(name: str) -> AssistantAgent:
    cfg    = AGENTS[name]
    client = _make_model_client(cfg["temperature"])
    return AssistantAgent(
        name          = name.lower().replace(" ", "_"),
        model_client  = client,
        system_message= cfg["role"],
    )

async def _async_run_agent(name: str, user_input: str, context: str = "") -> str:
    agent = make_agent(name)

    # Build the user message, prepend context if available
    if context:
        full_message = (
            f"Context from previous agents:\n{context}\n\n"
            f"Your task:\n{user_input}"
        )
    else:
        full_message = user_input

    # AutoGen: on_messages takes a list of ChatMessage
    response = await agent.on_messages(
        messages     = [TextMessage(content=full_message, source="user")],
        cancellation_token=None,
    )
    return response.chat_message.content.strip()   # response.chat_message.content holds the reply text

#SYNC WRAPPER  (main.py calls these directly)
def _run(name: str, user_input: str, context: str = "") -> str:
    future = asyncio.run_coroutine_threadsafe(
        _async_run_agent(name, user_input, context),
        _loop,
    )
    return future.result()   # blocks until the agent responds

# total 9 agents functions which will be called by the orchestrator.
def orchestrator(query: str, context: str = "") -> str:
    return _run("Orchestrator", query, context)

def planner(query: str, context: str = "") -> str:
    return _run("Planner", query, context)

def researcher(query: str, context: str = "", filepath: str = None) -> str:

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
    reasoning = _run("Coder", query, context)
    if not TOOLS_AVAILABLE:
        return reasoning

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
    #Analyses data and derives insights.Runs SQL queries via db_agent tool when data analysis is needed.
    reasoning = _run("Analyst", query, context)
    
    if not TOOLS_AVAILABLE:
        return reasoning

    db_keywords = ["revenue", "sales", "total", "average", "highest","lowest", "count", "query", "database", "sql"]
    if any(k in query.lower() for k in db_keywords):
        if raw_data and "data" in raw_data:
            db_agent.setup_database()
            db_agent.load_csv_into_db(raw_data["data"])
        db_result= db_agent.run(query)
        rows= db_result.get("result", {}).get("rows", [])
        if rows:
            return f"{reasoning}\n\n[DB Query Result]: {rows}"

    return reasoning

def critic(query: str, context: str = "") -> str:
    return _run("Critic", query, context)

def optimizer(query: str, context: str = "") -> str:
    return _run("Optimizer", query, context)

def validator(query: str, context: str = "") -> str:
    return _run("Validator", query, context)

def reporter(query: str, context: str = "") -> str:
    return _run("Reporter", query, context)