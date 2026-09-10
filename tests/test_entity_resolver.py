"""
Unit tests for deterministic entity resolution and canonicalization
"""

import pytest
from src.entity_resolution.resolver import EntityResolver
from src.entity_resolution.normalizer import EntityNormalizer


def test_normalizer():
    assert EntityNormalizer.strip_legal_suffixes("OpenAI, Inc.").lower() == "openai"
    assert EntityNormalizer.strip_legal_suffixes("Anthropic PBC").lower() == "anthropic"
    assert EntityNormalizer.strip_legal_suffixes("Cohere Technologies").lower() == "cohere"
    assert EntityNormalizer.normalize_name("Open AI").lower() == "openai"


def test_resolver_canonicalization():
    resolver = EntityResolver()

    # Exact match
    canonical, conf, method = resolver.resolve("OpenAI")
    assert canonical == "OpenAI"
    assert conf == 1.0

    # Legal suffix variation
    canonical, conf, method = resolver.resolve("OpenAI, Inc.")
    assert canonical == "OpenAI"
    assert method in ("EXACT_MATCH", "LEGAL_SUFFIX_STRIP")

    # Spacing variation
    canonical, conf, method = resolver.resolve("Open AI")
    assert canonical == "OpenAI"

    # Seed list entities
    canonical, conf, method = resolver.resolve("Anthropic, PBC")
    assert canonical == "Anthropic"

    canonical, conf, method = resolver.resolve("HuggingFace Inc.")
    assert canonical == "Hugging Face"

    canonical, conf, method = resolver.resolve("Perplexity, Inc.")
    assert canonical == "Perplexity AI"


def test_resolver_audit_log():
    resolver = EntityResolver()
    resolver.resolve("OpenAI, Inc.", source_context="YC Directory")
    resolver.resolve("Anthropic PBC", source_context="Jobicy")

    log = resolver.get_audit_log()
    assert len(log) >= 2
    assert log[0].canonical_name == "OpenAI"
    assert log[0].source_context == "YC Directory"
