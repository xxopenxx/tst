import importlib
import inspect
import time
import sys
import os

from api.database import ProviderManager
from api.utils.logging import logger
from api.config import config

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, base_dir)
provider_dir = os.path.join(base_dir, 'providers', 'chat')

DEBUG = config.debug
PROVIDERS = {}  # Will store {model: [{"stream": bool, "obj": provider_instance}, ...]}
ROUND_ROBIN_INDEX = {}
TIMED_OUT_PROVIDERS = {}
TIMEOUT_DURATION = 300

try:
    with open("/tmp/api_initialized_chat (1).flag", 'x') as _:
        logger("Loading chat providers...")
except:
    pass

for root, _, files in os.walk(provider_dir):
    for file in files:
        if file.endswith('.py') and file != '__init__.py':
            relative_path = os.path.relpath(root, base_dir)
            module_name = os.path.join(relative_path, file[:-3]).replace(os.sep, '.')
            if "deprecated" in module_name:
                continue
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    has_models = hasattr(obj, 'models')
                    has_generate = hasattr(obj, 'generate')
                    has_check = hasattr(obj, 'check')
                    if has_models and has_generate and has_check:
                        provider = obj()
                        working = getattr(provider, 'working', True)
                        if working:
                            provider_models = getattr(provider, 'models', [])
                            can_stream = getattr(provider, 'stream', False)
                            limit = getattr(provider, 'limit', None)
                            
                            if provider.working is False:
                                continue

                            for model in provider_models:
                                if model not in PROVIDERS:
                                    PROVIDERS[model] = []
                                    ROUND_ROBIN_INDEX[model] = 0
                                
                                provider_info = {
                                    "stream": can_stream, # whether or not the provider can stream
                                    "obj": provider, # the provider class obj
                                    "limit": limit # daily limit of requests that can be sent
                                }
                                
                                if provider_info not in PROVIDERS[model]:
                                    PROVIDERS[model].append(provider_info)

try:
    with open("/tmp/api_initialized_chat (2).flag", 'x') as _:
        logger(f"Loaded {len(PROVIDERS)} models with {len(set(p['obj'] for providers in PROVIDERS.values() for p in providers))} unique chat providers!")
except:
    pass

class Utils:
    """Utility class providing provider management."""

    @staticmethod
    async def get_next_provider(model: str, require_stream: bool = False):
        """
        Get the next available provider for a given model using round-robin selection.
        Checks usage limits and updates provider usage when applicable.

        Args:
            model: The model identifier to get a provider for
            require_stream: Whether streaming capability is required

        Returns:
            A provider instance or None if no providers are available
        """
        providers = PROVIDERS.get(model, [])
        available_providers = [
            p for p in providers 
            if not Utils.is_provider_timed_out(p["obj"]) and
            (not require_stream or p["stream"])
        ]
        
        if not available_providers:
            return None

        if model not in ROUND_ROBIN_INDEX or ROUND_ROBIN_INDEX[model] >= len(available_providers):
            ROUND_ROBIN_INDEX[model] = 0
            
        original_index = ROUND_ROBIN_INDEX[model]
        index = original_index
        
        for _ in range(len(available_providers)):
            provider_info = available_providers[index]
            provider = provider_info["obj"]
            limit = provider_info["limit"]
            
            if limit is None:
                ROUND_ROBIN_INDEX[model] = (index + 1) % len(available_providers)
                await ProviderManager.update_provider_usage(provider.__class__.__name__)
                return provider
            
            usage = await ProviderManager.get_provider_usage_today(provider.__class__.__name__)
            if usage is None:
                usage = 0
                
            if usage < limit:
                success = await ProviderManager.update_provider_usage(provider.__class__.__name__)
                if not success:
                    logger(f"Failed to update usage for provider {provider.__class__.__name__}")
                
                ROUND_ROBIN_INDEX[model] = (index + 1) % len(available_providers)
                return provider
            
            index = (index + 1) % len(available_providers)
            
            if index == original_index:
                break
        
        return None

    @staticmethod
    def is_provider_timed_out(provider) -> bool:
        """
        Check if a provider is currently timed out.
        
        Args:
            provider: The provider instance to check
            
        Returns:
            bool: True if the provider is timed out, False otherwise
        """
        if provider in TIMED_OUT_PROVIDERS:
            if time.time() > TIMED_OUT_PROVIDERS[provider]:
                del TIMED_OUT_PROVIDERS[provider]
                return False
            return True
        return False

    @staticmethod
    def timeout_provider(provider):
        """
        Mark a provider as timed out for the configured timeout duration.
        
        Args:
            provider: The provider instance to timeout
        """
        TIMED_OUT_PROVIDERS[provider] = time.time() + TIMEOUT_DURATION

    @staticmethod
    def get_provider_info(model: str, provider_obj):
        """
        Get provider info dictionary from the providers list for a given model and provider object.
        
        Args:
            model: The model identifier
            provider_obj: The provider instance to find
            
        Returns:
            dict: Provider info dictionary or None if not found
        """
        for provider_info in PROVIDERS.get(model, []):
            if provider_info["obj"] == provider_obj:
                return provider_info
        return None

async def handle_chat(data: dict, key: str, stream: bool = False):
    """
    Handle chat responses for both streaming and non-streaming requests.
    
    Args:
        data: Request data containing model and messages, can be dict or Pydantic model
        key: API key or authentication token
        stream: Whether to stream the response
    
    Returns:
        Generated response from the chosen provider or error message if no provider is available
    """
    model = data.get('model') if isinstance(data, dict) else data.model
    chosen_provider = await Utils.get_next_provider(model, require_stream=stream)
    
    if isinstance(data, dict):
        data.pop("tools", None)
    else:
        data = data.model_dump()
        data.pop("tools", None)

    if stream and not chosen_provider:
        return "No streaming provider available for the specified model."
    
    if not chosen_provider:
        chosen_provider = await Utils.get_next_provider(model, require_stream=False)
    
    while chosen_provider:
        if inspect.iscoroutinefunction(chosen_provider.check):
            check_result = await chosen_provider.check(data)
        else:
            check_result = chosen_provider.check(data)

        if check_result:
            if DEBUG:
                print(f"Using provider: {chosen_provider.__class__.__name__} for model: {model}")
                            
            return await chosen_provider.generate(
                data,
                stream,
                key
            )
        else:
            available_providers = [p["obj"] for p in PROVIDERS.get(model, [])]
            if len(available_providers) > 1:
                Utils.timeout_provider(chosen_provider)
            chosen_provider = await Utils.get_next_provider(model, require_stream=stream)

    if DEBUG:
        print(f'No provider found for {model}')
    
    return "No provider found for the specified model."