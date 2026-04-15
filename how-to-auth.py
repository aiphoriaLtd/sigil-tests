"""
how-to-authenticate.py
======================
Demonstrates every authentication mode supported by the Sigil Python SDK.

The SDK authenticates the *exporter* (the component that ships generation
telemetry to the Sigil ingest service).  Auth is configured via
`AuthConfig` on the `GenerationExportConfig`.

╔══════════════════════════════════════════════════════════════════════════╗
║  Auth mode  │  Required fields                                         ║
╠══════════════════════════════════════════════════════════════════════════╣
║  "none"     │  (nothing — no credentials allowed at all)               ║
║  "tenant"   │  tenant_id                                               ║
║  "bearer"   │  bearer_token                                            ║
║  "basic"    │  basic_password  +  (basic_user  OR  tenant_id)          ║
╚══════════════════════════════════════════════════════════════════════════╝

Each example below creates a fully-wired `Client` ready to record
generations.  Pick the one that matches your deployment.
"""

from sigil_sdk import AuthConfig, Client, ClientConfig, GenerationExportConfig


# ---------------------------------------------------------------------------
# 1.  NO AUTH  (mode="none")
# ---------------------------------------------------------------------------
# Use this for local development or when auth is handled at the network level
# (e.g. a sidecar proxy).  No credentials of any kind are permitted — if you
# accidentally pass a tenant_id or bearer_token the SDK will raise ValueError.

client_no_auth = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="localhost:4317",              # gRPC endpoint
            auth=AuthConfig(mode="none"),           # no credentials
            insecure=True,                          # plain-text (no TLS)
        ),
    )
)
print("[1] No-auth client created ✓")


# ---------------------------------------------------------------------------
# 2.  TENANT-ONLY AUTH  (mode="tenant")
# ---------------------------------------------------------------------------
# Sends an `X-Scope-OrgID` header with every export request.
# This is the typical mode for multi-tenant Grafana Cloud deployments.
#
# Required:  tenant_id   (your Grafana Cloud / Sigil org identifier)
# Forbidden: bearer_token

client_tenant = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="sigil.example.com:443",
            auth=AuthConfig(
                mode="tenant",
                tenant_id="my-org-123",             # ← your org / tenant ID
            ),
        ),
    )
)
print("[2] Tenant-auth client created ✓")


# ---------------------------------------------------------------------------
# 3.  BEARER TOKEN AUTH  (mode="bearer")
# ---------------------------------------------------------------------------
# Sends an `Authorization: Bearer <token>` header.
# Use this when your Sigil ingest endpoint requires a token (API key, JWT, etc.)
#
# Required:  bearer_token   (the raw token — the SDK adds the "Bearer " prefix)
# Forbidden: tenant_id

client_bearer = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="sigil.example.com:443",
            auth=AuthConfig(
                mode="bearer",
                bearer_token="sk-my-secret-api-key",  # ← your API key / token
            ),
        ),
    )
)
print("[3] Bearer-token client created ✓")


# ---------------------------------------------------------------------------
# 4.  BASIC AUTH  (mode="basic")
# ---------------------------------------------------------------------------
# Sends an `Authorization: Basic <base64(user:password)>` header.
# Optionally also sends `X-Scope-OrgID` if tenant_id is provided.
#
# Required:  basic_password
# Required:  basic_user  OR  tenant_id  (tenant_id is used as the username
#            fallback when basic_user is empty)
# Optional:  tenant_id  (also sent as X-Scope-OrgID when present)

# 4a.  basic_user + basic_password
client_basic = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="sigil.example.com:443",
            auth=AuthConfig(
                mode="basic",
                basic_user="my-username",           # ← username
                basic_password="my-password",       # ← password / API key
            ),
        ),
    )
)
print("[4a] Basic-auth (user+password) client created ✓")

# 4b.  tenant_id as username + basic_password  (+ X-Scope-OrgID header)
client_basic_tenant = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="sigil.example.com:443",
            auth=AuthConfig(
                mode="basic",
                tenant_id="my-org-123",             # ← used as username AND sent as X-Scope-OrgID
                basic_password="my-password",       # ← password / API key
            ),
        ),
    )
)
print("[4b] Basic-auth (tenant+password) client created ✓")


# ---------------------------------------------------------------------------
# 5.  CUSTOM HEADERS  (any mode)
# ---------------------------------------------------------------------------
# You can also pass arbitrary headers on GenerationExportConfig.headers.
# These are sent alongside any auth-generated headers.
# If a header key collides with one that auth would set, your explicit
# header takes precedence (auth will not overwrite it).

client_custom_headers = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            endpoint="sigil.example.com:443",
            headers={
                "X-Custom-Header": "custom-value",
                "Authorization": "Bearer my-pre-formatted-token",  # overrides auth
            },
            auth=AuthConfig(mode="none"),
        ),
    )
)
print("[5] Custom-headers client created ✓")


# ---------------------------------------------------------------------------
# 6.  CHOOSING gRPC vs HTTP PROTOCOL
# ---------------------------------------------------------------------------
# The export protocol is independent of auth.  Set `protocol` on the
# GenerationExportConfig:
#   "grpc"  (default) — uses gRPC with the endpoint as host:port
#   "http"  — uses HTTP POST
#   "none"  — no-op exporter (useful for tests)

client_http = Client(
    ClientConfig(
        generation_export=GenerationExportConfig(
            protocol="http",                        # ← HTTP transport
            endpoint="https://sigil.example.com/v1/ingest",
            auth=AuthConfig(
                mode="bearer",
                bearer_token="sk-my-secret-api-key",
            ),
        ),
    )
)
print("[6] HTTP-protocol bearer client created ✓")


# ---------------------------------------------------------------------------
# Cleanup — always shut down clients to flush pending exports
# ---------------------------------------------------------------------------
for c in [
    client_no_auth,
    client_tenant,
    client_bearer,
    client_basic,
    client_basic_tenant,
    client_custom_headers,
    client_http,
]:
    c.shutdown()

print("\nAll clients shut down cleanly.")
