
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
import requests

load_dotenv()


SIGIL_URL = "https://subphonic.grafana.net/api/v1/generations:export"
GLC_TOKEN = os.environ.get("GLC_TOKEN")
GRAFANA_USER_ID = os.environ.get("GRAFANA_USER_ID")

generation = {  
    "trace_id": str(uuid.uuid4()),  
    "span_id": str(uuid.uuid4()),  
    "generation_id": str(uuid.uuid4()),  
    "timestamp": datetime.now(timezone.utc).isoformat(),  
    "provider": "openai",  
    "model": "gpt-4o",  
    "mode": "SYNC",  
    "status": "ok",  
    "input_tokens": 150,  
    "output_tokens": 80,  
    "latency_ms": 1200,  
    "agent_name": "my-test-agent",  
    "labels": {"env": "local", "experiment": "test-run-1"}  
}  

resp = requests.post(
    SIGIL_URL,
    json={"generations": [generation]},
    headers={"Authorization": f"Bearer {GLC_TOKEN}"},
)
print(resp.status_code)
try:
    body = resp.json()
except Exception:
    body = resp.text

print(body)

import json
with open("response.json", "w") as f:
    json.dump({"status_code": resp.status_code, "body": body}, f, indent=2)