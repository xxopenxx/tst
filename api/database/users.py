import string
import random
from datetime import date
import ujson

from api.config import subscription_types, config
from .db_config import db

with open("data/models/list.json", 'r') as f:
    model_list = ujson.load(f)

class DatabaseManager:
    """Manages database operations for user accounts and usage."""

    @staticmethod
    async def _get_user_id(key_or_id: str) -> str | None:
        """Retrieves a user's ID (string) based on key or ID. No ObjectId conversion."""
        user = await db.usersV2.find_one({"user_id": key_or_id})
        if user:
            return user["user_id"]

        user = await db.usersV2.find_one({"keys.key": key_or_id})
        if user:
            return user["user_id"]

        user = await db.usersV2.find_one({"key": key_or_id})
        if user:
            return user.get("user_id", None)

        return None

    @staticmethod
    async def create_account(user_id: str = None) -> tuple[str]:
        """Creates a new user account. Generates a random user_id if none is provided."""
        if user_id is None:
           user_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        elif not isinstance(user_id, str):
          raise TypeError("User ID must be a string.")

        key = f"shard-{''.join(random.choices(string.ascii_letters + string.digits, k=33))}"
        user_data = {
            "key": key,
            "user_id": user_id,
            "banned": False,
            "ip": [],
            "usage": 0,
            "subscription_type": "free",
            'credit_limit': config.free.credits,
            'rate_limit': config.free.rate_limit,
            "daily_usage": {date.today().isoformat(): 0},
            "models": {},
            "keys": [{"key": key, "name": "default", "created": date.today().isoformat()}]
        }
        result = await db.usersV2.insert_one(user_data)
        return key


    @staticmethod
    async def delete_account(user_id: str) -> None:
        """Deletes a user account."""
        await db.usersV2.delete_one({"user_id": user_id})

    @staticmethod
    
    async def key_check(value: str) -> tuple[bool, str | None]:
        """Checks if an API key exists."""
        user = await db.usersV2.find_one({"keys.key": value})
        if user:
            key_data = next((k for k in user.get("keys", []) if k["key"] == value), None)
            return True, key_data["key"]
        user = await db.usersV2.find_one({"key": value})
        return bool(user), user.get('key') if user else None

    @staticmethod
    async def id_check(user_id: str) -> list[dict]:
        """Checks if a user ID exists and retrieves associated API keys."""
        user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            return user.get("keys", [])
        return []

    @staticmethod
    async def ban_check(value: str) -> bool:
        """Checks if a user is banned."""
        user = await db.usersV2.find_one({"user_id": value})
        if user:
            return user.get("banned", False)
        user_id = await DatabaseManager._get_user_id(value)  # Lookup by key if not found by user_id
        if user_id:
            user = await db.usersV2.find_one({"user_id": user_id}) #  Changed to find by user_id.
            if user: # check if user is found.
              return user.get("banned", False)
        return False

    @staticmethod
    async def update_subscription_type(value: str, subscription_type: str) -> None:
        """Updates a user's subscription type."""
        user = await db.usersV2.find_one({"user_id": value})  # Now looks up by user_id (string)
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})
        if user: # Check if user found.
          await db.usersV2.update_one({"user_id": user["user_id"]}, {"$set": {"subscription_type": subscription_type}})

    @staticmethod
    async def update_user_subscription(user_id: str, subscription_data: dict) -> None:
        """
        Updates a user's subscription details in the database.

        Args:
            user_id: The user's ID.
            subscription_data: A dictionary containing the subscription details to update.
                               This should include:
                               - stripe_customer_id: The Stripe customer ID.
                               - subscription_id: The Stripe subscription ID.
                               - subscription_status: The status of the subscription (e.g., "active", "canceled").
                               - current_period_end: (Optional) The end date of the current subscription period as a Unix timestamp.
        """
        user = await db.usersV2.find_one({"user_id": user_id})
        if not user:
            user_id = await DatabaseManager._get_user_id(user_id)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})

        if user:
            update_fields = {}
            if "stripe_customer_id" in subscription_data:
                update_fields["stripe_customer_id"] = subscription_data["stripe_customer_id"]
            if "subscription_id" in subscription_data:
                update_fields["subscription_id"] = subscription_data["subscription_id"]
            if "subscription_status" in subscription_data:
                update_fields["subscription_status"] = subscription_data["subscription_status"]
            if "current_period_end" in subscription_data:
                update_fields["current_period_end"] = subscription_data["current_period_end"]

            if update_fields:
                await db.usersV2.update_one({"user_id": user["user_id"]}, {"$set": update_fields})
                
    @staticmethod
    async def find_user_by_customer_id(customer_id: str) -> dict | None:
        """
        Finds a user by their Stripe customer ID.

        Args:
            customer_id: The Stripe customer ID.

        Returns:
            The user document (dict) if found, otherwise None.
        """
        user = await db.usersV2.find_one({"stripe_customer_id": customer_id})
        return user
                    
    @staticmethod
    async def get_subscription_type(value: str) -> str:
        """Retrieves a user's subscription type."""

        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})
        if user:
          return user.get("subscription_type", "free")
        return "free"

    @staticmethod
    async def premium_check(value: str) -> bool:
        """Deprecated. Use get_subscription_type instead."""
        return await DatabaseManager.get_subscription_type(value) != "free"

    @staticmethod
    
    async def set_custom_subscription_values(value: str, rate_limit: int, credit_limit: int) -> None:
        """Sets custom subscription values for a user."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})

        if user:
          await db.usersV2.update_one({"user_id": user["user_id"]}, {"$set": {"rate_limit": int(rate_limit), "credit_limit": int(credit_limit), "subscription_type": "custom"}})

    @staticmethod
    
    async def get_custom_subscription_values(value: str) -> tuple[int, int]:
        """Retrieves custom subscription values for a user."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})

        if user:
          return user.get('rate_limit', 0), user.get('credit_limit', 0)

        return 0, 0

    @staticmethod
    
    async def ip_check(value: str, id: str | None = None, key: str | None = None) -> bool:
        """Checks and adds an IP address for a user, limiting to 3 IPs."""

        user = None
        if id:
          user = await db.usersV2.find_one({"user_id": id})

        if user is None: # If no user ID provided or not found, try key.
            user_id = await DatabaseManager._get_user_id(key)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})

        if user:
            current_ips = user.get("ip", [])
            if isinstance(current_ips, str):
                current_ips = [current_ips]

            if len(current_ips) < 3 and value not in current_ips:
                await db.usersV2.update_one({"user_id": user["user_id"]}, {"$push": {"ip": value}})
                return True
            return value in current_ips
        
        return False



    @staticmethod
    async def add_ip(value: str, ip: str) -> bool:
        """Adds an IP address to a user's record, limiting to 3 IPs."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})

        if user:
            existing_ips = user.get("ip", [])
            if isinstance(existing_ips, str):
                existing_ips = [existing_ips]
            if ip not in existing_ips and len(existing_ips) < 3:
                await db.usersV2.update_one({"user_id": user["user_id"]}, {"$push": {"ip": ip}})
                return True
            return ip in existing_ips

        return False


    @staticmethod
    async def get_ips(value: str) -> list:
        """Gets the list of IPs associated with a user."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})

        if user:
            return user.get("ip", [])

        return []



    @staticmethod
    async def usage_update(value: str, model: str | None = None) -> None:
        """Updates the usage count for a user and optionally for a specific model."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            await db.usersV2.update_one({"user_id": user["user_id"]}, {"$inc": {"usage": 1}})
            if model:
                await db.usersV2.update_one(
                    {"user_id": user["user_id"], "models." + model: {"$exists": True}},
                    {"$inc": {"models." + model + ".usage": 1}}
                )
                await db.usersV2.update_one(
                    {"user_id": user["user_id"], "models." + model: {"$exists": False}},
                    {"$set": {"models." + model: {"usage": 1, "tokens": {"input": 0, "output": 0}}}}
                )


    @staticmethod
    async def reset_ip(value: str) -> None:
        """Resets the IP addresses associated with a user."""

        user = await db.usersV2.find_one({"user_id": value})

        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})
        if user:
          await db.usersV2.update_one({"user_id": user["user_id"]}, {"$set": {"ip": []}})


    @staticmethod
    async def add_key_to_user(user_id: str, name: str = "default", description: str = None) -> dict | None:
        """Adds a new API key to a user's account.

        Args:
            user_id: The user's ID to add the key to.
            name: The name for the new API key (default is "default").
            description: An optional description for the key.

        Returns:
            The new API key data (including the key itself, name and the creation date) or None if the user doesn't exist.
        """
        user = await db.usersV2.find_one({"user_id": user_id})

        if not user:
             user_id = await DatabaseManager._get_user_id(user_id)
             if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        
        if user:
            new_key_data = {
                "key": f"shard-{''.join(random.choices(string.ascii_letters + string.digits, k=33))}",
                "name": name,
                "created": date.today().isoformat()
            }
            if description:
              new_key_data["description"] = description
            await db.usersV2.update_one(
                {"user_id": user["user_id"]},
                {"$push": {"keys": new_key_data}}
            )
            return new_key_data
        return None

    @staticmethod
    async def reset_key(user_id: str) -> list[dict]:
        """Resets a user's API keys by removing all existing keys and adding a new one."""
        key_data = {
            "key": f"shard-{''.join(random.choices(string.ascii_letters + string.digits, k=33))}",
            "name": "default",
            "created": date.today().isoformat()
        }

        user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            await db.usersV2.update_one(
                {"user_id": user_id},
                {"$set": {"keys": [key_data]}}
            )
            return await DatabaseManager.get_keys(user_id=user_id)

        return []

    @staticmethod
    
    async def get_usage(value: str) -> int:
        """Retrieves the total usage count for a user."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
          user_id = await DatabaseManager._get_user_id(value)
          if user_id:
              user = await db.usersV2.find_one({"user_id": user_id})
        if user:
          return user.get("usage", 0)
        return 0

    @staticmethod
    
    async def get_id(value: str) -> str | None:
        """Retrieves a user's ID (the string user_id, not ObjectId) from their API key or user_id.
           Handles both new "keys" list format and old single "key" format.
        """
        user = await db.usersV2.find_one({"user_id": value})

        if user:
            return user["user_id"]

        user = await db.usersV2.find_one({"keys.key": value})
        if user:
            return user["user_id"]

        user = await db.usersV2.find_one({"key": value})  
        if user:
            return user.get("user_id", None) 

        return None
    
    @staticmethod
    async def reset_daily_usage_if_needed() -> None:
        today = date.today().isoformat()
        last_reset = await db.meta.find_one({"_id": "daily_usage_reset"})
        if last_reset and last_reset.get("date") == today:
            return
        await db.usersV2.update_many(
            {},
            {"$set": {f"daily_usage.{today}": 0}},
            upsert=False
        )
        await db.meta.update_one(
            {"_id": "daily_usage_reset"},
            {"$set": {"date": today}},
            upsert=True
        )

    @staticmethod
    async def get_daily_usage(value: str) -> tuple[int, int, int, dict]:
        """Retrieves the daily usage information for a user."""

        await DatabaseManager.reset_daily_usage_if_needed()
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            today = date.today().isoformat()
            daily_usage = user.get("daily_usage", {}).get(today, 0)
            usage = user.get("usage", 0)
            subscription_type = user.get("subscription_type", "free")
            try:
                limit = subscription_types[subscription_type]['credits'] if subscription_type != "custom" else user.get("credit_limit", 0)
            except KeyError:
                print(f"Invalid subscription type: {subscription_type} for user: {value}")
                limit = 0
            return daily_usage, usage, limit, user.get("daily_usage", {})
        return 0, 0, 0, {}

    @staticmethod
    async def update_daily_usage(value: str, model: str | None = None) -> bool:
        """Updates the daily usage count for a user."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            today = date.today().isoformat()
            cost = 1

            if model:
                model = model.lower().replace("-online", '').replace("-json", '')
                for obj in model_list['data']:
                    if obj['id'] == model:
                        cost = obj['cost']
                        break
            try:
                await db.usersV2.update_one(
                    {"user_id": user["user_id"]},
                    {"$inc": {f"daily_usage.{today}": int(cost)}}
                )
                return True
            except Exception as e:
                print(f"Error updating daily usage: {e}")
                return False
        print('Did not find user for daily usage')
        return False

    @staticmethod
    async def update_model_tokens(value: str, model: str, input_tokens: int | None = None, output_tokens: int | None = None) -> bool:
        """Updates the token usage for a specific model by a user."""

        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            update_data = {}
            if input_tokens is not None:
                update_data["$inc"] = {"models." + model + ".tokens.input": input_tokens}
            if output_tokens is not None:
                if "$inc" not in update_data:
                    update_data["$inc"] = {}
                update_data["$inc"]["models." + model + ".tokens.output"] = output_tokens

            if update_data:
                try:
                    await db.usersV2.update_one({"user_id": user["user_id"]}, update_data, upsert=True)
                    return True
                except Exception as e:
                    print(f"Error updating model tokens: {e}")
                    return False
        return False



    @staticmethod
    
    async def get_total_tokens(value: str) -> tuple[int, int]:
        """Retrieves the total input and output tokens used by a user across all models."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        if user:
          total_input = 0
          total_output = 0
          models = user.get("models", {})
          if models and isinstance(models, dict):
              for model_data in models.values():
                  if isinstance(model_data, dict) and "tokens" in model_data:
                      total_input += model_data["tokens"].get("input", 0)
                      total_output += model_data["tokens"].get("output", 0)
          return total_input, total_output
        return 0,0


        
    @staticmethod
    async def get_keys(user_id: str | None = None, value: str | None = None) -> list[dict]:
        """Retrieve all api keys associated with a user."""

        user = await db.usersV2.find_one({"user_id": user_id}) # Find by user_id if given
        if not user and value: # If not by id then by key or api key
          user_id = await DatabaseManager._get_user_id(value) # find user_id
          if user_id:
            user = await db.usersV2.find_one({"user_id": user_id}) # and now find user by user_id
        
        if user:
          return user.get("keys", [])
        return []
    
    @staticmethod
    async def delete_key_from_user(user_id: str, key: str) -> bool:
        """Deletes a specific API key from a user's account.

        Args:
            user_id: The user's ID to delete the key from.
            key: The API key to delete.

        Returns:
            True if the key was successfully deleted, False otherwise (e.g., user or key not found).
        """
        user = await db.usersV2.find_one({"user_id": user_id})
        if not user:
             user_id = await DatabaseManager._get_user_id(user_id)
             if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        
        if user:
            keys = user.get("keys", [])
            updated_keys = [k for k in keys if k.get("key") != key]
            if len(updated_keys) < len(keys):
                await db.usersV2.update_one(
                    {"user_id": user["user_id"]},
                    {"$set": {"keys": updated_keys}}
                )
                return True
        return False

    @staticmethod
    async def ban_update(value: str, banned: bool) -> None:
        """Updates a user's ban status."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        if user:
            await db.usersV2.update_one({"user_id": user["user_id"]}, {"$set": {"banned": banned}})
    
    @staticmethod
    async def update_recent_usage(value: str, model: str, input_tokens: int, output_tokens: int, action_type: str = "chat_completion", metadata: dict = None) -> None:
        """
        Updates the recent activity of a user's account with detailed usage information.

        Args:
            value (str): User ID or API key
            model (str): Model identifier used for the request
            input_tokens (int): Number of input tokens used
            output_tokens (int): Number of output tokens used
            action_type (str): Type of API action (e.g., "chat_completion", "image_generation")
            metadata (dict): Optional additional request metadata
        """
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        
        if user:
            credits_used = 1
            model_normalized = model.lower().replace("-online", "").replace("-json", "")
            for obj in model_list['data']:
                if obj['id'] == model_normalized:
                    credits_used = obj['cost']
                    break

            current_timestamp = date.today().isoformat()
            activity_entry = {
                "model": model,
                "credits": credits_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "timestamp": current_timestamp,
                "success": True
            }

            if metadata:
                activity_entry["metadata"] = metadata

            await db.usersV2.update_one(
                {"user_id": user["user_id"]},
                {
                    "$push": {
                        f"recent_activity.{action_type}": {
                            "$each": [activity_entry],
                        }
                    },
                    "$set": {
                        "last_activity_date": current_timestamp,
                        "last_model_used": model,
                    },
                    "$inc": {
                        f"model_usage_count.{model}": 1,
                    }
                },
                upsert=True
            )


    @staticmethod
    async def get_recent_activity(value: str, resource_type: str | None) -> dict:
        """Retrieve the recent requests, resource type or all."""
        user = await db.usersV2.find_one({"user_id": value})
        if not user:
            user_id = await DatabaseManager._get_user_id(value)
            if user_id:
                user = await db.usersV2.find_one({"user_id": user_id})
        
        data = {}
        
        if user:
            data = user.get("recent_activity", {})
            if resource_type:
                data = data.get(resource_type, [])
        
        return data