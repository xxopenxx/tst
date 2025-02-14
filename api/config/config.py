from dataclasses import dataclass
from typing import List, Dict, Any, Iterator, Literal, TypedDict, Union

import yaml

TierName = Literal['free', 'basic', 'premium', 'custom']

class TierDict(TypedDict):
    """Tier dict dataclass"""
    name: TierName
    price: int
    credits: int
    rate_limit: int
    premium: bool

class ConfigDict(TypedDict, total=False):
    "Config dict with optional debug field dataclass"
    debug: bool
    tiers: List[TierDict]
    api_version: str
    environment: str

@dataclass
class TierSettings:
    """Dataclass for each tier with explicit types"""
    name: TierName
    price: int
    credits: int
    rate_limit: int
    premium: bool

@dataclass
class Config:
    """Dataclass holding all configuration data with explicit tier types"""
    debug: bool
    proxy_url: str
    proxy_count: int
    stripe_webhook_url: str
    discord_webhook_url: str
    openai_moderations_api_key: str 
    
    _tiers: Dict[TierName, TierSettings]
    _config: Dict[str, Any]
    
    def __init__(self, tier_list: List[TierSettings], config: Dict[str, Any]):
        self._tiers = {tier.name: tier for tier in tier_list}
        self._config = config
        self.debug = config.get('debug', False)
    
    @property
    def tiers(self) -> Dict[TierName, TierSettings]:
        """Access all tiers as a dictionary"""
        return self._tiers
    
    @property
    def free(self) -> TierSettings:
        """Access free tier settings"""
        return self._tiers['free']
    
    @property
    def basic(self) -> TierSettings:
        """Access basic tier settings"""
        return self._tiers['basic']
    
    @property
    def premium(self) -> TierSettings:
        """Access premium tier settings"""
        return self._tiers['premium']
    
    @property
    def custom(self) -> TierSettings:
        """Access custom tier settings"""
        return self._tiers['custom']
    
    def __iter__(self) -> Iterator[TierSettings]:
        """Allow iterating over all tiers"""
        return iter(self._tiers.values())
    
    def __getattr__(self, name: str) -> Any:
        if name in self._tiers:
            return self._tiers[name]
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"No attribute named '{name}'")

def load_config(config_file: str = "secrets/config.yml") -> Config:
    """Load configuration from YAML file"""
    with open(config_file, 'r') as file:
        config_data: ConfigDict = yaml.safe_load(file)
        tier_list = [TierSettings(**tier) for tier in config_data['tiers']]
        config_without_tiers = {k: v for k, v in config_data.items() if k != 'tiers'}
        return Config(tier_list, config_without_tiers)