from typing import List
from pydantic import BaseModel, Field


class Yacht(BaseModel):
    id: int
    name: str
    build_year: int


class Tender(BaseModel):
    id: int
    yacht_id: int
    name: str


class YachtAlias(BaseModel):
    yacht_id: int
    alias: str


class YachtEvent(BaseModel):
    yacht_id: int
    event: str
    date: str


class Source(BaseModel):
    url: str
    domain: str


class ExtractionBundle(BaseModel):
    yachts: List[Yacht] = Field(default_factory=list)
    tenders: List[Tender] = Field(default_factory=list)
    aliases: List[YachtAlias] = Field(default_factory=list)
    events: List[YachtEvent] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
