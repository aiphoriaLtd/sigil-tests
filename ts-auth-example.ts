import "dotenv/config";
import { AzureOpenAI } from "openai";
import { createSigilClient } from "@grafana/sigil-sdk-js";
import type { GenerationRecorder } from "@grafana/sigil-sdk-js";

const alternativeEndpoint =
  "https://sigil-prod-eu-west-3.grafana.net/api/v1/generations:export";

const azureClient = new AzureOpenAI({
  apiVersion: "2024-12-01-preview",
  endpoint: process.env.AIPHORIA_AZURE_OPENAI_ENDPOINT!,
  apiKey: process.env.AIPHORIA_AZURE_OPENAI_KEY!,
});
const azureModel = process.env.AIPHORIA_AZURE_OPENAI_DEPLOYMENT!;

const sigil = createSigilClient({
  generationExport: {
    protocol: "http",
    endpoint: alternativeEndpoint,
    auth: {
      mode: "basic",
      tenantId: process.env.GRAFANA_INSTANCE_ID!,
      basicPassword: process.env.GLC_TOKEN!,
    },
  },
});

const prompt = "Say hello to James H from Subphonic";

// Make the real LLM call via aiphoria
const completion = await azureClient.chat.completions.create({
  model: azureModel,
  messages: [
    { role: "system", content: "You are a helpful assistant" },
    { role: "user", content: prompt },
  ],
  max_tokens: 4096,
});

const responseText = completion.choices[0].message.content ?? "";
const usage = completion.usage;

console.log(`LLM response: ${responseText}\n`);

// Record the generation in Sigil
await sigil.startGeneration(
  {
    conversationId: "real-llm-typescript",
    agentName: "my-test-agent",
    agentVersion: "1.0.0",
    model: { provider: "azure_openai", name: azureModel },
  },
  (rec: GenerationRecorder) => {
    rec.setResult({
      input: [{ role: "user", content: prompt }],
      output: [{ role: "assistant", content: responseText }],
      responseId: completion.id,
      responseModel: completion.model,
      stopReason: completion.choices[0].finish_reason ?? "",
      usage: {
        inputTokens: usage?.prompt_tokens ?? 0,
        outputTokens: usage?.completion_tokens ?? 0,
        totalTokens: usage?.total_tokens ?? 0,
      },
    });
  },
);

await sigil.shutdown();
console.log("Done.");
