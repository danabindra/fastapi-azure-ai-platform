# FastAPI Azure AI Governance 

A production-grade FastAPI service demonstrating enterprise Azure patterns in a minimal, runnable codebase. Deploy locally in minutes; promote to Azure Container Apps with Terraform and GitHub Actions OIDC — no long-lived credentials required.

---
![CI](https://github.com/danabindra/fastapi-azure-ai-platform/actions/workflows/ci.yml/badge.svg)
![Deploy](https://github.com/danabindra/fastapi-azure-ai-platform/actions/workflows/deploy.yml/badge.svg)

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        GitHub Actions                          │
│   CI (lint/test) ──► Deploy (terraform + build + ACA update)  │
└─────────────────────────────┬──────────────────────────────────┘
                              │ 
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Azure                                   │
│                                                                 │
│  ACR ◄── docker push                                           │
│   │                                                             │
│   └─► Container Apps (FastAPI)                                  │
│           │  Managed Identity                                   │
│           ├─► Key Vault  (DB_PASSWORD)                   │
│           ├─► App Insights / Log Analytics (OTel traces+logs)  │
│           └─► PostgreSQL Flexible Server                        │
└─────────────────────────────────────────────────────────────────┘
```


FastAPI → Azure Container Apps  
Managed Identity → Azure Key Vault  
Postgres → Azure Database for PostgreSQL  
Observability → OpenTelemetry + Azure Monitor  
CI/CD → GitHub Actions + Terraform

### Component Responsibilities

| Component | Purpose |
|---|---|
| **FastAPI app** | REST API with clean-architecture layering |
| **Azure Key Vault** | Stores DB password; app retrieves via Managed Identity at startup |
| **Managed Identity** | Keyless auth to Key Vault and ACR — no secrets stored anywhere |
| **Application Insights** | Distributed traces, logs, and metrics via OpenTelemetry |
| **PostgreSQL Flexible** | Managed relational DB; password rotated through Key Vault |
| **Container Apps** | Serverless container runtime with built-in HTTPS and scaling |
| **Terraform** | Reproducible IaC for all Azure resources |
| **GitHub Actions** | CI/CD with OIDC — no Service Principal secrets needed |

---

## Repository Structure

```
.
├── app/
│   ├── main.py               # FastAPI app factory + lifespan
│   ├── api/
│   │   ├── health.py         # GET /healthz, /readyz, /version
│   │   └── items.py          # CRUD /items
│   ├── core/
│   │   ├── config.py         # pydantic-settings Settings
│   │   ├── logging.py        # structlog JSON + OTel context
│   │   ├── telemetry.py      # OTel SDK setup (Azure Monitor / OTLP)
│   │   ├── security.py       # Optional Entra ID JWT validation
│   │   └── middleware.py     # Correlation ID middleware
│   ├── infra/
│   │   ├── db.py             # Async SQLAlchemy engine + session
│   │   └── keyvault.py       # Key Vault secret resolution
│   ├── models/
│   │   └── item.py           # SQLAlchemy ORM model
│   └── schemas/
│       ├── common.py         # APIResponse, PaginatedResponse, ErrorResponse
│       ├── item.py           # ItemCreate, ItemRead
│       └── health.py         # HealthResponse, ReadinessResponse, VersionResponse
├── tests/
│   ├── conftest.py           # Fixtures: in-memory SQLite, AsyncClient
│   ├── unit/                 # Config + schema tests (no DB)
│   └── integration/          # Full endpoint tests against SQLite
├── migrations/               # Alembic async migrations
├── infra/terraform/          # Terraform root module
├── .github/workflows/
│   ├── ci.yml                # Lint + test on every push/PR
│   └── deploy.yml            # Terraform + build + ACA deploy on main
├── Dockerfile                # Multi-stage production image
├── docker-compose.yml        # Local dev: FastAPI + Postgres
├── Makefile                  # Developer shortcuts
├── pyproject.toml            # uv/hatch project config + ruff/mypy
└── .env.example              # Documented environment variables
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/healthz` | None | Liveness probe – always 200 |
| GET | `/readyz` | None | Readiness – checks DB + Key Vault |
| GET | `/version` | None | Git SHA, build time, environment |
| POST | `/items` | Optional* | Create item |
| GET | `/items` | Optional* | List items (paginated) |
| GET | `/items/{id}` | Optional* | Get item by ID |
| DELETE | `/items/{id}` | Optional* | Delete item |
| GET | `/docs` | None | Swagger UI |
| GET | `/redoc` | None | ReDoc |

*Auth required when `AUTH_ENABLED=true` (Bearer JWT from Entra ID).

### Response shapes

```json
// Single resource
{ "data": { "id": "...", "name": "Widget", ... }, "message": "ok" }

// List
{ "data": [...], "total": 42, "skip": 0, "limit": 20, "message": "ok" }

// Error
{ "error": { "code": "NOT_FOUND", "message": "Item not found" } }
```

---

## Local Development

### Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Python 3.12+

### Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/danabindra/fastapi-azure-ai-platform.git


# 2. Copy env file
cp .env.example .env

# 3. Start the full stack (FastAPI + Postgres)
make dev
# API available at http://localhost:8000
# Swagger UI at  http://localhost:8000/docs
```

### Running tests

```bash
# Install dev dependencies
make install

# Install the in-memory test DB driver
uv pip install aiosqlite

# Run full test suite
make test

# Unit tests only
make test-unit

# Integration tests only (requires running Postgres via docker compose)
make test-int
```

### Useful Makefile targets

```
make dev              Start docker-compose stack with hot reload
make test             Run pytest with coverage
make lint             ruff check
make format           ruff format
make typecheck        mypy
make migrate          alembic upgrade head
make migrate-create   MSG="add_column" create a new migration
make build            Build production Docker image
```

---

## Security Model

### Key Vault (production)

```
App startup
  └─ USE_KEYVAULT=true?
       └─ DefaultAzureCredential (Managed Identity in ACA)
            └─ fetch secret "DB-PASSWORD" from Key Vault
                 └─ inject into DATABASE_URL
                      └─ create SQLAlchemy engine
```

- No password ever appears in environment variables, code, or logs.
- The Managed Identity is granted **Key Vault Secrets User** (read-only) via RBAC.
- Locally, use `.env` with a plain password (never committed).

### Entra ID JWT authentication

Set `AUTH_ENABLED=true` and provide:

```bash
ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
ENTRA_AUDIENCE=api://<client-id>
```

The app fetches JWKS from the issuer's OpenID Connect discovery endpoint and validates every request to `/items` endpoints. Signing keys are cached in memory.

### Managed Identity RBAC

| Identity | Resource | Role |
|---|---|---|
| App Managed Identity | Key Vault | Key Vault Secrets User |
| App Managed Identity | ACR | AcrPull |
| GitHub Actions SP | Subscription | Contributor (Terraform) |

---

## Observability

### Logs

Structured JSON logs via **structlog**, enriched with:
- `trace_id`, `span_id` (from active OTel span)
- `correlation_id`, `request_id` (from middleware)
- `method`, `path`, `status_code`, `duration_ms`

### Traces

OpenTelemetry SDK instruments:
- **FastAPI** (every request → span)
- **SQLAlchemy** (every query → span)
- **HTTPX** (outbound calls → span)

Exported to **Azure Monitor** (Application Insights) via `APPLICATIONINSIGHTS_CONNECTION_STRING`, or to any **OTLP** endpoint via `OTEL_EXPORTER_OTLP_ENDPOINT`.

### Correlation IDs

Every response includes:
- `X-Correlation-ID` – pass from upstream or generated per-request
- `X-Request-ID` – unique per request

---

## Deployment

### 1. Prerequisites

- Azure CLI (`az`) authenticated
- Terraform >= 1.7
- GitHub repository with the following **Secrets** configured:

| Secret | Description |
|---|---|
| `AZURE_CLIENT_ID` | Service Principal / App Registration client ID (for OIDC) |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `ACR_NAME` | Container Registry name (no `.azurecr.io`) |
| `KEY_VAULT_NAME` | Key Vault name |

### 2. Configure OIDC federated credential

```bash
# Create an App Registration for GitHub Actions
az ad app create --display-name "github-actions-governance-starter"

# Add federated credential for the main branch
az ad app federated-credential create \
  --id <app-id> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<org>/<repo>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'

# Grant Contributor on subscription (needed for Terraform)
az role assignment create \
  --assignee <app-id> \
  --role Contributor \
  --scope /subscriptions/<subscription-id>
```

### 3. Provision infrastructure

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

terraform init
terraform plan
terraform apply
```

### 4. Deploy via CI/CD

Push to `main` to trigger the deploy workflow:

```
CI  ──► (lint + test pass)
Deploy:
  1. terraform apply (idempotent)
  2. docker build + push to ACR
  3. az containerapp update (new revision)
```

### 5. Run migrations in Azure

```bash
# One-off via Azure CLI (exec into a running replica)
az containerapp exec \
  --name gov-starter \
  --resource-group governance-starter-rg \
  --command "alembic upgrade head"
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `local` | `local` \| `staging` \| `production` |
| `LOG_LEVEL` | `INFO` | Python log level |
| `GIT_SHA` | `unknown` | Injected at build time |
| `DATABASE_URL` | sqlite/local | Async SQLAlchemy URL |
| `USE_KEYVAULT` | `false` | Pull DB password from Key Vault |
| `KEYVAULT_URL` | — | Required when `USE_KEYVAULT=true` |
| `AUTH_ENABLED` | `false` | Enable Entra ID JWT auth on /items |
| `ENTRA_ISSUER` | — | Required when `AUTH_ENABLED=true` |
| `ENTRA_AUDIENCE` | — | Required when `AUTH_ENABLED=true` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | — | Azure Monitor exporter |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | OTLP gRPC exporter |
| `OTEL_SERVICE_NAME` | `governance-starter` | Service name in traces |

---

## Contributing

1. Fork and create a feature branch.
2. Run `make check` and `make test` before opening a PR.
3. The CI workflow validates all PRs.

## Example API Usage

Create item

curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name":"example","description":"demo"}'


