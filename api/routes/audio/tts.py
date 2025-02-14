import time

from fastapi import Response, Request, Depends, APIRouter
from fastapi.exceptions import HTTPException
import ujson

from api.providers.tts import elevenlabs, speechify, suno, tts as google_tts

from api.utils.checks import user_checks, rate_limit
from api.utils.logging import print_status
from api.database import DatabaseManager
from api.providers.tts import openai
from api.providers.tts import edge
from api.schemas import TtsBody

app = APIRouter()

with open('data/models/fakeyou.json', 'r') as f:
    fakeyou_models = ujson.loads(f.read())

@app.post("/v1/audio/speech", dependencies=[Depends(user_checks), Depends(rate_limit)])
async def tts(request: Request, data: TtsBody):
    key = request.headers.get("Authorization", "").replace("Bearer ", "")

    premium = await DatabaseManager.get_subscription_type(key) in ['basic', 'premium']
    start = time.time()

    if data.model == "gtts":
        content = await google_tts.tts(data.input)
    elif data.model == "suno-v3":
        content = await suno.main(data.input)
    elif data.model == "edge":
        content = await edge.edging_session(data.input)
    elif data.model == "elevenlabs" and premium and len(data.input) > 500:
        content = await elevenlabs.elevenlabs_premium(data.input, data.voice)
    elif data.model == "elevenlabs":
        content = await elevenlabs.elevenlabs(data.input, data.voice)
    elif data.model == "speechify":
        voice_data = next((voice for voice in speechify.Speechify.voices if voice['name'] == data.voice), None)
        content = await speechify.Speechify.generations(data.input, data.voice, voice_data['language'], voice_data['engine'])
    else:
        content = await openai.tts(data.model_dump())

    if content is None:
        raise HTTPException(detail={
            "error": {
                "message": "The provider sent an invalid response.",
                "type": "error",
                "param": None,
                "code": None
            }
        }, status_code=500)
    else:
        await print_status(True, round((time.time() - start), 2), data.model, await DatabaseManager.get_id(value=request.headers.get("Authorization").replace("Bearer ", "")), response=data.input)

    return Response(content=content, media_type="audio/mpeg", headers={"Content-Disposition": "attachment;filename=audio.mp3"})
