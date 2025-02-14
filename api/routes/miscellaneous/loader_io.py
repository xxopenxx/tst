from fastapi import FastAPI, APIRouter
from fastapi.responses import PlainTextResponse

app = APIRouter()

@app.get("/loaderio-645294146e584768ead4649339f7d34f.txt", response_class=PlainTextResponse)
async def loader():
    return "loaderio-645294146e584768ead4649339f7d34f"
