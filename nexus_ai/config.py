import os
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY_2")
MODEL        = "llama-3.3-70b-versatile"

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR   = os.path.join(BASE_DIR, "logs")
MEMORY_DIR = os.path.join(BASE_DIR, "..", "memory")
TOOLS_DIR  = os.path.join(BASE_DIR, "..", "tools")

DB_PATH    = os.path.join(MEMORY_DIR, "long_term.db")
FAISS_INDEX= os.path.join(MEMORY_DIR, "faiss.index")
FAISS_META = os.path.join(MEMORY_DIR, "faiss_metadata.json")
TRACE_FILE = os.path.join(LOGS_DIR, "trace.json")

MEMORY_WINDOW = 10
MAX_TOKENS    = 512
TEMPERATURE   = 0.3

# AGENT REGISTRY 
AGENTS = {
    "Orchestrator": {"role": "Master coordinator. Delegates tasks, monitors all agents, collects final report.", "temperature": 0.1},
    "Planner"     : {"role": "Breaks query into ordered steps. Assigns each step to the right agent.",           "temperature": 0.1},
    "Researcher"  : {"role": "Gathers facts, background knowledge, and context for the given topic.",            "temperature": 0.4},
    "Coder"       : {"role": "Writes and executes Python code to solve technical problems or analyze data.",     "temperature": 0.1},
    "Analyst"     : {"role": "Analyzes data, identifies patterns, and derives insights from outputs.",           "temperature": 0.3},
    "Critic"      : {"role": "Reviews agent work. Identifies weaknesses, gaps, errors, suggests improvements.", "temperature": 0.4},
    "Optimizer"   : {"role": "Takes critic feedback and improves previous output for quality and completeness.", "temperature": 0.3},
    "Validator"   : {"role": "Checks final output for correctness and completeness. Approves or flags issues.",  "temperature": 0.1},
    "Reporter"    : {"role": "Compiles all outputs into a clean, structured, human-readable final report.",      "temperature": 0.3},
}