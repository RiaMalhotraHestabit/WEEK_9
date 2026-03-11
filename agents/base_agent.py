class BaseAgent:
    def __init__(self, llm, system_prompt):
        self.llm = llm
        self.system_prompt = system_prompt
        self.memory = []

    def add_to_memory(self, role, content):
        self.memory.append({"role": role,"content": content})
        if len(self.memory) > 10:
            self.memory.pop(0)

    def build_prompt(self, input_text):
        conversation = ""
        for msg in self.memory:
            conversation += f"{msg['role']}: {msg['content']}\n"

        prompt = f"""
{self.system_prompt}

Conversation History:
{conversation}

User Question:
{input_text}

Answer:
"""
        return prompt.strip()

    def generate(self, input_text):
        self.add_to_memory("user", input_text)
        prompt = self.build_prompt(input_text)
        response = self.llm.generate(prompt)
        response = response.split("Question:")[0]
        response = response.split("User Question:")[0]
        response = response.split("Research Text:")[0]
        self.add_to_memory("assistant", response)
        return response.strip()