from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext
from model_client import model_client

summarizer_agent = AssistantAgent(
    name="summarizer_agent",
    model_client=model_client,
    model_context=BufferedChatCompletionContext(buffer_size=10),
    system_message="""
You are a Summarizer Agent.
Your job is to read research notes and produce a concise summary.
Rules:
- Condense the research into key points
- Do NOT add new information
- Do NOT answer the user directly
"""
)