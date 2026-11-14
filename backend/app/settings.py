# -*- coding: utf-8 -*-
"""تنظیمات زمان‌اجرا — ورود یکپارچه (SSO) و اتصال به برنامه‌یار۳۶۰

مقادیر پیش‌فرض از متغیرهای محیطی می‌آیند؛ تغییرات ادمین سیستم در جدول app_meta
ذخیره می‌شود، در همان پروسه بلافاصله اعمال می‌گردد و هنگام راه‌اندازی مجدد
نیز خودکار بازیابی می‌شود (بدون نیاز به redeploy یا ری‌استارت).
"""
from __future__ import annotations

import json
import time
import urllib.request

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import config as auth_config
from .auth.deps import require_authenticated
from .db import get_db
from .integration import config as by_config
from .integration.client import BarnamehYarClient
from .models import AppMeta

SETTINGS_KEY = "runtime_settings"

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
    if "barnameh_base_url" in overrides:
        by_config.BASE_URL = overrides["barnameh_base_url"]
        # کلاینت مشترک یکپارچگی هم به نشانی جدید برود
        from .integration.client import shared_client

        shared_client.base_url = by_config.BASE_URL
        shared_client._token = None  # توکن نشانی قبلی برای نشانی جدید معنا ندارد
    sso_changed = any(k in overrides for k in ("sso_issuer", "sso_redirect_uri", "sso_post_logout_uri", "sso_client_id"))
    if sso_changed:
        if "sso_issuer" in overrides:
            auth_config.SSO_ISSUER = overrides["sso_issuer"]
        if "sso_redirect_uri" in overrides:
            auth_config.SSO_REDIRECT_URI = overrides["sso_redirect_uri"]
        if "sso_post_logout_uri" in overrides:
            auth_config.SSO_POST_LOGOUT_URI = overrides["sso_post_logout_uri"]
        if "sso_client_id" in overrides:
            auth_config.CLIENT_ID = overrides["sso_client_id"]
        # کش سند Discovery باید برای issuer جدید بازخوانی شود
        from .auth import security

        security._DISCOVERY_CACHE["doc"] = None
        security._DISCOVERY_CACHE["at"] = 0.0


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
