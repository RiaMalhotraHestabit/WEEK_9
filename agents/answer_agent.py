from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext
from model_client import model_client

answer_agent = AssistantAgent(
    name="answer_agent",
    model_client=model_client,
    model_context=BufferedChatCompletionContext(buffer_size=10),
    system_message="""
You are the Final Answer Agent.
Your job is to read the summary and produce a clear, friendly final answer for the user.
Rules:
- Use only the provided summary
- Keep the answer concise and easy to understand
"""
)