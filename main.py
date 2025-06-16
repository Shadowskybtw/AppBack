from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from models import init_db
import requests as rq

 
@asynccontextmanager
async def lifespan(app_: FastAPI):
    await init_db()
    print('Bot Soset')
    yield


app = FastAPI(title="Stock App", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class RegisterPayload(BaseModel):
    tg_id: int
    firstName: str
    lastName: str
    phone: str


@app.post("/api/stocks/{tg_id}")
async def update_stock(tg_id: int, request: Request):
    body = await request.json()
    user = await rq.add_user(tg_id)

    if body.get("incrementSlot"):
        await rq.increment_stock(user.id)
    elif "filledSlots" in body:
        await rq.set_stock(user.id, body["filledSlots"])

    return await rq.get_stocks(user.id)
 

@app.get("/api/main/{tg_id}")
async def profile(tg_id: int):
    user = await rq.add_user(tg_id)
    completed_stocks_count = await rq.get_completed_stocks_count(user.id)
    return {'completedStocks': completed_stocks_count}