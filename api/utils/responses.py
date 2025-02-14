from typing import AsyncIterator, List, Dict, Any, Union, Optional
import random
import string

from fastapi.responses import Response
from fastapi import HTTPException
import ujson
import time

from api.utils.logging import print_status, log_and_return_error_id
from api.database import DatabaseManager, ModelManager
from api.utils.tokenizer import get_output_count

class ResponseGenerator:
    """A helper class to generate various types of API responses."""
    def __init__(self):
        pass

    def generate_completion_id(self) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=28))

    def generate_fingerprint_id(self) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=10))

    def generate_timestamp(self) -> int:
        return int(time.time())

    def generate_call_id(self) -> str:
        return f"call-{self.generate_completion_id()}"

    async def update_token_usage_stream(self, data: List[str], model: str, key: str):
        output_tokens = sum([await get_output_count(message) for message in data])
        await ModelManager.update_model_tokens(model, output_tokens=output_tokens)
        await DatabaseManager.update_model_tokens(key, model, output_tokens=output_tokens)

    async def stream_response_iterator_str(self, message: str, model: str, key: str) -> AsyncIterator[str]:
        try:
            yield self.create_initial_response(model)
            yield self.create_content_chunk(message, model)
        except Exception as e:
            error_response = await self.create_error_response(str(e))
            yield error_response
        finally:
            yield self.create_final_response(model)
            yield "data: [DONE]"
            await self.update_token_usage_stream([message], model, key)

    async def stream_response_iterator_tool(
        self,
        tool_call_data: List[Dict[str, Any]],
        model: str,
        key: str,
        start_time: float,
        user: str,
    ) -> AsyncIterator[str]:
        """Generates a streaming response for tool calls."""
        try:
            completion_id = f"chatcmpl-{self.generate_completion_id()}"
            fingerprint = f"fp_{self.generate_fingerprint_id()}"
            timestamp = self.generate_timestamp()

            async def create_chunk(tool_calls: List[Dict[str, Any]] = None, content: Optional[str] = None, finish_reason: Optional[str] = None) -> str:
                 chunk_data = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": timestamp,
                        "model": model,
                        "system_fingerprint": fingerprint,
                        "choices": [{
                            "index": 0,
                            "delta": {
                                "role": "assistant",
                                "content": content,
                                "tool_calls": tool_calls,
                            } if content is not None or tool_calls else {},
                            "logprobs": None,
                            "finish_reason": finish_reason,
                        }]
                    }
                 return f"data: {ujson.dumps(chunk_data, escape_forward_slashes=False)}\n\n"

            initial_chunk = await create_chunk(
                content=None,
                tool_calls=[{
                    "index": i,
                    "id": self.generate_call_id(),
                    "type": "function",
                    "function": {
                        "name": tool['function']['name'],
                        "arguments": ""
                    },
                } for i, tool in enumerate(tool_call_data) if tool['type'] == 'function']
            )
            yield initial_chunk

            all_arguments = [tool['function']['arguments'] for tool in tool_call_data if tool['type'] == 'function']

            for i, arguments in enumerate(all_arguments):
                    for char in arguments:
                         yield await create_chunk(tool_calls=[{
                                "index": i,
                                "function": {
                                    "arguments": char,
                                }
                            }])
            final_chunk = await create_chunk(finish_reason="tool_calls")
            yield final_chunk

        except Exception as e:
            error_response = await self.create_error_response(str(e))
            yield error_response
        finally:
            yield "data: [DONE]"
            await self.update_token_usage_stream([str(tool_call_data)], model, key)
            await print_status(True, round(time.time() - start_time, 2), model, user, str(tool_call_data))

    async def stream_response_iterator_str_generator(
        self,
        message: AsyncIterator[str],
        model: str,
        key: str,
        start_time: float,
        user: str
    ) -> AsyncIterator[str]:
        content_history: List[str] = []

        yield self.create_initial_response(model)

        try:
            async for obj in message:
                yield self.create_content_chunk(obj, model)
                content_history.append(obj)
        except Exception as e:
            error_response = await self.create_error_response(str(e))
            await print_status(False, round(time.time() - start_time, 2), model, user, ''.join(content_history))
            yield error_response
    
        yield self.create_final_response(model)
        yield "data: [DONE]"
        await self.update_token_usage_stream(content_history, model, key)
        await print_status(True, round(time.time() - start_time, 2), model, user, ''.join(content_history))


    def create_initial_response(self, model: str) -> str:
      return f"""data: {ujson.dumps({
          'id': f'chatcmpl-{self.generate_completion_id()}',
          'object': 'chat.completion.chunk',
          'created': self.generate_timestamp(),
          'model': model,
          'system_fingerprint': f'fp_{self.generate_fingerprint_id()}',
          'choices': [{
              'index': 0,
              'delta': {'role': 'assistant', 'content': ''},
              'logprobs': None,
              'finish_reason': None
          }]
      }, escape_forward_slashes=False)}\n\n"""

    def create_content_chunk(self, content: str, model: str) -> str:
        return f"""data: {ujson.dumps({
            'id': f'chatcmpl-{self.generate_completion_id()}',
            'object': 'chat.completion.chunk',
            'created': self.generate_timestamp(),
            'model': model,
            'system_fingerprint': 'Null',
            'choices': [{
                'index': 0,
                'delta': {'content': content},
                'logprobs': False,
                'finish_reason': False
            }]
        }, escape_forward_slashes=False)}\n\n"""

    async def create_error_response(self, error: str) -> str:
        trace_id = await log_and_return_error_id(error)
        return f"""data: {ujson.dumps({
            "error": {
                "message": "An unexpected error has occurred, please try again later! This error has been logged and staff have been notified.",
                "type": "internal_error",
                "param": None,
                "code": "internal_server_error",
                "trace_id": trace_id
            }
        })}\n\n"""

    def create_final_response(self, model: str) -> str:
         return f"""data: {ujson.dumps({
             'id': f'chatcmpl-{self.generate_completion_id()}',
             'object': 'chat.completion.chunk',
             'created': self.generate_timestamp(),
             'model': model,
             'system_fingerprint': f'fp_{self.generate_fingerprint_id()}',
             'choices': [{
                 'index': 0,
                 'delta': {},
                 'logprobs': None,
                 'finish_reason': 'stop'
             }]
         }, escape_forward_slashes=False)}\n\n"""

    def return_data(self, content: Union[str, dict], model: str, messages: List[Dict[str, str]]) -> Response:
        completion_id = self.generate_completion_id()
        completion_timestamp = self.generate_timestamp()
        if isinstance(content, Response):
            return content
        if not isinstance(content, dict):
             try:
                return Response(ujson.dumps({
                    "id": f"chatcmpl-{completion_id}",
                    "object": "chat.completion",
                    "created": completion_timestamp,
                    "model": model,
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": round(len("".join(message['content'] for message in messages)) / 4),
                        "completion_tokens": round(len(content) / 4),
                        "total_tokens": round((len("".join(message['content'] for message in messages)) / 4) + (len(content) / 4)),
                        "prompt_tokens_details": {
                            "cached_tokens": round(len(str(content)) // 4),
                            "audio_tokens": 0
                        },
                        "completion_tokens_details": {
                            "reasoning_tokens": 0,
                            "accepted_prediction_tokens": 0,
                            "rejected_prediction_tokens": 0
                        }
                    }
                }, indent=4, escape_forward_slashes=False), media_type="application/json")
             except TypeError:
                 return Response(ujson.dumps({
                     "id": f"chatcmpl-{completion_id}",
                     "object": "chat.completion",
                     "created": completion_timestamp,
                     "model": model,
                     "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                     "usage": {
                         "prompt_tokens": 1,
                         "completion_tokens": 1,
                         "total_tokens": 1,
                         "prompt_tokens_details": {
                             "cached_tokens": 0,
                             "audio_tokens": 0
                         },
                         "completion_tokens_details": {
                             "reasoning_tokens": 0,
                             "accepted_prediction_tokens": 0,
                             "rejected_prediction_tokens": 0
                         }
                     }
                 }, indent=4, escape_forward_slashes=False), media_type="application/json")
        else:
            return Response(ujson.dumps(content, indent=4, escape_forward_slashes=False), media_type="application/json")

    def return_tool_data(self, content: Union[str, dict], model: str, tools: List[Dict[str, Any]], messages: List[Dict[str, str]] ) -> Response:
        completion_id = self.generate_completion_id()
        completion_timestamp = self.generate_timestamp()
        if isinstance(content, Response):
            return content
        if not isinstance(content, dict):
            try:
              return Response(ujson.dumps({
                "id": f"chatcmpl-{completion_id}",
                "object": "chat.completion",
                "created": completion_timestamp,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None
                        },
                        "tool_calls": tools,
                        "logprobs": None,
                        "finish_reason": "tool_calls"
                    }
                ],
                "usage": {
                    "prompt_tokens": round(len("".join(message['content'] for message in messages)) / 4),
                    "completion_tokens": round(len(content) / 4),
                    "total_tokens": round((len("".join(message['content'] for message in messages)) / 4) + (len(content) / 4)),
                    "prompt_tokens_details": {
                        "cached_tokens": round(len(str(content)) // 4),
                        "audio_tokens": 0
                    },
                    "completion_tokens_details": {
                        "reasoning_tokens": 0,
                        "accepted_prediction_tokens": 0,
                        "rejected_prediction_tokens": 0
                    }
                },
                 "system_fingerprint": self.generate_fingerprint_id()
            }, indent=4, escape_forward_slashes=False), media_type="application/json")
            except TypeError:
                return Response(ujson.dumps({
                "id": f"chatcmpl-{completion_id}",
                "object": "chat.completion",
                "created": completion_timestamp,
                "model": model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 1,
                    "prompt_tokens_details": {
                        "cached_tokens": 0,
                        "audio_tokens": 0
                    },
                    "completion_tokens_details": {
                        "reasoning_tokens": 0,
                        "accepted_prediction_tokens": 0,
                        "rejected_prediction_tokens": 0
                    }
                }
            }, indent=4, escape_forward_slashes=False), media_type="application/json")
        else:
           return Response(ujson.dumps(content, indent=4, escape_forward_slashes=False), media_type="application/json")

# instance of the helper class
response_generator = ResponseGenerator()

# --- Backwards Compatible Functions --- because im lazy UwU
def generate_completion_id():
  return response_generator.generate_completion_id()

def generate_fingerprint_id():
  return response_generator.generate_fingerprint_id()

def generate_timestamp():
    return response_generator.generate_timestamp()

def generate_call_id():
    return response_generator.generate_call_id()

async def update_token_usage_stream(data: list, model: str, key: str):
  await response_generator.update_token_usage_stream(data, model, key)

async def stream_response_iterator_str(message: str, model: str, key: str):
    async for chunk in response_generator.stream_response_iterator_str(message, model, key):
        yield chunk

# deprecated, use stream_response_iterator_str / stream_response_iterator_str_generator instead
async def stream_response_iterator(message, model: str, key: str, start_time: float, user: str):
    content_history: list = []

    try:
        if isinstance(message, dict):
            yield f"data: {ujson.dumps(message)}\n\n"
            try:
                content_history.append(message['choices'][0]['delta']['content'])
            except Exception as e:
                print(e)
                pass
        else:
            async for chunk in message:
                try:
                    chunk = chunk.model_dump_json()
                except AttributeError:
                    chunk = chunk

                if chunk is not None and chunk != "":
                    yield f"data: {chunk}\n\n"

                try:
                    data = str(ujson.loads(chunk)['choices'][0]['delta']['content'])
                    if data is not None and data != "None":
                        content_history.append(data)
                except:
                    pass
    except Exception as e:
        async for error_chunk in response_generator.stream_error_response(str(e)):
            yield error_chunk
    finally:
        yield response_generator.create_final_response(model)
        yield "data: [DONE]"
        await response_generator.update_token_usage_stream(content_history, model, key)
        await print_status(True, round(time.time() - start_time, 2), model, user, ''.join(content_history))

async def stream_response_iterator_str_generator(
    message: AsyncIterator[str],
    model: str,
    key: str,
    start_time: float,
    user: str
) -> AsyncIterator[str]:
    async for chunk in response_generator.stream_response_iterator_str_generator(message, model, key, start_time, user):
        yield chunk

async def stream_response_iterator_tool(
    tool_call_data: List[Dict[str, Any]],
    model: str,
    key: str,
    start_time: float,
    user: str
) -> AsyncIterator[str]:
     async for chunk in response_generator.stream_response_iterator_tool(tool_call_data, model, key, start_time, user):
         yield chunk

async def stream_error_response(error: str) -> AsyncIterator[str]:
    yield await response_generator.create_error_response(error)

def create_initial_response(model: str) -> str:
    return response_generator.create_initial_response(model)

def create_content_chunk(content: str, model: str) -> str:
    return response_generator.create_content_chunk(content, model)

async def create_error_response(error: str) -> str:
    return await response_generator.create_error_response(error)

def create_final_response(model: str) -> str:
    return response_generator.create_final_response(model)

def return_data(content, model, messages):
   return response_generator.return_data(content, model, messages)

def return_tool_data(content, model, tools, messages):
   return response_generator.return_tool_data(content, model, tools, messages)