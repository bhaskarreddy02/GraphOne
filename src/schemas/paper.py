"""
Research Paper Entity Schema
"""

from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/landing page")
    pdf_url: Optional[str] = Field(None, description="Direct openable link to the paper PDF")
    github_url: Optional[str] = Field(None, description="Link to the associated open-source code repository")
    github_stars: Optional[int] = Field(0, description="Current number of stars on the GitHub repository")
    huggingface_url: Optional[str] = Field(None, description="Link to the Hugging Face paper / model page")
    huggingface_upvotes: Optional[int] = Field(0, description="Community upvotes on Hugging Face")
    source_platform: Optional[str] = Field("ArXiv", description="Origin platform: Hugging Face, ArXiv, Papers with Code, GitHub")
    has_code: Optional[bool] = Field(False, description="Flag indicating if verifiable open-source code is available")
    impact_score: Optional[float] = Field(0.0, description="Weighted impact score (stars + upvotes)")
    rank: Optional[int] = Field(None, description="Overall ranking based on impact and community engagement")
    published_date: str = Field(..., description="ISO-8601 publication date")


class ResearchPaperRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    content: PaperContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
