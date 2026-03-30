import os
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY_3")
MODEL        = "llama-3.3-70b-versatile"

# AutoGen 0.4.x expects an OpenAI-compatible client config
# Groq exposes an OpenAI-compatible endpoint
AUTOGEN_MODEL_CLIENT_CONFIG = {
    "model"   : MODEL,
    "api_key" : GROQ_API_KEY,
    "base_url": "https://api.groq.com/openai/v1",
}

#  PATHS
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR    = os.path.join(BASE_DIR, "logs")
MEMORY_DIR  = os.path.join(BASE_DIR, "..", "memory")
TOOLS_DIR   = os.path.join(BASE_DIR, "..", "tools")
DB_PATH     = os.path.join(MEMORY_DIR, "long_term.db")
FAISS_INDEX = os.path.join(MEMORY_DIR, "faiss.index")
FAISS_META  = os.path.join(MEMORY_DIR, "faiss_metadata.json")
TRACE_FILE  = os.path.join(LOGS_DIR, "trace.json")

#  GENERATION SETTINGS
MEMORY_WINDOW = 10
MAX_TOKENS    = 1024       # bumped up for richer agent responses
TEMPERATURE   = 0.3

#  AGENT REGISTRY
#  Each agent has:
#  role: system-prompt identity injected into AssistantAgent
#  keywords: used by Orchestrator to decide if this agent is needed
AGENTS = {
    "Orchestrator": {
        "role"       : (
            "You are the Master Coordinator of NEXUS AI. "
            "Given a user query, analyse it and return a JSON list of agent names "
            "(from: Planner, Researcher, Coder, Analyst, Critic, Optimizer, Validator, Reporter) "
            "that are REQUIRED to answer it — in the order they should run. "
            "Always end the list with Reporter. "
            "Return ONLY a valid JSON array, e.g.: [\"Planner\",\"Coder\",\"Reporter\"]"
        ),
        "temperature": 0.1,
        "keywords"   : [],          # always runs first
    },
    "Planner": {
        "role"       : (
            "You are the Planner agent in NEXUS AI. "
            "Break the query into an ordered, numbered action plan. "
            "Be concise. Do NOT repeat context verbatim."
        ),
        "temperature": 0.1,
        "keywords"   : ["plan", "strategy", "startup", "roadmap", "steps", "design", "pipeline", "architecture"],
    },
    "Researcher": {
        "role"       : (
            "You are the Researcher agent in NEXUS AI. "
            "Gather relevant facts, background knowledge, best practices and context. "
            "Cite sources or domain knowledge where applicable."
        ),
        "temperature": 0.4,
        "keywords"   : ["research", "healthcare", "market", "background", "facts", "rag", "documents", "knowledge"],
    },
    "Coder": {
        "role"       : (
            "You are the Coder agent in NEXUS AI. "
            "Write clean, runnable Python code or system design snippets to solve the technical task. "
            "Add brief inline comments."
        ),
        "temperature": 0.1,
        "keywords"   : ["code", "script", "function", "algorithm", "backend", "api", "database", "compute", "calculate", "implement"],
    },
    "Analyst": {
        "role"       : (
            "You are the Analyst agent in NEXUS AI. "
            "Analyse data, outputs or context — identify patterns, risks, and key insights. "
            "Be data-driven and precise."
        ),
        "temperature": 0.3,
        "keywords"   : ["csv", "data", "analyse", "analyze", "insight", "pattern", "revenue", "sales", "metrics", "statistics"],
    },
    "Critic": {
        "role"       : (
            "You are the Critic agent in NEXUS AI. "
            "Review all previous agent outputs. "
            "Identify weaknesses, missing pieces, logical errors, and suggest concrete improvements."
        ),
        "temperature": 0.4,
        "keywords"   : [],          # always added when >= 3 agents are selected
    },
    "Optimizer": {
        "role"       : (
            "You are the Optimizer agent in NEXUS AI. "
            "Take the Critic's feedback and rewrite / improve the previous outputs. "
            "Focus on quality, completeness, and clarity."
        ),
        "temperature": 0.3,
        "keywords"   : [],          # always paired with Critic
    },
    "Validator": {
        "role"       : (
            "You are the Validator agent in NEXUS AI. "
            "Check the final output for correctness, completeness, and consistency. "
            "Return APPROVED or list specific issues to fix."
        ),
        "temperature": 0.1,
        "keywords"   : ["validate", "verify", "check", "test", "architecture", "pipeline", "scalable"],
    },
    "Reporter": {
        "role"       : (
            "You are the Reporter agent in NEXUS AI. "
            "Compile ALL previous agent outputs into a single, clean, well-structured final report. "
            "Use markdown headings. Do not add new information — only organise and present."
        ),
        "temperature": 0.3,
        "keywords"   : [],          # always runs last
    },
}

#  PIPELINE RULES (used by smart selector)
# Critic + Optimizer always travel together
CRITIC_THRESHOLD = 3        # add Critic+Optimizer when pipeline has >= this many agents

# Fixed positions (cannot be reordered)
ALWAYS_FIRST = "Orchestrator"
ALWAYS_LAST  = "Reporter"

# Preferred execution order when multiple agents selected
AGENT_ORDER = [
    "Planner",
    "Researcher",
    "Coder",
    "Analyst",
    "Critic",
    "Optimizer",
    "Validator",
    "Reporter",
]