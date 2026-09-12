"""
LLM Providers (Tier 1: Gemini Flash -> Tier 2: Groq Llama 3 -> Tier 3: DeepSeek -> Tier 4: Local Fallback)
"""

import json
import logging
import re
from typing import Dict, Any, Optional
import aiohttp
from src.config import GEMINI_API_KEY, GROQ_API_KEY, DEEPSEEK_API_KEY, REQUEST_TIMEOUT_SECONDS
from src.llm.backoff import BackoffHandler

logger = logging.getLogger(__name__)


class LLMProvider:
    name: str = "base"

    async def extract_schema(self, text_content: str, target_schema_desc: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class GeminiFlashProvider(LLMProvider):
    name = "Gemini Flash (Tier 1)"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY

    async def extract_schema(self, text_content: str, target_schema_desc: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.debug(f"{self.name} skipped: No API key configured.")
            return None

        # Gemini Flash endpoint (supports gemini-2.5-flash and gemini-flash-latest)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        prompt = (
            f"You are an AI data extraction engine. Extract structured data from the following text into JSON.\n"
            f"Expected JSON Schema:\n{target_schema_desc}\n\n"
            f"Text to extract:\n{text_content}\n\n"
            f"Respond ONLY with valid JSON enclosed in ```json ... ``` tags."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(3):
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            raw_out = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            return self._parse_json(raw_out)
                    elif resp.status == 429:
                        await BackoffHandler.sleep_with_jitter(attempt)
                    else:
                        logger.warning(f"[{self.name} HTTP {resp.status}]: {await resp.text()}")
                        break
        return None

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict[str, Any]]:
        try:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            clean = match.group(1) if match else text
            return json.loads(clean.strip())
        except Exception:
            return None


class GroqLlama3Provider(LLMProvider):
    name = "Groq LPU (Tier 2)"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY

    async def extract_schema(self, text_content: str, target_schema_desc: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.debug(f"{self.name} skipped: No API key configured.")
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOne/1.0"
        }
        # Supports high-speed hosted open models on Groq LPUs
        models_to_try = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"]
        for model_name in models_to_try:
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a strict data extraction engine. Output valid JSON matching schema:\n{target_schema_desc}"
                    },
                    {"role": "user", "content": text_content}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    for attempt in range(2):
                        async with session.post(url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                raw_out = data["choices"][0]["message"]["content"]
                                return json.loads(raw_out)
                            elif resp.status == 429:
                                await BackoffHandler.sleep_with_jitter(attempt)
                            else:
                                logger.warning(f"[{self.name} {model_name} HTTP {resp.status}]: {await resp.text()}")
                                break
            except Exception as e:
                logger.debug(f"Groq {model_name} error: {e}")
                continue
        return None


class DeepSeekProvider(LLMProvider):
    name = "DeepSeek (Tier 3)"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY

    async def extract_schema(self, text_content: str, target_schema_desc: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.debug(f"{self.name} skipped: No API key configured.")
            return None

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOne/1.0"
        }
        models_to_try = ["deepseek-chat", "deepseek-flash"]
        for model_name in models_to_try:
            payload = {
                "model": model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a strict data extraction engine. Output valid JSON matching schema:\n{target_schema_desc}"
                    },
                    {"role": "user", "content": text_content}
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
            try:
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    for attempt in range(2):
                        async with session.post(url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                raw_out = data["choices"][0]["message"]["content"]
                                return json.loads(raw_out)
                            elif resp.status == 429:
                                await BackoffHandler.sleep_with_jitter(attempt)
                            elif resp.status == 402:
                                logger.warning(f"[{self.name}]: HTTP 402 Insufficient Balance on DeepSeek account.")
                                return None
                            else:
                                logger.warning(f"[{self.name} HTTP {resp.status}]: {await resp.text()}")
                                break
            except Exception as e:
                logger.debug(f"DeepSeek {model_name} error: {e}")
                continue
        return None


class LocalFallbackProvider(LLMProvider):
    """
    Tier 4: Offline Deterministic Heuristic Parser
    Acts as a zero-downtime safety net if all external LLM tiers are unavailable or rate-limited.
    """
    name = "Local Deterministic Parser (Tier 4 / Safety Net)"

    async def extract_schema(self, text_content: str, target_schema_desc: str) -> Optional[Dict[str, Any]]:
        # Deterministically extract fields using regex heuristics
        result: Dict[str, Any] = {}

        # Extract entity / startup name
        name_match = re.search(r"(?:Startup|Company|Product|Name)[:\s]+([^\n,\.]+)", text_content, re.IGNORECASE)
        if name_match:
            result["entityName"] = name_match.group(1).strip()
            result["startupName"] = name_match.group(1).strip()
            result["company"] = name_match.group(1).strip()

        # Extract employee count
        emp_match = re.search(r"(\d+)\s*(?:employees|team size|people|staff)", text_content, re.IGNORECASE)
        if emp_match:
            result["employeeCount"] = int(emp_match.group(1))

        # Extract pricing model
        lower = text_content.lower()
        if "free tier" in lower or "freemium" in lower:
            result["pricingModel"] = "FREEMIUM"
        elif "enterprise" in lower:
            result["pricingModel"] = "ENTERPRISE"
        elif "paid" in lower or "pricing" in lower:
            result["pricingModel"] = "PAID"
        else:
            result["pricingModel"] = "FREE"

        return result
