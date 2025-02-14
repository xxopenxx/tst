from typing import Optional, List, Dict
import re

from pydantic import BaseModel, field_validator, ValidationInfo
from fastapi import HTTPException
import ujson

from api.utils.tokenizer import input_count_schema

def load_model_ids(file_path: str, model_type: str) -> List[str]:
    with open(file_path, "r") as f:
        return [model['id'] for model in ujson.load(f)['data'] if model['type'] == model_type]

models = load_model_ids("data/models/list.json", "messages")

with open("data/models/list.json", "r") as f:
    data = ujson.load(f)
    model_max_tokens = {model['id']: model.get('max_tokens') for model in data['data']}

with open("data/models/bad_models.json", "r") as f:
    bad_models = ujson.load(f)

class AnthropicChatBody(BaseModel):
    model: str
    messages: List[Dict]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    system: Optional[str] = None

    @field_validator("model")
    def validate_model(cls, v):
        model_base = v.split('--')[0].replace("-online", "").replace("-json", "")
        if model_base.lower() in bad_models:
            raise HTTPException(status_code=422, detail=f"{v} is currently down, please use another.")
        if not isinstance(model_base, str) or (model_base not in models):
            raise HTTPException(status_code=422, detail='Invalid model.')
        return v

    @field_validator("messages")
    def validate_messages(cls, v, info: ValidationInfo):
        if not isinstance(v, list):
            raise HTTPException(status_code=422, detail='Invalid messages format; expected a list.')

        valid_roles = {"user", "assistant"}
        for message in v:
            if not isinstance(message, dict):
                raise HTTPException(status_code=422, detail='Each message must be a dictionary.')
            
            if "role" not in message or "content" not in message:
                raise HTTPException(status_code=422, detail='Each message must have "role" and "content" fields.')
            
            if message["role"] not in valid_roles:
                raise HTTPException(status_code=422, detail=f'Invalid role. Must be one of: {valid_roles}')
            
            if not isinstance(message["content"], str):
                raise HTTPException(status_code=422, detail='Message content must be a string.')

        for i in range(1, len(v)):
            if v[i]["role"] == v[i-1]["role"]:
                raise HTTPException(status_code=422, detail='Messages must alternate between user and assistant.')

        if v and v[0]["role"] != "user":
            raise HTTPException(status_code=422, detail='First message must be from user.')

        # Check total tokens
        model = info.data.get('model')
        max_tokens = info.data.get('max_tokens', 0)
        model_base = model.split('--')[0].replace("-online", "").replace("-json", "")
        total_input_tokens = input_count_schema(v)

        model_max_allowed_tokens = model_max_tokens.get(model_base, 128000)

        if total_input_tokens + (max_tokens or 0) > model_max_allowed_tokens:
            raise HTTPException(
                status_code=422,
                detail=f"You requested {total_input_tokens + (max_tokens or 0)} tokens, but '{model_base}'s maximum is {model_max_allowed_tokens} tokens. (You requested {total_input_tokens} tokens in messages and {max_tokens or 0} tokens in 'max_tokens')."
            )

        return v

    @field_validator("max_tokens")
    def validate_max_tokens(cls, tokens, info: ValidationInfo):
        if tokens is not None:
            if tokens <= 0:
                raise HTTPException(status_code=422, detail="max_tokens must be a positive integer")

            model = info.data.get('model')
            if model is None:
                raise HTTPException(status_code=422, detail="Model is not provided.")

            model_base = model.split('--')[0].replace("-online", "").replace("-json", "")
            max_allowed_tokens = model_max_tokens.get(model_base, 128000)
            
            if tokens > max_allowed_tokens:
                raise HTTPException(status_code=422, detail=f"You requested {tokens} tokens, while the max is {max_allowed_tokens} tokens.")

        return tokens