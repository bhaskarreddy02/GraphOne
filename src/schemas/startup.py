"""
Canonical Schemas for GraphOne / FrontierAtlas Intelligence Graph
"""

from enum import Enum
from typing import List, Optional, Any, Dict
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str = Field(..., description="Name of the source site")
    url: str = Field(..., description="Original source URL")


class StartupContentData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees if available")
    industry: Optional[str] = Field(None, description="Industry or tags")
    description: Optional[str] = Field(None, description="Brief description of the startup")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name")
    data: StartupContentData = Field(default_factory=StartupContentData)


class StartupRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("STARTUP", description="Fixed to STARTUP")
    source: SourceMeta = Field(...)
    content: StartupContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
