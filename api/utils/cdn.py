from pathlib import Path
import mimetypes
from uuid import uuid4
from typing import Tuple, Optional
import base64
from datetime import datetime, timedelta

import aiofiles
import aiohttp
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

images_dir = Path('cdn/images')
speech_dir = Path('cdn/speech')
images_dir.mkdir(parents=True, exist_ok=True)
speech_dir.mkdir(parents=True, exist_ok=True)

if not mimetypes.guess_type('file.webp')[0]:
    mimetypes.add_type('image/webp', '.webp')

scheduler = BackgroundScheduler()

max_age = timedelta(minutes=100)

def cleanup_cdn(dir: Path):
    try:
        now = datetime.now()
        for file in dir.iterdir():
            if file.is_file():
                file_age = now - datetime.fromtimestamp(file.stat().st_mtime)
                if file_age > max_age:
                    file.unlink()
    except:
        pass

scheduler.add_job(
    func=lambda: cleanup_cdn(images_dir),
    trigger=IntervalTrigger(minutes=1),
    id='cleanup_images',
    name='Cleanup old image files every minute',
    replace_existing=True
)

scheduler.add_job(
    func=lambda: cleanup_cdn(speech_dir),
    trigger=IntervalTrigger(minutes=1),
    id='cleanup_speech',
    name='Cleanup old speech files every minute',
    replace_existing=True
)

scheduler.start()

async def url_to_cdn(url: str) -> Tuple[Optional[str], bool]:
    try:
        file_url = None

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", '')

                if content_type == 'image/webp':
                    file_extension = '.webp'
                else:
                    file_extension = mimetypes.guess_extension(content_type) or '.bin'

                if content_type.startswith('image/'):
                    save_dir = images_dir
                else:
                    save_dir = speech_dir

                filename = f"{uuid4()}{file_extension}"
                file_path = save_dir / filename

                async with aiofiles.open(file_path, 'wb') as out_file:
                    while chunk := await response.content.read(1024):
                        await out_file.write(chunk)

        file_url = f"https://api.shard-ai.xyz/cdn/{save_dir.name}/{filename}"
        return (file_url, True)

    except Exception as e:
        print(e)
        return (None, False)

async def base64_to_cdn(bytes: str) -> Tuple[Optional[str], bool]:
    try:
        if "," in bytes:
            header, data = bytes.split(",")
            content_type = header.split(":")[1].split(";")[0]
        else:
            data = bytes
            content_type = 'application/octet-stream'

        extension = mimetypes.guess_extension(content_type) or '.bin'

        if content_type.startswith("image/"):
            save_dir = images_dir
        else:
            save_dir = speech_dir

        filename: str = f"{uuid4()}{extension}"
        fp: str = save_dir / filename

        decoded_data = base64.b64decode(data)

        async with aiofiles.open(fp, 'wb') as file:
            await file.write(decoded_data)

        return (f"https://api.shard-ai.xyz/cdn/{save_dir.name}/{filename}", True)

    except Exception as e:
        print(e)
        return (None, False)



async def data_to_cdn(data: str | bytes, content_type: str = "text/plain") -> tuple[str | None, bool]:
    try:
        filename = f"{uuid4()}.png"
        fp = images_dir / filename

        async with aiofiles.open(fp, 'wb') as file:
            await file.write(data)
        
        return f"https://api.shard-ai.xyz/cdn/{images_dir.name}/{filename}", True
    except Exception as e:
        print(f"Error saving data: {e}")
        return None, False