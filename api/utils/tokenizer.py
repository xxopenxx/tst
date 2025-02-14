import tiktoken
from typing import List, Dict

encoding = tiktoken.get_encoding("cl100k_base")

def input_count_schema(input: List[Dict[str, str]] | str) -> int:
    """
    Calculates the total input count across all messages in the list.
    
    Args:
        messages (List[Dict[str, str]]): list of messages
        
    Returns:
        int: total token count
    """
    if isinstance(input, str):
        return len(encoding.encode(input))
    elif isinstance(input, list):
        return sum(len(encoding.encode(message.get("content", ""))) for message in input if isinstance(message.get('content', ''), str))


async def get_input_count(messages: List[Dict[str, str]]) -> int:
    """
    Calculates the total input count across all messages in the list.
    
    Args:
        messages (List[Dict[str, str]]): list of messages
        
    Returns:
        int: total token count
    """
    try:
        return sum(len(encoding.encode(message.get("content", ""))) for message in messages if isinstance(message.get('content', ''), str))
    except:
        print(messages)
        return 0
async def get_output_count(message: str) -> int:
    """
    Gets the token count of the output of the model
    
    Args:
        message (str): the output from the model
        
    Returns:
        int: total token count
    """
    return len(encoding.encode(message)) if isinstance(message, str) else 0
    
if __name__ == '__main__':
    messages = [
    {"content": "Hello, how are you?"},
    {"content": "I am fine, thank you!"},
    {"content": "What about you?"}
]

    print(get_input_count(messages))
    print(get_output_count('hello world'))
