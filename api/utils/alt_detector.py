from alt_detection import alt_message_checker
from api.types import SubscriptionType

IDS_IP: dict[str, dict[str, str]] = {}

class AltDetector():
    def __init__(self, api_key: str, subscription_type: SubscriptionType, ip: str, user_id: str = None):
        self.paidL: bool = subscription_type.paid
        self.api_key: str = api_key
        self.user_id: str = user_id
        self.ip: str = ip
    
    def check(self) -> bool:
        """Returns true if user is detected as an alt account"""
