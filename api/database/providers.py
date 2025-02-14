from bson.json_util import dumps, loads
import ujson
from datetime import date
from typing import Optional

from .db_config import db

class ProviderManager:
    @staticmethod
    async def __load_db__():
        try:
            data = await db.providers.find_one({})
            return ujson.loads(dumps(data)) if data else {}
        except:
            return {}

    @staticmethod
    async def __save_db__(data: dict):
        try:
            if data:
                await db.providers.update_one({}, {"$set": loads(dumps(data))}, upsert=True)
        except Exception as e:
            print(f"Error saving provider database: {e}")

    @staticmethod
    async def update_provider_usage(provider: str) -> bool:
        """
        Updates the usage count for a provider for the current date.
        Increments the usage by 1.
        
        Args:
            provider: The name of the provider to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            current_date = date.today().isoformat()
            data = await ProviderManager.__load_db__()
            
            if provider not in data:
                data[provider] = {}
            
            if current_date not in data[provider]:
                data[provider][current_date] = 0
                
            data[provider][current_date] += 1
            
            await ProviderManager.__save_db__(data)
            return True
        except Exception as e:
            print(f"Error updating provider usage: {e}")
            return False

    @staticmethod
    async def get_provider_usage_today(provider: str) -> Optional[int]:
        """
        Gets the usage count for a provider for the current date.
        
        Args:
            provider: The name of the provider to check
            
        Returns:
            Optional[int]: The usage count for today, or None if not found
        """
        try:
            current_date = date.today().isoformat()
            data = await ProviderManager.__load_db__()
            
            if provider in data and current_date in data[provider]:
                return data[provider][current_date]
            return 0
        except Exception as e:
            print(f"Error getting provider usage: {e}")
            return None