from typing import Callable, Any, Optional, Tuple
import hashlib
import asyncio

from redis_rate_limit import RateLimit, TooManyRequests
from redis import ConnectionPool, Redis
import ujson
import yaml


with open("secrets/values.yml") as f:
    config = yaml.safe_load(f)["redis"]

redis_pool = ConnectionPool(
    host=config['host'],
    port=config['port'],
    password=config['password'],
    decode_responses=True
)
redis = Redis(connection_pool=redis_pool)


class RateLimited(Exception):
    """Custom exception for rate limiting"""
    def __init__(self, error: str):
        super().__init__(error)
        self.error: str = error

def generate_cache_key(json_data):
    return hashlib.sha256(ujson.dumps(json_data, sort_keys=True).encode()).hexdigest()

async def check_rate_limit(api_key: str, max_requests: int = 10) -> Tuple[bool, int]:
    """
    Check rate limit for an API key.

    Args:
        api_key (str): API key to check
        max_requests (int): Maximum requests allowed per minute (default: 10)
    
    Returns:
        Tuple[bool, int]: (is_allowed, seconds_to_wait)
        - is_allowed: True if within rate limit, False if exceeded
        - seconds_to_wait: Seconds until next request allowed (0 if allowed)
    """
    rate_limit = RateLimit(
        resource="rate_limit", 
        client=api_key, 
        redis_pool=redis_pool,
        max_requests=max_requests,
        expire=60
    )
    
    try:
        with rate_limit:
            return True, 0
    except TooManyRequests:
        wait_time = await asyncio.to_thread(rate_limit.get_wait_time)
        raise RateLimited(f"You have exceeded the rate limit of {max_requests} a minute, please wait {wait_time} seconds or purchase a higher plan.")
    
async def get_or_set_cache(
    cache_key: str, 
    function: Callable[..., Any], 
    *args,
    **kwargs
) -> Optional[Any]:
    """
    Retrieves a value from the Redis cache by a specified key. If the key does not 
    exist in the cache, the function will compute the value, cache it in Redis, 
    and then return the result.

    Args:
        key (str): The unique identifier for the cached value in Redis.
        function (Callable[..., Any]): The function to call if the value is not 
            in the cache. The result of this function will be cached.
        ttl (int): Time-to-live in seconds for the cached value (default is 60).
        *args: Additional positional arguments to pass to `function`.
        **kwargs: Additional keyword arguments to pass to `function`.

    Returns:
        Optional[Any]: The retrieved or computed value from the cache.

    Raises:
        CacheError: If there's an error interacting with Redis.
        ValueError: If the key is empty or None.
    """
    if not cache_key:
        raise ValueError("Cache key cannot be empty or None")
    
    cached_value = await asyncio.to_thread(redis.get, cache_key)
    
    if cached_value:
        return ujson.loads(cached_value)

    value = await function(*args, **kwargs)
    
    try:
        if value is not None:
            await asyncio.to_thread(redis.set, cache_key, ujson.dumps(value))
        
        return value
    except:
        print(value)