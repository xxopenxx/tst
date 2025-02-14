from pydantic import BaseModel, field_validator, ValidationInfo
from typing import Any, Optional

from ..providers.tts import elevenlabs
from ..providers.tts import speechify
import ujson

with open("data/models/list.json", "r") as f:
    models = [model['id'] for model in ujson.load(f)['data'] if model['type'] == "audio.speech"] + ['fakeyou'] + ["suno-v3"]

with open('data/models/fakeyou.json', 'r') as f:
    fakeyou_models = ujson.loads(f.read())
    
voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"] + [voice['name'] for voice in speechify.Speechify.voices] + elevenlabs.get_voices() + fakeyou_models

class TtsBody(BaseModel):
    input: Any
    model: Any
    voice: Optional[str] = 'alloy'

    @classmethod
    def check_input(cls, input):
        if not isinstance(input, str) or len(input) >= 4096:
            raise ValueError('Invalid input.')
        
    @classmethod
    def check_model(cls, model):
        if not isinstance(model, str) or model not in models:
            raise ValueError('Invalid model.')
        
    @classmethod
    def check_voice(cls, voice):
        if voice:
            if not isinstance(voice, str):
                raise ValueError('Invalid voice.')

    @field_validator("input")
    def validate_input(cls, v):
        cls.check_input(v)
        return v

    @field_validator("model")
    def validate_model(cls, v):
        cls.check_model(v)
        return v
    
    @field_validator("voice")
    def validate_voice(cls, v, info: ValidationInfo):
        cls.check_voice(v)
        return v