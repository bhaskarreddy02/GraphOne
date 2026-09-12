"""
Unit tests for multi-tier LLM fallback, chunking, and jitter backoff
"""

import pytest
import asyncio
from src.llm.chunker import SemanticChunker
from src.llm.backoff import BackoffHandler
from src.llm.orchestrator import LLMOrchestrator


def test_chunker_prevents_413():
    # Generate 20,000 char noisy HTML
    noisy_html = (
        "<html><body><script>alert('bad');</script>"
        + "<h1>Super AI Startup</h1>"
        + "<p>This is a revolutionary deep learning company with 50 employees.</p>"
        + "<div class='nav'>Nav links here</div>"
        + ("<p>Repeated paragraph for bloat.</p>" * 500)
        + "</body></html>"
    )
    densified = SemanticChunker.clean_and_densify(noisy_html, max_chars=1000)

    # Must be stripped and strictly within limit
    assert len(densified) <= 1000
    assert "Super AI Startup" in densified
    assert "alert('bad')" not in densified
    assert "<script>" not in densified


def test_backoff_jitter_calculation():
    # Backoff with jitter should be bounded and positive
    delay0 = BackoffHandler.calculate_delay(0, base_seconds=1.0, max_seconds=30.0)
    delay3 = BackoffHandler.calculate_delay(3, base_seconds=1.0, max_seconds=30.0)
    assert 0.1 <= delay0 <= 2.0
    assert 2.0 <= delay3 <= 15.0


@pytest.mark.asyncio
async def test_orchestrator_fallback_to_heuristic():
    # When external keys are empty, orchestrator falls back to Tier 4 local parser
    orchestrator = LLMOrchestrator()
    sample_text = "Startup: Anthropic. Team size: 450 employees. Pricing: Freemium tier available."
    result, tier_name = await orchestrator.extract(
        raw_text_or_html=sample_text,
        target_schema_desc="entityName: str, employeeCount: int, pricingModel: str"
    )

    assert result is not None
    assert "Tier 4" in tier_name or "Local" in tier_name
    assert result.get("employeeCount") == 450
    assert result.get("pricingModel") == "FREEMIUM"


def test_per_model_token_budget():
    from src.llm.chunker import get_char_budget, truncate_semantically

    # Gemini Flash budget should be large (128k context -> ~496k chars)
    gemini_budget = get_char_budget("gemini-flash")
    assert gemini_budget >= 100_000

    # Groq LLaMA 3 budget should be tighter (~26k chars)
    groq_budget = get_char_budget("groq-llama3")
    assert groq_budget < 50_000

    # DeepSeek budget (~248k chars)
    deepseek_budget = get_char_budget("deepseek")
    assert deepseek_budget > groq_budget

    # Semantic truncation on sentence boundary
    sample = "Autonomous agent reasoning. " * 2000
    truncated = truncate_semantically(sample, "groq-llama3")
    assert len(truncated) <= groq_budget
    assert truncated.endswith(".")

