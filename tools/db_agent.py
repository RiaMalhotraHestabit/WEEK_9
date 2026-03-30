import os
import sqlite3
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_3"))
DB_PATH = "sales.db"

SYSTEM_PROMPT = """You are a DB Agent. Your ONLY job is to translate natural language questions into SQLite SQL queries.
Rules:
- Output ONLY the raw SQL query, nothing else
- No markdown, no explanation, no backticks
- Use standard SQLite syntax only
- The database has multiple tables. ALWAYS use the table name explicitly mentioned in the question
- If question mentions 'employees' — query employees table
- If question mentions 'sales' — query sales table
- Default table is `sales` with columns: date TEXT, product TEXT, region TEXT, units_sold INTEGER, revenue REAL
- employees table has columns: id INTEGER, name TEXT, salary REAL
- For CREATE TABLE queries: generate the correct CREATE TABLE IF NOT EXISTS statement
- For INSERT queries: generate correct INSERT INTO statements with sample data
- For SELECT queries: generate correct SELECT statements
- Support all SQL operations: SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, DROP TABLE
- Keep queries simple and correct"""

MEMORY_WINDOW = 10
conversation_history = []

def setup_database(db_path: str = DB_PATH) -> str:
    #Create and seed the SQLite database if it doesn't exist.
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            product TEXT,
            region TEXT,
            units_sold INTEGER,
            revenue REAL
        )
    """)
    # fill with sample data if empty
    cur.execute("SELECT COUNT(*) FROM sales")
    if cur.fetchone()[0] == 0:
        sample_rows = [
            ("2024-01-01", "Laptop", "North", 12, 14400),
            ("2024-01-02", "Phone",  "South", 25, 12500),
            ("2024-01-03", "Tablet", "East",  8,  4000),
            ("2024-01-04", "Laptop", "West",  19, 22800),
            ("2024-01-05", "Phone",  "North", 31, 15500),
            ("2024-01-06", "Tablet", "South", 14, 7000),
            ("2024-01-07", "Laptop", "East",  7,  8400),
            ("2024-01-08", "Phone",  "West",  22, 11000),
            ("2024-01-09", "Tablet", "North", 10, 5000),
            ("2024-01-10", "Laptop", "South", 15, 18000),
        ]
        cur.executemany("INSERT INTO sales (date, product, region, units_sold, revenue) VALUES (?,?,?,?,?)", sample_rows)
        conn.commit()
        print(f"[DBAgent] Seeded database with {len(sample_rows)} rows.")
    conn.close()
    return db_path

def natural_language_to_sql(question: str) -> str:
    #Use Groq to convert a natural language question to SQL.
    global conversation_history
    conversation_history.append({"role": "user", "content": question})
    if len(conversation_history) > MEMORY_WINDOW:
        conversation_history = conversation_history[-MEMORY_WINDOW:]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history,
        temperature=0.0,
        max_tokens=256,
    )
    sql = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": sql})

    # strip any accidental fences
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    return sql.strip()

def execute_query(sql: str, db_path: str = DB_PATH) -> dict:
    #Execute a SQL query and return results as a list of dicts.
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql)
        sql_upper = sql.strip().upper()
        if sql_upper.startswith("SELECT"):
            rows = [dict(row) for row in cur.fetchall()]
            conn.close()
            return {
                "status": "success",
                "sql": sql,
                "rows": rows,
                "count": len(rows)
            }
        else:
            conn.commit()
            affected = cur.rowcount
            conn.close()
            return {
                "status": "success",
                "sql": sql,
                "message": f"Query executed successfully. Rows affected: {affected}",
                "rows_affected": affected
            }
    except sqlite3.Error as e:
        return {"status": "error", "sql": sql, "error": str(e)}

def load_csv_into_db(csv_data: list, db_path: str = DB_PATH):
    #Load CSV rows (list of dicts) into the sales table.
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM sales")  # replace existing data
    for row in csv_data:
        cur.execute(
            "INSERT INTO sales (date, product, region, units_sold, revenue) VALUES (?,?,?,?,?)",
            (row.get("date"), row.get("product"), row.get("region"),int(row.get("units_sold", 0)), float(row.get("revenue", 0))))
    conn.commit()
    conn.close()
    print(f"[DBAgent] Loaded {len(csv_data)} rows into database.")

def run(question: str, db_path: str = DB_PATH) -> dict:
    setup_database(db_path)

    print(f"[DBAgent] Question: {question}")
    print(f"[DBAgent] Translating to SQL via Groq...")

    sql = natural_language_to_sql(question)
    print(f"[DBAgent] Generated SQL: {sql}")

    print(f"[DBAgent] Executing query...")
    query_result = execute_query(sql, db_path)

    return {
        "agent": "DBAgent",
        "question": question,
        "sql": sql,
        "result": query_result,
    }

if __name__ == "__main__":
    print("=" * 50)
    print("  DB AGENT — Interactive Terminal")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 50)
    while True:
        print()
        question = input("Enter your query: ").strip()
        if not question:
            continue
        if question.lower() in ["exit", "quit"]:
            print("[DBAgent] Goodbye!")
            break
        result = run(question)
        print("\n" + "-" * 50)
        print("RESULT:")
        print("-" * 50)
        query_result = result.get("result", {})
        if query_result.get("status") == "error":
            print(f" Error: {query_result.get('error')}")
        elif query_result.get("status") == "success":
            print(f" Query executed successfully!")
            print(f"   SQL: {result.get('sql')}")
            # SELECT result — show rows
            if "rows" in query_result:
                rows = query_result.get("rows", [])
                print(f"   Rows returned: {query_result.get('count', 0)}")
                if rows:
                    print(f"\n   Data:")
                    for row in rows:
                        row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                        print(f"     • {row_str}")
            # INSERT/UPDATE/DELETE/CREATE result — show message
            else:
                print(f"   {query_result.get('message')}")
        print("-" * 50)