"""
Entity Normalizer (Phase IV: Deterministic Entity Resolution)
Strips legal suffixes, punctuation, and standardizes casing and whitespace.
"""

import re

# Comprehensive list of legal entity suffixes to strip
LEGAL_SUFFIXES = [
    r"\bincorporated\b",
    r"\binc\.?\b",
    r"\bcorporation\b",
    r"\bcorp\.?\b",
    r"\bllc\.?\b",
    r"\bl\.l\.c\.?\b",
    r"\bltd\.?\b",
    r"\blimited\b",
    r"\bgmbh\b",
    r"\bpte\.?\s*ltd\.?\b",
    r"\bs\.?a\.?\b",
    r"\bpbc\b",
    r"\bp\.?b\.?c\.?\b",
    r"\bco\.?\b",
    r"\bcompany\b",
    r"\btechnologies\b",
    r"\btechnology\b",
    r"\blabs\b",
    r"\bsystems\b",
    r"\bgroup\b",
    r"\bholdings\b",
]

COMPOUND_CORRECTIONS = {
    "open ai": "openai",
    "deep mind": "deepmind",
    "eleven labs": "elevenlabs",
    "runway ml": "runway",
    "hugging face": "hugging face",
    "pika labs": "pika",
    "modal labs": "modal",
    "lambda labs": "lambda labs",
    "together ai": "together ai",
    "stability ai": "stability ai",
    "perplexity ai": "perplexity ai",
    "mistral ai": "mistral ai",
}


class EntityNormalizer:
    @classmethod
    def strip_legal_suffixes(cls, name: str) -> str:
        """Removes corporate designations like Inc, LLC, Corp, Ltd."""
        cleaned = name
        for suffix_pattern in LEGAL_SUFFIXES:
            cleaned = re.sub(suffix_pattern, "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip(",. ")

    @classmethod
    def normalize_name(cls, raw_name: str) -> str:
        """
        Transforms messy strings into a standard normalized representation:
        e.g., 'OpenAI, Inc.' -> 'OpenAI', 'Open AI' -> 'OpenAI'
        """
        if not raw_name:
            return ""

        # Remove URLs or protocol prefixes if raw name was a domain
        cleaned = re.sub(r"^https?://(www\.)?", "", raw_name)
        cleaned = re.sub(r"(\.com|\.ai|\.io|\.org|\.net|\.co|\.art).*$", "", cleaned, flags=re.IGNORECASE)

        # Strip legal entity suffixes
        without_legal = cls.strip_legal_suffixes(cleaned)

        # Normalize punctuation (strip periods, commas, quotes)
        no_punct = re.sub(r"['\",._-]", " ", without_legal)
        single_spaced = re.sub(r"\s+", " ", no_punct).strip()

        # Check compound correction dictionary
        lower_spaced = single_spaced.lower()
        if lower_spaced in COMPOUND_CORRECTIONS:
            return COMPOUND_CORRECTIONS[lower_spaced]

        # Compact common spacing differences e.g. "Open AI" -> "OpenAI"
        if lower_spaced == "open ai":
            return "openai"

        return single_spaced
