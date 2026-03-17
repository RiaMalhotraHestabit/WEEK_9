from autogen_agentchat.agents import AssistantAgent
from model_client import model_client

validator_agent = AssistantAgent(
    name="validator_agent",
    model_client=model_client,
    system_message="""
ROLE:
You are a Validator Agent.

INPUT:
The refined answer from the reflection agent.

TASK:
Ensure the answer is correct, clear, and well-written.

INSTRUCTIONS:
- Fix any factual or logical errors if present
- Improve clarity if needed
- Keep the answer concise and readable
- Maintain paragraph format
- Do NOT add explanations or comments
- Do NOT mention corrections

OUTPUT FORMAT:
Return the final clean answer as a paragraph.
"""
)