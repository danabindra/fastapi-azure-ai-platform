"""Azure Key Vault integration using DefaultAzureCredential.

In production (USE_KEYVAULT=true) the DB password is fetched from Key Vault
at application startup.  The retrieved password is used to rewrite the
DATABASE_URL before the connection pool is created.

Locally (USE_KEYVAULT=false) this module is a no-op; credentials come from
the .env file / docker-compose environment.

Authentication chain (DefaultAzureCredential):
  - Managed Identity (ACA production)
  - Azure CLI (developer workstation)
  - Environment variables (CI)
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def resolve_database_url(settings: Settings) -> str:
    """Return the effective DATABASE_URL, substituting password from Key Vault if configured."""
    if not settings.use_keyvault:
        return settings.database_url

    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
    except ImportError as exc:
        raise RuntimeError(
            "azure-identity and azure-keyvault-secrets are required when USE_KEYVAULT=true"
        ) from exc

    logger.info("keyvault.fetch_secret", secret=settings.keyvault_db_password_secret)

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=settings.keyvault_url, credential=credential)

    secret = client.get_secret(settings.keyvault_db_password_secret)
    db_password: str = secret.value or ""

    # Replace the password placeholder in the DATABASE_URL.
    # Expected URL shape: postgresql+asyncpg://user:PASSWORD@host/db
    # or without a password: postgresql+asyncpg://user@host/db
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(settings.database_url)
    # Rebuild netloc with the retrieved password
    user = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{user}:{db_password}@{host}{port}"

    resolved = urlunparse(parsed._replace(netloc=netloc))
    logger.info("keyvault.secret_resolved", secret=settings.keyvault_db_password_secret)
    return resolved
