"""Typed configuration for the HGNC coordinate builder.

Defines Pydantic BaseSettings models for database connections and runtime
configuration. All values are loaded from environment variables surfaced
by Cloud Run and Secret Manager. No manual secret fetching.

See docs/configuration.md for the full specification.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Genew4Settings(BaseSettings):
    """PostgreSQL connection settings for the genew4 database.

    Attributes:
        host: Database host address.
        port: Database port number.
        database: Database name.
        user: Database user.
        password: Database password (ignored when use_iam_auth is True).
        use_iam_auth: Use Cloud SQL IAM authentication instead of password.
    """

    model_config = SettingsConfigDict(extra="forbid")

    host: str = Field(validation_alias="GENEW4_HOST")
    port: int = Field(default=5432, validation_alias="GENEW4_PORT")
    database: str = Field(validation_alias="GENEW4_DATABASE")
    user: str = Field(validation_alias="GENEW4_USER")
    password: str = Field(default="", validation_alias="GENEW4_PASSWORD")
    use_iam_auth: bool = Field(default=False, validation_alias="GENEW4_USE_IAM_AUTH")

    def dsn(self) -> str:
        """Build a psycopg-compatible connection string.

        Returns:
            A PostgreSQL DSN string. When use_iam_auth is True, the password
            component is omitted.
        """
        if self.use_iam_auth:
            return f"postgresql://{self.user}@{self.host}:{self.port}/{self.database}"
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


class EnsemblSettings(BaseSettings):
    """MySQL connection settings for the Ensembl database.

    Attributes:
        host: Database host address.
        port: Database port number.
        database: Database name.
        user: Database user.
        password: Database password (ignored when use_iam_auth is True).
        use_iam_auth: Use Cloud SQL IAM authentication instead of password.
    """

    model_config = SettingsConfigDict(extra="forbid")

    host: str = Field(validation_alias="ENSEMBL_HOST")
    port: int = Field(default=3306, validation_alias="ENSEMBL_PORT")
    database: str = Field(validation_alias="ENSEMBL_DATABASE")
    user: str = Field(validation_alias="ENSEMBL_USER")
    password: str = Field(default="", validation_alias="ENSEMBL_PASSWORD")
    use_iam_auth: bool = Field(default=False, validation_alias="ENSEMBL_USE_IAM_AUTH")

    def dsn(self) -> dict[str, str | int]:
        """Build a mysqlclient-compatible connection dictionary.

        Returns:
            A dictionary with host, port, user, database, and optionally password.
        """
        result: dict[str, str | int] = {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "database": self.database,
        }
        if not self.use_iam_auth and self.password:
            result["password"] = self.password
        return result


class RuntimeSettings(BaseSettings):
    """Application runtime settings.

    Attributes:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        project_id: GCP project ID.
        region: GCP region for Cloud Run deployments.
    """

    model_config = SettingsConfigDict(extra="forbid")

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    project_id: str = Field(default="", validation_alias="GCP_PROJECT_ID")
    region: str = Field(default="europe-west2", validation_alias="GCP_REGION")


class Settings(BaseSettings):
    """Top-level application settings aggregating all sub-models.

    Loads configuration from environment variables. Uses extra='forbid'
    to fail-fast on unexpected variables. EnsemblSettings is optional
    (only needed by services that connect to the Ensembl database).

    Sub-models use validation_alias to map flat env vars (e.g. GENEW4_HOST)
    to their fields. The top-level Settings delegates to each sub-model
    which independently resolves its own env vars.
    """

    model_config = SettingsConfigDict(extra="forbid")

    genew4: Genew4Settings = Field(default_factory=Genew4Settings)
    ensembl: EnsemblSettings | None = None
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
