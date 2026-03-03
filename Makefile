.DEFAULT_GOAL := help
SHELL := /bin/bash

APP_IMAGE ?= fastapi-governance-starter
APP_VERSION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "dev")

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Local Dev ──────────────────────────────────────────────────────────────────

.PHONY: install
install:  ## Install all dependencies via uv
	uv sync --extra dev

.PHONY: dev
dev:  ## Start local stack (FastAPI + Postgres) via docker-compose
	docker compose up --build

.PHONY: dev-detach
dev-detach:  ## Start local stack in background
	docker compose up --build -d

.PHONY: down
down:  ## Stop local stack
	docker compose down -v

.PHONY: run
run:  ## Run FastAPI locally without Docker (requires local Postgres)
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Code Quality ───────────────────────────────────────────────────────────────

.PHONY: lint
lint:  ## Run ruff linter
	uv run ruff check app tests

.PHONY: format
format:  ## Run ruff formatter
	uv run ruff format app tests

.PHONY: typecheck
typecheck:  ## Run mypy type checker
	uv run mypy app

.PHONY: check
check: lint typecheck  ## Run all static checks

# ── Tests ──────────────────────────────────────────────────────────────────────

.PHONY: test
test:  ## Run test suite with coverage
	uv run pytest

.PHONY: test-unit
test-unit:  ## Run unit tests only (no DB)
	uv run pytest tests/unit -v

.PHONY: test-int
test-int:  ## Run integration tests (requires running Postgres)
	uv run pytest tests/integration -v

# ── Database ───────────────────────────────────────────────────────────────────

.PHONY: migrate
migrate:  ## Run Alembic migrations (upgrade head)
	uv run alembic upgrade head

.PHONY: migrate-create
migrate-create:  ## Create a new Alembic migration (MSG=<name>)
	uv run alembic revision --autogenerate -m "$(MSG)"

.PHONY: migrate-downgrade
migrate-downgrade:  ## Downgrade one migration step
	uv run alembic downgrade -1

# ── Docker ─────────────────────────────────────────────────────────────────────

.PHONY: build
build:  ## Build the production Docker image
	docker build --build-arg GIT_SHA=$(APP_VERSION) -t $(APP_IMAGE):$(APP_VERSION) -t $(APP_IMAGE):latest .

.PHONY: push
push:  ## Push image to ACR (ACR_LOGIN_SERVER must be set)
	docker tag $(APP_IMAGE):$(APP_VERSION) $(ACR_LOGIN_SERVER)/$(APP_IMAGE):$(APP_VERSION)
	docker push $(ACR_LOGIN_SERVER)/$(APP_IMAGE):$(APP_VERSION)

# ── Terraform ─────────────────────────────────────────────────────────────────

.PHONY: tf-init
tf-init:  ## Terraform init
	cd infra/terraform && terraform init

.PHONY: tf-plan
tf-plan:  ## Terraform plan (TF_VAR_* must be set)
	cd infra/terraform && terraform plan

.PHONY: tf-apply
tf-apply:  ## Terraform apply (auto-approve)
	cd infra/terraform && terraform apply -auto-approve

.PHONY: tf-destroy
tf-destroy:  ## Terraform destroy (auto-approve)
	cd infra/terraform && terraform destroy -auto-approve

# ── Pre-commit ────────────────────────────────────────────────────────────────

.PHONY: pre-commit-install
pre-commit-install:  ## Install pre-commit hooks
	uv run pre-commit install

.PHONY: pre-commit-run
pre-commit-run:  ## Run pre-commit on all files
	uv run pre-commit run --all-files
