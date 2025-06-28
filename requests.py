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
        stocks_list = list(stocks)
        return stocks_list


async def set_stock(user_id: int, filledSlots: int):
    async with async_session() as session:
        # Пометить все незавершённые слоты как завершённые
        await session.execute(
            update(Stock)
            .where(Stock.user == user_id, Stock.completed == False)
            .values(completed=True)
        )
        await session.commit()


async def increment_stock(user_id: int):
    current_stock = await get_stocks(user_id)  # незавершённые слоты
    if len(current_stock) >= 5:
        # Обнуляем, даём бесплатный
        await set_stock(user_id, 0)
    else:
        # Добавляем новый платный слот
        async with async_session() as session:
            new_slot = Stock(user=user_id, completed=False, title="Платный кальян")
            session.add(new_slot)
            await session.commit()


async def get_completed_stocks_count(user_id):
    async with async_session() as session:
         return await session.scalar(
    select(func.count(Stock.id)).where(Stock.completed == True, Stock.user == user_id)
)


# --- New functions ---
async def get_free_hookah_count(user_id: int) -> int:
    async with async_session() as session:
        result = await session.execute(
            select(func.count(Stock.id)).where(
                Stock.user == user_id,
                Stock.completed == True,
                Stock.title == "Бесплатный кальян"
            )
        )
        return result.scalar() or 0


async def use_free_slot(user_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Stock)
            .where(
                Stock.user == user_id,
                Stock.completed == True,
                Stock.title == "Бесплатный кальян"
            )
            .limit(1)
        )
        free_slot = result.scalar_one_or_none()
        if free_slot:
            await session.delete(free_slot)
            await session.commit()
            return True
        return False