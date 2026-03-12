from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(
    model="mistral",
    base_url="http://localhost:11434/v1",
    api_key="not-needed",
    model_info={
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "family": "unknown"
    }
)