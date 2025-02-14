from typing import Optional, List, Dict
import re

from pydantic import BaseModel, field_validator, ValidationInfo
from fastapi import HTTPException
import ujson

from api.utils.tokenizer import input_count_schema

def load_model_ids(file_path: str, model_type: str) -> List[str]:
    with open(file_path, "r") as f:
        return [model['id'] for model in ujson.load(f)['data'] if model['type'] == model_type]

models = load_model_ids("data/models/list.json", "chat.completions")

with open("data/models/list.json", "r") as f:
    data = ujson.load(f)
    model_max_tokens = {model['id']: model.get('max_tokens') for model in data['data']}

with open("data/models/bad_models.json", "r") as f:
    bad_models = ujson.load(f)

class ChatBody(BaseModel):
    model: str
    messages: List[Dict]
    stream: Optional[bool] = False
    max_tokens: Optional[int] = 512
    tools: list = None

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

        if not any(message.get("role") == "user" for message in v):
            raise HTTPException(status_code=422, detail='At least one user message is required.')

        tools = info.data.get('tools', [])
        tool_names = {tool.function.name for tool in tools} if tools else set()

        for message in v:
            if message.get("role") == "tool_call":
                tool_call = message.get("tool_call", {})
                if not tool_call:
                    raise HTTPException(status_code=422, detail="Tool call message must contain 'tool_call' field.")
                tool_name = tool_call.get("name")
                if tool_name not in tool_names:
                    raise HTTPException(status_code=422, detail=f"Tool '{tool_name}' is not defined in 'tools'.")

        model = info.data.get('model')
        max_tokens = info.data.get('max_tokens', 0)
        model_base = model.split('--')[0].replace("-online", "").replace("-json", "")
        total_input_tokens = input_count_schema(v)

        model_max_allowed_tokens = model_max_tokens.get(model_base, 128000)

        if total_input_tokens + max_tokens > model_max_allowed_tokens:
            raise HTTPException(
                status_code=422,
                detail=f"You requested {total_input_tokens + max_tokens} tokens, but '{model_base}'s maximum is {model_max_allowed_tokens} tokens. (You requested {total_input_tokens} tokens in messages and {max_tokens} tokens in 'max_tokens')."
            )

        return v

    @field_validator("max_tokens")
    def validate_max_tokens(cls, tokens, info: ValidationInfo):
        model = info.data.get('model')
        if model is None:
            raise HTTPException(status_code=422, detail="Model is not provided.")

        model_base = model.split('--')[0].replace("-online", "").replace("-json", "")

        if tokens is not None and tokens <= 0:
            raise HTTPException(status_code=422, detail="max_tokens must be a positive integer")

        max_allowed_tokens = model_max_tokens.get(model_base, 128000)
        if tokens and tokens > max_allowed_tokens:
            raise HTTPException(status_code=422, detail=f"You requested {tokens} tokens, while the max is {max_allowed_tokens} tokens.")

        return tokens

    @field_validator("tools")
    def validate_tools(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise HTTPException(status_code=422, detail="tools must be a list")
            
            if len(v) > 128:
                raise HTTPException(status_code=422, detail="A maximum of 128 functions are supported")
            
            function_names = set()
            for tool in v:
                tool
                if not isinstance(tool, dict):
                    raise HTTPException(status_code=422, detail="Each tool must be a dictionary")
                
                if "type" not in tool:
                    raise HTTPException(status_code=422, detail="Each tool must have a 'type' field")
                
                if "function" not in tool:
                    raise HTTPException(status_code=422, detail="Each tool must have a 'function' field")
                
                function = tool.get("function", {})
                function_name = function.get("name")
                
                if function_name in function_names:
                    raise HTTPException(status_code=422, detail=f"Duplicate function name found: {function_name}")
                function_names.add(function_name)

        return v