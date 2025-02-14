from fastapi import Response, APIRouter
import ujson

from api.providers.tts import elevenlabs
from api.providers.tts import speechify

app = APIRouter()

with open('data/models/fakeyou.json', 'r') as f:
    fakeyou_models = ujson.loads(f.read())
    
@app.route("/v1/voices/speechify", methods=["GET", "POST", "PUT", "PATCH", "HEAD"])
async def speechify_voices(_):
    model_list = ujson.dumps({"voices": [voice['name'] for voice in speechify.Speechify.voices]}, indent=4, escape_forward_slashes=False)
    return Response(model_list, media_type="application/json")

@app.route("/v1/voices/elevenlabs", methods=["GET", "POST", "PUT", "PATCH", "HEAD"])
async def elevenlabs_voices(_):
    model_list = ujson.dumps({"voices": elevenlabs.get_voices()}, indent=4, escape_forward_slashes=False)
    return Response(model_list, media_type="application/json")

@app.route("/v1/voices/fakeyou", methods=["GET", "POST", "PUT", "PATCH", "HEAD"])
async def fakeyou_voices(_):
    model_list = ujson.dumps({"message": "Voice name is cap sensitive. Must be exact. No slurs allowed aswell.", "voices": fakeyou_models}, indent=4, escape_forward_slashes=False)
    return Response(model_list, media_type="application/json")