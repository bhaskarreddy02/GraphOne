"""
Job Entity Schema
"""

from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from src.schemas.startup import SourceMeta


class JobContent(BaseModel):
    title: Optional[str] = Field(None, description="Job title")
    company: str = Field(..., description="Canonical company name")
    date: str = Field(..., description="ISO-8601 publication date")
    is_remote: bool = Field(True, description="Remote eligibility")
    role_family: str = Field("Engineering", description="Functional category (e.g., 'Engineering')")
    location: Optional[str] = Field(None, description="Location if available")
    job_url: Optional[str] = Field(None, description="Direct URL to job posting")


class JobRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("JOB", description="Fixed to JOB")
    source: SourceMeta = Field(...)
    content: JobContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
