from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, field_validator
import json

class GatewaySettings(BaseModel):
    name: str
    json_response: bool
    backend_servers: dict[str, str]

    @field_validator("backend_servers", mode="before")
    @classmethod
    def parse_backend_servers(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError as e:
                raise ValueError(
                    "backend_servers must be valid JSON string"
                ) from e
        return v
    
class ModelSettings(BaseModel):
    name: str
    base_url: str
    api_key: str

class AgentSettings(BaseModel):
    name: str
    model: ModelSettings

class AppSettings(BaseModel):
    name: str
    host: str
    port: int

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="__")
    gateway: GatewaySettings
    agent: AgentSettings
    app: AppSettings

_config_instance = None


def get_config():
    """
    Returns the singleton instance of the Settings class.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Settings()  # type: ignore
    return _config_instance


if __name__ == "__main__":
    settings = get_config()
    print(settings.model_dump())