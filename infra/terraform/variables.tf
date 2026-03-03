##############################################################################
# Input Variables
##############################################################################

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "governance-starter-rg"
}

variable "app_name" {
  description = "Short name used as a prefix/suffix for all resources. Must be lowercase and ≤ 20 chars."
  type        = string
  default     = "gov-starter"

  validation {
    condition     = can(regex("^[a-z0-9-]{1,20}$", var.app_name))
    error_message = "app_name must be lowercase alphanumeric with hyphens, max 20 chars."
  }
}

variable "acr_name" {
  description = "Azure Container Registry name (globally unique, alphanumeric, 5-50 chars)"
  type        = string
  # Example: "govstarteracr"
}

variable "key_vault_name" {
  description = "Key Vault name (globally unique, 3-24 chars, alphanumeric and hyphens)"
  type        = string
  # Example: "gov-starter-kv-prod"
}

variable "db_admin_user" {
  description = "PostgreSQL administrator login"
  type        = string
  default     = "govadmin"
}

variable "db_name" {
  description = "Name of the application database"
  type        = string
  default     = "governance"
}

variable "image_tag" {
  description = "Container image tag to deploy (usually a git SHA)"
  type        = string
  default     = "latest"
}

variable "auth_enabled" {
  description = "Enable Entra ID JWT authentication on /items endpoints"
  type        = bool
  default     = false
}

variable "entra_issuer" {
  description = "Entra ID token issuer URL. Required when auth_enabled=true."
  type        = string
  default     = ""
  # Example: "https://login.microsoftonline.com/<tenant-id>/v2.0"
}

variable "entra_audience" {
  description = "Entra ID token audience. Required when auth_enabled=true."
  type        = string
  default     = ""
  # Example: "api://<client-id>"
}

variable "tags" {
  description = "Additional tags to merge into all resources"
  type        = map(string)
  default     = {}
}
