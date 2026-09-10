"""
Unit tests for strict canonical schemas
"""

import pytest
from datetime import datetime, timezone
from src.schemas import (
    StartupRecord,
    StartupContent,
    StartupContentData,
    SourceMeta,
    PricingModel,
    ProductRecord,
    ProductContent,
    ResearchPaperRecord,
    PaperContent,
    JobRecord,
    JobContent,
    NewsRecord,
    NewsContent,
    EntityMappingLogRecord,
)


def test_startup_schema():
    record = StartupRecord(
        schemaVersion="1.0",
        recordType="STARTUP",
        source=SourceMeta(name="Y Combinator", url="https://ycombinator.com/companies/openai"),
        content=StartupContent(
            entityName="OpenAI",
            data=StartupContentData(employeeCount=700, industry="AI")
        )
    )
    assert record.recordType == "STARTUP"
    assert record.content.entityName == "OpenAI"
    assert record.content.data.employeeCount == 700
    assert record.collectedAt is not None


def test_product_schema():
    record = ProductRecord(
        schemaVersion="1.0",
        recordType="PRODUCT",
        source=SourceMeta(name="Awesome AI Tools", url="https://openai.com/chatgpt"),
        content=ProductContent(
            name="ChatGPT",
            startupName="OpenAI",
            pricingModel=PricingModel.FREEMIUM
        )
    )
    assert record.recordType == "PRODUCT"
    assert record.content.pricingModel == PricingModel.FREEMIUM
    assert record.content.startupName == "OpenAI"


def test_paper_schema():
    record = ResearchPaperRecord(
        schemaVersion="1.0",
        recordType="RESEARCH_PAPER",
        content=PaperContent(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            paper_url="https://arxiv.org/abs/1706.03762",
            github_url="https://github.com/tensorflow/tensor2tensor",
            github_stars=45000,
            published_date="2017-06-12T00:00:00Z"
        )
    )
    assert record.recordType == "RESEARCH_PAPER"
    assert record.content.github_stars == 45000
    assert len(record.content.authors) == 2


def test_job_schema():
    record = JobRecord(
        schemaVersion="1.0",
        recordType="JOB",
        source=SourceMeta(name="RemoteOK", url="https://remoteok.com/remote-jobs/123"),
        content=JobContent(
            title="AI Research Engineer",
            company="Anthropic",
            date=datetime.now(timezone.utc).isoformat(),
            is_remote=True,
            role_family="AI / Machine Learning"
        )
    )
    assert record.recordType == "JOB"
    assert record.content.company == "Anthropic"
    assert record.content.is_remote is True
