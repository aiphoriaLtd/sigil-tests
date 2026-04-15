import json
import os

from dotenv import load_dotenv
from sigil_sdk import (
    AuthConfig,
    Client,
    ClientConfig,
    GenerationExportConfig,
    GenerationStart,
    ModelRef,
    assistant_text_message,
    user_text_message,
)

load_dotenv()
original_endpoint = "https://subphonic.grafana.net/api/v1/generations:export"
alternative_endpoint = "https://sigil-prod-eu-west-3.grafana.net/api/v1/generations:export"

client = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            protocol="http",
            endpoint=alternative_endpoint,
            auth=AuthConfig(
                mode="basic",
                tenant_id=os.environ["GRAFANA_INSTANCE_ID"],
                basic_password=os.environ["GLC_TOKEN"],
            ),
        ),
    )
)

with client.start_generation(
    GenerationStart(
        conversation_id="conv-1",
        agent_name="my-test-agent",
        agent_version="1.0.0",
        model=ModelRef(provider="openai", name="gpt-4o"),
    )
) as rec:
    rec.set_result(
        input=[user_text_message("Say hello to James H from Subphonic")],
        output=[assistant_text_message("Hello James H from Subphonic! Sigil is up and running perfectly. Here's an interesting fact: armadillos always give birth to identical quadruplets — every litter consists of four genetically identical babies!")],
    )
    if rec.err() is not None:
        print("SDK error:", rec.err())

client.shutdown()
print("Done.")
