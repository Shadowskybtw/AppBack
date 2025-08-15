from sqlalchemy import ForeignKey, String, BigInteger, Boolean, DateTime, Index
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.sql import func
from config import settings

# Database engine with improved configuration
engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=False,  # Set to True for debugging
    pool_pre_ping=True,
    pool_recycle=300,
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False
)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models with common fields"""
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str] = mapped_column(String(128), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    stocks = relationship("Stock", backref="owner", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_tg_id', 'tg_id'),
        Index('idx_user_username', 'username'),
    )


class Stock(Base):
    __tablename__ = 'stocks'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_stock_user_completed', 'user_id', 'completed'),
        Index('idx_stock_completed', 'completed'),
    )


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Database initialized successfully")


async def close_db():
    """Close database connections"""
    await engine.dispose()
    print("Database connections closed")