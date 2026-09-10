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
        max_chars: int = 4000
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Executes extraction through the multi-tier fallback chain.
        1. Truncates & densifies text using SemanticChunker to prevent 413s.
        2. Tries Tier 1 (Gemini Flash).
        3. If unavailable/fails, cascades to Tier 2 (Groq Llama 3).
        4. If fails, cascades to Tier 3 (DeepSeek).
        5. If all fail, invokes Tier 4 (Local Deterministic Heuristic).

        Returns: (parsed_json, tier_name_that_succeeded)
        """
        # Step 1: Semantic Chunking to prevent HTTP 413
        dense_text = SemanticChunker.clean_and_densify(raw_text_or_html, max_chars=max_chars)
        if not dense_text:
            return None, "Empty Input"

        # Step 2: Multi-tier cascade
        for provider in self.providers:
            try:
                logger.debug(f"Attempting extraction with {provider.name}...")
                result = await provider.extract_schema(dense_text, target_schema_desc)
                if result:
                    logger.info(f"Extraction succeeded using {provider.name}")
                    return result, provider.name
            except Exception as exc:
                logger.warning(f"Provider {provider.name} error: {exc}. Falling back to next tier.")

        return None, "All Tiers Failed"
