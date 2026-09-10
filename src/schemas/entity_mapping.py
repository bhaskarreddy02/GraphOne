"""
Entity Mapping Log Schema (Phase IV: Deterministic Entity Resolution)
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EntityMappingLogRecord(BaseModel):
    raw_name: str = Field(..., description="Raw unstructured entity name from source")
    canonical_name: str = Field(..., description="Resolved canonical name")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of resolution")
    resolution_method: str = Field(
        ...,
        description="Method used: EXACT_MATCH, LEGAL_SUFFIX_STRIP, FUZZY_TOKEN_SET, or NEW_CANONICAL"
    )
    source_context: str = Field("", description="Source or domain where raw name appeared")
    resolved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 resolution timestamp"
    )
