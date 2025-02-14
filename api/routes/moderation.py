import traceback
import time

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import HTTPException
import ujson

from api.utils.checks import rate_limit, user_checks
from api.utils.provider_manager import handle_moderation
from api.utils.logging import print_status
from api.database import DatabaseManager
from api.schemas import ModerationBody

app = APIRouter()

@app.post("/v1/moderations", dependencies=[Depends(user_checks), Depends(rate_limit)])
async def embeddings(request: Request, data: ModerationBody):
    start = time.time()
    key = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await DatabaseManager.get_id(key)
    
    try:
        for _ in range(4):
            content = await handle_moderation(data)
            await print_status(True, round(time.time() - start, 2), data.model, user, content, "Moderation Completion")
            return Response(ujson.dumps(content, indent=4), status_code=200)
    except ValueError as e:
        raise HTTPException(detail={"error": {"message": str(e)}}, status_code=500)
    except:
        traceback.print_exc()
        raise HTTPException(detail={"error": {"message": "Moderation check failed within 4 retries, please try again later."}}, status_code=500)