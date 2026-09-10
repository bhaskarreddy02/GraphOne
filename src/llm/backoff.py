"""
Exponential Backoff with Full Jitter (Phase III: 429 Rate Limit Handling)
Calculates decorrelated jittered backoff to avoid thundering herds during rate limits.
"""

import asyncio
import logging
import random
from typing import Callable, Any

logger = logging.getLogger(__name__)


class BackoffHandler:
    @staticmethod
    def calculate_delay(attempt: int, base_seconds: float = 1.0, max_seconds: float = 30.0) -> float:
        """
        Decorrelated Full Jitter:
        t = uniform(0.5, 1.5) * min(max_seconds, base_seconds * (2 ** attempt))
        """
        exp_backoff = min(max_seconds, base_seconds * (2 ** attempt))
        delay = random.uniform(0.5, 1.5) * exp_backoff
        return max(0.1, delay)

    @classmethod
    async def sleep_with_jitter(cls, attempt: int, base_seconds: float = 1.0, max_seconds: float = 30.0):
        delay = cls.calculate_delay(attempt, base_seconds, max_seconds)
        logger.warning(f"[429 Rate Limit Backoff] Sleeping {delay:.2f}s (attempt {attempt + 1})")
        await asyncio.sleep(delay)
        return delay
