from datetime import datetime, timedelta
from collections import defaultdict
import time

from fastapi import Response, Request, Depends, APIRouter
from fastapi.exceptions import HTTPException
import ujson

from api.database import DatabaseManager


app = APIRouter()

global request_count, last_reset
request_count = defaultdict(int)
last_reset = time.monotonic()

async def rate_limit(value):
    global request_count, last_reset

    current_time = time.monotonic()
    elapsed_time = current_time - last_reset
    
    if elapsed_time >= 60:
        request_count.clear()
        last_reset = current_time
    
    request_count[value] += 1
    
    if request_count[value] > 5:
        raise HTTPException(status_code=403, detail={"error": {"message": "Please enter a valid api key via Authorization headers.", "type": "error", "param": None, "code": None}})
    else:
        return True
    
async def anti_abuse(request: Request):
    key = request.headers.get("Authorization").replace("Bearer ", '')
    if key is None:
        raise HTTPException(status_code=403, detail={"error": {"message": "Please enter a valid api key via Authorization headers.", "type": "error", "param": None, "code": None}})
    
    elif await DatabaseManager.key_check(key) is False:
        raise HTTPException(status_code=403, detail={"error": {"message": "Please enter a valid api key via Authorization headers.", "type": "error", "param": None, "code": None}})
    
    ip = request.headers.get("CF-Connecting-IP")
    
    if ip != "" and ip is not None:
        await rate_limit(ip)

@app.get('/v1/me', dependencies=[Depends(anti_abuse)])
async def me_route(request: Request):
    data = await request.body()
    key = request.headers.get("Authorization").replace("Bearer ", '')
    
    if await DatabaseManager.id_check(key):
        pass
    else:
        if not await DatabaseManager.key_check(key):
            raise HTTPException(status_code=403, detail={"error": {"message": "Please enter a valid api key via Authorization headers.", "type": "error", "param": None, "code": None}})
    
    if data['action'] == 'usage':
        daily_usage, usage, limit, history = await DatabaseManager.get_daily_usage(key)
        
        body = {
            "usage": usage,
            "limit": limit,
            "daily_usage": daily_usage,
            "history": history,
            "reset": str((datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1) - datetime.now()))
        }
        
        return Response(status_code=200, content=ujson.dumps(indent=4, obj=body, escape_forward_slashes=False), media_type="application/json")
    elif data['action'] == "keys":
        keys = await DatabaseManager.get_id