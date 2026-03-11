from .base_agent import BaseAgent

class ResearchAgent(BaseAgent):

    def __init__(self, llm):

        system_prompt = """
You are a research specialist.

Your task:
- Gather factual information
- Provide detailed research notes
- Do not summarize
"""

        super().__init__(llm, system_prompt)

    def run(self, query):

        return self.generate(query)