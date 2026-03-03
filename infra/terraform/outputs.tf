##############################################################################
# Outputs
##############################################################################

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.rg.name
}

output "acr_login_server" {
  description = "ACR login server (use for docker push)"
  value       = azurerm_container_registry.acr.login_server
}

output "container_app_fqdn" {
  description = "Public FQDN of the Container App"
  value       = azurerm_container_app.api.latest_revision_fqdn
}

output "container_app_url" {
  description = "HTTPS URL of the Container App"
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
}

output "key_vault_uri" {
  description = "Key Vault URI"
  value       = azurerm_key_vault.kv.vault_uri
}

output "application_insights_connection_string" {
  description = "Application Insights connection string"
  value       = azurerm_application_insights.appi.connection_string
  sensitive   = true
}

output "postgres_fqdn" {
  description = "PostgreSQL flexible server FQDN"
  value       = azurerm_postgresql_flexible_server.pg.fqdn
}

output "managed_identity_client_id" {
  description = "Client ID of the user-assigned Managed Identity"
  value       = azurerm_user_assigned_identity.app_identity.client_id
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID"
  value       = azurerm_log_analytics_workspace.law.id
}
