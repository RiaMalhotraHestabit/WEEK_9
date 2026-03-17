from autogen_ext.models.openai import OpenAIChatCompletionClient
import os
from dotenv import load_dotenv
 
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
model_client = OpenAIChatCompletionClient(
    model="llama-3.3-70b-versatile",   # fast + high quality
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
    model_info={
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "structured_output": False,
        "family": "llama"
    }
)