"""
LLM Orchestrator (Phase III: Fallback Chain & Execution Engine)
Coordinates multi-tier LLM fallback, chunking, and rate-limit recovery.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from src.llm.chunker import SemanticChunker
from src.llm.providers import (
    LLMProvider,
    GeminiFlashProvider,
    GroqLlama3Provider,
    DeepSeekProvider,
    LocalFallbackProvider
)

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    def __init__(self, providers: Optional[List[LLMProvider]] = None):
        if providers:
            self.providers = providers
        else:
            self.providers = [
                GeminiFlashProvider(),
                GroqLlama3Provider(),
                DeepSeekProvider(),
                LocalFallbackProvider(),
            ]

    async def extract(
        self,
        raw_text_or_html: str,
        target_schema_desc: str,
        max_chars: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Executes extraction through the multi-tier fallback chain.
        1. Dynamically truncates & densifies text per model in the fallback chain
           based on real context limits and reserved prompt/output headroom.
        2. Tries Tier 1 (Gemini Flash).
        3. If unavailable/fails, cascades to Tier 2 (Groq Llama 3).
        4. If fails, cascades to Tier 3 (DeepSeek).
        5. If all fail, invokes Tier 4 (Local Deterministic Heuristic).

        Returns: (parsed_json, tier_name_that_succeeded)
        """
        if not raw_text_or_html:
            return None, "Empty Input"

        # Multi-tier cascade with per-model dynamic token budgeting
        for provider in self.providers:
            try:
                dense_text = SemanticChunker.clean_and_densify(
                    raw_text_or_html,
                    max_chars=max_chars,
                    model_key=provider.name
                )
                if not dense_text:
                    continue

                logger.debug(f"Attempting extraction with {provider.name} (budget chars={len(dense_text)})...")
                result = await provider.extract_schema(dense_text, target_schema_desc)
                if result:
                    logger.info(f"Extraction succeeded using {provider.name}")
                    return result, provider.name
            except Exception as exc:
                logger.warning(f"Provider {provider.name} error: {exc}. Falling back to next tier.")

        return None, "All Tiers Failed"

    async def extract_with_escalation(
        self,
        raw_text_or_html: str,
        item_type: str = "NEWS",
        is_ambiguous: bool = False,
        max_chars: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Multi-tier LLM extraction with per-model context budgeting:
        - Standard (Tier 1): Cheap/fast model extracts structured entities (title, company, role, summary).
        - Escalated (Tier 2): If is_ambiguous=True (date heuristic used, short text, or missing fields),
          escalates directly to a stronger reasoning model (Groq LLaMA 3 70B / DeepSeek) to infer missing metadata.
        """
        if not raw_text_or_html:
            return None, "Empty Input"

        if item_type.upper() == "JOB":
            schema_desc = (
                "Extract job details as JSON: {title: str, company: str, role_family: str, location: str, "
                "is_remote: bool, salary_estimate: str, summary: str}. Infer company or role if ambiguous."
            )
        else:
            schema_desc = (
                "Extract news details as JSON: {title: str, company_or_entity: str, category: str, "
                "summary: str, key_takeaways: list[str]}. Infer entity context if ambiguous."
            )

        if is_ambiguous:
            logger.info("[LLM Escalation] Item flagged as AMBIGUOUS (heuristic date or malformed content). Escalating to Tier 2+ strong models.")
            # Skip Tier 1 (Flash) and start directly from Tier 2 (Groq LLaMA 3 / DeepSeek)
            escalated_providers = self.providers[1:] if len(self.providers) > 1 else self.providers
            for provider in escalated_providers:
                try:
                    dense_text = SemanticChunker.clean_and_densify(
                        raw_text_or_html,
                        max_chars=max_chars,
                        model_key=provider.name
                    )
                    if not dense_text:
                        continue
                    res = await provider.extract_schema(dense_text, f"[ESCALATED RESOLUTION] {schema_desc}")
                    if res:
                        return res, f"Escalated Tier ({provider.name})"
                except Exception as exc:
                    logger.warning(f"Escalated provider {provider.name} failed: {exc}")

        # Standard execution or fallback
        return await self.extract(raw_text_or_html, schema_desc, max_chars=max_chars)


