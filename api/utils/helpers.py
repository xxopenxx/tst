from time import strftime
import random

from colorama import Fore

from api.config import config

PROXY_URL: str =   config.proxy_url
PROXY_COUNT: int = config.proxy_count

user_agents = [line.strip() for line in open("data/others/useragent.txt", 'r')]
referers = [line.strip() for line in open("data/others/referers.txt", 'r')]

def get_user_agent():
    return random.choice(user_agents)

def get_referer():
    return random.choice(referers)

async def clean_messages(old_messages: list) -> list | None:
    try:
        new_messages: list = []

        for message in old_messages:
            role = message['role']
            content = message['content']
            new_messages.append({"role": role, "content": content})
        return new_messages
    except Exception as e:
        print(e)
        return None

async def no_sys_message(messages: list) -> list | None:
    try:
        new_messages: list = []
        
        for message in messages:
            role = message['role']
            content = message['content']
            if role != "system":
                new_messages.append({"role": role, "content": content})
            elif role == 'system':
                new_messages.append({"role": "user", "content": content})
                new_messages.append({"role": "assistant", "content": 'Understood, I will follow these instructions'})
        
        return new_messages
    except:
        return None

def get_proxy():
    return PROXY_URL

def get_proxy_count() -> int:
    return PROXY_COUNT

async def stringify_messages(messages):
    try:
        return '\n'.join(f"{message['role'].capitalize()}: {message['content']}" for message in messages)
    except:
        return None