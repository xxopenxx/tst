import traceback
import time

from fastapi import Request, Response, APIRouter, Depends, HTTPException
import ujson

from api.utils.checks import user_checks, rate_limit
from api.utils.provider_manager import handle_images
from api.utils.logging import print_status
from api.database import DatabaseManager
from api.schemas import ImagesBody

app = APIRouter()

@app.post("/v1/images/generations", dependencies=[Depends(user_checks), Depends(rate_limit)])
async def images(request: Request, data: ImagesBody):
    start = time.time()
    key = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = await DatabaseManager.get_id(key)
    try:
        url = await handle_images(data.model_dump())
        if url:
            await print_status(True, round(time.time() - start, 2), data.model, user, (data.prompt, url))
            return Response(ujson.dumps({"created": int(time.time()), "data": [{"url": url}]}, escape_forward_slashes=False, indent=4), media_type="application/json")
        else:
            raise ValueError("Failed to create image, please try again.")
    except ValueError as e:
        await print_status(False, round(time.time() - start, 2), data.model, user, data.prompt)
        traceback.print_exc()
        raise HTTPException(detail={"error": {"message": f"{e}"}}, status_code=500)
    except:
        await print_status(False, round(time.time() - start, 2), data.model, user, data.prompt)
        traceback.print_exc()
        raise HTTPException(detail={"error": {"message": "Failed to generate your image, please try again later."}}, status_code=500)

