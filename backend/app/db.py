# -*- coding: utf-8 -*-
"""لایه دیتابیس — SQLAlchemy 2

پیش‌فرض SQLite است (بدون نیاز به نصب سرویس جانبی)؛ برای استفاده از PostgreSQL یا MySQL
تنها کافی است متغیر محیطی DANESHJO360_DATABASE_URL را تنظیم کنید:

    export DANESHJO360_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/daneshjo360"
    export DANESHJO360_DATABASE_URL="mysql+pymysql://user:pass@host:3306/daneshjo360"

ایجاد جداول و بارگذاری داده نمونه در نخستین اجرا به‌صورت خودکار انجام می‌شود.
برای بازتولید داده نمونه:  DANESHJO360_RESEED=1
"""
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./daneshjo360.db"


def _resolve_url():
    """انتخاب آدرس پایگاه داده: ابتدا متغیر اختصاصی سامانه، سپس DATABASE_URL
    (در صورت سازگار بودن با SQLAlchemy)، و در نهایت SQLite محلی."""
    custom = os.getenv("DANESHJO360_DATABASE_URL")
    if custom:
        return custom
    url = DATABASE_URL
    # آدرس‌های غیر SQLAchemy (مثل file: سبک Prisma) نادیده گرفته می‌شوند
    if url.startswith("file:"):
        return "sqlite:///./daneshjo360.db"
    return url


SQLALCHEMY_URL = _resolve_url()


def _ensure_sqlite_dir() -> None:
    """ساخت پوشهٔ والد فایل SQLite پیش از نخستین اتصال — اجرای پرتیبل حتی بدون
    پوشهٔ data هم بالا می‌آید (پیشگیری از خطای unable to open database file)."""
    if not SQLALCHEMY_URL.startswith("sqlite"):
        return
    rest = SQLALCHEMY_URL[len("sqlite:///"):]
    if not rest or rest.startswith(":memory:") or rest.startswith("file:"):
        return
    try:
        parent = Path(rest).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # مسیر معیوب را sqlite خودش با پیام واضح گزارش می‌کند


_ensure_sqlite_dir()

connect_args = {"check_same_thread": False} if SQLALCHEMY_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    """کلاس پایه همه مدل‌های ORM."""


def get_db():
    """سشن پایگاه داده برای تزریق در مسیرهای FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(force_seed: bool | None = None) -> bool:
    """ایجاد جداول و (در صورت خالی بودن یا force) بارگذاری داده نمونه.

    خروجی: True اگر داده نمونه بارگذاری شد.
    """
    from . import seed  # ایمپورت داخل تابع برای پرهیز از وابستگی حلقوی

    Base.metadata.create_all(engine)
    if force_seed is None:
        force_seed = os.getenv("DANESHJO360_RESEED", "").lower() in ("1", "true", "yes")
    return seed.seed_if_empty(engine, force=force_seed)
