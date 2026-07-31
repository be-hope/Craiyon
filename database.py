import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker

# Railway injects DATABASE_URL automatically when you add a Postgres plugin.
# Falls back to a local sqlite file so you can test on your laptop first.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./local.db")

# Railway/Heroku-style URLs sometimes start with postgres:// -- SQLAlchemy 2.x
# needs postgresql://, so we fix it up here.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class RoomSession(Base):
    """Tracks the CURRENT active session id for each room.
    Admin bumps this between batches -- old attempts stay in the DB
    but stop counting toward the live leaderboard/attempt caps."""

    __tablename__ = "room_sessions"

    room_id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, default="0")
    updated_at = Column(DateTime, default=datetime.utcnow)


class TargetImage(Base):
    """The images students are trying to recreate."""

    __tablename__ = "target_images"

    id = Column(Integer, primary_key=True)
    label = Column(String)          # e.g. "Image 1"
    image_url = Column(String)      # where the target image is hosted
    fingerprint = Column(String)    # precomputed hash + color histogram, JSON string
    active = Column(Boolean, default=True)


class Attempt(Base):
    """One student prompt attempt."""

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    seat_id = Column(String, index=True)
    room_id = Column(String, index=True)
    session_id = Column(String, index=True)
    target_id = Column(Integer, ForeignKey("target_images.id"), index=True)
    prompt = Column(String)
    image_url = Column(String)
    score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
