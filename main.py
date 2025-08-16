from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import List

from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from models import init_db, close_db, User, async_session
from rq import (
    add_user, get_user_by_tg_id, get_stocks_summary, increment_stock, 
    set_stock, get_completed_stocks_count, update_user_profile,
    DatabaseError, BusinessLogicError
)
from schemas import (
    RegisterPayload, StockUpdatePayload, ProfileResponse, 
    RegisterResponse, StockListResponse, ErrorResponse, SuccessResponse
)
from config import settings
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized successfully")
    yield
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Hookah Stock Manager API",
    description="API для управления слотами кальянов с интеграцией Telegram",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware - разрешаем все домены для WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все домены для WebApp
    allow_credentials=True,  # Разрешаем credentials для WebApp
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            detail=str(exc.errors())
        ).dict()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP Error",
            detail=exc.detail
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            detail="An unexpected error occurred"
        ).dict()
    )


# Dependency for getting user
async def get_current_user(tg_id: int) -> User:
    """Get current user by Telegram ID"""
    try:
        user = await get_user_by_tg_id(tg_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except DatabaseError as e:
        logger.error(f"Database error while getting user {tg_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# --- STOCKS ENDPOINTS ---

@app.post("/api/stocks/{tg_id}", response_model=StockListResponse)
async def update_stock(tg_id: int, payload: StockUpdatePayload):
    """Update stock slots for user"""
    try:
        # Create user if doesn't exist
        user = await add_user(tg_id)
        
        if payload.incrementSlot:
            await increment_stock(user.id)
            action = "incrementSlot"
            value = ""
        elif payload.filledSlots is not None:
            await set_stock(user.id, payload.filledSlots)
            action = "setFilled"
            value = str(payload.filledSlots)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either incrementSlot or filledSlots must be provided"
            )

        # Send data to Google Sheets (best-effort)
        await send_to_google_sheets(tg_id, user, action, value)
        
        # Return updated stocks
        stocks, total, completed, available = await get_stocks_summary(user.id)
        return StockListResponse(
            stocks=stocks,
            total=total,
            completed=completed,
            available=available
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in update_stock: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )
    except Exception as e:
        logger.error(f"Unexpected error in update_stock: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@app.get("/api/stocks/{tg_id}", response_model=StockListResponse)
async def get_stock(tg_id: int):
    """Get stock slots for user"""
    try:
        user = await add_user(tg_id)
        stocks, total, completed, available = await get_stocks_summary(user.id)
        
        return StockListResponse(
            stocks=stocks,
            total=total,
            completed=completed,
            available=available
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in get_stock: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# --- PROFILE ENDPOINTS ---

@app.get("/api/main/{tg_id}", response_model=ProfileResponse)
async def get_profile(tg_id: int):
    """Get user profile - НЕ создает пользователя автоматически"""
    try:
        user = await get_user_by_tg_id(tg_id)
        
        if not user:
            return ProfileResponse(registered=False, completedStocks=0)
        
        completed_stocks_count = await get_completed_stocks_count(user.id)
        
        return ProfileResponse(
            registered=True,
            completedStocks=completed_stocks_count,
            user=user
        )
        
    except DatabaseError as e:
        logger.error(f"Database error in get_profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# --- REGISTRATION ENDPOINT ---

@app.post("/api/register", response_model=RegisterResponse)
async def register_user(payload: RegisterPayload):
    """Register or update user"""
    try:
        logger.info(f"Registration request for user: {payload.tg_id}")
        
        # Update or create user profile
        user = await update_user_profile(
            tg_id=payload.tg_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            phone=payload.phone,
            username=payload.username
        )
        
        return RegisterResponse(success=True, user=user)
        
    except BusinessLogicError as e:
        logger.warning(f"Business logic error in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(f"Database error in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# --- ADMIN ENDPOINTS ---

@app.get("/redeem/{guest_tg_id}", response_model=SuccessResponse)
async def redeem(guest_tg_id: int, request: Request):
    """Admin endpoint to add free slot for guest"""
    admin_tg_id = int(request.headers.get("X-Telegram-ID", 0))
    
    if not settings.ADMIN_IDS:
        logger.warning("No admin IDs configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin system not configured"
        )
    
    if admin_tg_id not in settings.ADMIN_IDS:
        logger.warning(f"Unauthorized admin access attempt: {admin_tg_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    try:
        guest = await add_user(guest_tg_id)
        await increment_stock(guest.id)
        
        logger.info(f"Admin {admin_tg_id} added slot for guest {guest_tg_id}")
        return SuccessResponse(message=f"Slot added for user {guest_tg_id}")
        
    except DatabaseError as e:
        logger.error(f"Database error in redeem: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred"
        )


# --- TELEGRAM INTEGRATION ---

@app.post("/send_webapp_button/{chat_id}", response_model=SuccessResponse)
async def send_webapp_button(chat_id: int):
    """Send WebApp button to Telegram chat"""
    if not settings.BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bot token not configured"
        )
    
    try:
        message_data = {
            "chat_id": chat_id,
            "text": "Нажмите кнопку ниже, чтобы открыть приложение:",
            "reply_markup": {
                "inline_keyboard": [[
                    {
                        "text": "Открыть WebApp",
                        "web_app": {"url": settings.WEBAPP_URL},
                    }
                ]]
            },
        }

        response = requests.post(
            f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
            json=message_data,
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send Telegram message"
            )

        logger.info(f"WebApp button sent to chat {chat_id}")
        return SuccessResponse(message="WebApp button sent successfully")
        
    except requests.RequestException as e:
        logger.error(f"Request error in send_webapp_button: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to communicate with Telegram API"
        )


# --- HOOKAH ENDPOINTS ---

@app.get("/api/hookahs/{tg_id}")
async def get_hookahs(tg_id: int):
    """Get hookah information for user (placeholder)"""
    # TODO: Implement hookah-specific logic
    return []


# --- UTILITY FUNCTIONS ---

async def send_to_google_sheets(tg_id: int, user: User, action: str, value: str):
    """Send data to Google Sheets (best-effort)"""
    try:
        response = requests.post(
            settings.GOOGLE_APPS_SCRIPT_URL,
            json={
                "tg_id": tg_id,
                "username": getattr(user, "username", None),
                "timestamp": datetime.now().isoformat(),
                "action": action,
                "value": value,
            },
            timeout=5,
        )
        
        if response.status_code == 200:
            logger.info(f"Data sent to Google Sheets for user {tg_id}")
        else:
            logger.warning(f"Google Sheets returned status {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Failed to send data to Google Sheets: {e}")


# --- HEALTH CHECK ---

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# --- WEBAPP INIT ENDPOINT ---

@app.get("/api/webapp/init/{tg_id}")
async def webapp_init(tg_id: int):
    """Initialize WebApp session - проверяет существование пользователя"""
    try:
        user = await get_user_by_tg_id(tg_id)
        
        if not user:
            return {
                "initialized": False,
                "userExists": False,
                "message": "User not found"
            }
        
        return {
            "initialized": True,
            "userExists": True,
            "user": {
                "tg_id": user.tg_id,
                "username": getattr(user, "username", None),
                "firstName": getattr(user, "first_name", None),
                "lastName": getattr(user, "last_name", None),
                "phone": getattr(user, "phone", None),
            }
        }
        
    except Exception as e:
        logger.error(f"Error in webapp_init: {e}")
        return {
            "initialized": False,
            "userExists": False,
            "message": "Error occurred"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)