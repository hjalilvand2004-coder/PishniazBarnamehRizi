# -*- coding: utf-8 -*-
"""مدل‌های احراز هویت: کاربران سامانه، نشست‌های محلی و جریان‌های در حال اجرا

* توکن‌ها فقط سمت سرور نگهداری می‌شوند (هرگز به مرورگر داده نمی‌شوند).
* مرورگر فقط یک شناسهٔ نشست تصادفی در کوکی httpOnly می‌بیند.
* حساب محلی بر پایهٔ «sub» ساخته می‌شود (نه ایمیل) تا حساب تکراری ساخته نشود.
"""
from sqlalchemy import Boolean, Column, Integer, String, Text

from ..db import Base


class AppUser(Base):
    """کاربر محلی سامانه — بر پایه sub پایدار SSO یا حساب نمایشی"""
    __tablename__ = "app_users"

    sub = Column(String(64), primary_key=True)
    username = Column(String(64), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    role = Column(String(32), nullable=False, default="edu_manager")
    source = Column(String(16), nullable=False, default="sso")  # sso / demo
    created_at = Column(Integer, nullable=False, default=0)
    last_login_at = Column(Integer, nullable=True)


class AuthFlow(Base):
    """جریان ورود در حال اجرا — نگهداری code_verifier/state/nonce بین دو پرش"""
    __tablename__ = "auth_flows"

    state = Column(String(64), primary_key=True)
    code_verifier = Column(String(128), nullable=False)
    nonce = Column(String(64), nullable=False)
    created_at = Column(Integer, nullable=False, default=0)
    expires_at = Column(Integer, nullable=False, default=0)


class AuthSession(Base):
    """نشست محلی کاربر — توکن‌ها فقط همین‌جا (سمت سرور) ذخیره می‌شوند"""
    __tablename__ = "auth_sessions"

    id = Column(String(64), primary_key=True)   # مقدار تصادفی داخل کوکی httpOnly
    sub = Column(String(64), nullable=False, index=True)
    sid = Column(String(64), nullable=True, index=True)  # شناسه نشست مرکز احراز (برای خروج یکپارچه)
    role = Column(String(32), nullable=False)
    source = Column(String(16), nullable=False, default="sso")  # sso / demo
    id_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_family = Column(String(36), nullable=True, index=True)  # خانواده refresh برای پادزهر سرقت
    access_exp = Column(Integer, nullable=True)
    refresh_exp = Column(Integer, nullable=True)
    last_refresh_at = Column(Integer, nullable=True)
    created_at = Column(Integer, nullable=False, default=0)
    expires_at = Column(Integer, nullable=False, default=0)
    revoked = Column(Boolean, nullable=False, default=False)
