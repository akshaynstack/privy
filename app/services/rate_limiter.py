# app/services/rate_limiter.py
import time
from aioredis import Redis
from typing import Tuple

TOKENS_LUA = """
local tokens_key = KEYS[1]
local ts_key = KEYS[2]
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local tokens = tonumber(redis.call('get', tokens_key) or capacity)
local last = tonumber(redis.call('get', ts_key) or 0)
local delta = math.max(0, now - last)
local add = delta * rate
tokens = math.min(capacity, tokens + add)
if tokens < 1 then
  redis.call('set', tokens_key, tokens)
  redis.call('set', ts_key, now)
  return 0
else
  tokens = tokens - 1
  redis.call('set', tokens_key, tokens)
  redis.call('set', ts_key, now)
  return 1
end
"""

class RateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def allow_request(self, key: str, rate: float, capacity: int) -> bool:
        """
        rate = tokens per second (float)
        capacity = max tokens
        """
        now = int(time.time())
        tokens_key = f"rl:{key}:tokens"
        ts_key = f"rl:{key}:ts"
        res = await self.redis.eval(TOKENS_LUA, keys=[tokens_key, ts_key], args=[rate, capacity, now])
        return bool(res)