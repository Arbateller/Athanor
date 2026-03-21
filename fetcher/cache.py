import redis
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

class RedisCache:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD') or None,
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True,
        )
        self.ttl = int(os.getenv('REDIS_CACHE_TTL', 60))

    def is_connected(self):
        try:
            self.client.ping()
            return True
        except redis.ConnectionError:
            return False

    def set_stock(self, ticker, data):
        try:
            self.client.setex(f'stock:{ticker.upper()}', self.ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f'[Cache] Error storing {ticker}: {e}')
            return False

    def get_stock(self, ticker):
        try:
            raw = self.client.get(f'stock:{ticker.upper()}')
            return json.loads(raw) if raw else None
        except Exception as e:
            print(f'[Cache] Error retrieving {ticker}: {e}')
            return None

    def set_all_stocks(self, data):
        try:
            self.client.setex('stocks:all', self.ttl, json.dumps(data))
            return True
        except Exception as e:
            print(f'[Cache] Error storing all stocks: {e}')
            return False

    def get_all_stocks(self):
        try:
            raw = self.client.get('stocks:all')
            return json.loads(raw) if raw else None
        except Exception as e:
            print(f'[Cache] Error retrieving all stocks: {e}')
            return None

cache = RedisCache()
