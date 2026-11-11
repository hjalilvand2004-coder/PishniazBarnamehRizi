# -*- coding: utf-8 -*-
"""مسیرهای احراز هویت یکپارچه (SSO) دانشجو۳۶۰

جریان استاندارد OpenID Connect — Authorization Code + PKCE (S256) با ارائه‌دهنده هویت
مرکزی «دانشجویار۳۶۰»؛ بدون رمز عبور در خود سامانه و بدون ذخیره هیچ رمزی.

  GET  /auth/sso/login        شروع جریان (تولید PKCE/state/nonce و ریدایرکت به مرکز احراز)
  GET  /auth/sso/callback     بازگشت از مرکز احراز — تبادل کد، اعتبارسنجی توکن، ساخت نشست
  GET  /auth/logout           خروج کاربر (RP-initiated) — بستن نشست مرکز احراز هم می‌شود
  POST /auth/sso/backchannel  خروج متمرکز از SSO (Backchannel Logout) — بدون نشست کاربر هم پاسخ می‌دهد
  GET  /api/auth/config       پیکربندی عمومی برای صفحه ورود
  GET  /api/auth/me           کاربر جاری + نقش و دسترسی‌ها
  POST /api/auth/demo-login   ورود نمایشی برای ارزیابی (قابل خاموش کردن با متغیر محیطی)
  POST /api/auth/refresh      نوسازی توکن با چرخش تک‌مصرف
"""
import secrets
import time
import urllib.parse

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..db import get_db
from . import config, roles
from .security import (
    SSOError,
    SSORateLimit,
    get_discovery,
    make_pkce_pair,
    rate_limit_ok,
    refresh_exchange,
    token_exchange,
    verify_rs256_jwt,
)
from .sessions import (
    cleanup_expired,
    create_session,
    get_active_session,
    now_ts,
    revoke_by_sid_or_sub,
    revoke_session,
    upsert_user,
)
from .models import AppUser, AuthFlow, AuthSession

router = APIRouter(tags=["auth"])

ERROR_MESSAGES = {
    "no_access": "دسترسی به این سامانه برای شما ثبت نشده است؛ برای دریافت دسترسی با مدیر SSO تماس بگیرید (نقش daneshjo.access).",
    "sso": "ارتباط با مرکز احراز هویت سازمانی برقرار نشد؛ لطفاً کمی بعد دوباره تلاش کنید.",
    "state": "جریان ورود منقضی یا نامعتبر بود؛ لطفاً دوباره وارد شوید.",
    "token": "تبادل توکن یا اعتبارسنجی ورود ناموفق بود؛ لطفاً دوباره وارد شوید.",
    "rate": config.RATE_MESSAGE,
    "denied": "ورود از سمت مرکز احراز هویت پذیرفته نشد؛ لطفاً دوباره تلاش کنید.",
}


# ---------------------------------------------------------------------------
# ابزارهای کمکی
# ---------------------------------------------------------------------------

def _login_error(error_key: str) -> RedirectResponse:
    return RedirectResponse(f"/login?error={urllib.parse.quote(error_key)}", status_code=302)


def _set_session_cookie(response: RedirectResponse, request: Request, value: str) -> None:
    if config.COOKIE_SECURE_ENV == "1":
        secure = True
    elif config.COOKIE_SECURE_ENV == "0":
        secure = False
    else:
        secure = request.url.scheme == "https"
    response.set_cookie(
        config.SESSION_COOKIE,
        value,
        max_age=config.SESSION_TTL_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return (forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "?"))


def _token_exps(tokens: dict) -> tuple[int | None, int | None]:
    """استخراج انقضای access/refresh — توکن تازه مستقیماً از endpoint رسمی سرور رسیده است"""
    access_exp = refresh_exp = None
    try:
        if tokens.get("access_token"):
            access_exp = jwt.decode(
                tokens["access_token"], options={"verify_signature": False}
            ).get("exp")
        if tokens.get("refresh_token"):
            refresh_exp = jwt.decode(
                tokens["refresh_token"], options={"verify_signature": False}
            ).get("exp")
    except Exception:  # noqa: BLE001 — اگر JWT نبود، از عمر اعلامی پاسخ استفاده می‌شود
        pass
    if access_exp is None:
        access_exp = now_ts() + int(tokens.get("expires_in") or config.ACCESS_TOKEN_TTL)
    if refresh_exp is None:
        refresh_exp = now_ts() + int(tokens.get("refresh_expires_in") or config.REFRESH_TOKEN_TTL)
    return access_exp, refresh_exp


def _user_payload(user: AppUser) -> dict:
    return {
        "sub": user.sub,
        "username": user.username,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "role_label": roles.role_label(user.role),
        "source": user.source,
        "permissions": roles.role_services(user.role),
    }


# ---------------------------------------------------------------------------
# پیکربندی عمومی صفحه ورود + کاربر جاری
# ---------------------------------------------------------------------------

@router.get("/api/auth/config")
def auth_config():
    return {
        "app_name": config.APP_NAME,
        "demo_enabled": config.DEMO_LOGIN_ENABLED,
        "sso": {
            "issuer": config.SSO_ISSUER,
            "client_id": config.CLIENT_ID,
            "app_key": config.APP_KEY,
            "required_role": config.ACCESS_ROLE,
            "login_url": "/auth/sso/login",
        },
        "roles": [
            {"id": rid, "label": item["label"], "desc": item["desc"], "icon": item["icon"],
             "services_count": len(roles.role_services(rid)) - 1}
            for rid, item in roles.ROLES.items()
        ],
    }


@router.get("/api/auth/me")
def auth_me(request: Request, db: DBSession = Depends(get_db)):
    sess = get_active_session(db, request.cookies.get(config.SESSION_COOKIE))
    if sess is None:
        raise HTTPException(status_code=401, detail="نشست فعالی وجود ندارد؛ لطفاً وارد شوید.")
    user = db.get(AppUser, sess.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="کاربر نشست یافت نشد؛ لطفاً دوباره وارد شوید.")
    return {
        "authenticated": True,
        "user": _user_payload(user),
        "session": {"source": sess.source, "expires_at": sess.expires_at},
    }


# ---------------------------------------------------------------------------
# ورود نمایشی (ارزیابی سامانه بدون سرور SSO) — قابل خاموش کردن با DANESHJO360_DEMO_LOGIN=0
# ---------------------------------------------------------------------------

class DemoLoginInput(BaseModel):
    role: str


@router.post("/api/auth/demo-login")
def demo_login(payload: DemoLoginInput, request: Request, db: DBSession = Depends(get_db)):
    if not config.DEMO_LOGIN_ENABLED:
        raise HTTPException(status_code=403, detail="ورود نمایشی خاموش است؛ ورود فقط از طریق SSO سازمانی انجام می‌شود.")
    if payload.role not in roles.VALID_ROLES:
        raise HTTPException(status_code=400, detail="نقش انتخابی معتبر نیست.")
    if not rate_limit_ok(f"demo:{_client_key(request)}", config.DEMO_RATE_LIMIT, config.DEMO_RATE_WINDOW):
        raise HTTPException(status_code=429, detail=config.RATE_MESSAGE)
    cleanup_expired(db)
    user = upsert_user(
        db,
        sub=f"demo-{payload.role}",
        username=f"{payload.role}-demo",
        name=roles.ROLES[payload.role]["label"] + " (نمایشی)",
        email=None,
        role=payload.role,
        source="demo",
    )
    sess = create_session(
        db, sub=user.sub, sid=None, role=user.role, source="demo",
        id_token=None, access_token=None, refresh_token=None,
        access_exp=None, refresh_exp=None,
    )
    response = JSONResponse(content={"authenticated": True, "user": _user_payload(user)})
    _set_session_cookie(response, request, sess.id)
    return response


@router.post("/api/auth/refresh")
def auth_refresh(request: Request, db: DBSession = Depends(get_db), force: bool = False):
    """نوسازی توکن با چرخش تک‌مصرف — reuse توکن کهنه به خروج تمیز می‌رسد"""
    sess = get_active_session(db, request.cookies.get(config.SESSION_COOKIE))
    if sess is None:
        raise HTTPException(status_code=401, detail="نشست فعالی وجود ندارد.")
    if not rate_limit_ok(f"refresh:{_client_key(request)}", config.REFRESH_RATE_LIMIT, config.REFRESH_RATE_WINDOW):
        raise HTTPException(status_code=429, detail=config.RATE_MESSAGE)
    if not sess.refresh_token:
        return {"refreshed": False, "note": "نشست نمایشی است و نیاز به نوسازی توکن ندارد."}
    if not force and sess.access_exp and sess.access_exp - 90 > now_ts():
        return {"refreshed": False, "note": "توکن دسترسی هنوز معتبر است."}
    try:
        tokens = refresh_exchange(sess.refresh_token)
    except SSOError:
        # invalid_grant (مثلاً استفاده دوباره از refresh_token مصرف‌شده) → پادزهر سرقت: خروج تمیز
        revoke_session(db, sess)
        raise HTTPException(status_code=401, detail="نشست اعتبار خود را از دست داد؛ لطفاً دوباره وارد شوید.")
    access_exp, refresh_exp = _token_exps(tokens)
    sess.access_token = tokens.get("access_token") or sess.access_token
    sess.id_token = tokens.get("id_token") or sess.id_token
    sess.refresh_token = tokens.get("refresh_token") or sess.refresh_token  # چرخش: جایگزینی فوری
    sess.access_exp = access_exp
    sess.refresh_exp = refresh_exp
    sess.last_refresh_at = now_ts()
    db.commit()
    return {"refreshed": True, "access_exp": sess.access_exp}


# ---------------------------------------------------------------------------
# شروع جریان ورود SSO
# ---------------------------------------------------------------------------

@router.get("/auth/sso/login")
def sso_login(request: Request, db: DBSession = Depends(get_db)):
    if not rate_limit_ok(f"login:{_client_key(request)}", config.LOGIN_RATE_LIMIT, config.LOGIN_RATE_WINDOW):
        return _login_error("rate")
    try:
        get_discovery()
        auth_endpoint = get_discovery()["authorization_endpoint"]
    except SSOError:
        # سرور احراز هویت در دسترس نیست → بازگشت به صفحه ورود با پیام فارسی
        return _login_error("sso")
    verifier, challenge = make_pkce_pair()
    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)
    db.add(AuthFlow(
        state=state, code_verifier=verifier, nonce=nonce,
        created_at=now_ts(), expires_at=now_ts() + 900,
    ))
    db.commit()
    params = {
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.SSO_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(auth_endpoint + "?" + urllib.parse.urlencode(params), status_code=302)


# ---------------------------------------------------------------------------
# بازگشت از مرکز احراز — تبادل کد، اعتبارسنجی توکن، حساب محلی و نشست
# ---------------------------------------------------------------------------

@router.get("/auth/sso/callback")
def sso_callback(request: Request, db: DBSession = Depends(get_db)):
    # خطای صریح سرور (مثل access_denied) بدون فراخوانی endpoint توکن
    oauth_error = request.query_params.get("error")
    if oauth_error:
        return _login_error("denied")

    state = request.query_params.get("state", "")
    code = request.query_params.get("code", "")
    if request.query_params.get("iss") and request.query_params["iss"] != config.SSO_ISSUER:
        return _login_error("state")

    flow = db.get(AuthFlow, state)
    if flow is None or flow.expires_at < now_ts():
        return _login_error("state")
    db.delete(flow)  # مصرف تک‌بار state
    db.commit()

    if not rate_limit_ok(f"login:{_client_key(request)}", config.LOGIN_RATE_LIMIT, config.LOGIN_RATE_WINDOW):
        return _login_error("rate")

    try:
        tokens = token_exchange(code, flow.code_verifier)
        claims = verify_rs256_jwt(
            tokens.get("id_token", ""),
            audience=config.CLIENT_ID,
            nonce=flow.nonce,
            require={"exp", "iat", "sub", "aud"},
        )
    except SSORateLimit:
        return _login_error("rate")
    except SSOError:
        return _login_error("token")

    token_roles = ((claims.get("resource_access") or {}).get(config.CLIENT_ID) or {}).get("roles", [])
    role = roles.resolve_role_from_token(token_roles, config.ACCESS_ROLE, config.DEFAULT_ROLE)
    if role is None:
        return _login_error("no_access")

    cleanup_expired(db)
    user = upsert_user(
        db,
        sub=claims["sub"],
        username=claims.get("preferred_username") or claims["sub"][:12],
        name=claims.get("name") or claims.get("preferred_username") or "کاربر سامانه",
        email=claims.get("email"),
        role=role,
        source="sso",
    )
    access_exp, refresh_exp = _token_exps(tokens)
    sess = create_session(
        db,
        sub=user.sub,
        sid=claims.get("sid"),
        role=user.role,
        source="sso",
        id_token=tokens.get("id_token"),
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        access_exp=access_exp,
        refresh_exp=refresh_exp,
    )
    response = RedirectResponse("/", status_code=302)  # پس از ورود: شروع سامانه روی داشبورد
    _set_session_cookie(response, request, sess.id)
    return response


# ---------------------------------------------------------------------------
# خروج یکپارچه (RP-initiated) — نشست مرکز احراز هم بسته می‌شود
# ---------------------------------------------------------------------------

def _end_session_url(id_token: str | None) -> str:
    params = {"post_logout_redirect_uri": config.SSO_POST_LOGOUT_URI}
    if id_token:
        params["id_token_hint"] = id_token
    try:
        endpoint = get_discovery()["end_session_endpoint"]
    except SSOError:
        endpoint = config.SSO_ISSUER.rstrip("/") + "/protocol/openid-connect/logout"
    return endpoint + "?" + urllib.parse.urlencode(params)


@router.get("/auth/logout", include_in_schema=False)
@router.get("/logout", include_in_schema=False)
def logout(request: Request, db: DBSession = Depends(get_db)):
    sess = get_active_session(db, request.cookies.get(config.SESSION_COOKIE))
    id_token = None
    if sess is not None:
        id_token = sess.id_token
        revoke_session(db, sess)
    target = _end_session_url(id_token) if (id_token and sess and sess.source == "sso") else "/login?logout=1"
    response = RedirectResponse(target, status_code=302)
    response.delete_cookie(config.SESSION_COOKIE, path="/")
    return response


# ---------------------------------------------------------------------------
# خروج متمرکز از SSO — Backchannel Logout (بدون نشست کاربر هم باید پاسخ دهد)
# ---------------------------------------------------------------------------

@router.post("/auth/sso/backchannel")
async def backchannel_logout(request: Request, db: DBSession = Depends(get_db)):
    body = (await request.body()).decode("utf-8", errors="replace")
    fields = urllib.parse.parse_qs(body)
    logout_token = (fields.get("logout_token") or [""])[0]
    if not logout_token:
        raise HTTPException(status_code=400, detail="logout_token missing")
    try:
        claims = verify_rs256_jwt(logout_token, audience=config.CLIENT_ID,
                                  require={"exp", "iat", "iss", "sub"})
    except SSOError:
        raise HTTPException(status_code=400, detail="invalid logout_token")
    events = claims.get("events") or {}
    if config.BACKCHANNEL_LOGOUT_EVENT not in events:
        raise HTTPException(status_code=400, detail="not a backchannel logout event")
    if "nonce" in claims:
        # طبق مشخصات، logout_token نباید nonce داشته باشد
        raise HTTPException(status_code=400, detail="logout_token must not contain nonce")
    sid = claims.get("sid")
    sub = claims.get("sub")
    revoke_by_sid_or_sub(db, sid=sid, sub=sub)
    return Response(status_code=204)
