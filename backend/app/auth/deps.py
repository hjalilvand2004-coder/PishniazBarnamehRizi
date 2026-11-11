# -*- coding: utf-8 -*-
"""وابستگی‌های FastAPI برای احراز هویت و کنترل دسترسی نقش‌محور (RBAC)"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from ..db import get_db
from . import config, roles
from .models import AppUser, AuthSession
from .sessions import get_active_session


def current_session(request: Request, db: DBSession = Depends(get_db)) -> AuthSession | None:
    return get_active_session(db, request.cookies.get(config.SESSION_COOKIE))


def current_user(session: AuthSession | None = Depends(current_session),
                 db: DBSession = Depends(get_db)) -> AppUser | None:
    if session is None:
        return None
    return db.get(AppUser, session.sub)


def require_authenticated(user: AppUser | None = Depends(current_user)) -> AppUser:
    if user is None:
        raise HTTPException(status_code=401, detail="ابتدا باید وارد سامانه شوید.")
    return user


def require_service(service_id: str):
    """وابستگی کنترل دسترسی نقش‌محور برای یک سرویس تحلیلی مشخص"""
    title = roles.SERVICE_TITLES.get(service_id, service_id)
    allowed = roles.SERVICE_ROLES.get(service_id, set(roles.ROLES.keys()))

    def dependency(user: AppUser = Depends(require_authenticated)) -> AppUser:
        if user.role not in allowed:
            from .roles import role_label
            raise HTTPException(
                status_code=403,
                detail=f"سرویس «{title}» برای نقش «{role_label(user.role)}» فعال نیست؛ "
                       f"در صورت نیاز با ادمین سامانه تماس بگیرید.",
            )
        return user

    return dependency
