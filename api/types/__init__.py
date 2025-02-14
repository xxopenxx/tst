from dataclasses import dataclass, field
from typing import ClassVar, List, Optional, Dict, Union, Literal
import yaml

@dataclass
class ImageGeneration:
    model: str
    response_type: str
    SUPPORTED_RESPONSE_TYPES: ClassVar[List[str]] = ["data", "base64", "url"]

    def is_supported_response_type(self) -> bool:
        return self.response_type in self.SUPPORTED_RESPONSE_TYPES

@dataclass
class SubscriptionType:
    subscription: str
    
    @property
    def paid(self) -> bool:
        return self.subscription != "free"

__all__ = [
    "ImageGeneration",
    "SubscriptionType",
]