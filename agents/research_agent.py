from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext
from model_client import model_client

research_agent = AssistantAgent(
    name="research_agent",
    model_client=model_client,
    model_context=BufferedChatCompletionContext(buffer_size=10),
    system_message="""
You are a Research Agent.
Your job is to gather factual information about the user query.
Rules:
- Provide detailed research notes
- Do NOT summarize
- Do NOT answer the user directly
"""
)