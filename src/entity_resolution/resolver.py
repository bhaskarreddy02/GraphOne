"""
Deterministic Entity Resolution Engine (Phase IV: Deterministic Entity Resolution)
Canonicalizes entity strings using exact normalized matching and RapidFuzz scoring.
Logs every decision with schema: {raw_name, canonical_name, method, confidence}.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from rapidfuzz import fuzz
from rapidfuzz.distance import JaroWinkler

from src.entity_resolution.seed_database import SEED_CANONICAL_STARTUPS
from src.entity_resolution.normalizer import EntityNormalizer
from src.schemas.entity_mapping import EntityMappingLogRecord

logger = logging.getLogger(__name__)

# Configurable threshold for fuzzy match acceptance
FUZZY_THRESHOLD: float = 0.70


class EntityResolver:
    def __init__(self, fuzzy_threshold: float = FUZZY_THRESHOLD):
        self.fuzzy_threshold = fuzzy_threshold
        self.seed_db = SEED_CANONICAL_STARTUPS
        self.mapping_log: List[EntityMappingLogRecord] = []
        self.decision_logs: List[Dict[str, Any]] = []
        self.last_decision: Optional[Dict[str, Any]] = None

        # canonical_map: normalized_name -> Canonical Name
        self.canonical_map: Dict[str, str] = {}
        # canonical_names: List of target canonical entity names
        self.canonical_names: List[str] = []

        self._build_canonical_map()

    def _build_canonical_map(self):
        """Constructs canonical_map (normalized string -> canonical name) and canonical_names list."""
        for canonical, info in self.seed_db.items():
            norm_canonical = self.normalize(canonical)
            if norm_canonical:
                self.canonical_map[norm_canonical] = canonical
            self.canonical_map[canonical.lower().strip()] = canonical

            for alias in info.get("aliases", []):
                norm_alias = self.normalize(alias)
                if norm_alias:
                    self.canonical_map[norm_alias] = canonical
                self.canonical_map[alias.lower().strip()] = canonical

        self.canonical_names = list(dict.fromkeys(self.seed_db.keys()))

    def normalize(self, raw_name: str) -> str:
        """
        Normalizes a raw entity name:
        Strips URLs, legal suffixes (Inc, LLC, Corp, Ltd, etc.), punctuation, extra whitespace,
        and standardizes compound variants (e.g. 'open ai' -> 'openai').
        """
        if not raw_name:
            return ""
        return EntityNormalizer.normalize_name(raw_name).lower().strip()

    def fuzzy_match(self, normalized: str, canonical_names: List[str]) -> Tuple[Optional[str], float]:
        """
        Calculates similarity against known canonical entities.
        Uses RapidFuzz with combined character/token ratio and JaroWinkler similarity.
        Returns: (best_match_canonical_name, confidence_score)
        """
        if not normalized or not canonical_names:
            return None, 0.0

        best_match = None
        best_score = 0.0

        for canonical in canonical_names:
            c_norm = self.normalize(canonical)
            r = fuzz.ratio(normalized, c_norm) / 100.0
            jw = JaroWinkler.similarity(normalized, c_norm)
            score = jw if r >= 0.60 else r

            # Also check aliases of this canonical
            info = self.seed_db.get(canonical, {})
            for alias in info.get("aliases", []):
                a_norm = self.normalize(alias)
                ar = fuzz.ratio(normalized, a_norm) / 100.0
                ajw = JaroWinkler.similarity(normalized, a_norm)
                a_score = ajw if ar >= 0.60 else ar
                if a_score > score:
                    score = a_score

            if score > best_score:
                best_score = score
                best_match = canonical

        return best_match, round(best_score, 2)

    def resolve_entity(self, raw_name: str, return_details: bool = False) -> Any:
        """
        Deterministic Entity Resolution Flow:
        1. Exact: if normalized in canonical_map -> return canonical_map[normalized]
        2. Fuzzy: match, score = fuzzy_match(normalized, canonical_names)
                  if score >= FUZZY_THRESHOLD -> return match
        3. Don't guess -> return None

        And log every decision:
        {
          "raw_name": "...",
          "canonical_name": "..." | null,
          "method": "normalized_exact" | "fuzzy" | "unresolved",
          "confidence": float
        }
        """
        if not raw_name or not str(raw_name).strip():
            decision = {
                "raw_name": raw_name or "",
                "canonical_name": None,
                "method": "unresolved",
                "confidence": 0.0,
            }
            self._log_decision(decision)
            return decision if return_details else None

        clean_raw = str(raw_name).strip()
        normalized = self.normalize(clean_raw)

        # 1. Exact
        if normalized in self.canonical_map:
            canonical = self.canonical_map[normalized]
            decision = {
                "raw_name": clean_raw,
                "canonical_name": canonical,
                "method": "normalized_exact",
                "confidence": 1.0,
            }
            self._log_decision(decision)
            return decision if return_details else canonical

        # 2. Fuzzy
        match, score = self.fuzzy_match(normalized, self.canonical_names)

        if score >= self.fuzzy_threshold:
            decision = {
                "raw_name": clean_raw,
                "canonical_name": match,
                "method": "fuzzy",
                "confidence": round(float(score), 2),
            }
            self._log_decision(decision)
            return decision if return_details else match

        # 3. Don't guess
        decision = {
            "raw_name": clean_raw,
            "canonical_name": None,
            "method": "unresolved",
            "confidence": round(float(score), 2),
        }
        self._log_decision(decision)
        return decision if return_details else None

    def _log_decision(self, decision: Dict[str, Any]):
        """Logs decision to audit trail, logger, and stdout."""
        self.decision_logs.append(decision)
        self.last_decision = decision

        # Output JSON formatted decision
        decision_json = json.dumps(decision, indent=2)
        logger.info("Entity Resolution Decision:\n%s", decision_json)
        print(decision_json)

        # Backward compatibility with EntityMappingLogRecord
        record = EntityMappingLogRecord(
            raw_name=decision["raw_name"],
            canonical_name=decision["canonical_name"] or decision["raw_name"],
            confidence_score=decision["confidence"],
            resolution_method=decision["method"],
            source_context="EntityResolver",
        )
        self.mapping_log.append(record)

    def resolve(self, raw_name: str, source_context: str = "") -> Tuple[Optional[str], float, str]:
        """
        Backwards-compatible interface for pipeline runner.
        Returns: (canonical_name, confidence_score, resolution_method)
        """
        decision = self.resolve_entity(raw_name, return_details=True)
        return decision["canonical_name"], decision["confidence"], decision["method"]

    def get_audit_log(self) -> List[EntityMappingLogRecord]:
        return self.mapping_log

    def get_decision_logs(self) -> List[Dict[str, Any]]:
        return self.decision_logs

