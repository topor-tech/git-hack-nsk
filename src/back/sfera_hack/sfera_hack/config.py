from pydantic import Field
from pydantic_settings import BaseSettings


class SferaConfig(BaseSettings):
    """Configuration for SFERA platform integration."""

    # SFERA API Configuration
    sfera_auth_url: str = Field(
        default="https://gateway-codemetrics.saas.sferaplatform.ru",
        description="SFERA authentication endpoint URL",
    )

    sfera_api_base_url: str = Field(
        default="https://gateway-codemetrics.saas.sferaplatform.ru/app/sourcecode/api/api/v2",
        description="SFERA API base URL",
    )

    environment: str = Field(
        default="dev", description="Application environment (dev, stage, prod)"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global configuration instance
config = SferaConfig()
