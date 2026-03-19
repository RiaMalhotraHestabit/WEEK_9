import os
import csv
import json
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_D3"))

# 2 SYSTEM PROMPTS — one for file analysis, and one for task parsing
ANALYSIS_PROMPT = """You are a File Agent. Your ONLY job is to reason about file contents.
You receive raw file data and return a clean, structured JSON summary.
You do NOT execute code. You do NOT query databases.
When given CSV data, identify columns, row count, data types, and notable patterns.
Always respond in JSON format:
{
  "file_type": "csv|txt",
  "summary": "brief description",
  "columns": ["col1", "col2"],
  "row_count": 0,
  "sample_data": [],
  "observations": ["obs1", "obs2"]
}"""

TASK_PARSER_PROMPT = """You are a task parser. Extract file operation details from the given task.
Return ONLY valid JSON with no extra text, no markdown, no code fences:
{
  "operation": "read or write",
  "filepath": "filename to read (only if operation is read, else null)",
  "write_path": "filename to write to (only if operation is write, else null)",
  "write_content": "exact content to write into the file (only if operation is write, else null)"
}
Rules:
- operation must be exactly "read" or "write"
- For write: extract the EXACT content the user wants written
- For read: extract the EXACT filename the user wants read
- If no filename is mentioned for read, use "sales.csv" as default
- If no filename is mentioned for write, use "output.txt" as default
- If no content is mentioned for write, use empty string"""

# MEMORY
MEMORY_WINDOW = 10
conversation_history = []

# TASK PARSER — LLM BASED
def parse_task_with_llm(task: str) -> dict:
    """
    Use LLM to parse the task and extract:
    - operation (read/write)
    - filepath (for read)
    - write_path + write_content (for write)
    Handles any phrasing naturally.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": TASK_PARSER_PROMPT},
                {"role": "user",   "content": task},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()

        # Clean markdown fences if present
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)

        # Validate required keys
        if "operation" not in parsed:
            raise ValueError("Missing operation key")

        return parsed

    except Exception as e:
        print(f"[FileAgent] Task parser fallback due to: {e}")
        # Safe fallback based on keywords
        task_lower = task.lower()
        if any(w in task_lower for w in ["write", "create", "save", "store"]):
            return {
                "operation": "write",
                "filepath": None,
                "write_path": "output.txt",
                "write_content": task,
            }
        else:
            return {
                "operation": "read",
                "filepath": "sales.csv",
                "write_path": None,
                "write_content": None,
            }

# CORE FILE OPERATIONS
def read_file(filepath: str) -> dict:
    """Read a .txt or .csv file and return its contents."""
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".csv":
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            return {
                "file_type": "csv",
                "filepath": filepath,
                "columns": list(reader.fieldnames) if reader.fieldnames else [],
                "row_count": len(rows),
                "data": rows,
            }

    elif ext == ".txt":
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {
            "file_type": "txt",
            "filepath": filepath,
            "content": content,
        }

    else:
        return {"error": f"Unsupported file type: {ext}. Only .csv and .txt supported."}


def write_file(filepath: str, content: str) -> dict:
    """Write content to a .txt or .csv file. Creates file and folders if they don't exist."""
    parent = os.path.dirname(filepath)
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "status": "success",
        "filepath": filepath,
        "bytes_written": len(content),
        "message": f"Successfully written to {filepath}",
    }


# LLM FILE ANALYSIS
def analyze_file_with_llm(file_data: dict) -> dict:
    """Send file data to Groq LLM for intelligent analysis."""
    global conversation_history

    user_message = f"Analyze this file data and return structured JSON:\n{json.dumps(file_data, indent=2)}"
    conversation_history.append({"role": "user", "content": user_message})

    # Keep memory window
    if len(conversation_history) > MEMORY_WINDOW:
        conversation_history = conversation_history[-MEMORY_WINDOW:]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": ANALYSIS_PROMPT}] + conversation_history,
        temperature=0.2,
        max_tokens=1024,
    )

    assistant_message = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": assistant_message})

    # Parse JSON response
    try:
        clean = assistant_message.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except json.JSONDecodeError:
        return {"raw_response": assistant_message}


# MAIN ENTRY POINT
def run(task: str = None, filepath: str = None, write_path: str = None, write_content: str = None) -> dict:
    """
    Main entry point for the File Agent.

    Can be called in two ways:
    1. Natural language task (recommended):
       file_agent.run(task="Write Hello to output.txt")
       file_agent.run(task="Read sales.csv and return its contents")

    2. Direct parameters (for orchestrator use):
       file_agent.run(filepath="sales.csv")
       file_agent.run(write_path="output.txt", write_content="Hello")
    """
    result = {"agent": "FileAgent"}

    # MODE 1: Natural language task -> parse with LLM
    if task:
        print(f"[FileAgent] Parsing task: {task}")
        parsed = parse_task_with_llm(task)
        print(f"[FileAgent] Parsed → operation: {parsed.get('operation')} | "
              f"filepath: {parsed.get('filepath')} | "
              f"write_path: {parsed.get('write_path')}")

        operation     = parsed.get("operation", "read")
        filepath      = parsed.get("filepath") or filepath
        write_path    = parsed.get("write_path") or write_path
        write_content = parsed.get("write_content") or write_content

        # If write operation, clear filepath so we don't try to read
        if operation == "write":
            filepath = None

    # MODE 2: WRITE operation
    if write_path and write_content is not None:
        print(f"[FileAgent] Writing to: {write_path}")
        write_result = write_file(write_path, write_content)
        result["operation"] = "write"
        result["write_result"] = write_result
        print(f"[FileAgent] Write successful: {write_result['message']}")
        return result

    #MODE 3: READ operation
    if filepath:
        print(f"[FileAgent] Reading: {filepath}")
        file_data = read_file(filepath)

        if "error" in file_data:
            result["error"] = file_data["error"]
            print(f"[FileAgent] {file_data['error']}")
            return result

        print(f"[FileAgent] Analyzing with LLM...")
        analysis = analyze_file_with_llm(file_data)
        result["operation"] = "read"
        result["raw_data"]  = file_data
        result["analysis"]  = analysis
        return result

    # FALLBACK if no valid operation determined
    result["error"] = "No task, filepath, or write parameters provided."
    return result

# STANDALONE TEST — Terminal Input

if __name__ == "__main__":

    # Create a sample CSV for testing if it doesn't exist
    sample_csv = "sales.csv"
    if not os.path.exists(sample_csv):
        with open(sample_csv, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["date", "product", "region", "units_sold", "revenue"])
            writer.writerows([
                ["2024-01-01", "Laptop", "North", 12, 14400],
                ["2024-01-02", "Phone",  "South", 25, 12500],
                ["2024-01-03", "Tablet", "East",   8,  4000],
                ["2024-01-04", "Laptop", "West",  19, 22800],
                ["2024-01-05", "Phone",  "North", 31, 15500],
            ])
        print(f"[FileAgent] Created sample {sample_csv} for testing.\n")

    print("=" * 50)
    print("  FILE AGENT — Interactive Terminal")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 50)

    while True:
        print()
        task = input("Enter your task: ").strip()

        if not task:
            continue

        if task.lower() in ["exit", "quit"]:
            print("[FileAgent] Goodbye!")
            break

        result = run(task=task)

        print("\n" + "-" * 50)
        print("RESULT:")
        print("-" * 50)

        if "error" in result:
            print(f" Error: {result['error']}")

        elif result.get("operation") == "write":
            wr = result.get("write_result", {})
            print(f" File written successfully!")
            print(f"   Path         : {wr.get('filepath')}")
            print(f"   Bytes written: {wr.get('bytes_written')}")
            print(f"   Message      : {wr.get('message')}")

        elif result.get("operation") == "read":
            analysis = result.get("analysis", {})
            raw      = result.get("raw_data", {})

            if "raw_response" in analysis:
                print(analysis["raw_response"])
            else:
                print(f" File read successfully!")
                print(f"   File     : {raw.get('filepath')}")
                print(f"   Type     : {analysis.get('file_type', raw.get('file_type'))}")
                print(f"   Summary  : {analysis.get('summary', 'N/A')}")

                if raw.get("file_type") == "csv":
                    print(f"   Columns  : {', '.join(analysis.get('columns', []))}")
                    print(f"   Rows     : {analysis.get('row_count', raw.get('row_count'))}")
                    print(f"\n   Observations:")
                    for obs in analysis.get("observations", []):
                        print(f"     • {obs}")

                elif raw.get("file_type") == "txt":
                    print(f"\n   Content:\n{raw.get('content', '')}")

        print("-" * 50)