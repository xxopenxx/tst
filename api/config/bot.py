from dataclasses import dataclass
from typing import List, Dict, Any, Iterator, Literal, TypedDict, Union

import yaml

@dataclass
class BotData:
    token: str
    banner_url: str
    pfp_url: str
    pfp_transparent_url: str

with open("secrets/bot.yml", 'r') as file:
    bot_data = yaml.safe_load(file)

bot_data = BotData(**bot_data)