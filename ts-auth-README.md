# Sigil SDK — TypeScript Quick Start

## Prerequisites

- **Node.js** v22+ (for top-level `await` support)
- **Git** (to clone the SDK monorepo)
- Access to the [grafana/sigil-sdk](https://github.com/grafana/sigil-sdk) GitHub repository
- Azure OpenAI credentials (endpoint, deployment name, and API key)

## 1. Clone this repo and install the Sigil JS SDK

The `@grafana/sigil-sdk-js` package is not published to the public npm registry. You need to clone the monorepo, build the JS SDK locally, and install it as a file dependency.

```bash
# Clone the Sigil SDK monorepo (shallow clone is fine)
git clone --depth 1 https://github.com/grafana/sigil-sdk.git /tmp/sigil-sdk

# Install the JS SDK's own dependencies and build it
cd /tmp/sigil-sdk/js
npm install --legacy-peer-deps
npx tsc --project tsconfig.build.json
```

> **Note:** `--legacy-peer-deps` is needed to resolve a peer dependency conflict with `@google/adk`.

## 2. Install project dependencies

Back in this project directory:

```bash
npm install /tmp/sigil-sdk/js openai dotenv tsx typescript
```

This installs:

- `@grafana/sigil-sdk-js` — the Sigil SDK (from the local build)
- `openai` — the OpenAI Node.js SDK (supports Azure OpenAI)
- `dotenv` — loads environment variables from `.env`
- `tsx` — TypeScript runner (no separate compile step needed)
- `typescript` — TypeScript compiler

## 3. Configure environment variables

Create a `.env` file in the project root with your Grafana and Azure OpenAI credentials:

```dotenv
GLC_TOKEN=glc_your_token_here
GRAFANA_INSTANCE_ID=your_instance_id_here
AIPHORIA_AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AIPHORIA_AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AIPHORIA_AZURE_OPENAI_KEY=your-api-key
```

- **`GLC_TOKEN`** — a Grafana Cloud API token with write permissions
- **`GRAFANA_INSTANCE_ID`** — your Grafana Cloud instance ID (numeric)
- **`AIPHORIA_AZURE_OPENAI_ENDPOINT`** — your Azure OpenAI resource endpoint
- **`AIPHORIA_AZURE_OPENAI_DEPLOYMENT`** — the model deployment name (e.g. `gpt-4.1`)
- **`AIPHORIA_AZURE_OPENAI_KEY`** — your Azure OpenAI API key

> The Azure OpenAI variables can also be set in your shell profile (e.g. `~/.zshrc`) instead of `.env`.

## 4. Ensure `package.json` has ESM enabled

Your `package.json` must include `"type": "module"` for top-level `await` to work:

```json
{
  "type": "module"
}
```

## 5. Run the example

```bash
npx tsx ts-auth-example.ts
```

Expected output:

```
LLM response: Hello James H from Subphonic! ...

Done.
```

If you see `Done.` with no errors, the LLM call succeeded and the generation was exported to Sigil.

## How it works

The example script in `ts-auth-example.ts`:

1. Loads environment variables from `.env` via `dotenv/config`
2. Creates an Azure OpenAI client and makes a real LLM call
3. Creates a Sigil client configured to export generations over HTTP to the `sigil-prod-eu-west-3.grafana.net` endpoint
4. Authenticates with Sigil using basic auth (Grafana instance ID + API token)
5. Records the generation with full input/output messages, token usage, and model metadata
6. Shuts down the client, flushing any buffered data

### Key SDK concepts

```typescript
import "dotenv/config";
import { AzureOpenAI } from "openai";
import { createSigilClient } from "@grafana/sigil-sdk-js";
import type { GenerationRecorder } from "@grafana/sigil-sdk-js";

// Set up the Azure OpenAI client
const azureClient = new AzureOpenAI({
  apiVersion: "2024-12-01-preview",
  endpoint: process.env.AIPHORIA_AZURE_OPENAI_ENDPOINT!,
  apiKey: process.env.AIPHORIA_AZURE_OPENAI_KEY!,
});

// Set up the Sigil client
const sigil = createSigilClient({
  generationExport: {
    protocol: "http",
    endpoint:
      "https://sigil-prod-eu-west-3.grafana.net/api/v1/generations:export",
    auth: {
      mode: "basic",
      tenantId: process.env.GRAFANA_INSTANCE_ID!,
      basicPassword: process.env.GLC_TOKEN!,
    },
  },
});

// Make an LLM call
const completion = await azureClient.chat.completions.create({
  model: process.env.AIPHORIA_AZURE_OPENAI_DEPLOYMENT!,
  messages: [{ role: "user", content: "your prompt" }],
});

// Record the generation in Sigil
await sigil.startGeneration(
  {
    conversationId: "my-conversation",
    agentName: "my-agent",
    agentVersion: "1.0.0",
    model: { provider: "azure_openai", name: "gpt-4.1" },
  },
  (rec: GenerationRecorder) => {
    rec.setResult({
      input: [{ role: "user", content: "your prompt" }],
      output: [{ role: "assistant", content: completion.choices[0].message.content ?? "" }],
      responseId: completion.id,
      responseModel: completion.model,
      stopReason: completion.choices[0].finish_reason ?? "",
      usage: {
        inputTokens: completion.usage?.prompt_tokens ?? 0,
        outputTokens: completion.usage?.completion_tokens ?? 0,
        totalTokens: completion.usage?.total_tokens ?? 0,
      },
    });
  },
);

await sigil.shutdown();
```

## Troubleshooting

| Error                                                                     | Cause                                        | Fix                                                    |
| ------------------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------ |
| `Top-level await is currently not supported with the "cjs" output format` | Missing `"type": "module"` in `package.json` | Add `"type": "module"` to `package.json`               |
| `HTTP Error 401: Unauthorized`                                            | Wrong credentials or tenant ID               | Verify `GLC_TOKEN` and `GRAFANA_INSTANCE_ID` in `.env` |
| `HTTP Error 405: Method Not Allowed`                                      | Endpoint URL missing the API path            | Ensure endpoint ends with `/api/v1/generations:export` |
| `Cannot find module '@grafana/sigil-sdk-js'`                              | SDK not built or not installed               | Re-run the clone/build/install steps above             |
| `ModuleNotFoundError: No module named 'dotenv'` (Python)                  | Wrong environment                            | Use `.venv/bin/python3` for the Python examples        |
