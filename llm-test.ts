/**
 * Sigil + OTel + Azure OpenAI — TypeScript reference implementation.
 *
 * Makes multiple LLM calls in a loop so the OTel histogram counter increments
 * within a single process lifetime. This ensures Mimir's increase() can compute
 * a delta (single-call scripts export count=1 every cycle → increase(1→1) = 0).
 *
 * Two telemetry channels:
 *   1. Generation export (Sigil) → "Conversations", "Total Tokens"
 *   2. OTel metrics + traces    → "Total Requests", "Latency", "Error Rate"
 *
 * Usage:
 *   npx tsx llm-test.ts
 *   NUM_CALLS=5 npx tsx llm-test.ts
 */

import "dotenv/config";
import { AzureOpenAI } from "openai";
import { metrics } from "@opentelemetry/api";
import { Resource } from "@opentelemetry/resources";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import {
  MeterProvider,
  PeriodicExportingMetricReader,
} from "@opentelemetry/sdk-metrics";
import { OTLPMetricExporter } from "@opentelemetry/exporter-metrics-otlp-http";
import { createSigilClient } from "@grafana/sigil-sdk-js";
import type { GenerationRecorder } from "@grafana/sigil-sdk-js";

// --- OTel providers (MUST be configured BEFORE Sigil client creation) --------
const resource = new Resource({ "service.name": "sigil-tests-typescript" });

const tp = new NodeTracerProvider({ resource });
tp.addSpanProcessor(new BatchSpanProcessor(new OTLPTraceExporter()));
tp.register();

const mp = new MeterProvider({
  resource,
  readers: [
    new PeriodicExportingMetricReader({
      exporter: new OTLPMetricExporter(),
      exportIntervalMillis: 5_000,
    }),
  ],
});
metrics.setGlobalMeterProvider(mp);

// --- LLM client --------------------------------------------------------------
const llm = new AzureOpenAI({
  apiVersion: "2024-12-01-preview",
  endpoint: process.env.AIPHORIA_AZURE_OPENAI_ENDPOINT!,
  apiKey: process.env.AIPHORIA_AZURE_OPENAI_KEY!,
});
const models = ["gpt-4.1", "gpt-5.4"];

// --- Sigil client ------------------------------------------------------------
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

const AGENT_NAME = "my-test-agent";
const AGENT_VERSION = "1.0.0";
const NUM_CALLS = parseInt(process.env.NUM_CALLS ?? "6", 10);

const prompts = [
  "What are the three pillars of observability?",
  "Explain distributed tracing in one sentence.",
  "What is a histogram metric?",
  "What does SLO stand for?",
  "What is the difference between logs and traces?",
  "What is an SLI and how does it relate to an SLO?",
];

for (let i = 0; i < NUM_CALLS; i++) {
  const prompt = prompts[i % prompts.length];
  const model = models[i % models.length];
  console.log(`\n[${i + 1}/${NUM_CALLS}] [${model}] Prompt: ${prompt}`);

  // Record start time so the generation span captures actual LLM latency
  const startedAt = new Date();

  const completion = await llm.chat.completions.create({
    model,
    messages: [
      { role: "system", content: "You are a helpful assistant. Be brief." },
      { role: "user", content: prompt },
    ],
  });

  const responseText = completion.choices[0].message.content ?? "";
  const usage = completion.usage;
  console.log(`  Response: ${responseText.slice(0, 80)}...`);

  await sigil.startGeneration(
    {
      conversationId: `ts-test-${Math.floor(Math.random() * 900_000) + 100_000}`,
      agentName: AGENT_NAME,
      agentVersion: AGENT_VERSION,
      operationName: "chat",
      model: { provider: "azure.ai.openai", name: model },
      startedAt,
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

  // Space out calls so metrics export between them
  if (i < NUM_CALLS - 1) {
    await new Promise((r) => setTimeout(r, 5_000));
  }
}

// --- Shutdown ----------------------------------------------------------------
console.log("\nFlushing telemetry...");
await sigil.shutdown();
await tp.shutdown();
await mp.shutdown();
console.log("Done. Check AI Observability dashboard in ~1 min.");
