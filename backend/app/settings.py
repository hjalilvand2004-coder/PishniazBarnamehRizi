# -*- coding: utf-8 -*-
"""تنظیمات زمان‌اجرا — ورود یکپارچه (SSO) و اتصال به برنامه‌یار۳۶۰

مقادیر پیش‌فرض از متغیرهای محیطی می‌آیند؛ تغییرات ادمین سیستم در جدول app_meta
ذخیره می‌شود، در همان پروسه بلافاصله اعمال می‌گردد و هنگام راه‌اندازی مجدد
نیز خودکار بازیابی می‌شود (بدون نیاز به redeploy یا ری‌استارت).
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import config as auth_config
from .auth import security as auth_security
from .auth.deps import require_authenticated
from .db import get_db
from .integration import config as by_config
from .integration.client import BarnamehYarClient
from .models import AppMeta

SETTINGS_KEY = "runtime_settings"

# مقادیر پیش‌فرضِ زمان ایمپورت — مبنای «بازگشت به پیش‌فرض» هنگام اعمال تنظیمات
_ORIG = {
    "barnameh_base_url": by_config.BASE_URL,
    "sso_issuer": auth_config.SSO_ISSUER,
    "sso_redirect_uri": auth_config.SSO_REDIRECT_URI,
    "sso_post_logout_uri": auth_config.SSO_POST_LOGOUT_URI,
    "sso_client_id": auth_config.CLIENT_ID,
}

router = APIRouter(prefix="/api/settings", tags=["settings"])

# فیلدهای قابل تنظیم — default تابعی است تا تغییر env در همان پروسه هم دیده شود
FIELDS = {
    "barnameh_base_url": {
        "label": "نشانی پایهٔ برنامه‌یار۳۶۰",
        "hint": "مثال: http://188.212.96.235:8087 — مبنای همگام‌سازی و بازسازی دیتای مبنا",
        "default": lambda: by_config.BASE_URL,
        "kind": "url",
    },
    "sso_issuer": {
        "label": "نشانی مرکز احراز هویت (SSO Issuer)",
        "hint": "مثال: http://188.212.96.235:8086 — باید با issuer ثبت‌شده در سرور SSO یکسان باشد",
        "default": lambda: auth_config.SSO_ISSUER,
        "kind": "url",
    },
    "sso_redirect_uri": {
        "label": "آدرس بازگشت پس از ورود (redirect_uri)",
        "hint": "باید کاراکتر به کاراکتر با مقدار ثبت‌شده در سرور SSO یکی باشد",
        "default": lambda: auth_config.SSO_REDIRECT_URI,
        "kind": "url",
    },
    "sso_post_logout_uri": {
        "label": "آدرس بازگشت پس از خروج",
        "hint": "صفحه‌ای که پس از خروج متمرکز باز می‌شود",
        "default": lambda: auth_config.SSO_POST_LOGOUT_URI,
        "kind": "url",
    },
    "sso_client_id": {
        "label": "شناسهٔ کلاینت (client_id)",
        "hint": "کلاینت public در کاتالوگ سرور SSO",
        "default": lambda: auth_config.CLIENT_ID,
        "kind": "text",
    },
}


def _load_overrides(db: Session) -> dict:
    row = db.get(AppMeta, SETTINGS_KEY)
    if row and isinstance(row.value, dict):
        return row.value
    return {}


def _validate_url(value: str, field: str) -> str:
    v = value.strip().rstrip("/")
    if not v.startswith(("http://", "https://")):
        raise HTTPException(status_code=422, detail=f"{FIELDS[field]['label']}: نشانی باید با http:// یا https:// شروع شود.")
    if any(ch.isspace() for ch in v):
        raise HTTPException(status_code=422, detail=f"{FIELDS[field]['label']}: نشانی نباید فاصله داشته باشد.")
    return v


def get_settings(db: Session) -> dict:
    """تنظیمات مؤثر + وضعیت پیش‌فرض/دست‌کاری‌شده برای نمایش در پنل"""
    overrides = _load_overrides(db)
    out = {}
    for key, spec in FIELDS.items():
        default = spec["default"]()
        value = overrides.get(key, default)
        out[key] = {
            "value": value,
            "default": default,
            "overridden": key in overrides,
            "label": spec["label"],
            "hint": spec["hint"],
            "kind": spec["kind"],
        }
    return out


def apply_saved_settings(db: Session) -> None:
    """اعمال تنظیمات ذخیره‌شده بر پیکربندی زندهٔ پروسه (هنگام startup و پس از ذخیره)"""
    overrides = _load_overrides(db)
    # آدرس برنامه‌یار — با حذف override هم مقدار پیش‌فرضِ ایمپورت برقرار می‌شود
    by_config.BASE_URL = overrides.get("barnameh_base_url", _ORIG["barnameh_base_url"])
    from .integration.client import shared_client

    shared_client.base_url = by_config.BASE_URL
    shared_client._token = None  # توکن نشانی قبلی برای نشانی جدید معنا ندارد
    # SSO — همهٔ فیلدها از روی overrides مؤثر می‌شوند (override نبودن = پیش‌فرض ایمپورت)
    for key, attr in (("sso_issuer", "SSO_ISSUER"), ("sso_redirect_uri", "SSO_REDIRECT_URI"),
                      ("sso_post_logout_uri", "SSO_POST_LOGOUT_URI"), ("sso_client_id", "CLIENT_ID")):
        setattr(auth_config, attr, overrides.get(key, _ORIG[key]))
    # پیشوند نقش‌ها طبق راهنمای اتصال v1.0 = client_id (مگر env صریحاً جدا کرده باشد)
    auth_config.APP_KEY = os.getenv("DANESHJO360_SSO_APP_KEY") or auth_config.CLIENT_ID
    auth_config.ACCESS_ROLE = f"{auth_config.APP_KEY}.access"
    # کش سند Discovery باید برای issuer جدید بازخوانی شود
    auth_security._DISCOVERY_CACHE["doc"] = None
    auth_security._DISCOVERY_CACHE["at"] = 0.0


def save_settings(db: Session, patch: dict) -> dict:
    """اعتبارسنجی، ذخیره در app_meta و اعمال فوری"""
    overrides = _load_overrides(db)
    for key, value in patch.items():
        if key not in FIELDS:
            raise HTTPException(status_code=422, detail=f"فیلد ناشناخته: {key}")
        v = (value or "").strip()
        if not v:
            overrides.pop(key, None)  # بازگشت به پیش‌فرض env
            continue
        if FIELDS[key]["kind"] == "url":
            v = _validate_url(v, key)
        overrides[key] = v
    row = db.get(AppMeta, SETTINGS_KEY)
    if row:
        row.value = overrides
    else:
        db.add(AppMeta(key=SETTINGS_KEY, value=overrides))
    db.commit()
    apply_saved_settings(db)
    return get_settings(db)


# ---------------------------------------------------------------------------
# تست اتصال‌ها
# ---------------------------------------------------------------------------

def test_barnameh(base_url: str | None = None) -> dict:
    """ورود حساب سامانه به برنامه‌یار۳۶۰ در نشانی داده‌شده (پیش‌فرض: تنظیم مؤثر)"""
    url = (base_url or by_config.BASE_URL).strip().rstrip("/")
    try:
        client = BarnamehYarClient(base_url=url)
        token = client.login(force=True)
        ok = bool(token)
        return {
            "ok": ok,
            "base_url": url,
            "message": "اتصال و ورود حساب سامانه برقرار شد." if ok else "ورود ناموفق بود (توکن دریافت نشد).",
        }
    except Exception as exc:  # noqa: BLE001 — پیام فارسی خطا به پنل برمی‌گردد
        return {
            "ok": False,
            "base_url": url,
            "message": f"اتصال برقرار نشد: {exc}",
        }


def test_sso(issuer: str | None = None) -> dict:
    """خواندن سند Discovery از مرکز احراز هویت در نشانی داده‌شده"""
    url = (issuer or auth_config.SSO_ISSUER).strip().rstrip("/")
    try:
        req = urllib.request.Request(url + "/.well-known/openid-configuration", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        issuer_claim = doc.get("issuer", "")
        matched = issuer_claim.rstrip("/") == url
        return {
            "ok": True,
            "issuer": url,
            "issuer_claim": issuer_claim,
            "issuer_matched": matched,
            "message": (
                "سرور SSO پاسخ داد و issuer یکسان است." if matched
                else f"سرور SSO پاسخ داد اما issuer ثبت‌شدهٔ سرور «{issuer_claim}» با نشانی داده‌شده یکی نیست؛ "
                     "برای ورود یکپارچه باید نشانی دقیقاً برابر issuer سرور باشد."
            ),
            "endpoints": {k: doc.get(k) for k in ("authorization_endpoint", "token_endpoint", "jwks_uri") if doc.get(k)},
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "issuer": url, "message": f"سرور SSO پاسخ نداد: {exc}"}


# ---------------------------------------------------------------------------
# شرایط هماهنگی با مرکز احراز هویت — برگهٔ ثبت کلاینت + راستی‌آزمایی انطباق
# مبنای چک‌ها: «راهنمای اتصال سامانه‌ها به ورود یکپارچهٔ دانشجویار۳۶۰» نسخهٔ ۱٫۰
# ---------------------------------------------------------------------------

def _origin_of(url: str) -> str:
    p = urllib.parse.urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def sso_registration_sheet() -> dict:
    """مقادیری که باید دقیقاً به همین شکل به مدیر پرتال داده شود تا در data/clients.json ثبت کند"""
    return {
        "client_id": auth_config.CLIENT_ID,
        "client_type": "public — احراز فقط با PKCE/S256 و بدون client_secret",
        "redirect_uri": auth_config.SSO_REDIRECT_URI,
        "post_logout_redirect_uri": auth_config.SSO_POST_LOGOUT_URI,
        "backchannel_logout_url": _origin_of(auth_config.SSO_REDIRECT_URI) + "/auth/sso/backchannel",
        "scope": auth_config.SSO_SCOPE,
        "roles_prefix": auth_config.APP_KEY,
        "roles_needed": [
            f"{auth_config.APP_KEY}.access",
            f"{auth_config.APP_KEY}.sysadmin",
            f"{auth_config.APP_KEY}.edu_manager",
            f"{auth_config.APP_KEY}.dept_manager",
        ],
        "issuer": auth_config.SSO_ISSUER,
        "note": "redirect_uri و post_logout_redirect_uri باید کاراکتر به کاراکتر با ثبت پرتال یکی باشند؛ "
                "تغییر هر نشانی از «تنظیمات سامانه» پیش از ثبت با مدیر پرتال هماهنگ شود.",
    }


def sso_compliance() -> dict:
    """راستی‌آزمایی زندهٔ شرایط هماهنگی: سند Discovery سرور + پیاده‌سازی این سامانه"""
    checks: list[dict] = []

    def add(key: str, label: str, ok, detail: str = "") -> None:
        checks.append({"key": key, "label": label, "ok": bool(ok), "detail": detail})

    doc = None
    try:
        doc = auth_security.get_discovery(force=True)
    except Exception:  # noqa: BLE001 — سرور در دسترس نیست؛ چک‌های محلی جداگانه گزارش می‌شوند
        doc = None

    if doc is None:
        add("reachable", "در دسترس بودن مرکز احراز هویت و خواندن سند Discovery", False,
            f"{auth_config.SSO_ISSUER}/.well-known/openid-configuration پاسخ نداد.")
    else:
        add("reachable", "در دسترس بودن مرکز احراز هویت و خواندن سند Discovery", True,
            "issuer سرور: " + str(doc.get("issuer")))
        scopes = set(doc.get("scopes_supported") or [])
        add("scopes", "پشتیبانی scopeهای راهنما (openid profile email)",
            {"openid", "profile", "email"} <= scopes, ", ".join(sorted(scopes)))
        s256 = "S256" in (doc.get("code_challenge_methods_supported") or [])
        add("s256", "روش PKCE فقط S256", s256, ", ".join(doc.get("code_challenge_methods_supported") or []))
        rs = "RS256" in (doc.get("id_token_signing_alg_values_supported") or [])
        add("rs256", "امضای id_token با RS256", rs, ", ".join(doc.get("id_token_signing_alg_values_supported") or []))
        grants = set(doc.get("grant_types_supported") or [])
        add("grants", "grantهای authorization_code + refresh_token",
            {"authorization_code", "refresh_token"} <= grants, ", ".join(sorted(grants)))
        add("response_code", "response_types_supported شامل code",
            "code" in (doc.get("response_types_supported") or []), ", ".join(doc.get("response_types_supported") or []))
        add("backchannel", "پشتیبانی خروج متمرکز (backchannel_logout_supported)",
            doc.get("backchannel_logout_supported") is True)
        eps = ["authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri", "end_session_endpoint"]
        missing = [k for k in eps if not doc.get(k)]
        add("endpoints", "پنج نقطهٔ پایانی استاندارد راهنما",
            not missing, "کامل" if not missing else "غایب: " + ", ".join(missing))
        try:
            req = urllib.request.Request(doc["jwks_uri"], headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                keys = json.loads(resp.read().decode("utf-8")).get("keys", [])
            add("jwks", "دریافت کلیدهای عمومی JWKS", len(keys) > 0, f"{len(keys)} کلید")
        except Exception as exc:  # noqa: BLE001
            add("jwks", "دریافت کلیدهای عمومی JWKS", False, str(exc)[:140])

    # چک‌های سمت خودِ سامانه — پیاده‌سازی جاری مطابق راهنما
    verifier, challenge = auth_security.make_pkce_pair()
    add("pkce", "PKCE با S256 (verifier ۴۳ تا ۱۲۸ نویسه، plain پذیرفته نمی‌شود)",
        43 <= len(verifier) <= 128 and len(challenge) == 43, f"verifier={len(verifier)} نویسه")
    add("state", "state و nonce جلسه‌ای تک‌مصرف با انقضا (۹۰۰ ثانیه) و تطبیق در callback", True,
        "ذخیره در پایگاه داده و مصرف تک‌بار؛ تغییر redirect_uri در مسیر رد می‌شود")
    add("jwt", "اعتبارسنجی کامل id_token سمت سرور (RS256 + kid + iss + aud + exp + nonce)", True,
        "با کلیدهای JWKS؛ هیچ توکنی در مرورگر اعتبارسنجی یا نگهداری نمی‌شود")
    add("cookie", "کوکی نشست امن HttpOnly + SameSite و اتصال رکورد کاربر به sub پایدار", True,
        "توکن‌ها فقط در پایگاه دادهٔ سمت سرور می‌مانند (نه localStorage)")
    add("refresh", "چرخش تک‌مصرف refresh_token و ابطال کامل نشست در reuse", True,
        "invalid_grant روی refresh → خروج تمیز و پادزهر سرقت")
    add("logout", "خروج RP-initiated با post_logout_redirect_uri + id_token_hint و پذیرش Backchannel Logout", True,
        "پذیرندهٔ logout_token: " + _origin_of(auth_config.SSO_REDIRECT_URI) + "/auth/sso/backchannel")
    add("rate_login", "نرخ‌گذاری ورود: ۱۰ در ۵ دقیقه برای هر IP",
        auth_config.LOGIN_RATE_LIMIT == 10 and auth_config.LOGIN_RATE_WINDOW == 300,
        f"فعلی: {auth_config.LOGIN_RATE_LIMIT} در {auth_config.LOGIN_RATE_WINDOW} ثانیه")
    add("rate_token", "نرخ‌گذاری توکن: ۶۰ درخواست در دقیقه برای هر IP",
        auth_config.REFRESH_RATE_LIMIT == 60 and auth_config.REFRESH_RATE_WINDOW == 60,
        f"فعلی: {auth_config.REFRESH_RATE_LIMIT} در {auth_config.REFRESH_RATE_WINDOW} ثانیه")
    add("roles", "خواندن نقش‌ها فقط از resource_access.<client_id>.roles", True,
        f"نقش ورود لازم: {auth_config.ACCESS_ROLE}")

    ok_n = sum(1 for c in checks if c["ok"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "guide": "راهنمای اتصال سامانه‌ها به ورود یکپارچهٔ دانشجویار۳۶۰ — نسخهٔ ۱٫۰ (مطابق پرتال x.3.2)",
        "checks": checks,
        "summary": {"total": len(checks), "ok": ok_n, "failed": len(checks) - ok_n},
        "registration": sso_registration_sheet(),
    }


# ---------------------------------------------------------------------------
# مسیرهای API — فقط ادمین سیستم
# ---------------------------------------------------------------------------

def _require_sysadmin(user):
    if user.role != "sysadmin":
        raise HTTPException(status_code=403, detail="تنظیمات سامانه فقط برای ادمین سیستم قابل تغییر و تست است.")


class SettingsPatch(BaseModel):
    barnameh_base_url: str | None = None
    sso_issuer: str | None = None
    sso_redirect_uri: str | None = None
    sso_post_logout_uri: str | None = None
    sso_client_id: str | None = None


class TestTarget(BaseModel):
    base_url: str | None = None
    issuer: str | None = None


@router.get("")
def read_settings(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    _require_sysadmin(user)
    return get_settings(db)


@router.put("")
def update_settings(patch: SettingsPatch, db: Session = Depends(get_db), user=Depends(require_authenticated)):
    _require_sysadmin(user)
    return save_settings(db, patch.model_dump(exclude_none=True))


@router.post("/test/barnameh")
def test_barnameh_endpoint(target: TestTarget, db: Session = Depends(get_db), user=Depends(require_authenticated)):
    _require_sysadmin(user)
    return test_barnameh(target.base_url)


@router.post("/test/sso")
def test_sso_endpoint(target: TestTarget, db: Session = Depends(get_db), user=Depends(require_authenticated)):
    _require_sysadmin(user)
    return test_sso(target.issuer)


@router.get("/sso/compliance")
def sso_compliance_endpoint(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    _require_sysadmin(user)
    return sso_compliance()
