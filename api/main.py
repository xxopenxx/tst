from contextlib import asynccontextmanager
from pathlib import Path
import importlib
import warnings
import asyncio
import os

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import starlette.requests

from api.database import DatabaseManager
from api import exceptions

import uvloop # type: ignore
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


warnings.filterwarnings("ignore")
flags: list[str] = [
    "api_initialized.flag",
    "api_initialized_chat (1).flag",
    "api_initialized_chat (2).flag",
    "api_initialized_moderation (1).flag",
    "api_initialized_moderation (2).flag",
    "api_initialized_tts (1).flag",
    "api_initialized_tts (2).flag",
    "api_initialized_images (1).flag",
    "api_initialized_images (2).flag",
    "api_initialized_embedding (1).flag",
    "api_initialized_embedding (2).flag",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # on startup
    try:
        with open("/tmp/api_initialized.flag", 'x') as _:
            print("💎 API is up!")
    except FileExistsError:
        pass
    
    yield # seperate startup from shutdown
    
    # on shutdown
    try:
        # remove tmp flags used for logging
        [os.remove(f"/tmp/{flag}") for flag in flags if os.path.exists(f"/tmp/{flag}")]
    except:
        pass

app = FastAPI(docs_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(404, exceptions.not_found)
app.add_exception_handler(405, exceptions.method_not_allowed)
app.add_exception_handler(Exception, exceptions.exception_handler)
app.add_exception_handler(ValueError, exceptions.exception_handler)
app.add_exception_handler(HTTPException, exceptions.http_exception_handler)

class IPHandler:
    async def __call__(self, request: starlette.requests.Request, call_next):
        response = await call_next(request)

        if request.url.path.startswith('/v1/'):
            ip = request.headers.get("CF-Connecting-IP")
            auth = request.headers.get("Authorization")

            if ip is None or auth is None:
                return response
            
            auth = auth.replace("Bearer ", "")
            
            await DatabaseManager.add_ip(auth, ip)
        return response 

app.middleware("http")(IPHandler())

def load_routers(app, package_name: str, dir: Path) -> None:
    for root, _, files in os.walk(dir):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                module_path = os.path.join(root, file)
                module_name = module_path.replace(str(dir) + os.sep, "").replace(os.sep, ".").rstrip(".py")
                full_module_name = f"{package_name}.{module_name}"
                try:
                    module = importlib.import_module(full_module_name)
                    if hasattr(module, "app"):
                        app.include_router(module.app)
                except Exception as e:
                    print(f"Failed to import {full_module_name}: {e}")
            
routes_dir = "api/routes"
load_routers(app, "api.routes", routes_dir)