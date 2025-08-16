from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError
from models import async_session, User, Stock
from schemas import StockResponse, UserResponse
from typing import List, Optional, Tuple
from config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class BusinessLogicError(Exception):
    """Custom exception for business logic errors"""
    pass


async def add_user(tg_id: int) -> User:
    """Add or get existing user by Telegram ID"""
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            if user:
                return user
            
            new_user = User(tg_id=tg_id)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            logger.info(f"Created new user with tg_id: {tg_id}")
            return new_user
    except SQLAlchemyError as e:
        logger.error(f"Database error while adding user {tg_id}: {e}")
        raise DatabaseError(f"Failed to add user: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while adding user {tg_id}: {e}")
        raise


async def get_user_by_tg_id(tg_id: int) -> Optional[User]:
    """Get user by Telegram ID without creating"""
    try:
        async with async_session() as session:
            return await session.scalar(select(User).where(User.tg_id == tg_id))
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting user {tg_id}: {e}")
        raise DatabaseError(f"Failed to get user: {e}")


async def get_stocks(user_id: int) -> List[Stock]:
    """Get all active (incomplete) stocks for user"""
    try:
        async with async_session() as session:
            stocks = await session.scalars(
                select(Stock).where(
                    Stock.user_id == user_id,
                    Stock.completed == False
                ).order_by(Stock.created_at.desc())
            )
            return list(stocks)
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting stocks for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get stocks: {e}")


async def get_stocks_summary(user_id: int) -> Tuple[List[Stock], int, int, int]:
    """Get stocks with summary statistics"""
    try:
        async with async_session() as session:
            # Get active stocks
            active_stocks = await session.scalars(
                select(Stock).where(
                    Stock.user_id == user_id,
                    Stock.completed == False
                ).order_by(Stock.created_at.desc())
            )
            active_list = list(active_stocks)
            
            # Get completed count
            completed_count = await session.scalar(
                select(func.count(Stock.id)).where(
                    Stock.user_id == user_id,
                    Stock.completed == True
                )
            ) or 0
            
            return active_list, len(active_list), completed_count, len(active_list)
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting stocks summary for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get stocks summary: {e}")


async def set_stock(user_id: int, filled_slots: int) -> bool:
    """Mark all incomplete stocks as completed"""
    try:
        async with async_session() as session:
            result = await session.execute(
                update(Stock)
                .where(Stock.user_id == user_id, Stock.completed == False)
                .values(completed=True)
            )
            await session.commit()
            
            affected_rows = result.rowcount
            logger.info(f"Marked {affected_rows} stocks as completed for user {user_id}")
            return affected_rows > 0
    except SQLAlchemyError as e:
        logger.error(f"Database error while setting stocks for user {user_id}: {e}")
        raise DatabaseError(f"Failed to set stocks: {e}")


async def increment_stock(user_id: int) -> Stock:
    """Add new stock slot or reset if max reached"""
    try:
        current_stocks = await get_stocks(user_id)
        
        if len(current_stocks) >= settings.MAX_STOCKS_PER_USER:
            # Reset all stocks and give free hookah
            await set_stock(user_id, 0)
            new_slot = Stock(
                user_id=user_id,
                completed=False,
                title=settings.FREE_HOOKAH_TITLE
            )
            logger.info(f"User {user_id} reached max stocks, giving free hookah")
        else:
            # Add new paid slot
            new_slot = Stock(
                user_id=user_id,
                completed=False,
                title=settings.PAID_HOOKAH_TITLE
            )
            logger.info(f"Added new paid slot for user {user_id}")
        
        async with async_session() as session:
            session.add(new_slot)
            await session.commit()
            await session.refresh(new_slot)
            return new_slot
            
    except SQLAlchemyError as e:
        logger.error(f"Database error while incrementing stock for user {user_id}: {e}")
        raise DatabaseError(f"Failed to increment stock: {e}")


async def get_completed_stocks_count(user_id: int) -> int:
    """Get count of completed stocks for user"""
    try:
        async with async_session() as session:
             return await session.scalar(
        select(func.count(Stock.id)).where(Stock.completed == True, Stock.user_id == user_id)
    )
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting completed stocks count for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get completed stocks count: {e}")


async def get_free_hookah_count(user_id: int) -> int:
    """Get count of free hookah slots for user"""
    try:
        async with async_session() as session:
            result = await session.scalar(
                select(func.count(Stock.id)).where(
                    Stock.user_id == user_id,
                    Stock.completed == True,
                    Stock.title == settings.FREE_HOOKAH_TITLE
                )
            )
            return result or 0
    except SQLAlchemyError as e:
        logger.error(f"Database error while getting free hookah count for user {user_id}: {e}")
        raise DatabaseError(f"Failed to get free hookah count: {e}")


async def use_free_slot(user_id: int) -> bool:
    """Use one free hookah slot"""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Stock)
                .where(
                    Stock.user_id == user_id,
                    Stock.completed == True,
                    Stock.title == settings.FREE_HOOKAH_TITLE
                )
                .limit(1)
            )
            free_slot = result.scalar_one_or_none()
            
            if free_slot:
                await session.delete(free_slot)
                await session.commit()
                logger.info(f"Used free hookah slot for user {user_id}")
                return True
            return False
    except SQLAlchemyError as e:
        logger.error(f"Database error while using free slot for user {user_id}: {e}")
        raise DatabaseError(f"Failed to use free slot: {e}")


async def update_user_profile(
    tg_id: int,
    first_name: str = None,
    last_name: str = None,
    phone: str = None,
    username: str = None
) -> User:
    """Update user profile information or create new user"""
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            
            if not user:
                # Create new user with provided data
                user = User(
                    tg_id=tg_id,
                    first_name=first_name,
                    last_name=last_name,
                    phone=phone,
                    username=username
                )
                session.add(user)
                logger.info(f"Created new user with tg_id: {tg_id}")
            else:
                # Update existing user
                if first_name is not None:
                    user.first_name = first_name
                if last_name is not None:
                    user.last_name = last_name
                if phone is not None:
                    user.phone = phone
                if username is not None:
                    user.username = username
                logger.info(f"Updated profile for user {tg_id}")
            
            await session.commit()
            await session.refresh(user)
            return user
            
    except SQLAlchemyError as e:
        logger.error(f"Database error while updating user profile {tg_id}: {e}")
        raise DatabaseError(f"Failed to update user profile: {e}")


async def create_user_if_not_exists(tg_id: int) -> User:
    """Create user if doesn't exist, return existing if does"""
    try:
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.tg_id == tg_id))
            
            if not user:
                user = User(tg_id=tg_id)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"Created new user with tg_id: {tg_id}")
            
            return user
            
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating user {tg_id}: {e}")
        raise DatabaseError(f"Failed to create user: {e}")