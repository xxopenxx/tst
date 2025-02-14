from openai import AsyncClient
import profanity_check
import aiocache

from api.utils.helpers import stringify_messages
from api.config import config

rp_websites = [
    "https://venus.chub.ai/",
    "https://www.janitorai.com/",
    "https://janitorai.chat/",
    "https://janitorai.pro/",
    "https://risuai.xyz/",
    "https://venuschat.ai/",
    "https://venuschat.ai",
    "https://risuai.xyz",
    "https://janitorai.chat",
    "https://janitorai.pro",
    "https://venus.chub.ai",
    "https://www.janitorai.com",
    "https://agnai.chat"
]

@aiocache.cached(ttl=180)
async def moderation(inp, origin):
    try:
        if isinstance(inp, str):
            return await check_nsfw(inp, origin)
        else:
            inp = await stringify_messages(inp)
            return await check_nsfw(inp, origin)
    except:
        return False

async def check_nsfw(inp, origin):
    try:
        if origin in rp_websites:
            return True
        else:
            check = profanity_check.predict([inp.lower()])[0]
            return True if check else False
    except:
        return False


OPENAI_CLIENT: AsyncClient = AsyncClient(api_key=config.openai_moderations_api_key)
MODELS_SCORES: dict[str, dict[str, float]] = {
    "o1-preview": {
        "harassment": 0.2,
        "harassment_threatening": 0.1,
        "hate": 0.2,
        "hate_threatening": 0.1,
        "illicit": 0.2,
        "illicit_violent": 0.1,
        "self_harm": 0.15,
        "self_harm_instructions": 0.1,
        "self_harm_intent": 0.1,
        "sexual": 0.15,
        "sexual_minors": 0.05,
        "violence": 0.2,
        "violence_graphic": 0.1
    },
    "o1-mini": {
        "harassment": 0.2,
        "harassment_threatening": 0.1,
        "hate": 0.2,
        "hate_threatening": 0.1,
        "illicit": 0.2,
        "illicit_violent": 0.1,
        "self_harm": 0.15,
        "self_harm_instructions": 0.1,
        "self_harm_intent": 0.1,
        "sexual": 0.15,
        "sexual_minors": 0.05,
        "violence": 0.2,
        "violence_graphic": 0.1
    },
    "claude-3.5-sonnet": {
        "harassment": 0.3,
        "harassment_threatening": 0.2,
        "hate": 0.3,
        "hate_threatening": 0.2,
        "illicit": 0.3,
        "illicit_violent": 0.2,
        "self_harm": 0.25,
        "self_harm_instructions": 0.2,
        "self_harm_intent": 0.2,
        "sexual_minors": 0.1,
        "violence": 0.3,
        "violence_graphic": 0.2
    },
    "claude-3-opus": {
        "harassment": 0.3,
        "harassment_threatening": 0.2,
        "hate": 0.3,
        "hate_threatening": 0.2,
        "illicit": 0.3,
        "illicit_violent": 0.2,
        "self_harm": 0.25,
        "self_harm_instructions": 0.2,
        "self_harm_intent": 0.2,
        "sexual": 0.25,
        "sexual_minors": 0.1,
        "violence": 0.3,
        "violence_graphic": 0.2
    },
    "claude-3-sonnet": {
        "harassment": 0.3,
        "harassment_threatening": 0.2,
        "hate": 0.3,
        "hate_threatening": 0.2,
        "illicit": 0.3,
        "illicit_violent": 0.2,
        "self_harm": 0.25,
        "self_harm_instructions": 0.2,
        "self_harm_intent": 0.2,
        "sexual": 0.25,
        "sexual_minors": 0.1,
        "violence": 0.3,
        "violence_graphic": 0.2
    },
    "claude-3-haiku": {
        "harassment": 0.3,
        "harassment_threatening": 0.2,
        "hate": 0.3,
        "hate_threatening": 0.2,
        "illicit": 0.3,
        "illicit_violent": 0.2,
        "self_harm": 0.25,
        "self_harm_instructions": 0.2,
        "self_harm_intent": 0.2,
        "sexual": 0.25,
        "sexual_minors": 0.1,
        "violence": 0.3,
        "violence_graphic": 0.2
    },
    "gpt-4o": {
        "harassment": 0.4,
        "harassment_threatening": 0.3,
        "hate": 0.4,
        "hate_threatening": 0.3,
        "illicit": 0.4,
        "illicit_violent": 0.3,
        "self_harm": 0.35,
        "self_harm_instructions": 0.3,
        "self_harm_intent": 0.3,
        "sexual": 0.35,
        "sexual_minors": 0.2,
        "violence": 0.4,
        "violence_graphic": 0.3
    },
    "gemini": {
        "harassment": 0.8,
        "harassment_threatening": 0.8,
        "hate": 0.7,
        "hate_threatening": 0.5,
        "illicit": 0.6,
        "illicit_violent": 0.5,
        "self_harm": 0.55,
        "self_harm_instructions": 0.5,
        "self_harm_intent": 0.5,
        "sexual": 0.55,
        "sexual_minors": 0.3,
        "violence": 0.6,
        "violence_graphic": 0.5
    }
}

default_scores: dict[str, float] = {
    "harassment": 0.8,
    "harassment_threatening": 0.8,
    "hate": 0.65,
    "hate_threatening": 0.6,
    "illicit": 0.65,
    "illicit_violent": 0.6,
    "self_harm": 0.6,
    "self_harm_instructions": 0.55,
    "self_harm_intent": 0.55,
    "sexual": 0.3, # rp
    "sexual_minors": 0.2, # minors
    "violence": 0.65,
    "violence_graphic": 0.6
}

async def openai_moderation(model: str, messages: list[dict[str, str]], premium: bool) -> tuple[bool, str | None]:
    """Returns boolean if request should be blocked."""
    if "gemini" in model.lower():
        model = "gemini"
        
    prompt: str = await stringify_messages(messages)
    model_scores = MODELS_SCORES.get(model, {k: v * 0.85 for k, v in default_scores.items()} if not premium else default_scores) # free users cannot exceed 0.5 for all categories
    response = await OPENAI_CLIENT.moderations.create(model="omni-moderation-latest", input=prompt, timeout=3)
    if response:
        results = response.model_dump()['results'][0]
        
        for category, score in results['category_scores'].items():
            if category in model_scores and score >= model_scores[category]:
                return True, category

    return False, None