# -*- coding: utf-8 -*-
"""ابزارهای امنیتی SSO — Discovery، PKCE (S256)، تبادل توکن و اعتبارسنجی JWT با JWKS

قواعد مطابق پرامت SSO دانشجویار۳۶۰:
  * endpointها از سند Discovery خوانده می‌شوند؛ issuer باید دقیقاً برابر مقدار ثابت باشد.
  * امضای id_token با RS256 و کلیدهای عمومی JWKS اعتبارسنجی می‌شود (با پشتیبانی kid).
  * فقط کتابخانه استاندارد + PyJWT استفاده شده؛ هیچ رازی در مرورگر قرار نمی‌گیرد.
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict, deque

import jwt
from jwt import PyJWKClient

from . import config


class SSOError(Exception):
    """خطای عمومی جریان SSO (پیام فارسی برای نمایش به کاربر)"""


class SSORateLimit(SSOError):
    """محدودیت نرخ (۴۲۹) — پیام «کمی بعد دوباره تلاش کنید»"""


# ---------------------------------------------------------------------------
# Discovery — خواندن endpointها از سند استاندارد با اعتبارسنجی issuer
# ---------------------------------------------------------------------------
_DISCOVERY_CACHE: dict = {"doc": None, "at": 0.0}
DISCOVERY_TTL = 3600

_FALLBACK_PATHS = {
    "authorization_endpoint": "/protocol/openid-connect/auth",
    "token_endpoint": "/protocol/openid-connect/token",
    "userinfo_endpoint": "/protocol/openid-connect/userinfo",
    "jwks_uri": "/protocol/openid-connect/certs",
    "end_session_endpoint": "/protocol/openid-connect/logout",
}


def get_discovery(force: bool = False) -> dict:
    """خواندن و کش سند Discovery؛ در خطا SSOError با پیام فارسی برمی‌گرداند"""
    now = time.time()
    if not force and _DISCOVERY_CACHE["doc"] and now - _DISCOVERY_CACHE["at"] < DISCOVERY_TTL:
        return _DISCOVERY_CACHE["doc"]
    url = config.SSO_ISSUER.rstrip("/") + "/.well-known/openid-configuration"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — هر خطای شبکه به خطای فارسی تبدیل می‌شود
        raise SSOError("ارتباط با سرور احراز هویت مرکزی برقرار نشد؛ لطفاً بعداً دوباره تلاش کنید.") from exc
    if doc.get("issuer") != config.SSO_ISSUER:
        raise SSOError("پیکربندی SSO نامعتبر است (issuer با مقدار ثبت‌شده یکسان نیست).")
    # endpointهای غایب با مسیرهای استاندارد پرتال جایگزین می‌شوند
    for key, path in _FALLBACK_PATHS.items():
        if not doc.get(key):
            doc[key] = config.SSO_ISSUER.rstrip("/") + path
    _DISCOVERY_CACHE["doc"] = doc
    _DISCOVERY_CACHE["at"] = now
    return doc


# ---------------------------------------------------------------------------
# PKCE — code_verifier تصادفی و code_challenge با S256 (روش plain رد می‌شود)
# ---------------------------------------------------------------------------

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce_pair() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(48))  # ۶۴ کاراکتر — در بازه ۴۳ تا ۱۲۸
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


# ---------------------------------------------------------------------------
# فراخوانی HTTP سمت سرور (توکن/یوزراینفو) با urllib — بدون وابستگی جدید
# ---------------------------------------------------------------------------

def http_post_form(url: str, fields: dict, timeout: int = 20) -> dict:
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise SSORateLimit(config.RATE_MESSAGE) from exc
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        raise SSOError(f"تبادل توکن ناموفق بود (کد {exc.code}). لطفاً دوباره وارد شوید. {detail}") from exc
    except Exception as exc:  # noqa: BLE001
        raise SSOError("ارتباط با سرور احراز هویت مرکزی برقرار نشد؛ لطفاً بعداً دوباره تلاش کنید.") from exc


def token_exchange(code: str, verifier: str) -> dict:
    """تبادل کد مجوز — همان redirect_uri ثبت‌شده، کاراکتر به کاراکتر"""
    return http_post_form(
        get_discovery()["token_endpoint"],
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.SSO_REDIRECT_URI,
            "client_id": config.CLIENT_ID,
            "code_verifier": verifier,
        },
    )


def refresh_exchange(refresh_token: str) -> dict:
    """نوسازی توکن — refresh_token جدید باید فوراً جایگزین قبلی شود (چرخش تک‌مصرف)"""
    return http_post_form(
        get_discovery()["token_endpoint"],
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.CLIENT_ID,
        },
    )


def userinfo_request(access_token: str) -> dict:
    req = urllib.request.Request(
        get_discovery()["userinfo_endpoint"],
        headers={"Accept": "application/json", "Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise SSORateLimit(config.RATE_MESSAGE) from exc
        raise SSOError("دریافت اطلاعات کاربر از سرور احراز هویت ناموفق بود.") from exc
    except Exception as exc:  # noqa: BLE001
        raise SSOError("ارتباط با سرور احراز هویت مرکزی برقرار نشد.") from exc


# ---------------------------------------------------------------------------
# اعتبارسنجی JWT (RS256 با JWKS؛ کلیدها با kid چرخش می‌شوند)
# ---------------------------------------------------------------------------
_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client(jwks_uri: str) -> PyJWKClient:
    client = _jwks_clients.get(jwks_uri)
    if client is None:
        client = PyJWKClient(jwks_uri, cache_keys=True, lifespan=1800)
        _jwks_clients[jwks_uri] = client
    return client


def verify_rs256_jwt(token: str, *, audience: str | None = None, nonce: str | None = None,
                     require: set[str] | None = None) -> dict:
    """اعتبارسنجی امضا/iss/aud/exp؛ تطبیق nonce (وقتی الزامی است) جداگانه انجام می‌شود."""
    try:
        doc = get_discovery()
        key = _jwks_client(doc["jwks_uri"]).get_signing_key_from_jwt(token)
        options = {"require": require or {"exp", "iat", "sub"}}
        if audience is None:
            options["verify_aud"] = False  # توکن بدون بررسی مخاطب (مثل logout_token) یا بدون ادعای aud
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=config.SSO_ISSUER,
            options=options,
        )
    except SSOError:
        raise
    except jwt.PyJWTError as exc:
        raise SSOError("توکن احراز هویت معتبر نیست؛ لطفاً دوباره وارد شوید.") from exc
    except Exception as exc:  # noqa: BLE001
        raise SSOError("اعتبارسنجی توکن با کلیدهای عمومی سرور SSO ناموفق بود.") from exc
    if nonce is not None and claims.get("nonce") != nonce:
        raise SSOError("تطبیق nonce ناموفق بود؛ احتمال حمله تکرار (replay) — ورود رد شد.")
    return claims


# ---------------------------------------------------------------------------
# محدودیت نرخ ساده در حافظه (پر هر بارگذاری مجدد برنامه ریست می‌شود)
# ---------------------------------------------------------------------------
_HITS: dict[str, deque] = defaultdict(deque)


def rate_limit_ok(key: str, limit: int, window: int) -> bool:
    now = time.monotonic()
    dq = _HITS[key]
    while dq and now - dq[0] > window:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True
