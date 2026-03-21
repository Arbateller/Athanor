"""
cache.py - Redis Cache Manager
Handles all Redis operations for storing/retrieving stock data
"""

import redis
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("config/.env.example")


class RedisCache:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD") or None,
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True,
        )
        self.ttl = int(os.getenv("REDIS_CACHE_TTL", 60))

    def is_connected(self) -> bool:
        """Check if Redis connection is alive."""
        try:
            self.client.ping()
            return True
        except redis.ConnectionError:
            return False

    def set_stock(self, ticker: str, data: dict) -> bool:
        """Store stock data in Redis with TTL."""
        try:
            key = f"stock:{ticker.upper()}"
            self.client.setex(key, self.ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f"[Cache] Error storing {ticker}: {e}")
            return False

    def get_stock(self, ticker: str) -> dict | None:
        """Retrieve stock data from Redis."""
        try:
            key = f"stock:{ticker.upper()}"
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            print(f"[Cache] Error retrieving {ticker}: {e}")
            return None

    def set_all_stocks(self, data: dict) -> bool:
        """Store all stocks snapshot."""
        try:
            self.client.setex("stocks:all", self.ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f"[Cache] Error storing all stocks: {e}")
            return False

    def get_all_stocks(self) -> dict | None:
        """Retrieve all stocks snapshot."""
        try:
            raw = self.client.get("stocks:all")
            return json.loads(raw) if raw else None
        except Exception as e:
            print(f"[Cache] Error retrieving all stocks: {e}")
            return None

    def get_ttl(self, ticker: str) -> int:
        """Get remaining TTL for a stock key."""
        return self.client.ttl(f"stock:{ticker.upper()}")


# Singleton instance
cache = RedisCache()
