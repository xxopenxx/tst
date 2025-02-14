from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi import APIRouter
from pathlib import Path

app = APIRouter()

js_dir = Path("websites/scripts")
html_dir = Path("websites/templates")
css_dir = Path("websites/styles")

@app.get("/scripts/{file_path:path}")
async def serve_js(file_path: str):
    path = js_dir / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="JS file not found")
    return FileResponse(path)

@app.get("/sites/{file_path:path}")
async def serve_html(file_path: str):
    path = html_dir / (file_path + ".html")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="HTML file not found")
    return FileResponse(path)

@app.get("/css/{file_path:path}")
async def serve_css(file_path: str):
    path = css_dir / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="CSS file not found")
    return FileResponse(path)
