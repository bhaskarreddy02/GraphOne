"""
Deterministic Entity Resolution Engine (Phase IV: Deterministic Entity Resolution)
Canonicalizes messy startup and product entities against seed databases and generates resolution audit logs.
"""

import difflib
import logging
from typing import Dict, List, Optional, Tuple
from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
from src.entity_resolution.normalizer import EntityNormalizer
from src.schemas.entity_mapping import EntityMappingLogRecord

logger = logging.getLogger(__name__)


class EntityResolver:
    def __init__(self):
        self.seed_db = SEED_CANONICAL_STARTUPS
        self.mapping_log: List[EntityMappingLogRecord] = []

        # Inverted index: alias_lower -> canonical_name
        self.alias_to_canonical: Dict[str, str] = {}
        # normalized_alias -> canonical_name
        self.normalized_to_canonical: Dict[str, str] = {}

        self._build_indexes()

    def _build_indexes(self):
        for canonical, info in self.seed_db.items():
            self.alias_to_canonical[canonical.lower()] = canonical
            norm_canonical = EntityNormalizer.normalize_name(canonical).lower()
            self.normalized_to_canonical[norm_canonical] = canonical

            for alias in info.get("aliases", []):
                self.alias_to_canonical[alias.lower()] = canonical
                norm_alias = EntityNormalizer.normalize_name(alias).lower()
                self.normalized_to_canonical[norm_alias] = canonical

    def resolve(self, raw_name: str, source_context: str = "") -> Tuple[str, float, str]:
        """
        Resolves a raw entity string to its canonical entity name.
        Returns: (canonical_name, confidence_score, resolution_method)
        """
        if not raw_name or not raw_name.strip():
            return "", 0.0, "EMPTY_INPUT"

        clean_raw = raw_name.strip()
        lower_raw = clean_raw.lower()

        # 1. Exact Match against Seed Canonical or Aliases (Confidence: 1.0)
        if lower_raw in self.alias_to_canonical:
            canonical = self.alias_to_canonical[lower_raw]
            method = "EXACT_MATCH"
            confidence = 1.0
            self._log(clean_raw, canonical, confidence, method, source_context)
            return canonical, confidence, method

        # 2. Normalized Match (Legal Suffix & Punctuation Stripped) (Confidence: 0.98)
        norm_name = EntityNormalizer.normalize_name(clean_raw).lower()
        if norm_name in self.normalized_to_canonical:
            canonical = self.normalized_to_canonical[norm_name]
            method = "LEGAL_SUFFIX_STRIP"
            confidence = 0.98
            self._log(clean_raw, canonical, confidence, method, source_context)
            return canonical, confidence, method

        # Also check compact version (e.g., 'openai' vs 'open ai')
        compact_name = norm_name.replace(" ", "")
        for target_norm, canonical in self.normalized_to_canonical.items():
            if target_norm.replace(" ", "") == compact_name:
                method = "LEGAL_SUFFIX_STRIP"
                confidence = 0.96
                self._log(clean_raw, canonical, confidence, method, source_context)
                return canonical, confidence, method

        # 3. Fuzzy String Similarity (Confidence: 0.88 - 0.95)
        best_match = None
        best_score = 0.0
        for target_norm, canonical in self.normalized_to_canonical.items():
            # difflib SequenceMatcher ratio
            ratio = difflib.SequenceMatcher(None, norm_name, target_norm).ratio()
            if ratio > best_score:
                best_score = ratio
                best_match = canonical

        if best_score >= 0.88 and best_match:
            method = "FUZZY_TOKEN_SET"
            confidence = round(best_score, 2)
            self._log(clean_raw, best_match, confidence, method, source_context)
            return best_match, confidence, method

        # 4. New Canonical Entity (Cleaned title-cased name)
        # Suffix-stripped and properly capitalized
        cleaned_canonical = EntityNormalizer.strip_legal_suffixes(clean_raw).strip()
        # Title case if all lower or all upper
        if cleaned_canonical.islower() or cleaned_canonical.isupper():
            cleaned_canonical = cleaned_canonical.title()

        method = "NEW_CANONICAL"
        confidence = 0.90
        self._log(clean_raw, cleaned_canonical, confidence, method, source_context)
        return cleaned_canonical, confidence, method

    def _log(self, raw: str, canonical: str, confidence: float, method: str, context: str):
        record = EntityMappingLogRecord(
            raw_name=raw,
            canonical_name=canonical,
            confidence_score=confidence,
            resolution_method=method,
            source_context=context
        )
        self.mapping_log.append(record)

    def get_audit_log(self) -> List[EntityMappingLogRecord]:
        return self.mapping_log
