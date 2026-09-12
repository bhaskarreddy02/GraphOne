"""
Intelligent Chunking & Semantic Truncation Engine (Phase III: 413 Prevention)
Preserves semantically dense content while dynamically computing input character budgets
based on each model's real context window and instruction headroom.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict
from bs4 import BeautifulSoup

# Standard rule-of-thumb for English text tokenizers (GPT, LLaMA, DeepSeek)
CHARS_PER_TOKEN = 4


@dataclass
class ModelBudget:
    name: str
    context_window_tokens: int
    reserved_for_prompt_and_output_tokens: int  # system prompt + expected completion

    @property
    def usable_input_tokens(self) -> int:
        return max(self.context_window_tokens - self.reserved_for_prompt_and_output_tokens, 0)

    @property
    def usable_input_chars(self) -> int:
        return self.usable_input_tokens * CHARS_PER_TOKEN


# Configured per model in the fallback chain:
# - Gemini 1.5/2.0 Flash: 1M token context (conservatively capped to 128k input tokens for performance)
# - Groq LLaMA 3.3 70B: 8,192 input budget or 128k context
# - DeepSeek: 64,000 tokens
MODEL_BUDGETS: Dict[str, ModelBudget] = {
    "gemini-flash": ModelBudget("gemini-flash", 128_000, 4_000),
    "groq-llama3":  ModelBudget("groq-llama3",   8_192, 1_500),
    "deepseek":     ModelBudget("deepseek",      64_000, 2_000),
}

DEFAULT_BUDGET = ModelBudget("default-fallback", 8_192, 1_500)


def get_char_budget(model_key: str) -> int:
    """Returns the safe input-char budget for a given model key or provider name."""
    clean_key = model_key.lower()
    for key, budget in MODEL_BUDGETS.items():
        if key in clean_key:
            return budget.usable_input_chars
    return DEFAULT_BUDGET.usable_input_chars


class SemanticChunker:
    @staticmethod
    def clean_and_densify(raw_text: str, max_chars: Optional[int] = None, model_key: Optional[str] = None) -> str:
        """
        Cleans HTML/raw text and retains semantically dense content
        (headings, metadata, paragraphs) within the allocated token/char budget.
        Computes dynamic per-model budget if model_key is supplied.
        """
        if not raw_text:
            return ""

        # Compute dynamic budget if model_key provided, else fallback to max_chars or default
        if model_key:
            limit = get_char_budget(model_key)
        elif max_chars is not None:
            limit = max_chars
        else:
            limit = DEFAULT_BUDGET.usable_input_chars

        # If raw_text is HTML, parse with BeautifulSoup to extract structured elements
        if "<" in raw_text and ">" in raw_text:
            soup = BeautifulSoup(raw_text, "html.parser")
            for noisy in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
                noisy.decompose()

            # Prioritize title, meta descriptions, headings, tables, and strong paragraphs
            dense_parts: List[str] = []
            if soup.title and soup.title.string:
                dense_parts.append(f"Title: {soup.title.string.strip()}")

            for meta in soup.find_all("meta"):
                name = meta.get("name", "").lower() or meta.get("property", "").lower()
                content = meta.get("content", "").strip()
                if name in ("description", "og:description", "article:published_time", "author") and content:
                    dense_parts.append(f"{name}: {content}")

            # Headings
            for h in soup.find_all(["h1", "h2", "h3"]):
                text = h.get_text(strip=True)
                if text:
                    dense_parts.append(f"Heading: {text}")

            # Paragraphs and list items
            for p in soup.find_all(["p", "li"]):
                text = p.get_text(strip=True)
                if len(text) > 25:
                    dense_parts.append(text)

            combined = "\n".join(dense_parts)
            if len(combined) < 100:  # Fallback to general text if markup was sparse
                combined = soup.get_text(separator=" ", strip=True)
        else:
            combined = raw_text

        # Normalize whitespace
        combined = re.sub(r"\s+", " ", combined).strip()

        # Enforce strict budget to prevent HTTP 413
        if len(combined) <= limit:
            return combined

        # Truncate at sentence or word boundary within limit
        truncated = combined[:limit]
        last_period = truncated.rfind(". ")
        if last_period > limit * 0.7:
            return truncated[:last_period + 1]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space] + "..."
        return truncated + "..."

    @classmethod
    def truncate_semantically(cls, text: str, model_key: str) -> str:
        """Convenience method matching drop-in replacement signature."""
        return cls.clean_and_densify(text, model_key=model_key)


def truncate_semantically(text: str, model_key: str) -> str:
    """Module-level function matching drop-in replacement signature."""
    return SemanticChunker.clean_and_densify(text, model_key=model_key)


