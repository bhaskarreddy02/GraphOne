"""
Product Entity Schema
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from src.schemas.startup import SourceMeta, PricingModel


class ProductContent(BaseModel):
    name: Optional[str] = Field(None, description="Product name")
    startupName: str = Field(..., description="Canonical startup/parent name")
    pricingModel: PricingModel = Field(PricingModel.FREEMIUM, description="Pricing model tier")
    description: Optional[str] = Field(None, description="Product summary")
    category: Optional[str] = Field(None, description="Product category")


class ProductRecord(BaseModel):
    schemaVersion: str = Field("1.0", description="Schema version")
    recordType: str = Field("PRODUCT", description="Fixed to PRODUCT")
    source: SourceMeta = Field(...)
    content: ProductContent = Field(...)
    collectedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 collection timestamp"
    )
