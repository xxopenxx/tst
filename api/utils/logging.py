# logging.py
from datetime import datetime
from time import strftime
import traceback
import hashlib
import time
import os

from colorama import Fore
import aiohttp
import ujson

from api.config import config

WEBHOOK_URL: str = config.discord_webhook_url
STRIPE_WEBHOOK_URL: str = config.stripe_webhook_url

def generate_trace_id(exception: Exception) -> str:
    """Generates a short trace ID based on the exception type and message."""
    error_signature = f"{type(exception).__name__}:{str(exception)}"
    hashed_signature = hashlib.sha256(error_signature.encode()).hexdigest()
    return hashed_signature[:10]

async def log_and_return_error_id(
    e: Exception,
    user: str | None = None,
    model: str | None = None,
    subscription_type: str | None = None,
    premium: bool | None = None,
    request_headers: dict | None = None,
    input_data: dict | None = None,
    start_time: float | None = None
) -> str:
    """Logs the traceback of an error and optionally other provided information to a file. Returns the trace ID."""
    trace_id = generate_trace_id(e)
    logs_dir = "logs/errors"
    os.makedirs(logs_dir, exist_ok=True)
    filename = f"{model}_{trace_id}.txt"  # Simplified filename
    filepath = os.path.join(logs_dir, filename)

    if not os.path.exists(filepath):
        with open(filepath, "w") as log_file:
            log_file.write(f"Trace ID: {trace_id}\n")
            log_file.write("Traceback:\n")
            traceback.print_exc(file=log_file)
            log_file.write("\n--------------------\n")
            log_file.write(f"Timestamp: {datetime.now().isoformat()}\n")
            if user is not None:
                log_file.write(f"User: {user}\n")
            if model is not None:
                log_file.write(f"Model: {model}\n")
            if subscription_type is not None:
                log_file.write(f"Subscription Type: {subscription_type}\n")
            if premium is not None:
                log_file.write(f"Premium User: {premium}\n")
            if request_headers is not None:
                log_file.write(f"Request Headers: {request_headers}\n")
            if input_data is not None:
                log_file.write(f"Input Data: {ujson.dumps(input_data, indent=4)}\n")
            log_file.write(f"Error Type: {type(e).__name__}\n")
            log_file.write(f"Error Message: {str(e)}\n")
            if start_time is not None:
                log_file.write(f"Time Elapsed: {round(time.time() - start_time, 2)} seconds\n")
            log_file.close()

        truncated_filename = filename[:50] + "..." if len(filename) > 50 else filename
        print(
            f"{Fore.RED}Error logged to file:{Fore.RESET} {Fore.LIGHTCYAN_EX}{truncated_filename}{Fore.RESET}"
        )
    return trace_id

def logger(text: str, type: str = "INFO"):
    print(f"{Fore.LIGHTBLUE_EX}(!) {strftime('%H:%M:%S')} - {Fore.LIGHTBLUE_EX}[{type}] - {Fore.CYAN}{text}")

async def log_req(status: bool, time: float, model: str, user: str, response: str = None, provder: str = None) -> None:
    url = None

    if isinstance(response, tuple):
        url = response[1]
        prompt = response[0]

    fields = [
        {"name": "🤖Model", "value": f"**`{model}`**", "inline": True},
        {"name": "⏳Response Time", "value": f"**`{time:.2f} seconds`**", "inline": True},
        {"name": "🙍‍♂️User", "value": f"{user}", "inline": True}
    ]

    if response and url is None:
        fields.append({"name": "📝Response", "value": response[:1021] + '...' if len(response) > 1024 else response, "inline": True})
    if url:
        fields.append({"name": "📝Prompt", "value": prompt[:1021] + '...' if len(prompt) > 1024 else prompt, "inline": True})

    if provder:
        fields.append({"name": "🌐Provider", "value": provder, "inline": True})

    embed = {
        "title": "Shard API Logging",
        "description": "Completion Created",
        "color": 0x02101b if status else 0xd2403f,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if url:
        embed["image"] = {"url": url}

    async with aiohttp.ClientSession() as session:
        webhook = {"embeds": [embed]}
        async with session.post(WEBHOOK_URL, json=webhook) as response:
            pass

async def print_status(status: bool, response_time: float, model: str, user: str, response: str = None, provider=None):
    print(
        f"{Fore.LIGHTBLUE_EX}{strftime('%H:%M:%S')}{Fore.RESET} - "
        f"{Fore.LIGHTMAGENTA_EX if status else Fore.LIGHTRED_EX}({'Success' if status else 'Failed'}){Fore.RESET} - "
        f"{Fore.LIGHTBLUE_EX}[{model}]{Fore.RESET} - "
        f"{Fore.CYAN}{round(response_time, 2)}s{Fore.RESET} - "
        f"{Fore.LIGHTCYAN_EX}<@{user}>"
    )
    await log_req(status, response_time, model, f'<@{user}>', response, provider)

async def log_info(message, reason, status, user, input_: str = None):
    print(
        f"{Fore.LIGHTBLUE_EX}{strftime('%H:%M:%S')}{Fore.RESET} - "
        f"{Fore.LIGHTGREEN_EX if status else Fore.LIGHTRED_EX}({message}){Fore.RESET}"
        f"{f' - {Fore.YELLOW}[{reason}]{Fore.RESET}' if reason else ''} - "
        f"{Fore.LIGHTCYAN_EX}<@{user}>{Fore.RESET}"
    )

    embed = {
        "title": "Shard API Moderation",
        "color": 0x000000,
        "fields": [
            {"name": "❔Reason", "value": reason or "No reason provided", "inline": False},
            {"name": "🙍‍♂️User", "value": f"<@{user}>", "inline": True},
            {"name": "📝Input", "value":  f"{input_[:-1021] + '...' if len(input_) > 1024 else input_ or 'No input provided'}", "inline": False},
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    async with aiohttp.ClientSession() as session:
        webhook = {"embeds": [embed]}
        async with session.post(WEBHOOK_URL, json=webhook) as _:
            pass
        
        
async def stripe_logging(event_type: str, status: str, details: dict = None, error: str = None):
    """
    Logs Stripe webhook events to the console and a Discord webhook.

    Args:
        event_type: The type of Stripe event (e.g., "checkout.session.completed").
        status: The status of the event handling ("success" or "failure").
        details: A dictionary containing relevant details about the event (optional).
        error: An error message, if applicable (optional).
    """
    timestamp = datetime.utcnow().isoformat()
    color = 0x02101b if status == "success" else 0xff0000

    print(
        f"{Fore.LIGHTBLUE_EX}{strftime('%H:%M:%S')}{Fore.RESET} - "
        f"{Fore.LIGHTMAGENTA_EX if status == 'success' else Fore.LIGHTRED_EX}(SUCCESS) {Fore.RESET}-{Fore.LIGHTBLUE_EX} [STRIPE] ➡️ {Fore.RESET} - "
        f"{Fore.CYAN}{event_type}{Fore.RESET} - "
        f"{Fore.LIGHTWHITE_EX}{status.upper()}{Fore.RESET}"
    )
    if error:
        print(f"  {Fore.RED}❌ Error: {error}{Fore.RESET}")

    embed = {
        "title": "💳 Stripe Event",
        "description": f"Event Type: `{event_type}`",
        "color": color,
        "timestamp": timestamp,
        "fields": [],
        "footer": {"text": "Shard API"}
    }

    if details:
        for key, value in details.items():
            if isinstance(value, (int, float)):
                value_str = str(value)
            elif isinstance(value, str):
                value_str = value
            elif isinstance(value, dict):
                value_str = ujson.dumps(value)
            else:
                value_str = str(value)

            if len(value_str) > 1024:
                 value_str = value_str[:1021] + "..."
            
            emoji = "➡️"
            if key == "user_id":
                emoji = "👤"
            elif key == "customer_id":
                emoji = "💳"
            elif key == "subscription_id":
                emoji = "🆔"
            elif key == "subscription_status":
                emoji = "📊"
            elif key == "current_period_end":
                emoji = "📅"
            elif key == "type":
                emoji = "🗂️"
            
            key = key.replace("_", " ").title()

            embed["fields"].append({"name": f"{emoji} {key}", "value": f"`{value_str}`", "inline": True})

    if error:
        embed["fields"].append({"name": "❌ Error", "value": f"`{error}`", "inline": False})

    async with aiohttp.ClientSession() as session:
        async with session.post(STRIPE_WEBHOOK_URL, json={"embeds": [embed]}) as response:
            if response.status != 204:
                print(f"{Fore.RED}Error sending Discord webhook: {await response.text()}{Fore.RESET}")