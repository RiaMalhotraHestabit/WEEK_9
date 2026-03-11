from transformers import pipeline

class LocalLLM:
    def __init__(self):
        self.generator = pipeline(
            "text-generation",
            model="microsoft/Phi-3-mini-4k-instruct",
            max_new_tokens=80,
            do_sample=False,
            return_full_text=False
        )

    def generate(self, prompt):
        result = self.generator(prompt)
        text = result[0]["generated_text"]
        text = text.split("User")[0]
        text = text.split("Conversation")[0]

        return text.strip()