import os
import json
import subprocess
import tempfile
import sys
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_D3"))

SYSTEM_PROMPT = """You are a Code Agent. Your ONLY job is to write and execute Python code.
You receive a task and write Python code to accomplish it.
Rules:
- Write ONLY pure Python code (no markdown, no explanation, no ```python fences)
- Use only standard library + pandas + json (always available)
- If the task involves data analysis, the data will be in a variable called `raw_data_json`
  Parse it with: import json; data = json.loads(raw_data_json)
- If the task is a general coding task (binary search, sorting, math etc), just write the code directly
- ALWAYS print your final result using: print(json.dumps(result, default=lambda x: int(x) if hasattr(x, 'item') else str(x)))
- If result is a simple value (number, string), wrap it: print(json.dumps({"result": your_value}, default=lambda x: int(x) if hasattr(x, 'item') else str(x)))
- The last print statement must be valid JSON
- Never use input(), open(), or network calls"""
MEMORY_WINDOW = 10
conversation_history = []

def generate_code(task: str, data_context: str) -> str:
    """Ask Groq to write Python code for the task."""
    global conversation_history

    user_message = f"""Task: {task}

Data context:
{data_context}

Write Python code to accomplish this task. The raw data JSON will be in a variable called `raw_data_json`.
Output ONLY executable Python code."""

    conversation_history.append({"role": "user", "content": user_message})

    if len(conversation_history) > MEMORY_WINDOW:
        conversation_history = conversation_history[-MEMORY_WINDOW:]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
        temperature=0.1,
        max_tokens=2048,
    )

    code = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": code})

    # Strip markdown fences if the model adds them anyway
    if code.startswith("```"):
        lines = code.split("\n")
        code = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return code

def execute_code(code: str, raw_data: dict, timeout: int = 15) -> dict:
    """Execute the generated Python code in a subprocess with the data injected."""
    data_injection = f'raw_data_json = {json.dumps(json.dumps(raw_data))}\n'
    full_code = data_injection + code

    # Write to a temp file and run it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(full_code)
        tmp_path = f.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if result.returncode != 0:
            return {"status": "error", "stderr": stderr, "code": full_code}

        # Try to parse the last line as JSON
        output_lines = [l for l in stdout.split("\n") if l.strip()]
        if not output_lines:
            return {"status": "error", "stderr": "No output produced", "code": full_code}

        try:
            parsed = json.loads(output_lines[-1])
            return {"status": "success", "result": parsed, "stdout": stdout}
        except json.JSONDecodeError:
            return {"status": "success", "result": stdout, "stdout": stdout}

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"Execution exceeded {timeout}s"}
    finally:
        os.unlink(tmp_path)

def run(task: str, raw_data: dict) -> dict:
    print(f"[CodeAgent] Task: {task}")

    # Build a compact context summary for the prompt
    data_context = json.dumps(raw_data, indent=2)[:1500]  # cap context length

    print(f"[CodeAgent] Generating code via Groq...")
    code = generate_code(task, data_context)
    print(f"[CodeAgent] Generated code:\n{'-'*40}\n{code}\n{'-'*40}")

    print(f"[CodeAgent] Executing code...")
    exec_result = execute_code(code, raw_data)

    return {
        "agent": "CodeAgent",
        "task": task,
        "generated_code": code,
        "execution": exec_result,
    }

if __name__ == "__main__":
    # Sample data available if task needs it
    sample_data = {
        "columns": ["date", "product", "region", "units_sold", "revenue"],
        "row_count": 7,
        "data": [
            {"date": "2024-01-01", "product": "Laptop", "region": "North", "units_sold": "12", "revenue": "14400"},
            {"date": "2024-01-02", "product": "Phone",  "region": "South", "units_sold": "25", "revenue": "12500"},
            {"date": "2024-01-03", "product": "Tablet", "region": "East",  "units_sold": "8",  "revenue": "4000"},
            {"date": "2024-01-04", "product": "Laptop", "region": "West",  "units_sold": "19", "revenue": "22800"},
            {"date": "2024-01-05", "product": "Phone",  "region": "North", "units_sold": "31", "revenue": "15500"},
            {"date": "2024-01-06", "product": "Tablet", "region": "South", "units_sold": "14", "revenue": "7000"},
            {"date": "2024-01-07", "product": "Laptop", "region": "East",  "units_sold": "7",  "revenue": "8400"},
        ],
    }

    print("=" * 50)
    print("  CODE AGENT — Interactive Terminal")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 50)

    while True:
        print()
        task = input("Enter your task: ").strip()

        if not task:
            continue

        if task.lower() in ["exit", "quit"]:
            print("[CodeAgent] Goodbye!")
            break

        # Use sample_data only if task seems data related
        data_keywords = ["sales", "csv", "data", "analyze", "revenue", "product", "region"]
        raw_data = sample_data if any(k in task.lower() for k in data_keywords) else {}

        result = run(task=task, raw_data=raw_data)

        print("\n" + "-" * 50)
        print("RESULT:")
        print("-" * 50)

        execution = result.get("execution", {})

        if execution.get("status") == "success":
            print(" Code executed successfully!")
            print(f"\n   Generated Code:\n")
            for line in result.get("generated_code", "").split("\n"):
                print(f"   {line}")
            print(f"\n   Output:")
            output = execution.get("result", "")
            if isinstance(output, dict):
                for k, v in output.items():
                    print(f"     • {k}: {v}")
            elif isinstance(output, list):
                for item in output:
                    if isinstance(item, dict):
                        for k, v in item.items():
                            print(f"     • {k}: {v}")
                        print()
                    else:
                        print(f"     • {item}")
            else:
                print(f"     {output}")

        elif execution.get("status") == "error":
            print(f" Execution Error:")
            print(f"   {execution.get('stderr', 'Unknown error')}")

        elif execution.get("status") == "timeout":
            print(f" Timeout: {execution.get('error')}")

        print("-" * 50)

