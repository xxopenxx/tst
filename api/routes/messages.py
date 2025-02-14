from typing import Any, Union, Dict
import time
import sys

from fastapi import Request, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import ujson

from api.utils.logging import print_status, log_and_return_error_id
from api.utils.redis_manager import get_or_set_cache, generate_cache_key
from api.utils.tokenizer import get_input_count, get_output_count
from api.database import DatabaseManager, ModelManager
from api.utils.checks import user_checks, rate_limit
from api.schemas import AnthropicChatBody, ChatBody
from api.utils.provider_manager import handle_chat
from api.utils.helpers import clean_messages

sys.path.append('....')

from tools.internet_search import run_internet_access

app = APIRouter()

with open("data/models/list.json", "r") as f:
    data = ujson.load(f)
    model_max_tokens = {model['id']: model.get('max_tokens') for model in data['data']}

premium_models = {model['id']: [k for k, v in model['access'].items() if v is True] for model in data['data']}

class ChatHandler:
    def __init__(self, request: Request, data: AnthropicChatBody):
        self.request = request
        self.data = data
        self.key = request.headers.get("Authorization", "").replace("Bearer ", "")
        self.user = None
        self.subscription_type = None
        self.premium = False
        self.start_time = time.time()

    async def _load_user_data(self) -> None:
        try:
            self.user = await DatabaseManager.get_id(self.key)
            self.subscription_type = await DatabaseManager.get_subscription_type(self.key)
            self.premium = self.subscription_type in ['basic', 'premium', 'custom']
        except Exception as e:
            trace_id = await log_and_return_error_id(
                e,
                None,
                self.data.model,
                None,
                False,
                dict(self.request.headers),
                self.data.model_dump()
            )
            raise HTTPException(status_code=500, detail={"error": {"message": f"Error loading user data. Trace ID: {trace_id}", "trace_id": trace_id}})

    async def _check_token_limits(self) -> None:
        if not self.premium:
            input_tokens = await get_input_count(self.data.messages)
            max_allowed_tokens = model_max_tokens.get(self.data.model, 128000)
            if input_tokens > (max_allowed_tokens // 2):
                raise HTTPException(status_code=413, detail={"error": {"message": "Your subscription tier does not allow for this many input tokens. Please upgrade your subscription at https://discord.shard-ai.xyz"}})

    async def _preprocess_messages(self) -> None:
        try:
            self.data.messages = await clean_messages(self.data.messages)
            internet_search_bool = '-online' in self.data.model
            self.data.model = self.data.model.replace("-online", "").replace("-json", '')

            if internet_search_bool and self.premium:
                online_messages = await run_internet_access(self.data.messages)
                if online_messages is not None:
                    self.data.messages = online_messages
        except Exception as e:
            trace_id = await log_and_return_error_id(
                e,
                self.user,
                self.data.model,
                self.subscription_type,
                self.premium,
                dict(self.request.headers),
                self.data.model_dump(),
                self.start_time
            )
            await print_status(False, round(time.time() - self.start_time, 2), self.data.model, self.user)
            raise HTTPException(status_code=500, detail={"error": {"message": f"Error preprocessing messages. Trace ID: {trace_id}", "trace_id": trace_id}})

    async def _check_model_access(self) -> None:
        if self.subscription_type not in premium_models[self.data.model] and self.subscription_type != 'custom':
            raise HTTPException(status_code=403, detail={"error": {"message": "You do not have access to this model. Please purchase through https://discord.shard-ai.xyz/"}})

    def _prepare_request_data(self) -> Dict:
        data_dict = self.data.model_dump()
        if data_dict.get('system'):
            data_dict['messages'].insert(0, {"role": "system", "content": data_dict.pop('system')})
        return data_dict

    async def _get_response_content(self, stream: bool = False) -> Union[str]:
        async def _get_non_stream_response() -> str | None:
            start = time.time()
            request_data = self._prepare_request_data()
            
            for _ in range(4):
                try:
                    c = await get_or_set_cache(
                        generate_cache_key(request_data), 
                        handle_chat, 
                        data=ChatBody(**request_data), 
                        key=self.key, 
                        stream=False
                    )
                    if c is not None:
                        return c
                except Exception as e:
                    trace_id = await log_and_return_error_id(
                        e,
                        self.user,
                        self.data.model,
                        self.subscription_type,
                        self.premium,
                        dict(self.request.headers),
                        request_data,
                        self.start_time
                    )
                    await print_status(False, round(time.time() - start, 2), self.data.model, self.user)
                    raise HTTPException(status_code=500, detail={"error": {"message": f"Error preprocessing request. Trace ID: {trace_id}", "trace_id": trace_id}})
            return None

        try:
            if stream:
                input_tokens = await get_input_count(self.data.messages)
                await ModelManager.update_model_tokens(self.data.model.lower(), input_tokens=input_tokens)
                await DatabaseManager.update_model_tokens(self.key, self.data.model.lower(), input_tokens=input_tokens)
                
                request_data = self._prepare_request_data()
                return await handle_chat(ChatBody(**request_data), self.key, True)
            else:
                return await _get_non_stream_response()
        except Exception as e:
            trace_id = await log_and_return_error_id(
                e,
                self.user,
                self.data.model,
                self.subscription_type,
                self.premium,
                dict(self.request.headers),
                self.data.model_dump(),
                self.start_time
            )
            await print_status(False, round(time.time() - self.start_time, 2), self.data.model, self.user)
            raise HTTPException(status_code=500, detail={"error": {"message": f"Error getting response content. Trace ID: {trace_id}", "trace_id": trace_id}})

    async def _update_tokens(self, content: str) -> None:
        input_tokens = await get_input_count(self.data.messages)
        output_tokens = await get_output_count(content)
        model = self.data.model.lower()
        await ModelManager.update_model_tokens(model, input_tokens, output_tokens)
        await DatabaseManager.update_model_tokens(self.key, model, input_tokens, output_tokens)

    async def handle_request(self) -> Any:
        await user_checks(self.request)
        await rate_limit(self.request)
        await self._load_user_data()
        await self._check_token_limits()
        await self._preprocess_messages()
        await self._check_model_access()

        try:
            response_content = await self._get_response_content(stream=self.data.stream)
            
            if self.data.stream:
                return StreamingResponse(response_content, media_type='text/event-stream')
            
            if response_content is None:
                raise HTTPException(
                    status_code=500,
                    detail={"error": {"message": "Chat completion failed within 4 retries, please try again later."}}
                )
            
            await self._update_tokens(response_content)
            elapsed = round(time.time() - self.start_time, 2)
            await print_status(True, elapsed, self.data.model, self.user, response_content)
            return {
                "model": self.data.model,
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": response_content
                    },
                    "index": 0,
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": await get_input_count(self.data.messages),
                    "completion_tokens": await get_output_count(response_content),
                    "total_tokens": await get_input_count(self.data.messages) + await get_output_count(response_content)
                }
            }

        except HTTPException as e:
            raise e
        except Exception as e:
            trace_id = await log_and_return_error_id(
                e,
                self.user,
                self.data.model,
                self.subscription_type,
                self.premium,
                dict(self.request.headers),
                self.data.model_dump(),
                self.start_time
            )
            await print_status(False, round(time.time() - self.start_time, 2), self.data.model, self.user)
            raise HTTPException(
                status_code=500,
                detail={"error": {"message": f"Chat completion failed, please try again later. Trace ID: {trace_id}", "trace_id": trace_id}}
            )
                        
@app.post("/v1/messages")
async def chat(request: Request, data: AnthropicChatBody) -> Any:
    handler = ChatHandler(request, data)
    return await handler.handle_request()