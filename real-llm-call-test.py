import os

from dotenv import load_dotenv
from openai import AzureOpenAI
from sigil_sdk import (
    AuthConfig,
    Client,
    ClientConfig,
    GenerationExportConfig,
    GenerationStart,
    ModelRef,
    TokenUsage,
    assistant_text_message,
    user_text_message,
)

load_dotenv()

azure_client = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=os.environ["AIPHORIA_AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AIPHORIA_AZURE_OPENAI_KEY"],
)
azure_model = os.environ["AIPHORIA_AZURE_OPENAI_DEPLOYMENT"]

sigil = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            protocol="http",
            endpoint="https://sigil-prod-eu-west-3.grafana.net/api/v1/generations:export",
            auth=AuthConfig(
                mode="basic",
                tenant_id=os.environ["GRAFANA_INSTANCE_ID"],
                basic_password=os.environ["GLC_TOKEN"],
            ),
        ),
    )
)

prompt = "Say hello to James H from Subphonic"

# Make the real LLM call via aiphoria
completion = azure_client.chat.completions.create(
    model=azure_model,
    messages=[
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": prompt},
    ],
    max_tokens=4096,
)

response_text = completion.choices[0].message.content
usage = completion.usage

print(f"LLM response: {response_text}\n")

# Record the generation in Sigil
with sigil.start_generation(
    GenerationStart(
        conversation_id="real-llm-python",
        agent_name="my-test-agent",
        agent_version="1.0.0",
        model=ModelRef(provider="azure_openai", name=azure_model),
    )
) as rec:
    rec.set_result(
        input=[user_text_message(prompt)],
        output=[assistant_text_message(response_text)],
        response_id=completion.id,
        response_model=completion.model,
        stop_reason=completion.choices[0].finish_reason or "",
        usage=TokenUsage(
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
        ),
    )
    if rec.err() is not None:
        print("SDK error:", rec.err())

sigil.shutdown()
print("Done.")
