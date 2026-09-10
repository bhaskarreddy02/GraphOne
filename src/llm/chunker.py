"""
Intelligent Chunking & Semantic Truncation Engine (Phase III: 413 Prevention)
Preserves semantically dense content while ensuring payloads never trigger 413 Payload Too Large.
"""

import re
from typing import List
from bs4 import BeautifulSoup


class SemanticChunker:
    @staticmethod
    def clean_and_densify(raw_text: str, max_chars: int = 4000) -> str:
        """
        Cleans HTML/raw text and retains semantically dense content
        (headings, metadata, paragraphs) within the allocated token/char budget.
        """
        if not raw_text:
            return ""

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
        if len(combined) <= max_chars:
            return combined

        # Truncate at sentence or word boundary within max_chars
        truncated = combined[:max_chars]
        last_period = truncated.rfind(".")
        if last_period > max_chars * 0.7:
            return truncated[:last_period + 1]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            return truncated[:last_space] + "..."
        return truncated + "..."
