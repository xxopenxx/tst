from fastapi.exceptions import HTTPException
from fastapi import Response, APIRouter
import ujson

app = APIRouter()

with open('data/models/list.json', 'r') as f:
    data = ujson.load(f)

@app.route("/v1/models", methods=["GET", "POST", "PUT", "PATCH", "HEAD"])
async def models(_):
    return Response(ujson.dumps(data, indent=4, escape_forward_slashes=False), media_type="application/json")

@app.route("/v1/models/{model:str}", methods=["GET", "POST", "PUT", "PATCH", "HEAD"])
async def model_info(_, model: str):
    model_info = next((model_info for model_info in data['data'] if model_info['id'] == model), None)
    print(model_info)
    if model_info:
        return Response(ujson.dumps({"model": model_info}, indent=4, escape_forward_slashes=False), media_type="application/json")
    else:
        raise HTTPException(detail={"error": {"message": "This model does not exist.", "type": "error", "param": None, "code": None}}, status_code=400)