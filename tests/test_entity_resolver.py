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
    assert method == "normalized_exact"

    # Legal suffix variation
    canonical, conf, method = resolver.resolve("OpenAI, Inc.")
    assert canonical == "OpenAI"
    assert method == "normalized_exact"

    # Spacing variation
    canonical, conf, method = resolver.resolve("Open AI")
    assert canonical == "OpenAI"
    assert method == "normalized_exact"

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

    decisions = resolver.get_decision_logs()
    assert len(decisions) >= 2
    assert decisions[0]["raw_name"] == "OpenAI, Inc."
    assert decisions[0]["canonical_name"] == "OpenAI"
    assert decisions[0]["method"] == "normalized_exact"
    assert decisions[0]["confidence"] == 1.0


def test_resolver_exact_user_spec():
    """
    Tests the 3 exact user specified test cases:
    1. 'Open AI, Inc.' -> 'OpenAI', 'normalized_exact', 1.0
    2. 'dopemind' -> 'DeepMind', 'fuzzy', ~0.89
    3. 'Something Random' -> None, 'unresolved', ~0.31
    """
    resolver = EntityResolver()

    # 1. Exact
    res1 = resolver.resolve_entity("Open AI, Inc.")
    dec1 = resolver.last_decision
    assert res1 == "OpenAI"
    assert dec1 == {
        "raw_name": "Open AI, Inc.",
        "canonical_name": "OpenAI",
        "method": "normalized_exact",
        "confidence": 1.0
    }

    # 2. Fuzzy
    res2 = resolver.resolve_entity("dopemind")
    dec2 = resolver.last_decision
    assert res2 == "DeepMind"
    assert dec2["raw_name"] == "dopemind"
    assert dec2["canonical_name"] == "DeepMind"
    assert dec2["method"] == "fuzzy"
    assert dec2["confidence"] >= 0.70

    # 3. Don't guess -> unresolved
    res3 = resolver.resolve_entity("Something Random")
    dec3 = resolver.last_decision
    assert res3 is None
    assert dec3["raw_name"] == "Something Random"
    assert dec3["canonical_name"] is None
    assert dec3["method"] == "unresolved"
    assert dec3["confidence"] < 0.70

