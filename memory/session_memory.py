import os
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY_D3"))

SYSTEM_PROMPT = """You are a helpful AI assistant with memory.
You remember the conversation history and use it to give contextual answers.
Always refer back to what was said earlier when relevant."""

class SessionMemory:
    """
    Short-term rolling window memory.
    Stores the last `window_size` messages in a list.
    Injected into every LLM call as conversation history.
    """
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.messages = []      # list of {role, content, timestamp}
        self.turn_count = 0

    def add(self, role: str, content: str):
        """Add a message to memory."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.turn_count += 1

        # Keep only last window_size messages
        if len(self.messages) > self.window_size:
            self.messages = self.messages[-self.window_size:]

    def get_history(self) -> list:
        """Return messages in LLM-ready format (role + content only)."""
        return [{"role": m["role"], "content": m["content"]} for m in self.messages]

    def clear(self):
        """Clear all memory."""
        self.messages = []
        self.turn_count = 0
        print("[SessionMemory] Memory cleared.")
        
    def summary(self):
        """Print current memory state."""
        print(f"\n[SessionMemory] Window size : {self.window_size}")
        print(f"[SessionMemory] Total turns : {self.turn_count}")
        print(f"[SessionMemory] Stored msgs : {len(self.messages)}")
        for i, m in enumerate(self.messages):
            preview = m["content"][:60] + "..." if len(m["content"]) > 60 else m["content"]
            print(f"  [{i+1}] {m['role'].upper()} ({m['timestamp'][:19]}): {preview}")

# CHAT FUNCTION
def chat(user_input: str, memory: SessionMemory) -> str:
    """
    Send a message to the LLM with full conversation history injected.
    Stores both user message and assistant response in memory.
    """
    # Add user message to memory
    memory.add("user", user_input)
    # Build messages with history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + memory.get_history()
    # Call LLM
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=512,
    )
    assistant_reply = response.choices[0].message.content.strip()
    memory.add("assistant", assistant_reply)
    return assistant_reply

if __name__ == "__main__":
    memory = SessionMemory(window_size=10)
    print("=" * 50)
    print("  SESSION MEMORY — Interactive Terminal")
    print("  Commands: 'memory' to see state, 'clear' to reset, 'exit' to quit")
    print("=" * 50)
    while True:
        print()
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("[SessionMemory] Goodbye!")
            break
        if user_input.lower() == "memory":
            memory.summary()
            continue
        if user_input.lower() == "clear":
            memory.clear()
            continue
        reply = chat(user_input, memory)
        print(f"\nAssistant: {reply}")