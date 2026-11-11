# -*- coding: utf-8 -*-
"""مدیریت نشست محلی — ایجاد، خواندن، ابطال و پاکسازی دوره‌ای"""
import secrets
import time
import uuid

from sqlalchemy.orm import Session as DBSession

from . import config
from .models import AppUser, AuthFlow, AuthSession


def now_ts() -> int:
    return int(time.time())


def create_session(db: DBSession, *, sub: str, sid: str | None, role: str, source: str,
                   id_token: str | None, access_token: str | None, refresh_token: str | None,
                   access_exp: int | None, refresh_exp: int | None) -> AuthSession:
    """نشست جدید با شناسه تصادفی — کوکی فقط همین شناسه را می‌بیند (httpOnly)"""
    ttl = config.SESSION_TTL_HOURS * 3600
    sess = AuthSession(
        id=secrets.token_urlsafe(32),
        sub=sub,
        sid=sid,
        role=role,
        source=source,
        id_token=id_token,
        access_token=access_token,
        refresh_token=refresh_token,
        token_family=str(uuid.uuid4()) if refresh_token else None,
        access_exp=access_exp,
        refresh_exp=refresh_exp,
        created_at=now_ts(),
        expires_at=now_ts() + ttl,
        revoked=False,
    )
    db.add(sess)
    db.commit()
    return sess


def get_active_session(db: DBSession, session_id: str | None) -> AuthSession | None:
    if not session_id:
        return None
    sess = db.get(AuthSession, session_id)
    if sess is None or sess.revoked or sess.expires_at < now_ts():
        return None
    return sess


def revoke_session(db: DBSession, sess: AuthSession) -> None:
    sess.revoked = True
    db.commit()


def revoke_by_sid_or_sub(db: DBSession, sid: str | None = None, sub: str | None = None) -> int:
    """ابطال نشست‌های هم‌شناسه (برای خروج یکپارچه Backchannel)"""
    now = now_ts()
    q = db.query(AuthSession).filter(AuthSession.revoked.is_(False), AuthSession.expires_at >= now)
    conds = []
    if sid:
        conds.append(AuthSession.sid == sid)
    if sub:
        conds.append(AuthSession.sub == sub)
    if not conds:
        return 0
    count = 0
    for sess in q.filter(*conds).all():
        sess.revoked = True
        count += 1
    if count:
        db.commit()
    return count


def cleanup_expired(db: DBSession) -> None:
    """پاکسازی جریان‌های منقضی و نشست‌های قدیمی (فراخوانی فرصتی پس از ورود/نوسازی)"""
    now = now_ts()
    db.query(AuthFlow).filter(AuthFlow.expires_at < now).delete(synchronize_session=False)
    db.query(AuthSession).filter(AuthSession.expires_at < now - 86400).delete(synchronize_session=False)
    db.commit()


def upsert_user(db: DBSession, *, sub: str, username: str, name: str, email: str | None,
                role: str, source: str) -> AppUser:
    """ساخت/به‌روزرسانی حساب محلی بر پایه sub — نه ایمیل (جلوگیری از حساب تکراری)"""
    user = db.get(AppUser, sub)
    if user is None:
        user = AppUser(
            sub=sub, username=username, name=name, email=email,
            role=role, source=source, created_at=now_ts(), last_login_at=now_ts(),
        )
        db.add(user)
    else:
        user.username = username
        user.name = name
        if email:
            user.email = email
        user.role = role
        user.last_login_at = now_ts()
    db.commit()
    return user


DEMO_USERS = [
    {"sub": "demo-sysadmin", "username": "sysadmin-demo", "name": "مدیر سیستم (نمایشی)",
     "role": "sysadmin", "email": "sysadmin-demo@daneshjo360.local"},
    {"sub": "demo-dept_manager", "username": "dept-manager-demo", "name": "مدیرگروه (نمایشی)",
     "role": "dept_manager", "email": "dept-manager-demo@daneshjo360.local"},
    {"sub": "demo-edu_manager", "username": "edu-manager-demo", "name": "مدیرآموزش (نمایشی)",
     "role": "edu_manager", "email": "edu-manager-demo@daneshjo360.local"},
]


def ensure_demo_users(db: DBSession) -> None:
    """ایجاد حساب‌های نمایشی برای ارزیابی سامانه در نبود سرور SSO"""
    for item in DEMO_USERS:
        if db.get(AppUser, item["sub"]) is None:
            db.add(AppUser(
                sub=item["sub"], username=item["username"], name=item["name"],
                email=item["email"], role=item["role"], source="demo", created_at=now_ts(),
            ))
    db.commit()
