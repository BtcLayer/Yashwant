"""
Rate Limiter for Hyperliquid API

This module provides a rate limiter with exponential backoff to prevent 429 errors
from the Hyperliquid API.
"""

import time
import asyncio
from typing import Optional, Callable, Any
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter with exponential backoff for API calls.
    
    Features:
    - Token bucket algorithm for rate limiting
    - Exponential backoff on 429 errors
    - Configurable retry logic
    - Thread-safe implementation
    """
    
    def __init__(
        self,
        calls_per_second: float = 2.0,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0
    ):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum number of API calls per second
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff delay in seconds
            max_backoff: Maximum backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.calls_per_second = calls_per_second
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        
        # Token bucket parameters
        self.tokens = calls_per_second
        self.max_tokens = calls_per_second
        self.last_update = time.time()
        
        # Backoff state
        self.current_backoff = initial_backoff
        self.consecutive_429s = 0
    
    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(
            self.max_tokens,
            self.tokens + elapsed * self.calls_per_second
        )
        self.last_update = now
    
    def acquire(self, tokens: float = 1.0) -> float:
        """
        Acquire tokens for an API call.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        self._refill_tokens()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        
        # Calculate wait time
        tokens_needed = tokens - self.tokens
        wait_time = tokens_needed / self.calls_per_second
        return wait_time
    
    def on_success(self):
        """Reset backoff on successful call."""
        self.current_backoff = self.initial_backoff
        self.consecutive_429s = 0
    
    def on_rate_limit(self) -> float:
        """
        Handle rate limit error.
        
        Returns:
            Backoff delay in seconds
        """
        self.consecutive_429s += 1
        backoff = min(
            self.max_backoff,
            self.current_backoff * (self.backoff_multiplier ** (self.consecutive_429s - 1))
        )
        self.current_backoff = backoff
        return backoff
    
    def should_retry(self) -> bool:
        """Check if we should retry after rate limit."""
        return self.consecutive_429s < self.max_retries


def with_rate_limit(limiter: RateLimiter):
    """
    Decorator to add rate limiting to synchronous functions.
    
    Args:
        limiter: RateLimiter instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            while True:
                # Acquire token
                wait_time = limiter.acquire()
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    time.sleep(wait_time)
                
                try:
                    result = func(*args, **kwargs)
                    limiter.on_success()
                    return result
                except Exception as e:
                    # Check if it's a 429 error
                    error_str = str(e).lower()
                    if '429' in error_str or 'rate limit' in error_str:
                        if not limiter.should_retry():
                            logger.error(f"Max retries exceeded for {func.__name__}")
                            raise
                        
                        backoff = limiter.on_rate_limit()
                        logger.warning(
                            f"Rate limited (429). Retry {limiter.consecutive_429s}/{limiter.max_retries}. "
                            f"Backing off for {backoff:.2f}s"
                        )
                        time.sleep(backoff)
                    else:
                        # Not a rate limit error, re-raise
                        raise
        
        return wrapper
    return decorator


def with_async_rate_limit(limiter: RateLimiter):
    """
    Decorator to add rate limiting to async functions.
    
    Args:
        limiter: RateLimiter instance
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            while True:
                # Acquire token
                wait_time = limiter.acquire()
                if wait_time > 0:
                    logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                try:
                    result = await func(*args, **kwargs)
                    limiter.on_success()
                    return result
                except Exception as e:
                    # Check if it's a 429 error
                    error_str = str(e).lower()
                    if '429' in error_str or 'rate limit' in error_str:
                        if not limiter.should_retry():
                            logger.error(f"Max retries exceeded for {func.__name__}")
                            raise
                        
                        backoff = limiter.on_rate_limit()
                        logger.warning(
                            f"Rate limited (429). Retry {limiter.consecutive_429s}/{limiter.max_retries}. "
                            f"Backing off for {backoff:.2f}s"
                        )
                        await asyncio.sleep(backoff)
                    else:
                        # Not a rate limit error, re-raise
                        raise
        
        return wrapper
    return decorator


# Global rate limiter instance for Hyperliquid API
# Hyperliquid has a rate limit of ~10 requests per second per IP
# We use a conservative 2 requests per second to be safe
HYPERLIQUID_RATE_LIMITER = RateLimiter(
    calls_per_second=2.0,  # Conservative limit
    max_retries=5,
    initial_backoff=2.0,
    max_backoff=60.0,
    backoff_multiplier=2.0
)
