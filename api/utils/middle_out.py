from typing import List, Dict, TypeVar, Generic
import tiktoken
from dataclasses import dataclass
import numpy as np

encoding = tiktoken.get_encoding("cl100k_base")
T = TypeVar('T', str, Dict[str, str])


@dataclass
class CompressionResult(Generic[T]):
    messages: List[T]
    tokens_removed: int
    compression_ratio: float

class CompressorUtils:
    @staticmethod
    def count_tokens(text: str, encoding) -> int:
        return len(encoding.encode(text))
    
    @staticmethod
    def get_message_tokens(message: Dict[str, str], encoding) -> int:
        if not isinstance(message, dict) or 'content' not in message:
            return 0
        return CompressorUtils.count_tokens(message['content'], encoding)

    @staticmethod
    def calculate_compression_ratios(num_messages: int) -> List[float]:
        if num_messages <= 2:
            return [1.0] * num_messages
        
        x = np.linspace(-2, 2, num_messages)
        base_curve = 1 - (np.exp(-(x ** 2) / 2))
        
        intensity = min(0.7, 0.3 + (num_messages / 50))
        ratios = 1 - (base_curve * intensity)
        
        ratios[0] = min(1.0, ratios[0] + 0.2)
        ratios[-1] = min(1.0, ratios[-1] + 0.2)
        
        return ratios.tolist()

    @staticmethod
    def compress_single_message(message: Dict[str, str], ratio: float, encoding) -> Dict[str, str]:
        if not isinstance(message, dict) or 'content' not in message:
            return message
            
        content = message['content']
        tokens = encoding.encode(content)
        target_tokens = max(1, int(len(tokens) * ratio))
        
        if len(tokens) <= target_tokens:
            return message
            
        if ratio > 0.5:
            half_tokens = target_tokens // 2
            kept_tokens = tokens[:half_tokens] + [encoding.encode("...")[0]] + tokens[-half_tokens:]
        else:
            kept_tokens = tokens[:target_tokens-1] + [encoding.encode("...")[0]]
        
        return {**message, 'content': encoding.decode(kept_tokens)}

def compress_messages(messages: List[Dict[str, str]], max_tokens: int = 8192) -> CompressionResult[Dict[str, str]]:
    total_tokens: int = sum(CompressorUtils.get_message_tokens(msg, encoding) for msg in messages)
    
    if total_tokens <= max_tokens:
        return CompressionResult(
            messages=messages,
            tokens_removed=0,
            compression_ratio=1.0
        )
    
    compression_ratios = CompressorUtils.calculate_compression_ratios(len(messages))
    compressed_messages = []
    for index, msg in enumerate(messages):
        ratio = compression_ratios[index]
        compressed_msg = CompressorUtils.compress_single_message(msg, ratio, encoding)
        compressed_messages.append(compressed_msg)
    
    final_tokens = sum(CompressorUtils.get_message_tokens(msg, encoding) for msg in compressed_messages)
    
    while final_tokens > max_tokens:
        compression_ratios = [max(ratio * 0.9, 0.1) for ratio in compression_ratios]
        compressed_messages = [
            CompressorUtils.compress_single_message(msg, compression_ratios[index], encoding)
            for index, msg in enumerate(messages)
        ]
        final_tokens = sum(CompressorUtils.get_message_tokens(msg, encoding) for msg in compressed_messages)
    
    tokens_removed = total_tokens - final_tokens
    compression_ratio = final_tokens / total_tokens
    
    return CompressionResult(
        messages=compressed_messages,
        tokens_removed=tokens_removed,
        compression_ratio=compression_ratio
    )

def test_compress_messages():
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you for asking. How can I assist you today?"},
        {"role": "user", "content": "Can you explain the concept of machine learning in simple terms?"},
        {"role": "assistant", "content": "Certainly! Machine learning is a branch of artificial intelligence that focuses on creating systems that can learn and improve from experience without being explicitly programmed. It's like teaching a computer to recognize patterns and make decisions based on data, similar to how humans learn from experience."},
    ]

    result = compress_messages(messages, 30) # messages, max tokens
    
    print(result)

test_compress_messages()