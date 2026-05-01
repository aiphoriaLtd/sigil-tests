import json
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
    ToolCall,
    ToolDefinition,
    ToolExecutionEnd,
    ToolExecutionStart,
    TokenUsage,
    assistant_text_message,
    tool_call_part,
    tool_result_message,
    user_text_message,
    Message,
    MessageRole,
    Part,
    PartKind,
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

# Define a simple tool for the model to call
get_weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a given city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"},
            },
            "required": ["city"],
        },
    },
}

# Sigil tool definition for tracing
sigil_tool_def = ToolDefinition(
    name="get_weather",
    description="Get the current weather for a given city",
    type="function",
    input_schema_json=json.dumps(get_weather_tool["function"]["parameters"]).encode(),
)

prompt = "What's the weather like in Dublin right now?"
messages = [
    {"role": "system", "content": "You are a helpful assistant. Use the get_weather tool when asked about weather."},
    {"role": "user", "content": prompt},
]

# Step 1: Initial LLM call — model should request a tool call
print("Step 1: Sending prompt to LLM...")
completion1 = azure_client.chat.completions.create(
    model=azure_model,
    messages=messages,
    tools=[get_weather_tool],
    max_tokens=4096,
)

choice1 = completion1.choices[0]
print(f"  Finish reason: {choice1.finish_reason}")

assert choice1.finish_reason == "tool_calls", f"Expected tool_calls, got {choice1.finish_reason}"
tool_call_resp = choice1.message.tool_calls[0]
tool_call_id = tool_call_resp.id
tool_call_args = json.loads(tool_call_resp.function.arguments)
print(f"  Tool call: {tool_call_resp.function.name}({tool_call_args})")

# Step 2: Execute the tool (simulated)
print("\nStep 2: Executing tool...")
tool_result = json.dumps({"city": tool_call_args.get("city", "Dublin"), "temperature": "14°C", "condition": "Overcast with light rain"})
print(f"  Tool result: {tool_result}")

# Record tool execution in Sigil
with sigil.start_tool_execution(
    ToolExecutionStart(
        tool_name="get_weather",
        tool_call_id=tool_call_id,
        tool_type="function",
        tool_description="Get the current weather for a given city",
        conversation_id="tool-call-test",
        agent_name="my-test-agent",
        agent_version="1.0.0",
        request_model=azure_model,
        request_provider="azure_openai",
        include_content=True,
    )
) as tool_rec:
    tool_rec.set_result(ToolExecutionEnd(
        arguments=tool_call_args,
        result=tool_result,
    ))

# Step 3: Send tool result back to the model for a final response
messages.append(choice1.message.to_dict())
messages.append({
    "role": "tool",
    "tool_call_id": tool_call_id,
    "content": tool_result,
})

print("\nStep 3: Sending tool result back to LLM...")
completion2 = azure_client.chat.completions.create(
    model=azure_model,
    messages=messages,
    tools=[get_weather_tool],
    max_tokens=4096,
)

response_text = completion2.choices[0].message.content
usage1 = completion1.usage
usage2 = completion2.usage
print(f"  LLM response: {response_text}\n")

# Record the full generation in Sigil (both LLM calls + tool call in the message history)
with sigil.start_generation(
    GenerationStart(
        conversation_id="tool-call-test",
        agent_name="my-test-agent",
        agent_version="1.0.0",
        model=ModelRef(provider="azure_openai", name=azure_model),
        tools=[sigil_tool_def],
    )
) as rec:
    rec.set_result(
        input=[user_text_message(prompt)],
        output=[
            # Assistant message with tool call
            Message(
                role=MessageRole.ASSISTANT,
                parts=[tool_call_part(ToolCall(
                    name=tool_call_resp.function.name,
                    id=tool_call_id,
                    input_json=tool_call_resp.function.arguments.encode(),
                ))],
            ),
            # Tool result message
            tool_result_message(tool_call_id, tool_result),
            # Final assistant response
            assistant_text_message(response_text),
        ],
        response_id=completion2.id,
        response_model=completion2.model,
        stop_reason=completion2.choices[0].finish_reason or "",
        usage=TokenUsage(
            input_tokens=(usage1.prompt_tokens if usage1 else 0) + (usage2.prompt_tokens if usage2 else 0),
            output_tokens=(usage1.completion_tokens if usage1 else 0) + (usage2.completion_tokens if usage2 else 0),
            total_tokens=(usage1.total_tokens if usage1 else 0) + (usage2.total_tokens if usage2 else 0),
        ),
    )
    if rec.err() is not None:
        print("SDK error:", rec.err())

sigil.shutdown()
print("Done.")
