from typing import Optional
import tempfile
import time
import sys
import os

import ujson
from fastapi import Request, APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import JSONResponse, PlainTextResponse

from api.utils.checks import user_checks, rate_limit
from api.utils.logging import print_status
from api.database import DatabaseManager

sys.path.append('....')
from ai.whisper.main import WhisperTranscriber

# Load the model list
with open("data/models/list.json", "r") as f:
    models = [model['id'] for model in ujson.load(f)['data'] if model['type'] == "audio.transcriptions"]

formats = ['json', 'text', 'srt', 'verbose_json', 'vtt']


whisper_transcriber = WhisperTranscriber()

app = APIRouter()

@app.post('/v1/audio/transcriptions', dependencies=[Depends(user_checks), Depends(rate_limit)])
async def transcriptions_route(
    request: Request,
    model: str = Form(...),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form('json'),
    temperature: Optional[float] = Form(0),
    file: UploadFile = File(...)
):
    start_time: float = time.time()
    
    auth = request.headers.get("Authorization", None).replace("Bearer ", '')
    user = await DatabaseManager.get_id(auth)
    
    if model not in models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Valid models are: {models}")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    params = {
        "file_path": temp_file_path,
        "model_size": model,
        "timestamp_granularities": ['segment'],
        "response_format": response_format
    }

    if prompt:
        params["initial_prompt"] = prompt
    if temperature is not None:
        params["temperature"] = temperature

    result = await whisper_transcriber.transcribe_audio(**params)

    os.unlink(temp_file_path) 

    await print_status(True, round(time.time() - start_time, 2), model, user, result)
    
    if response_format == 'json':
        return JSONResponse(content={"text": result["text"]})
    elif response_format == 'text':
        return PlainTextResponse(content=result["text"])
    elif response_format in ['verbose_json', 'vtt', 'srt']:
        return JSONResponse(content=result)
    else:
        raise HTTPException(status_code=400, detail="Unsupported response format")