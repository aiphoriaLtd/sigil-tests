# Sigil SDK — Working Examples

Reference implementations for instrumenting LLM calls with [Grafana Sigil](https://github.com/grafana/sigil-sdk). These examples make real Azure OpenAI calls and export generation telemetry to Grafana Cloud's AI Observability dashboards.

For the full instrumentation brief from the Grafana team (OTel setup, telemetry fields, multi-agent tracking, SDK API reference), see [`instructions.md`](instructions.md).

---

## What Must Be In Place

For the AI Observability dashboard to fully populate (**both** conversations/tokens **and** Total Requests/Latency/Error Rate), you need:

### 1. SDK Version

- **Python:** `sigil-sdk >= 0.2.0` (install from source: `pip install git+https://github.com/grafana/sigil-sdk.git#subdirectory=python`)
- **TypeScript:** `@grafana/sigil-sdk-js` (built from source — not on npm yet)

### 2. OTel Providers Before Sigil Client

The Sigil SDK calls `trace.get_tracer()` / `metrics.get_meter()` at construction time. If no providers are registered, metrics silently go to a no-op. **Always** set up `TracerProvider` + `MeterProvider` before creating the Sigil client.

### 3. Two Telemetry Channels (Both Required)

| Channel                                | What it powers                      | How it's configured                                              |
| -------------------------------------- | ----------------------------------- | ---------------------------------------------------------------- |
| **Generation export** (Sigil-specific) | Conversations, Total Tokens         | `GenerationExportConfig` with endpoint + auth                    |
| **OTel traces + metrics**              | Total Requests, Latency, Error Rate | `OTEL_EXPORTER_OTLP_*` env vars (read automatically by OTel SDK) |

### 4. Short Export Interval (for short-lived scripts)

Grafana Cloud Mimir uses `increase()` over cumulative counters. It needs **at least 2 data points** from separate exports to compute a delta. With the default 60-second export interval, a script that finishes in under a minute only exports once at shutdown — so `increase()` returns nothing and "Total Requests" shows 0.

**Fix:** Set `export_interval_millis=5000` (Python) / `exportIntervalMillis: 5_000` (TypeScript) so metrics export every 5 seconds. Combined with spacing calls 5s apart, a 6-call script produces ~8 exports → Mimir sees proper increments.

### 5. Multiple Calls Per Process

The scripts use a **loop** (default 6 calls, configurable via `NUM_CALLS`) so the counter increments `1→2→3→...` and Mimir computes real deltas.

> For long-running services (web servers, agents), neither #4 nor #5 are issues — the counter naturally increments and exports fire many times over the process lifetime.

### 6. Environment Variables

All six of these must be set in `.env`:

```dotenv
# Grafana Cloud / Sigil (generation export → conversations + tokens)
GLC_TOKEN=glc_your_token_here
GRAFANA_INSTANCE_ID=1234567

# OTel (traces + metrics → Total Requests, Latency, Error Rate)
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-<region>.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64(instance_id:cloud_api_token)>

# Azure OpenAI
AIPHORIA_AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AIPHORIA_AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AIPHORIA_AZURE_OPENAI_KEY=your-api-key
```

**Where to find these values:**

| Variable                      | Source                                                                                                  |
| ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| `GLC_TOKEN`                   | Grafana Cloud → Administration → Cloud Access Policies → create token with AI Observability write scope |
| `GRAFANA_INSTANCE_ID`         | Grafana Cloud portal → stack details (numeric ID)                                                       |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Grafana Cloud portal → stack Details → OpenTelemetry                                                    |
| `OTEL_EXPORTER_OTLP_HEADERS`  | `Authorization=Basic <base64(instance_id:cloud_api_token)>`                                             |
| `AIPHORIA_AZURE_OPENAI_*`     | Azure Portal → your OpenAI resource → Keys and Endpoint / Model deployments                             |

---

## Python Example

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install sigil-sdk 0.2.0 from source (required):
pip install git+https://github.com/grafana/sigil-sdk.git#subdirectory=python
```

### Run

```bash
# macOS needs SSL cert fix:
SSL_CERT_FILE="$(.venv/bin/python -m certifi)" .venv/bin/python llm-test-with-prometheus.py

# More calls:
SSL_CERT_FILE="$(.venv/bin/python -m certifi)" NUM_CALLS=5 .venv/bin/python llm-test-with-prometheus.py

# Or use the convenience script:
./run-python.sh
```

---

## TypeScript Example

### Setup

```bash
# 1. Clone and build the Sigil JS SDK (not on npm yet)
git clone --depth 1 https://github.com/grafana/sigil-sdk.git /tmp/sigil-sdk
cd /tmp/sigil-sdk/js
npm install --legacy-peer-deps
npx tsc --project tsconfig.build.json

# 2. Install project dependencies
cd /path/to/sigil-tests
npm install
```

### Run

```bash
npx tsx llm-test.ts

# More calls:
NUM_CALLS=5 npx tsx llm-test.ts

# Or use the convenience script:
./run-typescript.sh
```

---

## Simple Example (Sigil-only, no OTel metrics)

[`real-llm-call-test.py`](real-llm-call-test.py) — minimal script that only does the Sigil generation export (conversations + tokens). Does **not** set up OTel providers, so "Total Requests" won't populate. Useful as a baseline reference.

```bash
SSL_CERT_FILE="$(.venv/bin/python -m certifi)" .venv/bin/python real-llm-call-test.py
```

---

## Other Examples

- [`tool-call-test.py`](tool-call-test.py) — LLM calls with function/tool calling
- [`error-test.py`](error-test.py) — Deliberate error test (records `call_error` field)

---

## How It Works

### Two telemetry paths

```
Your Script
    │
    ├─→ Sigil generation export ──→ sigil-prod-<region>.grafana.net
    │       (conversations, tokens, messages)
    │
    └─→ OTel OTLP export ──→ otlp-gateway-prod-<region>.grafana.net
            (traces: gen_ai spans)
            (metrics: gen_ai.client.operation.duration, gen_ai.client.token.usage)
```

Both feed into the AI Observability dashboard. Without OTel, you get conversations but no request counts/latency. Without Sigil export, you get request metrics but no conversation content.

### Key technical details

- The SDK uses scope `github.com/grafana/sigil/sdks/python` (Python) / `github.com/grafana/sigil/sdks/js` (JS) — dashboards filter by this
- Provider name must be `azure.ai.openai` (OTel semantic conventions canonical value)
- `operation_name` must be `"chat"` for chat completions
- The `OTEL_EXPORTER_OTLP_*` env vars are read automatically by OTel SDK exporters — no extra code needed

---

## Reference

- [Sigil SDK repository](https://github.com/grafana/sigil-sdk) — source for all language SDKs
- [`instructions.md`](instructions.md) — full instrumentation brief from the Grafana team
- [Grafana Cloud OTLP docs](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp) — how to send OTel data to Cloud
- [OTel GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) — canonical attribute names

---

## Quick Start

### Python

```bash
# Set up the virtual environment (requires uv)
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Run
.venv/bin/python3 real-llm-call-test.py
```

### TypeScript

See [ts-auth-README.md](ts-auth-README.md) for full setup instructions, including how to build the Sigil JS SDK from source.

```bash
npx tsx ts-auth-example.ts
```

---

## Further Reading

- [ts-auth-README.md](ts-auth-README.md) — Detailed TypeScript setup guide (building the SDK, dependencies, troubleshooting)
- [Grafana AI Observability docs](https://grafana.com/docs/grafana-cloud/monitor-applications/ai-observability/)
- [Grafana Cloud Access Policies](https://grafana.com/docs/grafana-cloud/account-management/authentication-and-permissions/access-policies/)
- [Sigil SDK monorepo](https://github.com/grafana/sigil-sdk)
