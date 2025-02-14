from fastapi import Request, APIRouter, HTTPException
from fastapi.responses import JSONResponse
import stripe
import ujson
import yaml

from api.utils.logging import stripe_logging
from api.database import DatabaseManager
from api.schemas import (
    StripeCheckoutSession,
    StripeSubscription,
    stripe_plans,
    StripeEvent
)

class StripeWebhookHandler:
    def __init__(self, api_key, endpoint_secret):
        stripe.api_key = api_key
        self.endpoint_secret = endpoint_secret
        self.router = APIRouter()
        self.router.add_api_route("/v1/stripe/webhook", self.webhook_handler, methods=["POST"])

    async def handle_checkout_session_completed(self, session: StripeCheckoutSession):
        """Handles the checkout.session.completed event."""
        customer_id = session.customer
        subscription_id = session.subscription
        user_id = session.metadata.get("userId") or session.client_reference_id

        if not user_id:
            return

        user = await DatabaseManager.id_check(user_id)
        if not user:
            return

        try:
            subscription_details = stripe.Subscription.retrieve(subscription_id)
            subscription_plan = subscription_details.plan.id if subscription_details.plan else "N/A"
            subscription_status = subscription_details.status
        except stripe.error.StripeError as e:
            await stripe_logging("checkout.session.completed", "failure", error=str(e))
            return

        plan = None
        
        if subscription_plan == stripe_plans.basic.prod_price_id or subscription_plan == stripe_plans.basic.test_price_id:
            plan = "Basic"
            await DatabaseManager.update_subscription_type(user_id, "basic")
        elif subscription_plan == stripe_plans.premium.prod_price_id or subscription_plan == stripe_plans.premium.test_price_id:
            plan = "Premium"
            await DatabaseManager.update_subscription_type(user_id, "premium")
        else:
            await DatabaseManager.update_subscription_type(user_id, "custom")

        await DatabaseManager.update_user_subscription(
            user_id,
            {
                "stripe_customer_id": customer_id,
                "subscription_id": subscription_id,
                "subscription_status": subscription_status,
            }
        )

        await stripe_logging(
            "checkout.session.completed",
            "success",
            {
                "user_id": user_id,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "subscription_status": subscription_status,
                "type": plan
            }
        )

    async def retrieve_subscription_details(self, subscription_id: str) -> StripeSubscription:
        """Retrieves subscription details from Stripe."""
        try:
            subscription_data = stripe.Subscription.retrieve(subscription_id)
            subscription_dict = subscription_data.to_dict()
            subscription = StripeSubscription(**subscription_dict)
            return subscription
        except stripe.error.StripeError as e:
            await stripe_logging("retrieve_subscription_details", "failure", error=str(e))
            raise HTTPException(status_code=500, detail="Error retrieving subscription details")
        except Exception as e:
            await stripe_logging("retrieve_subscription_details", "failure", error=str(e))
            raise HTTPException(status_code=500, detail="Error parsing subscription data")

    async def handle_subscription_update(self, subscription: StripeSubscription):
        """Handles customer.subscription.updated and customer.subscription.deleted events."""
        customer_id = subscription.customer
        subscription_id = subscription.id
        status = subscription.status
        current_period_end = subscription.current_period_end
        subscription_plan = subscription.id

        user = await DatabaseManager.find_user_by_customer_id(customer_id)

        if user:
            user_id = user["_id"]
            plan = None
            if subscription_plan == stripe_plans.basic.prod_price_id or subscription_plan == stripe_plans.basic.test_price_id:
                plan = "Basic"
                await DatabaseManager.update_subscription_type(user_id, "basic")
            elif subscription_plan == stripe_plans.premium.prod_price_id or subscription_plan == stripe_plans.premium.test_price_id:
                plan = "Premium"
                await DatabaseManager.update_subscription_type(user_id, "premium")
            else:
                await DatabaseManager.update_subscription_type(user_id, "custom")

            await DatabaseManager.update_user_subscription(
                user_id,
                {
                    "subscription_id": subscription_id,
                    "subscription_status": status,
                    "current_period_end": current_period_end,
                }
            )

            log_details = {
                "user_id": user_id,
                "customer_id": customer_id,
                "subscription_id": subscription_id,
                "subscription_status": status,
                "current_period_end": current_period_end,
                "type": plan
            }

            if status == "canceled" or status == "unpaid":
                await DatabaseManager.update_subscription_type(user_id, "free")
                log_details["subscription_plan"] = "free"

            await stripe_logging(
                f"customer.subscription.{'deleted' if status == 'canceled' else 'updated'}",
                "success",
                log_details
            )

        else:
            await stripe_logging(
                f"customer.subscription.{'deleted' if status == 'canceled' else 'updated'}",
                "failure",
                error=f"User not found for customer ID: {customer_id}"
            )

    async def webhook_handler(self, request: Request):
        """
        Handles Stripe webhook events.
        """
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.endpoint_secret
            )
        except ValueError as e:
            await stripe_logging("webhook_handler", "failure", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            await stripe_logging("webhook_handler", "failure", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid signature")

        try:
            event = StripeEvent(**ujson.loads(payload.decode()))
        except Exception as e:
            await stripe_logging("webhook_handler", "failure", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid event data")

        if event.type == 'checkout.session.completed':
            session = StripeCheckoutSession(**event.data.object)
            await self.handle_checkout_session_completed(session)

        elif event.type.startswith('customer.subscription.'):
            subscription_id = event.data.object['id']
            subscription = await self.retrieve_subscription_details(subscription_id)
            await self.handle_subscription_update(subscription)
        else:
            await stripe_logging("webhook_handler", "info", details=f"Unhandled event type: {event.type}")

        return JSONResponse(content={"success": True}, status_code=200)

with open('secrets/stripe.yml', 'r') as f:
    secrets = yaml.safe_load(f)

handler = StripeWebhookHandler(secrets['secret_key'], secrets['webhook_secret'])
app = handler.router