import importlib
import inspect
import random
import sys
import os

from api.utils.cdn import url_to_cdn, base64_to_cdn, data_to_cdn
from api.baseproviders import ImagesBaseProvider
from api.utils.logging import logger
from api.config import config

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_dir)
provider_dir = os.path.join(base_dir, 'providers', 'images')

DEBUG: bool = config.debug
PROVIDERS = {}

try:
    with open("/tmp/api_initialized_images (1).flag", 'x') as _:
        logger("Loading images providers...")
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
                        issubclass(obj, ImagesBaseProvider) and 
                        obj != ImagesBaseProvider):
                        provider = obj()
                                                
                        if provider.models:
                            for model in provider.models:
                                if DEBUG:
                                    print(f"Registering {name} for model: {model}")
                                if model not in PROVIDERS:
                                    PROVIDERS[model] = [provider]
                                else:
                                    PROVIDERS[model].append(provider)
            except Exception as e:
                if DEBUG:
                    print(f"Error loading {module_name}: {e}")
                continue

try:
    with open("/tmp/api_initialized_images (2).flag", 'x') as _:
        logger(f"Loaded {len(PROVIDERS)} models with {len(set(p['obj'] for providers in PROVIDERS.values() for p in providers))} unique image providers!")
except:
    pass

async def handle_images(data: dict):
    """Generates an image and returns the url to our cdn

    Args:
        data (dict): A dictionary containing the prompt and model name

    Raises:
        ValueError: No sources for the model were found
    """
    providers = PROVIDERS.get(data['model'], [])
    
    if providers:
        provider = random.choice(providers)
        response, response_type = await provider.generate(data)
        
        if response_type is None: return response
               
        if response_type == "url":
            cdn_url, status = await url_to_cdn(response)
        elif response_type == "base64":
            cdn_url, status = await base64_to_cdn(response)
        elif response_type == "data":
            cdn_url, status = await data_to_cdn(response)
    
        if status:
            return cdn_url
        else:
            raise ValueError(f"Failed to save file to the cdn.")
    else:
        raise ValueError(f"No sources were found for {data['model']}")