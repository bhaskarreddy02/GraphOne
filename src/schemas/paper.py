"""
Research Paper Entity Schema
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page")
    github_url: Optional[str] = Field(None, description="Link to the associated code repository")
    github_stars: Optional[int] = Field(0, description="Current number of stars on the GitHub repository")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    content: PaperContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
