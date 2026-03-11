from .base_agent import BaseAgent

class AnswerAgent(BaseAgent):

    def __init__(self, llm):

        system_prompt = """
You are an answer generator.

Your task:
- Use the summarized research
- Provide a clear final answer
"""

        super().__init__(llm, system_prompt)

    def run(self, summary):

        return self.generate(summary)