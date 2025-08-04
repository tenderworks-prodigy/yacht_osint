from pathlib import Path

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path("configs/settings.yml")


class SearchConfig(BaseModel):
    queries: list[str] = Field(default_factory=list)
    result_count: int = 5
    domain_whitelist: list[str] = Field(default_factory=list)
    domain_blacklist: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    search: SearchConfig = Field(default_factory=SearchConfig)

    class Config:
        extra = "allow"


def load_settings(path: Path = CONFIG_PATH) -> Settings:
    data = yaml.safe_load(path.read_text())
    return Settings(**data)
