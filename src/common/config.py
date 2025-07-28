from pathlib import Path
from typing import List

import yaml
from pydantic import BaseModel, Field

CONFIG_PATH = Path("configs/settings.yml")


class SearchConfig(BaseModel):
    queries: List[str] = Field(default_factory=list)
    result_count: int = 5
    domain_whitelist: List[str] = Field(default_factory=list)
    domain_blacklist: List[str] = Field(default_factory=list)


class Settings(BaseModel):
    search: SearchConfig = Field(default_factory=SearchConfig)

    class Config:
        extra = "allow"


def load_settings(path: Path = CONFIG_PATH) -> Settings:
    data = yaml.safe_load(path.read_text())
    return Settings(**data)
