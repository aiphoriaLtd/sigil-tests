# Sigil Tests

Working examples of using [Grafana Sigil](https://github.com/grafana/sigil-sdk) to trace real LLM calls made via Azure OpenAI (Aiphoria endpoints).

Each example makes a live LLM call and records the generation — including input/output messages, token usage, and model metadata — to Sigil for observability.

## Examples

| File | Language | Description |
|------|----------|-------------|
| [real-llm-call-test.py](real-llm-call-test.py) | Python | Calls Azure OpenAI and records the generation via the Sigil Python SDK |
| [ts-auth-example.ts](ts-auth-example.ts) | TypeScript | Same flow using the Sigil JS SDK and OpenAI Node.js SDK |

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

## Environment Variables

Both examples require the following environment variables. These can be set in a `.env` file or in your shell profile (e.g. `~/.zshrc`).

### Sigil / Grafana Cloud

| Variable | Description |
|----------|-------------|
| `GLC_TOKEN` | Grafana Cloud API token with write permissions |
| `GRAFANA_INSTANCE_ID` | Grafana Cloud instance ID (numeric) |

### Azure OpenAI (Aiphoria)

| Variable | Description |
|----------|-------------|
| `AIPHORIA_AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource endpoint |
| `AIPHORIA_AZURE_OPENAI_DEPLOYMENT` | Model deployment name (e.g. `gpt-4.1`) |
| `AIPHORIA_AZURE_OPENAI_KEY` | Azure OpenAI API key |

## Further Reading

- [ts-auth-README.md](ts-auth-README.md) — Detailed TypeScript setup guide (building the SDK, dependencies, troubleshooting)
