# api/config/__init__.py
from api.config.config import Config, load_config
from api.config.bot import bot_data

config: Config = load_config()

subscription_types: dict[str, dict[str, str | int | bool]] = {
    tier.name: {'credits': tier.credits, 'rate_limit': tier.rate_limit} for tier in config.tiers.values()
}

__all__ = ["config", "Config", "bot_data"]