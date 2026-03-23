import asyncio
import os
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_core.model_context import BufferedChatCompletionContext
from autogen_ext.models.openai import OpenAIChatCompletionClient

from memory.session_memory import SessionMemory
from memory.vector_store import VectorStore
from memory.long_term_memory import LongTermMemory

load_dotenv()

model_client = OpenAIChatCompletionClient(
    model="llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
    model_info={
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "structured_output": False,
        "family": "llama"
    },
)

# Initialize memory systems 
os.makedirs("memory", exist_ok=True)

session = SessionMemory(window_size=10)
vector = VectorStore()
long_term = LongTermMemory()

def build_agent(query: str) -> AssistantAgent:
    # FAISS recall
    recalled = vector.search(query, top_k=3)
    memory_block = "\n".join([r["text"] for r in recalled])

    # SQLite recent
    recent = long_term.get_recent(limit=5)
    db_block = "\n".join([f"{m['role']}: {m['content']}" for m in recent])

    # Session history
    session_block = "\n".join([f"{m['role']}: {m['content']}" for m in session.get_history()])

    system_prompt = f"""
You are an AI assistant with memory.

You are given past context, but you MUST follow these rules:

- Only use memory if the user query clearly requires it
- Do NOT mention past information for greetings like "hello", "hi"
- Do NOT force memory into every response
- Use memory ONLY when it improves the answer
- If the answer is known from memory, respond in one clear sentence
- Answer directly and concisely
- Do NOT add unnecessary explanations

Relevant past context:
{memory_block}

Recent conversation:
{db_block}

Current session:
{session_block}
"""

    return AssistantAgent(
        name="MemoryAgent",
        system_message=system_prompt,
        model_client=model_client,
        model_context=BufferedChatCompletionContext(buffer_size=10),
    )

# Summarizer agent 
def build_summarizer() -> AssistantAgent:
    return AssistantAgent(
        name="Summarizer",
        system_message="Summarize the following text into one concise sentence.",
        model_client=model_client,
    )


async def summarize(text: str) -> str:
    agent = build_summarizer()
    response = await agent.on_messages(
        [TextMessage(content=text, source="user")],
        cancellation_token=CancellationToken(),
    )
    return response.chat_message.content.strip()


# Chat pipeline 
async def chat(query: str) -> str:
    agent = build_agent(query)

    response = await agent.on_messages(
        [TextMessage(content=query, source="user")],
        cancellation_token=CancellationToken(),
    )
    reply = response.chat_message.content

    # summarize for FAISS
    summary = await summarize(reply)

    # store memory
    session.add("user", query)
    session.add("assistant", reply)

    long_term.add("user", query)
    long_term.add("assistant", reply)

    vector.add(f"User: {query}")
    vector.add(f"Assistant: {summary}")

    return reply

async def main():
    print("=== Day 4 Memory Agent ===")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            vector.save()
            break

        if user_input.lower() == "clear":
            session.clear()
            print("Session cleared.")
            continue

        reply = await chat(user_input)
        print("Agent:", reply)

if __name__ == "__main__":
    asyncio.run(main())