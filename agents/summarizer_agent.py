from autogen_agentchat.agents import AssistantAgent
from model_client import model_client

summarizer_agent = AssistantAgent(
    name="summarizer_agent",
    model_client=model_client,
    system_message="""
You are a Summarizer Agent.

Your job is to read research notes and produce a concise summary.

Rules:
- Do NOT answer the user
"""
)