from contextlib import asynccontextmanager
from datetime import datetime
import os

from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import init_db, User, async_session
from sqlalchemy import select

# Our DB/helpers module (previously requests.py -> renamed to rq.py)
import rq
# Real HTTP client for Telegram/Google requests
import requests


@asynccontextmanager
async def lifespan(app_: FastAPI):
    await init_db()
    print('Bot Soset')
    yield


app = FastAPI(title="Stock App", lifespan=lifespan)

# --- CORS ---
# Codespaces URL меняется на каждом запуске, поэтому для разработки открываем CORS полностью.
# На проде лучше ограничить доменами (или взять из переменной окружения).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterPayload(BaseModel):
    tg_id: int
    firstName: str
    lastName: str
    phone: str


# --- STOCKS ---

@app.post("/api/stocks/{tg_id}")
async def update_stock(tg_id: int, request: Request):
    body = await request.json()

    # создаём пользователя только при явных действиях (инкремент/сет), а не в профиле
    user = await rq.add_user(tg_id)

    if body.get("incrementSlot"):
        await rq.increment_stock(user.id)
    elif "filledSlots" in body:
        await rq.set_stock(user.id, body["filledSlots"])

    # Отправка данных в Google Таблицу через Apps Script (best-effort)
    try:
        requests.post(
            "https://script.google.com/macros/s/AKfycbx6Tl9msvSJFsYqr2ZSpZa0We5-pf_q5q0vr5g33tPU8huEX3Lrys97E0brARF8ahnJ/exec",
            json={
                "tg_id": tg_id,
                "username": getattr(user, "username", None),
                "timestamp": datetime.now().isoformat(),
                "action": "incrementSlot" if body.get("incrementSlot") else "setFilled",
                "value": body.get("filledSlots", ""),
            },
            timeout=2,
        )
    except Exception as e:
        print("Не удалось записать в Google Таблицу:", e)

    return await rq.get_stocks(user.id)


@app.get("/api/stocks/{tg_id}")
async def get_stock(tg_id: int):
    user = await rq.add_user(tg_id)
    stocks = await rq.get_stocks(user.id)
    # Гарантируем массив
    if not isinstance(stocks, list):
        return []
    return stocks


# --- PROFILE ---

@app.get("/api/main/{tg_id}")
async def profile(tg_id: int):
    # Не создаём пользователя автоматически.
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))

    if not user:
        # Нет записи — фронт должен показать форму регистрации
        return JSONResponse(status_code=404, content={"registered": False})

    completed_stocks_count = await rq.get_completed_stocks_count(user.id)

    return {
        "registered": True,
        "completedStocks": completed_stocks_count,
        "user": {
            "tg_id": user.tg_id,
            "username": getattr(user, "username", None),
            "firstName": getattr(user, "first_name", None),
            "lastName": getattr(user, "last_name", None),
            "phone": getattr(user, "phone", None),
        },
    }


# --- REDEEM (только админы) ---

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


# --- REGISTER ---

@app.post("/api/register")
async def register_user(payload: RegisterPayload):
    """
    Создаёт (если нужно) и обновляет пользователя в БД,
    затем возвращает унифицированный объект user.
    """
    print("Регистрация пользователя:", payload.dict())

    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == payload.tg_id))

        if not user:
            user = User(
                tg_id=payload.tg_id,
                first_name=payload.firstName,
                last_name=payload.lastName,
                phone=payload.phone,
            )
            session.add(user)
        else:
            user.first_name = payload.firstName
            user.last_name = payload.lastName
            user.phone = payload.phone

        await session.commit()
        await session.refresh(user)

    return {
        "success": True,
        "user": {
            "tg_id": user.tg_id,
            "username": getattr(user, "username", None),
            "firstName": getattr(user, "first_name", None),
            "lastName": getattr(user, "last_name", None),
            "phone": getattr(user, "phone", None),
        },
    }


# --- TELEGRAM WEBAPP BUTTON ---

@app.post("/send_webapp_button/{chat_id}")
async def send_webapp_button(chat_id: int):
    token = os.getenv("BOT_TOKEN", "7829386579:AAGAUFZdd6PbuDtdEI1zxAkfY1vlj0Mu0WE")  # ЗАМЕНИ на свой токен/переменную
    webapp_url = os.getenv("WEBAPP_URL", "https://frontend-delta-sandy-58.vercel.app")

    message_data = {
        "chat_id": chat_id,
        "text": "Нажмите кнопку ниже, чтобы открыть приложение:",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "Открыть WebApp",
                    "web_app": {"url": webapp_url},
                }
            ]]
        },
    }

    response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=message_data)

    if response.status_code != 200:
        print("Ошибка Telegram API:", response.text)
        return JSONResponse(status_code=response.status_code, content={"error": response.text})

    return {"status": "sent", "response": response.json()}


# --- HOOKAHS (заглушка пока пустая) ---

@app.get("/api/hookahs/{tg_id}")
async def get_hookahs(tg_id: int):
    return []