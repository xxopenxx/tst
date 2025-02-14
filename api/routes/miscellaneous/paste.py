from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pathlib import Path

app = APIRouter()
cdn_dir = Path("cdn")

@app.get("/paste/{file_path:path}")
async def serve_file(file_path: str):
    path = cdn_dir / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)