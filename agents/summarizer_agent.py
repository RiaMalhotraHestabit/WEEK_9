from .base_agent import BaseAgent

class SummarizerAgent(BaseAgent):

    def __init__(self, llm):

        system_prompt = """
You are a summarization expert.

Your task:
- Convert research text into concise bullet points
- Keep key facts
- Do not introduce new information
"""

        super().__init__(llm, system_prompt)

    def run(self, research_text):

        return self.generate(research_text)