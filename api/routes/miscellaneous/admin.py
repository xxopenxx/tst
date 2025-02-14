from fastapi import Response, Request, Body, APIRouter
from fastapi.exceptions import HTTPException
from colorama import Fore, Style
from time import strftime
import ujson
import yaml

from api.config import config
from api.database import DatabaseManager

app = APIRouter()

with open('secrets/values.yml', 'r') as f:
    admin_key = yaml.safe_load(f)['admin_key']

def validate_payload(keys: list[str], data: dict, action: str):
    if action == 'update':
        if not len([data.get(key) for key in keys if data.get(key) is not None]) >= 2:
            raise HTTPException(detail={'success': False, 'error': 'Invalid payload.'}, status_code=400)
    elif action in {'check', 'usage', 'ips'}:
        if not len([data.get(key) for key in keys if data.get(key)]) == 1:
            raise HTTPException(detail={'success': False, 'error': 'Invalid payload.'}, status_code=400)
    elif not all(data.get(key) for key in keys):
        raise HTTPException(detail={'success': False, 'error': 'Invalid payload.'}, status_code=400)

def handle_action(action: str, data: dict):
    actions = {
        'register': register_key, # register user
        'check': check_key, # check key status
        'reset': reset_key, # delete all keys
        'delete': delete_key, # delete key
        'update': update_key, # update user
        'usage': get_usage,
        'ips': get_ips,
        "subscription": get_subscription,
        "add": add_key, # add a key to user
        "get_activity": get_activity # get users recent activity
    }

    if action not in actions:
        raise HTTPException(detail={'success': False, 'error': 'Invalid action.'}, status_code=400)

    return actions[action](data)

async def log_admin_action(status: bool, action: str, user: str, details: dict = None):
    color = Fore.LIGHTMAGENTA_EX if status else Fore.LIGHTRED_EX
    action_text = f"{Fore.LIGHTBLUE_EX}{strftime('%H:%M:%S')} - {color} ({'Success' if status else 'Failed'}) - {Fore.LIGHTGREEN_EX}[{action}] - {Fore.CYAN}<@{user}>"    
    print(action_text + Style.RESET_ALL)

@app.post('/v1/admin/{action:str}')
async def admin(request: Request, action: str, data: dict = Body(...)) -> Response:
    try:
        if request.headers.get('Authorization', '').replace('Bearer ', '') != admin_key:
            await log_admin_action(False, action, data.get('id', ''), {"error": "Invalid admin key"})
            raise HTTPException(detail={'success': False, 'error': 'Invalid admin key.'}, status_code=401)

        if action in {'register', 'reset'}:
            validate_payload(['id'], data, action)
        elif action == 'update':
            validate_payload(['id', 'key', 'banned', 'premium', 'resetip'], data, action)
        elif action == "delete":
            validate_payload(['id', 'key'], data, action)
        else:
            validate_payload(['id'], data, action)
        
        response = await handle_action(action, data)
        await log_admin_action(True, action, data.get('id', ''), {"info": "Action completed successfully"})
        return response
    
    except HTTPException as e:
        await log_admin_action(False, action, data.get('id', ''), e.detail)
        raise
    except Exception as e:
        await log_admin_action(False, action, data.get('id', ''), {"error": str(e)})
        raise HTTPException(detail={'success': False, 'error': 'Internal server error.'}, status_code=500)


async def register_key(data: dict) -> Response:
    if await DatabaseManager.id_check(data['id']):
        raise HTTPException(detail={'success': False, 'error': 'The key for the specified ID already exists.'}, status_code=400)

    data = await DatabaseManager.create_account(data['id'])

    return Response(ujson.dumps({'success': True, 'key': str(data)}, indent=4), media_type='application/json')

async def check_key(data: dict) -> Response:
    check_key, key_value = await DatabaseManager.key_check(data.get('key')) if data.get('key') else (None, None)
    check_id = await DatabaseManager.id_check(data.get('id')) if data.get('id') else None
    
    if not check_key and data.get('key') and not check_id and data.get('id'):
        raise HTTPException(detail={'success': False, 'error': 'This user or key does not exist.'}, status_code=400)
    
    if check_id is not None and not check_key:
        if check_id == []:
          key = await DatabaseManager.add_key_to_user(data.get('id'), name="default")
          return Response(ujson.dumps({'success': True, 'key': [key] }, indent=4), media_type='application/json')
        
    return Response(ujson.dumps({'success': True, 'key': key_value if check_key else check_id}, indent=4), media_type='application/json')

async def delete_key(data: dict) -> Response:
    success = await DatabaseManager.delete_key_from_user(data.get("id", None), data.get("key", None))
    return Response(ujson.dumps({'success': success}, indent=4), media_type='application/json')

async def reset_key(data: dict) -> Response:
    check_key, key_value = await DatabaseManager.key_check(data.get('key')) if data.get('key') else (None, None)
    check_id = await DatabaseManager.id_check(data.get('id')) if data.get('id') else None
    print(check_id, check_key, key_value)
    if not check_key and data.get('key') or not check_id and data.get('id'):
        raise HTTPException(detail={'success': False, 'error': 'The key for the specified ID does not exist.'}, status_code=400)

    key = await DatabaseManager.reset_key(key_value if check_key else data.get('id'))

    return Response(ujson.dumps({'success': True, 'key': key}, indent=4), media_type='application/json')

async def update_key(data):
    check_key, key_value = await DatabaseManager.key_check(data.get('key')) if data.get('key') else (None, None)
    check_id = await DatabaseManager.id_check(data.get('id')) if data.get('id') else None

    if not check_key and data.get('key') or not check_id and data.get('id'):
        raise HTTPException(detail={'success': False, 'error': 'The key for the specified ID does not exist.'}, status_code=400)
    if data.get('banned') is not None:
        await DatabaseManager.ban_update(data.get('id'), data.get('banned'))
    elif data.get('premium') is not None:
        if data.get("premium") == "custom":
            rate_limit = data.get('rate_limit')
            credit_limit = data.get("credit_limit")
            await DatabaseManager.set_custom_subscription_values(data.get("id"), rate_limit, credit_limit)
        
        await DatabaseManager.update_subscription_type(key_value if check_key else data.get('id'), data.get('premium'))
    elif data.get('resetip') == True:
        await DatabaseManager.reset_ip(key_value if check_key else data.get('id'))

    return Response(ujson.dumps({'success': True, 'info': 'Successfully updated key.'}, indent=4), media_type='application/json')

async def get_usage(data: dict) -> Response:
    daily_usage, usage, limit, history = await DatabaseManager.get_daily_usage(data.get("id", None))
    total_input, total_output = await DatabaseManager.get_total_tokens(data.get("id", None))

    shards = limit - daily_usage
    data = {
        "credits": shards,
        "usage": usage,
        "history": history,
        "tokens": {
            "output": total_output,
            "input": total_input
        }
    }

    return Response(ujson.dumps({'success': True, 'usage': data}, indent=4), media_type='application/json')

async def get_subscription(data: dict) -> Response:
    price = None
    subscription_type = await DatabaseManager.get_subscription_type(data.get("id", None))
    if subscription_type == "custom":
        rate_limit, credit_limit = await DatabaseManager.get_custom_subscription_values(data.get("id", None))
    else:
        if subscription_type == "free":
            rate_limit = config.free.rate_limit
            credit_limit = config.free.credits
            price = config.free.price
        elif subscription_type == "basic":
            rate_limit = config.basic.rate_limit
            credit_limit = config.basic.credits
            price = config.basic.price
        elif subscription_type == "premium":
            rate_limit = config.premium.rate_limit
            credit_limit = config.premium.credits
            price = config.premium.price

    return Response(ujson.dumps({'success': True, 'subscription': {'rate_limit': rate_limit, 'credit_limit': credit_limit, 'price': price, "type": subscription_type}}, indent=4), media_type='application/json')


async def get_ips(data: dict) -> Response:
    check_key, key_value = await DatabaseManager.key_check(data.get('key')) if data.get('key') else (None, None)
    check_id = await DatabaseManager.id_check(data.get('id')) if data.get('id') else None

    if not check_key and data.get('key') or not check_id and data.get('id'):
        raise HTTPException(detail={'success': False, 'error': 'The key for the specified ID does not exist.'}, status_code=400)

    return Response(ujson.dumps({'success': True, 'ips': await DatabaseManager.get_ips(key_value if check_key else data.get('id'))}, indent=4), media_type='application/json')

async def add_key(data: dict) -> Response:
    success = await DatabaseManager.add_key_to_user(data.get("id"), data.get("name", None), data.get('description', None))
    return Response(ujson.dumps({'success': True, 'key': success}, indent=4), media_type='application/json')

async def get_activity(data: dict) -> Response:
    data = await DatabaseManager.get_recent_activity(data.get("id"), data.get("resource", None))
    return Response(ujson.dumps({"success": True, "data": data}, indent=4), media_type="application/json")