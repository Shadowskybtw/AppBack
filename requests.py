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
    

async def get_completed_stocks_count(user_id):
    async with async_session() as session:
         return await session.scalar(select(func.count(Stock.id)).where(Stock.completed == True))
    

# Обновляет имя, фамилию и телефон пользователя по его ID
async def update_user_info(user_id, first_name, last_name, phone):
    async with async_session() as session:
        await session.execute(
            update(User)
            .where(User.id == user_id)
            .values(first_name=first_name, last_name=last_name, phone=phone)
        )
        await session.commit()