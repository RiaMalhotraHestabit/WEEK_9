from autogen_agentchat.agents import AssistantAgent
from model_client import model_client

answer_agent = AssistantAgent(
    name="answer_agent",
    model_client=model_client,
    system_message="""
You are the Final Answer Agent.
Your job is to read the summary and produce the final answer for the user.
"""
)