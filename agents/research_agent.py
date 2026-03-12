from autogen_agentchat.agents import AssistantAgent
from model_client import model_client

research_agent = AssistantAgent(
    name="research_agent",
    model_client=model_client,
    system_message="""
You are a Research Agent.

Your job is to gather factual information about the user query.

Rules:
- Provide research notes
- Do NOT summarize
- Do NOT answer the user
"""
)