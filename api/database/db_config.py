# api/database/db_config.py
import yaml
from motor.motor_asyncio import AsyncIOMotorClient

with open("secrets/values.yml") as f:
    config = yaml.safe_load(f)['mongodb']

client = AsyncIOMotorClient(config['uri'])
db = client[config['database']]