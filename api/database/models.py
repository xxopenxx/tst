from bson.json_util import dumps, loads
import ujson
import traceback

from typing import Dict, List

from .db_config import db

class ModelManager:
    @staticmethod
    async def __load_db__():
        try:
            data = await db.models.find_one({})
            return ujson.loads(dumps(data)) if data else {}
        except Exception as e:
            traceback.print_exc()
            print(e)
            return {}
        
    @staticmethod
    async def __save_db__(data: dict):
        try:
            if data:
                update_data = {k: v for k, v in data.items() if k != '_id'}
                await db.models.update_one({}, {"$set": loads(dumps(update_data))}, upsert=True)
        except Exception as e:
            print(f"Error saving model database: {e}")
    
    @staticmethod
    async def get_list(value: str) -> List | Dict | None:
        """Get model list, accepted values: list, speechify, elevenlabs

        Args:
            value (str): model list type

        Returns:
            list | dict | none: returns that model list if found.
        """
        try:
            data = await ModelManager.__load_db__()
            return data['models'].get(value, None)
        except Exception as e:
            traceback.print_exc()
            print(e)
            return None
        
    @staticmethod
    async def get_model_usages() -> Dict[str, int]:
        """Get the usage of all models

        Returns:
            Dict[str, int]: Returns a dictionary of all model names and their usage
        """
        try:
            data = await ModelManager.__load_db__()
            return {model: info['usage'] for model, info in data.get('usage', {}).items()}
        except Exception as e:
            traceback.print_exc()
            print(e)
            return {}
    
    @staticmethod
    async def update_model_usage(model: str, user: str) -> bool:
        """Update the usage of a model"""
        try:
            data = await ModelManager.__load_db__()
            if 'usage' not in data:
                data['usage'] = {}
            if model not in data['usage']:
                data['usage'][model] = {'usage': 1, 'users': {user: 1}}
            else:
                if 'usage' not in data['usage'][model]:
                    data['usage'][model]['usage'] = 0
                data['usage'][model]['usage'] += 1
                if 'users' not in data['usage'][model]:
                    data['usage'][model]['users'] = {}
                if user not in data['usage'][model]['users']:
                    data['usage'][model]['users'][user] = 1
                else:
                    data['usage'][model]['users'][user] += 1
            return await ModelManager.__save_db__(data)
        except Exception as e:
            traceback.print_exc()
            print(e)
            return False
    
    @staticmethod
    async def update_model_tokens(model: str, input_tokens: int = None, output_tokens: int = None) -> bool:
        """update the total input and output tokens for a model
        

        Args:
            model (str): the models name
            input_tokens (int): total input tokens
            output_tokens (int): total output tokens

        Returns:
            bool: whether or not the update was successful
        """
        try:
            data = await ModelManager.__load_db__()
            if 'usage' not in data:
                data['usage'] = {}
            if model not in data['usage']:
                data['usage'][model] = {}
            
            if 'tokens' not in data['usage'][model]:
                data['usage'][model]['tokens'] = {'input': 0, 'output': 0}
            
            if input_tokens is not None:
                data['usage'][model]['tokens']['input'] += input_tokens
            if output_tokens is not None:
                data['usage'][model]['tokens']['output'] += output_tokens
            
            return await ModelManager.__save_db__(data)
        except Exception as e:
            traceback.print_exc()
            print(e)
            return False
