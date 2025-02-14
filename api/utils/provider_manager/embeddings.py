import importlib
import inspect
import random
import sys
import os

from api.baseproviders import EmbeddingsBaseProvider
from api.utils.logging import logger

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_dir)
provider_dir = os.path.join(base_dir, 'providers', 'embeddings')

DEBUG: bool = True
PROVIDERS = {}

try:
    with open("/tmp/api_initialized_embedding (1).flag", 'x') as _:
        logger("Loading embedding providers...")
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
                            issubclass(obj, EmbeddingsBaseProvider) and
                            obj != EmbeddingsBaseProvider):
                        provider = obj()

                        if provider.models:
                            for model in provider.models:
                                PROVIDERS[model] = provider

            except Exception as e:
                if DEBUG:
                    print(f"Error loading {module_name}: {e}")
                continue
try:
    with open("/tmp/api_initialized_embedding (2).flag", 'x') as _:
        logger(f"Loaded {len(PROVIDERS)} models with {len(set(p['obj'] for providers in PROVIDERS.values() for p in providers))} unique embedding providers!")
except:
    pass

async def handle_embeddings(data: dict):
    """Generates a OpenAI formated dictionary for a embedding response

    Args:
        data (dict): A dictionary containing the input text and model name

    Raises:
        ValueError: No sources for the model were found
    """
    providers = PROVIDERS.get(data['model'], [])

    if providers:
        provider = random.choice(providers)
        completion = await provider.generate(data.input)
        return completion
    else:
        raise ValueError(f"No sources were found for {data.model}")