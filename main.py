from contextlib import asynccontextmanager

from pydantic import BaseModel
from fastapi import FastAPI
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


@app.get("api/stocks/{tg_id}")
async def stocks(tg_id: int):
    user = await rq.add_user(tg_id)
    return await rq.get_stocks(user.id)
 

@app.get("/api/main/{tg_id}")
async def profile(tg_id: int):
    user = await rq.add_user(tg_id)
    completed_stocks_count = await rq.get_completed_stocks_count(user.id)
    return {'completedStocks': completed_stocks_count}


@app.post("/api/register")
async def register_user(payload: RegisterPayload):
    user = await rq.add_user(payload.tg_id)
    await rq.update_user_info(
        user_id=user.id,
        first_name=payload.firstName,
        last_name=payload.lastName,
        phone=payload.phone
    )
    return {"message": "User registered"}