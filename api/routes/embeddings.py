import traceback
import time

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import HTTPException
import ujson

from api.utils.checks import rate_limit, user_checks
from api.utils.provider_manager import handle_embeddings
from api.schemas import EmbeddingsBody

app = APIRouter()
models = ''

@app.post("/v1/embeddings", dependencies=[Depends(user_checks), Depends(rate_limit)])
async def embeddings(request: Request, data: EmbeddingsBody):
    try:
        for _ in range(4):
            content = await handle_embeddings(data.model_dump())
            return Response(ujson.dumps(content, indent=4), status_code=200)
    except ValueError as e:
        raise HTTPException(detail={"error": {"message": str(e)}}, status_code=500)
    except:
        traceback.print_exc()
        raise HTTPException(detail={"error": {"message": "Moderation check failed within 4 retries, please try again later."}}, status_code=500)

