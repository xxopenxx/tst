from typing import Any, Union, Dict
import time
import sys

from fastapi import Request, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import ujson

from api.utils.logging import print_status, log_and_return_error_id, log_info
from api.utils.redis_manager import get_or_set_cache, generate_cache_key
from api.utils.tokenizer import get_input_count, get_output_count
from api.utils.moderation import openai_moderation, moderation
from api.database import DatabaseManager, ModelManager
from api.utils.checks import user_checks, rate_limit
from api.utils.provider_manager import handle_chat
from api.utils.helpers import clean_messages
from api.utils.tools import ToolCalls
from api.utils.rag import rag_system
from api.schemas import ChatBody
from api.utils.responses import (
    stream_response_iterator_tool,
    return_tool_data,
    return_data
)

sys.path.append('....')

from tools.internet_search import run_internet_access

app = APIRouter()

with open("data/models/list.json", "r") as f:
    data = ujson.load(f)
    model_max_tokens = {model['id']: model.get('max_tokens') for model in data['data']}

premium_models = {model['id']: [k for k, v in model['access'].items() if v is True] for model in data['data']}

class ChatHandler:
    """Handles chat completion requests."""
    def __init__(self, request: Request, data: ChatBody):
        self.request = request
        self.data = data
        self.key = request.headers.get("Authorization", "").replace("Bearer ", "")
        self.user = None
        self.subscription_type = None
        self.premium = False
        self.start_time = time.time()

    async def _load_user_data(self) -> None:
        """Loads user data from the database."""
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

    async def _moderate(self) -> None:
        if not self.premium:
            block = await moderation(self.data.messages, '')
            reason = "Profanity Check"
            if block:
                await log_info("REJECTED", reason, False, self.user, self.data.messages[-1]['content'])
                raise HTTPException(detail={"error": {"message": "Please purchase a paid subscription to role play on our services."}}, status_code=400)
            else:
                block, reason = await openai_moderation(self.data.model, self.data.messages, False)
                
                if block:
                    await log_info("REJECTED", reason, False, self.user, self.data.messages[-1]['content'])
                    raise HTTPException(detail={"error": {"message": f"Your request has been blocked becuase of {reason} inputs."}}, status_code=400)
        else:
            block, reason = await openai_moderation(self.data.model, self.data.messages, True)

            if block:
                await log_info("REJECTED", reason, False, self.user, self.data.messages[-1]['content'])
                raise HTTPException(detail={"error": {"message": f"Your request has been blocked because of {reason} inputs."}}, status_code=400)
            
    async def _check_token_limits(self) -> None:
        """Checks if the user has exceeded their token limits."""
        if not self.premium:
            input_tokens = await get_input_count(self.data.messages)
            max_allowed_tokens = model_max_tokens.get(self.data.model, 128000)
            if input_tokens > (max_allowed_tokens // 2):
                raise HTTPException(status_code=413, detail={"error": {"message": "Your subscription tier does not allow for this many input tokens. Please upgrade your subscription at https://discord.shard-ai.xyz"}})

    async def _preprocess_messages(self) -> None:
        """Preprocesses messages, including online search if enabled."""
        try:
            self.data.messages = await rag_system.process_messages(self.data.messages)
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
        """Checks if the user has access to the requested model."""
        if self.subscription_type not in premium_models[self.data.model] and self.subscription_type != 'custom':
            raise HTTPException(status_code=403, detail={"error": {"message": "You do not have access to this model. Please purchase through https://discord.shard-ai.xyz/"}})

    def _prepare_request_data(self, include_tools: bool = False) -> Dict:
        """Prepares request data with or without tools."""
        data_dict = self.data.model_dump()
        if not include_tools:
            data_dict.pop('tools', None)
        data_dict['messages'][-1]['content'] += "Make your answer short and concise."
        return data_dict

    async def _get_response_content(self, stream: bool = False) -> Union[str]:
        """Helper function to get either the content or the stream response."""
        async def _get_non_stream_response() -> str | None:
            start = time.time()
            request_data = self._prepare_request_data(include_tools=False)
            
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
                
                request_data = self._prepare_request_data(include_tools=False)
                try:
                    return await handle_chat(ChatBody(**request_data), self.key, True)
                except:
                    pass
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

    async def _handle_tool_calls(self) -> Any | None:
        """Handles tool calls if they are present in the request."""
        if not self.data.tools:
            return None
            
        trace_id = None
        tool_messages = ToolCalls.create_model_instruction(self.data.messages, self.data.tools)
        self.data.messages = tool_messages
        tool_response = await self._get_response_content(stream=False)
        
        if self.data.stream:
            try:
                tool_call_extracted, result = ToolCalls.convert_model_response(tool_response)
                elapsed = round(time.time() - self.start_time, 2)
                await print_status(True, elapsed, self.data.model, self.user, tool_response)
                return StreamingResponse(
                    content=stream_response_iterator_tool(result, self.data.model, self.key, self.start_time, self.user),
                    media_type='text/event-stream'
                )
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
                raise HTTPException(status_code=500, detail={"error": {"message": f"Error handling stream tool call response. Trace ID: {trace_id}", "trace_id": trace_id}})
        
        if not tool_response:
            error_message = "Chat completion failed within 4 retries, please try again later."
            if trace_id:
                error_message += f" Trace ID: {trace_id}"
            raise HTTPException(status_code=500, detail={"error": {"message": error_message}})
            
        try:
            tool_call_extracted, result = ToolCalls.convert_model_response(tool_response)
            if tool_call_extracted:
                elapsed = round(time.time() - self.start_time, 2)
                await print_status(True, elapsed, self.data.model, self.user, tool_response)
                return return_tool_data('', self.data.model, result, self.data.messages)
            
            await self._update_tokens(result)
            elapsed = round(time.time() - self.start_time, 2)
            await print_status(True, elapsed, self.data.model, self.user, tool_response)
            return return_data(result, self.data.model, self.data.messages)
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
            raise HTTPException(status_code=500, detail={"error": {"message": f"Error handling non-stream tool call response. Trace ID: {trace_id}", "trace_id": trace_id}})

    async def _update_tokens(self, content: str) -> None:
        """Updates token counts in the database."""
        input_tokens = await get_input_count(self.data.messages)
        output_tokens = await get_output_count(content)
        model = self.data.model.lower()
        await ModelManager.update_model_tokens(model, input_tokens, output_tokens)
        await DatabaseManager.update_model_tokens(self.key, model, input_tokens, output_tokens)

        # update recent activity as well
        await DatabaseManager.update_recent_usage(self.key, model, input_tokens, output_tokens, "chat")

    async def handle_request(self) -> Any:
        """Main method to handle incoming chat request."""
        await user_checks(self.request)
        await rate_limit(self.request)

        await self._load_user_data()
        await self._moderate()
        await self._check_token_limits()
        await self._preprocess_messages()
        await self._check_model_access()

        tool_call_response = await self._handle_tool_calls()
        if tool_call_response:
            return tool_call_response

        try:
            response_content = await self._get_response_content(stream=self.data.stream)
            
            if self.data.stream:
                return response_content
            
            if response_content is None:
                raise HTTPException(
                    status_code=500,
                    detail={"error": {"message": "Chat completion failed within 4 retries, please try again later."}}
                )
            
            await self._update_tokens(response_content)
            elapsed = round(time.time() - self.start_time, 2)
            await print_status(True, elapsed, self.data.model, self.user, response_content)
            return return_data(response_content, self.data.model, self.data.messages)

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
                        
@app.post("/v1/chat/completions")
async def chat(request: Request, data: ChatBody) -> Any:
    """Endpoint for chat completions."""
    handler = ChatHandler(request, data)
    return await handler.handle_request()