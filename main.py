from contextlib import asynccontextmanager

from datetime import datetime

from pydantic import BaseModel
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware

from models import init_db
import requests as rq

from fastapi.responses import JSONResponse

 
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

    # Отправка данных в Google Таблицу через Apps Script
    try:
        rq.post(
            "https://script.google.com/macros/s/AKfycbx6Tl9msvSJFsYqr2ZSpZa0We5-pf_q5q0vr5g33tPU8huEX3Lrys97E0brARF8ahnJ/exec",  # ← замени на свой URL
            json={
                "tg_id": tg_id,
                "username": user.username,
                "timestamp": datetime.now().isoformat(),
                "action": "incrementSlot" if body.get("incrementSlot") else "setFilled",
                "value": body.get("filledSlots", "")
            },
            timeout=2
        )
    except Exception as e:
        print("Не удалось записать в Google Таблицу:", e)

    return await rq.get_stocks(user.id)
 

@app.get("/api/main/{tg_id}")
async def profile(tg_id: int):
    user = await rq.add_user(tg_id)
    completed_stocks_count = await rq.get_completed_stocks_count(user.id)
    return {'completedStocks': completed_stocks_count}


# список Telegram ID админов
ADMIN_IDS = [123456789, 987654321]  # ← замени на настоящие TG ID админов

@app.get("/redeem/{guest_tg_id}")
async def redeem(guest_tg_id: int, request: Request):
    admin_tg_id = int(request.headers.get("X-Telegram-ID", 0))  # получаем TG ID из заголовка

    if admin_tg_id not in ADMIN_IDS:
        return JSONResponse(status_code=403, content={"error": "Недостаточно прав"})

    guest = await rq.add_user(guest_tg_id)
    await rq.increment_stock(guest.id)
    return {"message": f"Слот добавлен пользователю {guest_tg_id}"}
@app.post("/api/register")
async def register_user(payload: RegisterPayload):
    print("Регистрация пользователя:", payload.dict())

    # Здесь можно добавить сохранение в БД, если нужно
    return {
        "success": True,
        "user": {
            "id": payload.tg_id,
            "name": payload.firstName,
            "surname": payload.lastName,
            "phone": payload.phone,
        }
    }