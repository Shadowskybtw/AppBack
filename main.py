from contextlib import asynccontextmanager
from datetime import datetime
import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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


# --- CORS ---
# Разрешаем запросы с фронтенда на Vercel, из Telegram Web и публичных Codespaces (*.app.github.dev).
DEFAULT_ORIGINS = [
    "https://frontend-delta-sandy-58.vercel.app",
    "https://web.telegram.org",
    "https://telegram.org",
    "https://t.me",
]

# Дополнительные домены можно передать через settings.CORS_ORIGINS (строка с доменами через запятую)
extra = []
try:
    if getattr(settings, "CORS_ORIGINS", None):
        extra = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
except Exception:
    extra = []

ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ORIGINS + extra))

# Любой публичный домен Codespaces вроде https://<name>-8000.app.github.dev
CODESPACES_REGEX = r"https://.*\.app\.github\.dev$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],
    allow_origin_regex=CODESPACES_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
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


@app.get("/api/free-hookahs/{tg_id}")
async def get_free_hookahs(tg_id: int):
    """Return number of available free hookahs for a user."""
    try:
        user = await add_user(tg_id)
        _, _total, _completed, available = await get_stocks_summary(user.id)
        return {"count": int(available) if available is not None else 0}
    except DatabaseError as e:
        logger.error(f"Database error in get_free_hookahs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred")


# --- REGISTRATION ENDPOINT ---

@app.post("/api/register", response_model=RegisterResponse)
async def register_user(payload: RegisterPayload | None = None, request: Request = None):
    """Register or update user (idempotent). Accepts both snake_case and camelCase keys.
    Frontend may send {tg_id, firstName, lastName, phone, username} or snake_case.
    """
    try:
        body = None
        if request is not None:
            try:
                body = await request.json()
            except Exception:
                body = None

        # Prefer explicit Pydantic payload if parsed, otherwise normalize raw body
        if payload is None and isinstance(body, dict):
            # normalize keys
            def pick(d, *names):
                for n in names:
                    if n in d and d[n] not in (None, ""):
                        return d[n]
                return None

            tg_id_val = pick(body, "tg_id", "telegram_id", "id", "tgId")
            first_name = pick(body, "first_name", "firstName") or ""
            last_name  = pick(body, "last_name", "lastName") or ""
            phone      = pick(body, "phone", "telephone", "tel") or ""
            username   = pick(body, "username", "userName")

            try:
                tg_id_int = int(tg_id_val)
            except Exception:
                tg_id_int = None

            if not tg_id_int:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="tg_id is required")
            if not isinstance(phone, str) or len(phone.strip()) < 5:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="phone is invalid")

            # Manual upsert using SQLAlchemy session to avoid hidden integrity errors
            async with async_session() as session:
                user = await session.scalar(select(User).where(User.tg_id == tg_id_int))

                # Phone conflict with another user
                if phone:
                    owner = await session.scalar(select(User).where(User.phone == phone))
                    if owner and (not user or owner.id != user.id):
                        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already in use")

                if user:
                    user.first_name = first_name
                    user.last_name  = last_name
                    user.phone      = phone
                    user.username   = username
                else:
                    user = User(
                        tg_id=tg_id_int,
                        first_name=first_name,
                        last_name=last_name,
                        phone=phone,
                        username=username,
                    )
                    session.add(user)

                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    logger.exception("Integrity error in /api/register")
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User/phone already exists")

            # success
            return RegisterResponse(success=True, user=user)

        # If we have a validated Pydantic payload (snake_case), use existing DAL helper
        if payload is not None:
            logger.info(f"Registration request for user: {payload.tg_id}")
            try:
                # Extra pre-check for phone conflicts to convert to 409 instead of 500
                async with async_session() as session:
                    existing_by_tg = await session.scalar(select(User).where(User.tg_id == payload.tg_id))
                    if payload.phone:
                        owner = await session.scalar(select(User).where(User.phone == payload.phone))
                        if owner and (not existing_by_tg or owner.id != existing_by_tg.id):
                            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already in use")
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Pre-check error before update_user_profile: {e}")

            user = await update_user_profile(
                tg_id=payload.tg_id,
                first_name=payload.first_name,
                last_name=payload.last_name,
                phone=payload.phone,
                username=payload.username,
            )
            return RegisterResponse(success=True, user=user)

        # No payload, no body
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid register payload")

    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error in registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred",
        )
    except Exception as e:
        logger.error(f"Unexpected error in registration: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal registration error")


# --- ADMIN ENDPOINTS ---

async def _redeem_core(guest_tg_id: int, admin_tg_id: int):
    if not settings.ADMIN_IDS:
        logger.warning("No admin IDs configured")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin system not configured")
    if admin_tg_id not in settings.ADMIN_IDS:
        logger.warning(f"Unauthorized admin access attempt: {admin_tg_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    try:
        guest = await add_user(guest_tg_id)
        await increment_stock(guest.id)
        logger.info(f"Admin {admin_tg_id} added slot for guest {guest_tg_id}")
        return SuccessResponse(message=f"Slot added for user {guest_tg_id}")
    except DatabaseError as e:
        logger.error(f"Database error in redeem: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error occurred")

@app.get("/redeem/{guest_tg_id}", response_model=SuccessResponse)
async def redeem_get(guest_tg_id: int, request: Request):
    admin_tg_id = int(request.headers.get("X-Telegram-ID", 0))
    return await _redeem_core(guest_tg_id, admin_tg_id)

@app.post("/redeem/{guest_tg_id}", response_model=SuccessResponse)
async def redeem_post(guest_tg_id: int, request: Request):
    admin_tg_id = int(request.headers.get("X-Telegram-ID", 0))
    return await _redeem_core(guest_tg_id, admin_tg_id)


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
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
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