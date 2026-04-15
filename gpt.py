import sys
import os
from openai import OpenAI, AzureOpenAI
from pydantic import BaseModel

AIPHORIA_AZURE_OPENAI_ENDPOINT = os.getenv("AIPHORIA_AZURE_OPENAI_ENDPOINT")
AIPHORIA_AZURE_OPENAI_DEPLOYMENT = os.getenv("AIPHORIA_AZURE_OPENAI_DEPLOYMENT")
AIPHORIA_AZURE_OPENAI_KEY = os.getenv("AIPHORIA_AZURE_OPENAI_KEY")

client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=AIPHORIA_AZURE_OPENAI_ENDPOINT,
    api_key=AIPHORIA_AZURE_OPENAI_KEY,
)
model = AIPHORIA_AZURE_OPENAI_DEPLOYMENT

# Optionally, package up as a function
def complete(message, developer_message = "You are a helpful assistant", max_completion_tokens = 4096, response_format = { "type": "text" }):
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": developer_message},
            {"role": "user", "content": message}
        ],
        max_tokens=max_completion_tokens,
        response_format=response_format
    )
    return completion.choices[0].message.content

# Structured output-friendly function
class Response(BaseModel):
    response: str
    observations: str

def complete_structured(message, developer_message = "You are a helpful assistant. You always respond using a JSON object containing a response key, where you write your freetext response, and an 'observations' key, where you may include any additional observations about the user query or the nature of the conversation. ", max_completion_tokens = 4096, output_model = Response):
    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": developer_message},
            {"role": "user", "content": message}
        ],
        max_tokens=max_completion_tokens,
        response_format=output_model
    )
    return completion.choices[0].message.parsed.model_dump_json()


# 

# Example of tracking LLM-generated calls with sigil

from sigil_sdk import Client, ClientConfig, GenerationStart, ModelRef, assistant_text_message

client = Client(
    ClientConfig(
        generation_export_endpoint="http://localhost:8080/api/v1/generations:export",
    )
)

with client.start_generation(
    GenerationStart(
        conversation_id="conv-1",
        model=ModelRef(provider="openai", name="gpt-5"),
    )
) as rec:
    rec.set_result(output=[assistant_text_message("Hello from Sigil")])

client.shutdown()