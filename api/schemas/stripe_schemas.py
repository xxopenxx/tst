from typing import Optional, Dict, Any, List, Literal
from dataclasses import dataclass

from pydantic import BaseModel, Field
import yaml

class StripeSubscriptionItemPrice(BaseModel):
    id: str
    product: str
    type: str
    currency: str
    recurring: Dict[str, Any]
    unit_amount: int

class StripeSubscriptionItem(BaseModel):
    id: str
    price: Optional[StripeSubscriptionItemPrice] = None
    quantity: int
    object: str

class StripeSubscriptionItemList(BaseModel):
    object: str
    data: List[StripeSubscriptionItem]
    has_more: bool
    total_count: int
    url: str

class StripeSubscription(BaseModel):
    id: str
    customer: str
    status: str
    items: StripeSubscriptionItemList
    current_period_end: int
    object: str = Field(..., alias="object")

class StripeCheckoutSession(BaseModel):
    id: str
    customer: str
    subscription: Optional[str] = None
    metadata: Dict[str, str] = {}
    client_reference_id: Optional[str] = None
    object: str

class StripeEventData(BaseModel):
    object: Dict[str, Any]

class StripeEvent(BaseModel):
    id: str
    type: str
    data: StripeEventData
    object: str
    
@dataclass
class PriceID:
    test: str
    prod: str

@dataclass
class Plan:
    price: str
    price_id: Optional[PriceID] = None
    
    @property
    def test_price_id(self) -> Optional[str]:
        return self.price_id.test if self.price_id else None
    
    @property
    def prod_price_id(self) -> Optional[str]:
        return self.price_id.prod if self.price_id else None

PlanType = Literal["free", "basic", "premium", "enterprise"]

class StripePlans:
    free: Plan
    basic: Plan
    premium: Plan
    enterprise: Plan

    def __init__(self) -> None:
        with open("secrets/stripe.yml", "r") as file:
            config = yaml.safe_load(file)
            
        for plan_name, plan_data in config['plans'].items():
            price_id = None
            if 'test' in plan_data and 'prod' in plan_data:
                price_id = PriceID(
                    test=plan_data['test']['priceId'],
                    prod=plan_data['prod']['priceId']
                )
            
            setattr(self.__class__, plan_name, Plan(
                price=plan_data['price'],
                price_id=price_id
            ))

stripe_plans = StripePlans()