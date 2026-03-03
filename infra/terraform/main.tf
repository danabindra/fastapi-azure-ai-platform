##############################################################################
# FastAPI Azure AI Governance Starter – Terraform root module
#
# Resources provisioned:
#   - Resource Group
#   - Azure Container Registry (ACR)
#   - Log Analytics Workspace
#   - Application Insights
#   - Key Vault (with RBAC)
#   - User-assigned Managed Identity
#   - Azure Database for PostgreSQL Flexible Server
#   - Container Apps Environment
#   - Container App (FastAPI service)
#   - RBAC: Managed Identity → Key Vault (Secrets User)
#   - RBAC: Managed Identity → ACR (AcrPull)
##############################################################################

terraform {
  required_version = ">= 1.7"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Uncomment and configure for remote state in Azure Blob Storage:
  # backend "azurerm" {
  #   resource_group_name  = "tfstate-rg"
  #   storage_account_name = "<storage_account>"
  #   container_name       = "tfstate"
  #   key                  = "governance-starter.tfstate"
  # }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.subscription_id
}

data "azurerm_client_config" "current" {}

##############################################################################
# Resource Group
##############################################################################

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.common_tags
}

##############################################################################
# Container Registry
##############################################################################

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.common_tags
}

##############################################################################
# Log Analytics + Application Insights
##############################################################################

resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.app_name}-law"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

resource "azurerm_application_insights" "appi" {
  name                = "${var.app_name}-appi"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
  tags                = local.common_tags
}

##############################################################################
# Key Vault
##############################################################################

resource "azurerm_key_vault" "kv" {
  name                       = var.key_vault_name
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  tags                       = local.common_tags
}

# Allow the deploying principal to manage secrets (needed to store DB_PASSWORD)
resource "azurerm_role_assignment" "kv_deployer_admin" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Store DB password as a Key Vault secret
resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_key_vault_secret" "db_password" {
  name         = "DB-PASSWORD"
  value        = random_password.db_password.result
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_deployer_admin]
}

##############################################################################
# User-assigned Managed Identity
##############################################################################

resource "azurerm_user_assigned_identity" "app_identity" {
  name                = "${var.app_name}-identity"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.common_tags
}

# Managed Identity → Key Vault: Secrets User (read secrets)
resource "azurerm_role_assignment" "kv_secrets_user" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

# Managed Identity → ACR: AcrPull
resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app_identity.principal_id
}

##############################################################################
# PostgreSQL Flexible Server
##############################################################################

resource "random_string" "pg_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_postgresql_flexible_server" "pg" {
  name                   = "${var.app_name}-pg-${random_string.pg_suffix.result}"
  resource_group_name    = azurerm_resource_group.rg.name
  location               = azurerm_resource_group.rg.location
  version                = "16"
  administrator_login    = var.db_admin_user
  administrator_password = random_password.db_password.result
  storage_mb             = 32768
  sku_name               = "B_Standard_B1ms"
  backup_retention_days  = 7
  tags                   = local.common_tags

  authentication {
    active_directory_auth_enabled = false
    password_auth_enabled         = true
  }
}

resource "azurerm_postgresql_flexible_server_database" "app_db" {
  name      = var.db_name
  server_id = azurerm_postgresql_flexible_server.pg.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

# Allow connections from Container Apps (public access, filter by ACA egress)
# For production, consider VNet integration instead.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.pg.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

##############################################################################
# Container Apps Environment
##############################################################################

resource "azurerm_container_app_environment" "env" {
  name                       = "${var.app_name}-cae"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  tags                       = local.common_tags
}

##############################################################################
# Container App
##############################################################################

resource "azurerm_container_app" "api" {
  name                         = var.app_name
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.common_tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app_identity.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.app_identity.id
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    min_replicas = 1
    max_replicas = 5

    container {
      name   = var.app_name
      image  = "${azurerm_container_registry.acr.login_server}/${var.app_name}:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "APP_ENV"
        value = "production"
      }
      env {
        name  = "USE_KEYVAULT"
        value = "true"
      }
      env {
        name  = "KEYVAULT_URL"
        value = azurerm_key_vault.kv.vault_uri
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql+asyncpg://${var.db_admin_user}@${azurerm_postgresql_flexible_server.pg.fqdn}/${var.db_name}?ssl=require"
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.appi.connection_string
      }
      env {
        name  = "AUTH_ENABLED"
        value = tostring(var.auth_enabled)
      }
      env {
        name  = "ENTRA_ISSUER"
        value = var.entra_issuer
      }
      env {
        name  = "ENTRA_AUDIENCE"
        value = var.entra_audience
      }
      env {
        name  = "OTEL_SERVICE_NAME"
        value = var.app_name
      }

      liveness_probe {
        path             = "/healthz"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 10
        period_seconds   = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        path             = "/readyz"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 5
        period_seconds   = 10
        failure_count_threshold = 3
      }
    }
  }
}
