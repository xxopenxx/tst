from pydantic import BaseModel, field_validator
from typing import Any
import ujson

with open("data/models/list.json", "r") as f:
    models = [model['id'] for model in ujson.load(f)['data'] if model['type'] == "embeddings"]

class EmbeddingsBody(BaseModel):
    input: Any
    model: Any

    @classmethod
    def check_input(cls, input):
        pass
        
    @classmethod
    def check_model(cls, model):
        if not isinstance(model, str) or model not in models:
            raise ValueError('Invalid model.')

    @field_validator("input")
    def validate_input(cls, v):
        cls.check_input(v)
        return v
    
    @field_validator("model")
    def validate_model(cls, v):
        cls.check_model(v)
        return v