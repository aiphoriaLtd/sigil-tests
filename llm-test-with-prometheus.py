"""Sigil + OTel + Azure OpenAI — Python reference implementation.

This script makes multiple LLM calls in a loop so the OTel histogram counter
INCREMENTS within a single process lifetime. Grafana Cloud Mimir uses increase()
over cumulative counters — a single-call script exports count=1 every cycle,
and increase(1→1) = 0. A loop that does N calls exports count=1,2,3... so
increase() correctly computes the delta.

Two telemetry channels:
  1. Generation export (Sigil) → "Conversations", "Total Tokens"
  2. OTel metrics + traces    → "Total Requests", "Latency", "Error Rate"

Usage:
  SSL_CERT_FILE="$(.venv/bin/python -m certifi)" .venv/bin/python llm-test-with-prometheus.py
"""

import os
import random
import time

from dotenv import load_dotenv
from openai import AzureOpenAI
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
    assistant_text_message,
    user_text_message,
)

load_dotenv()

# --- OTel providers (MUST be configured BEFORE Sigil Client creation) --------
resource = Resource.create({"service.name": "sigil-tests-python"})

tp = TracerProvider(resource=resource)
tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tp)

mp = MeterProvider(
    resource=resource,
    metric_readers=[
        PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=5000)
    ],
)
metrics.set_meter_provider(mp)

# --- LLM client --------------------------------------------------------------
llm = AzureOpenAI(
    api_version="2024-12-01-preview",
    azure_endpoint=os.environ["AIPHORIA_AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AIPHORIA_AZURE_OPENAI_KEY"],
)
models = ["gpt-4.1", "gpt-5.4"]

# --- Sigil client -------------------------------------------------------------
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

AGENT_NAME = "my-test-agent"
AGENT_VERSION = "1.0.0"
NUM_CALLS = int(os.environ.get("NUM_CALLS", "6"))

prompts = [
    "What are the three pillars of observability?",
    "Explain distributed tracing in one sentence.",
    "What is a histogram metric?",
    "What does SLO stand for?",
    "What is the difference between logs and traces?",
    "What is an SLI and how does it relate to an SLO?",
]

for i in range(NUM_CALLS):
    prompt = prompts[i % len(prompts)]
    model = models[i % len(models)]
    print(f"\n[{i+1}/{NUM_CALLS}] [{model}] Prompt: {prompt}")

    with sigil.start_generation(
        GenerationStart(
            conversation_id=f"py-test-{random.randint(100_000, 999_999)}",
            agent_name=AGENT_NAME,
            agent_version=AGENT_VERSION,
            operation_name="chat",
            model=ModelRef(provider="azure.ai.openai", name=model),
        )
    ) as rec:
        completion = llm.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Be brief."},
                {"role": "user", "content": prompt},
            ],
        )

        response_text = completion.choices[0].message.content
        usage = completion.usage
        print(f"  Response: {response_text[:80]}...")

        rec.set_result(
            input=[user_text_message(prompt)],
            output=[assistant_text_message(response_text or "")],
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
            print(f"  Sigil error: {rec.err()}")

    # Space out calls so metrics have time to export between them
    if i < NUM_CALLS - 1:
        time.sleep(5)

# --- Shutdown -----------------------------------------------------------------
print("\nFlushing telemetry...")
sigil.shutdown()
tp.shutdown()
mp.shutdown()
print("Done. Check AI Observability dashboard in ~1 min.")
