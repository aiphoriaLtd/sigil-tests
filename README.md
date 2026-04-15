# Sigil Tests

Working examples of using [Grafana Sigil](https://github.com/grafana/sigil-sdk) to trace real LLM calls made via Azure OpenAI (Aiphoria endpoints). Each example makes a live LLM call and records the generation — including input/output messages, token usage, and model metadata — to Sigil for observability.

## Examples

| File | Language | Description |
|------|----------|-------------|
| [real-llm-call-test.py](real-llm-call-test.py) | Python | Calls Azure OpenAI and records the generation via the Sigil Python SDK |
| [ts-auth-example.ts](ts-auth-example.ts) | TypeScript | Same flow using the Sigil JS SDK and OpenAI Node.js SDK |

For full TypeScript setup instructions (building the SDK from source, dependencies, troubleshooting), see [ts-auth-README.md](ts-auth-README.md).

---

## Authentication

Both the Sigil export and the Azure OpenAI call require credentials. These are passed as environment variables.

### Sigil / Grafana Cloud credentials

Sigil uses **HTTP Basic Auth** to authenticate generation exports. You need two values: your **Grafana Cloud instance ID** (used as the tenant) and a **Grafana Cloud API token** (used as the password).

| Variable | What it is | Where to find it |
|----------|-----------|-----------------|
| `GRAFANA_INSTANCE_ID` | Your Grafana Cloud stack's numeric instance ID. This is the **tenant ID** used in the `X-Scope-OrgID` header. | In your Grafana Cloud stack: go to **Connections → Sigil plugin → Connection tab**. The value is shown under **Tenant ID Fallback**. You can also find it in the Grafana Cloud Portal under your stack details. |
| `GLC_TOKEN` | A Grafana Cloud API token (starts with `glc_`). Used as the Basic Auth password alongside the instance ID. | Create one in your Grafana Cloud stack: go to **Administration → Cloud Access Policies** (or via the [Cloud Portal](https://grafana.com/orgs)). Create an access policy scoped to your stack, then generate a token. The token only needs write permissions for AI Observability / Sigil. See [Grafana Cloud Access Policies docs](https://grafana.com/docs/grafana-cloud/account-management/authentication-and-permissions/access-policies/) for details. |

**How auth works in the SDK:**

The Sigil SDK sends generation data to the ingest endpoint using HTTP Basic Auth where:
- **Username** = the instance/tenant ID (`GRAFANA_INSTANCE_ID`)
- **Password** = the API token (`GLC_TOKEN`)

The endpoint URL follows the pattern:
```
https://sigil-prod-<region>.grafana.net/api/v1/generations:export
```

You can find the correct URL for your stack in the **Sigil plugin → Connection tab** under **Sigil API URL** — just append `/api/v1/generations:export` to it.

### Azure OpenAI (Aiphoria) credentials

These examples use Aiphoria's Azure OpenAI endpoints to make real LLM calls.

| Variable | What it is | Where to find it |
|----------|-----------|-----------------|
| `AIPHORIA_AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI resource endpoint URL | Azure Portal → your OpenAI resource → **Keys and Endpoint** |
| `AIPHORIA_AZURE_OPENAI_DEPLOYMENT` | The model deployment name (e.g. `gpt-4.1`) | Azure Portal → your OpenAI resource → **Model deployments** |
| `AIPHORIA_AZURE_OPENAI_KEY` | API key for the Azure OpenAI resource | Azure Portal → your OpenAI resource → **Keys and Endpoint** (Key 1 or Key 2) |

### Setting the variables

You can set these in a `.env` file in the project root:

```dotenv
GLC_TOKEN=glc_your_token_here
GRAFANA_INSTANCE_ID=1234567
AIPHORIA_AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AIPHORIA_AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AIPHORIA_AZURE_OPENAI_KEY=your-api-key
```

Or export them in your shell profile (e.g. `~/.zshrc`):

```bash
export AIPHORIA_AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AIPHORIA_AZURE_OPENAI_DEPLOYMENT="gpt-4.1"
export AIPHORIA_AZURE_OPENAI_KEY="your-api-key"
```

> **Note:** The `.env` file is gitignored — credentials will not be committed.

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
