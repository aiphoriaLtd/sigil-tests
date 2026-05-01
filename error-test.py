"""Deliberately trigger an LLM error and record it via Sigil.

This tests that errors are correctly tracked in the AI Observability dashboard.
"""

import os
import random

from dotenv import load_dotenv
from openai import AzureOpenAI, BadRequestError
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sigil_sdk import (
    AuthConfig,
    Client,
    ClientConfig,
    GenerationExportConfig,
    GenerationStart,
    ModelRef,
    TokenUsage,
    user_text_message,
)

load_dotenv()

# --- OTel setup ---
resource = Resource.create({
    "service.name": "sigil-tests-python",
    "service.instance.id": "sigil-tests-python-1",
})

tp = TracerProvider(resource=resource)
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tp)

mp = MeterProvider(
    resource=resource,
    metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=5_000)],
)
metrics.set_meter_provider(mp)

# --- Clients ---
llm = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=os.environ["AIPHORIA_AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AIPHORIA_AZURE_OPENAI_KEY"],
)
model = os.environ["AIPHORIA_AZURE_OPENAI_DEPLOYMENT"]

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

# --- Force an error by requesting an impossible max_tokens value ---
prompt = "This request should fail"
error_type = ""
error_message = ""

try:
    # content_filter trigger: ask for something that will hit Azure's content filter
    # OR use an absurdly large max_tokens that exceeds model context window
    llm.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=999_999_999,  # far exceeds any model's context window
    )
except Exception as e:
    error_type = type(e).__name__
    error_message = str(e)[:200]
    print(f"Got expected error: {error_type}: {error_message}\n")

# Record the failed generation in Sigil
with sigil.start_generation(
    GenerationStart(
        conversation_id=f"error-test-{random.randint(100_000, 999_999)}",
        agent_name="my-test-agent",
        agent_version="1.0.0",
        operation_name="chat",
        model=ModelRef(provider="azure.ai.openai", name=model),
        tags={"test": "deliberate-error"},
    )
) as rec:
    rec.set_result(
        input=[user_text_message(prompt)],
        output=[],
        usage=TokenUsage(input_tokens=0, output_tokens=0, total_tokens=0),
        call_error=f"{error_type}: {error_message}",
    )
    if rec.err() is not None:
        print("Sigil SDK error:", rec.err())

# --- Shutdown ---
sigil.shutdown()
tp.shutdown()
mp.shutdown()
print("Done. Error should appear in AI Observability dashboard shortly.")
