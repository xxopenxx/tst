import importlib
import inspect
import random
import sys
import os

from api.baseproviders import ModerationBaseProvider
from api.utils.logging import logger
from api.config import config

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_dir)
provider_dir = os.path.join(base_dir, 'providers', 'moderation')

DEBUG: bool = config.debug
PROVIDERS = {}

try:
    with open("/tmp/api_initialized_moderation (1).flag", 'x') as _:
        logger("Loading moderation providers...")
except:
    pass

for root, _, files in os.walk(provider_dir):
    for file in files:
        if file.endswith('.py') and file != '__init__.py':
            relative_path = os.path.relpath(root, base_dir)
            module_name = os.path.join(relative_path, file[:-3]).replace(os.sep, '.')
            try:
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, ModerationBaseProvider) and 
                        obj != ModerationBaseProvider):
                        provider = obj()
                        if provider.models:
                            for model in provider.models:
                                if model not in PROVIDERS:
                                    PROVIDERS[model] = [provider]
                                else:
                                    PROVIDERS[model].append(provider)
                                                            
            except Exception as e:
                if DEBUG:
                    print(f"Error loading {module_name}: {e}")
                print(e)
                continue

try:
    logger(f"Loaded {len(PROVIDERS)} models with {len(set(p['obj'] for providers in PROVIDERS.values() for p in providers))} unique moderation providers!")
except:
    pass

async def handle_moderation(data: dict):
    """Generates a OpenAI formated dictionary for a moderation response

    Args:
        data (dict): A dictionary containing the input text and model name

    Raises:
        ValueError: No sources for the model were found
    """
    providers = PROVIDERS.get(data.model, [])
    
    if providers:
        provider = random.choice(providers)
        completion = await provider.generate(data.input, data.model)
        return completion
    else:
        raise ValueError(f"No sources were found for {data.model}")