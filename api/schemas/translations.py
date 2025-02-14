from typing import Optional, List
import re

from pydantic import BaseModel, Field, model_validator
import ujson

with open("data/models/list.json", "r") as f:
    models = [model['id'] for model in ujson.load(f)['data'] if model['type'] == "transcriptions"]

formats = ['json', 'text', 'srt', 'verbose_json', 'vtt']

class TranslationsBody(BaseModel):
    model: str
    language: Optional[str] = None
    prompt: Optional[str] = None
    response_format: Optional[str] = 'json'
    temperature: Optional[float] = 0
    timestamp_granularities: Optional[List[str]] = ['segment']
    
    @model_validator(mode='before')
    def validate_inputs(cls, values):
        model = values.get('model')
        response_format = values.get('response_format')
        language = values.get('language')
        temperature = values.get('temperature')
        
        if not isinstance(temperature, (float, int)):
            raise ValueError("Temperature must be of type int or float.")
        
        if model not in models:
            raise ValueError(f"Invalid model. Valid models are: {list(models.keys())}")

        if response_format not in ['json', 'text', 'srt', 'verbose_json', 'vtt']:
            raise ValueError(f"Invalid response_format. Valid formats are: {formats}")

        if language and not re.match(r'^[a-z]{2}$', language):
            raise ValueError("Invalid language. It should be in ISO 639-1 format.")

        return values
