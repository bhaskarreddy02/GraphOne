"""
News Entity Schema (Phase II: High-Fidelity Signal Ingestion)
"""

from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from src.schemas.startup import SourceMeta


class NewsContent(BaseModel):
    title: str = Field(..., description="Headline of the article")
    published_date: str = Field(..., description="ISO-8601 publication date (<24h fresh)")
    summary: Optional[str] = Field(None, description="Article summary / full text excerpt")
    author: Optional[str] = Field(None, description="Author name")
    category: Optional[str] = Field("Artificial Intelligence", description="Topic category")
    url: str = Field(..., description="Direct link to original article")


class NewsRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("NEWS", description="Fixed to NEWS")
    source: SourceMeta = Field(...)
    content: NewsContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
