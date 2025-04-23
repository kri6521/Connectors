from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

TRELLO_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
BASE_URL = "https://api.trello.com/1"

@app.get("/")
async def root():
    return {"message": "Trello Connector API is running"}

# format of request body in create card
class CardCreateRequest(BaseModel):
    name: str
    desc: str = ""
    idList: str

@app.get("/boards")
async def get_boards():
    url = f"{BASE_URL}/members/me/boards"
    params = {"key": TRELLO_KEY, "token": TRELLO_TOKEN}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/lists/{board_id}")
async def get_lists(board_id: str):
    url = f"{BASE_URL}/boards/{board_id}/lists"
    params = {"key": TRELLO_KEY, "token": TRELLO_TOKEN}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.post("/cards")
async def create_card(request: CardCreateRequest):
    url = f"{BASE_URL}/cards"
    params = {
        "key": TRELLO_KEY,
        "token": TRELLO_TOKEN,
        "idList": request.idList,
        "name": request.name,
        "desc": request.desc,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/cards/{list_id}")
async def get_cards_from_list(list_id: str):
    url = f"{BASE_URL}/lists/{list_id}/cards"
    params = {"key": TRELLO_KEY, "token": TRELLO_TOKEN}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()
