from bson.json_util import dumps, loads
import ujson

from typing import Dict, List

from .db_config import db

class ModelManager:
    @staticmethod
    async def __load_db__():
        try:
            data = await db.other.find_one({})
            return ujson.loads(dumps(data)) if data else {}
        except:
            return {}
    
    @staticmethod
    async def __save_db__(data: dict):
        try:
            if data:
                update_data = {k: v for k, v in data.items() if k != '_id'}
                await db.other.update_one({}, {"$set": loads(dumps(update_data))}, upsert=True)
        except Exception as e:
            print(f"Error saving other database: {e}")
    
    @staticmethod
    async def get_value(value: str) -> dict | list | None:
        """Returns data from the category 

        Args:
            value (str): category to get data of

        Returns:
            dict | list | None: returns that data, or None
        """
        
        data = await ModelManager.__load_db__()
        
        if data[value]:
            return data[value]
        else:
            return None

