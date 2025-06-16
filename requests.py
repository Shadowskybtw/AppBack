from sqlalchemy import select, update, delete, func
from models import async_session, User, Stock
from pydantic import BaseModel, ConfigDict
from typing import List


class StockSchema(BaseModel):
    id: int
    title: str
    completed: bool
    user: int

    model_config = ConfigDict(from_attributes=True)


async def add_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            return user
        
        new_user = User(tg_id=tg_id)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user


async def get_stocks(user_id):
    async with async_session() as session:
        stocks = await session.scalars(
            select(Stock).where(Stock.user == user_id, Stock.completed == False)
        )

        serialized_stocks = [
            StockSchema.model_validate(t).model_dump() for t in stocks
        ]
        return serialized_stocks


async def set_stock(user_id: int, filledSlots: int):
    # Тут пишешь свою логику сохранения в БД / Google Sheets
    # Например:
    # UPDATE users SET filled_slots = filledSlots WHERE id = user_id
    pass


async def increment_stock(user_id: int):
    # получаем текущее количество слотов
    current_stock = await get_stocks(user_id)
    filled_slots = current_stock.get('filledSlots', 0)

    # увеличиваем на 1, максимум до 5
    filled_slots = min(filled_slots + 1, 5)

    # устанавливаем новое значение
    await set_stock(user_id, filled_slots)


async def get_completed_stocks_count(user_id):
    async with async_session() as session:
         return await session.scalar(
    select(func.count(Stock.id)).where(Stock.completed == True, Stock.user == user_id)
)