from pydantic import BaseModel, field_validator
from typing import Optional
import ujson

with open("data/models/list.json", "r") as f:
    models = [model['id'] for model in ujson.load(f)['data'] if model['type'] == "images.generations"]

class ImagesBody(BaseModel):
    prompt: str
    model: str
    size: Optional[str] = '1024x1024'
    n: Optional[int] = 1

    @classmethod
    def model_check(cls, model: str):
        if not isinstance(model, str) or model not in models:
            raise ValueError('Invalid model.')
    
    @classmethod
    def prompt_check(cls, prompt: str):
        if not isinstance(prompt, str):
            raise ValueError('Invalid prompt.')

    @classmethod
    def size_check(cls, size: str):
        width, height = size.split("x")
        if int(width) % 4 != 0 or int(height) % 4 != 0:
            raise ValueError('Invalid size. Width and height must be divisible by 4.')
    
    @field_validator("model")
    def validate_model(cls, v):
        cls.model_check(v)
        return v

    @field_validator("prompt")
    def validate_prompt(cls, v):
        cls.prompt_check(v)
        return v
    
    @field_validator("size", mode="before")
    def validate_size(cls, v):
        v = v or '1024x1024'
        cls.size_check(v)
        return v
