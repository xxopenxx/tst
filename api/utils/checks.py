from redis_rate_limit import RateLimit, TooManyRequests
from fastapi.exceptions import HTTPException
from fastapi import Request

from api.database import DatabaseManager, ModelManager
from api.utils.redis_manager import RateLimited, check_rate_limit
from api.config import subscription_types

async def user_checks(request: Request):
    key = request.headers.get("Authorization", "").replace("Bearer ", "")
    origin = (
        request.headers.get("HTTP-Referer", "")
        or request.headers.get("Referer", "")
        or request.headers.get("Origin", "")
    )
    
    subscription_type = await DatabaseManager.get_subscription_type(key)
    premium: bool = (subscription_type in ['basic', 'premium', 'custom'])

    if key == "":
        raise HTTPException(
            detail={
                "error": {
                    "message": "You didn't provide a key.",
                    "type": "error",
                    "param": None,
                    "code": None,
                }
            },
            status_code=401,
        )

    key_check, _ = await DatabaseManager.key_check(key)

    if not key_check:
        raise HTTPException(
            detail={
                "error": {
                    "message": f"Your key is invalid.",
                    "type": "error",
                    "param": None,
                    "code": None,
                }
            },
            status_code=401,
        )

    if await DatabaseManager.ban_check(key):
        raise HTTPException(
            detail={
                "error": {
                    "message": "Your key is banned.",
                    "type": "error",
                    "param": None,
                    "code": None,
                }
            },
            status_code=403,
        )

    if "chat" in request.url.path:
        data = await request.json()
        model = data.get('model')
    elif "transcriptions" in request.url.path:
        model = "whisper"
    else:
        data = await request.json()
        model = data.get('model')
    
    await ModelManager.update_model_usage(model, await DatabaseManager.get_id(key))


    daily_usage, usage, limit, history = await DatabaseManager.get_daily_usage(key)
    if daily_usage >= limit:
        raise HTTPException(
            detail={
                "error": {
                    "message": "Daily limit exceeded, please wait for the reset.",
                    "type": "error",
                    "param": None,
                    "code": None,
                }
            },
            status_code=429,
        )

    await DatabaseManager.update_daily_usage(key, model if model is not None else None)    
    await DatabaseManager.usage_update(key, model if model is not None else None)

async def rate_limit(request: Request):
    key = request.headers.get("Authorization", "").replace("Bearer ", "")

    subscription = await DatabaseManager.get_subscription_type(key)
    key_check, _ = await DatabaseManager.key_check(key)

    if subscription == 'custom':
        user_rate_limit, _ = await DatabaseManager.get_custom_subscription_values(key)
    else:
        user_rate_limit = subscription_types[subscription]['rate_limit']

    if key_check:
        try:
            await check_rate_limit(key, user_rate_limit)
        except RateLimited as e:
            raise HTTPException(
                detail={
                    "error": {
                        "message": f"{e.error}",
                        "type": "error",
                        "param": None,
                        "code": None,
                    }
                },
                status_code=429,
            )