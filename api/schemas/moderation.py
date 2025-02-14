from pydantic import BaseModel, field_validator, model_validator
import ujson

from api.utils.tokenizer import input_count_schema

# Load model token limits from file
with open("data/models/list.json", "r") as f:
    data = ujson.load(f)
    model_max_tokens = {model['id']: model.get('max_tokens') for model in data['data']}

class ModerationBody(BaseModel):
    input: str
    model: str

    @field_validator("input")
    def validate_input(cls, v):
        if not isinstance(v, str):
            raise ValueError("Input must be a string.")
        return v

    @model_validator(mode="after")
    def validate_model_and_input(self):
        if self.model not in model_max_tokens:
            raise ValueError(f"Model '{self.model}' is not recognized.")

        max_tokens = model_max_tokens[self.model]
        if input_count_schema(self.input) > max_tokens:
            raise ValueError(f"Input exceeds maximum token length for model '{self.model}' ({max_tokens} tokens).")
        
        return self
