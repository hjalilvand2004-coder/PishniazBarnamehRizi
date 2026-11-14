# -*- coding: utf-8 -*-
"""کلاینت HTTP برای سامانهٔ برنامه‌یار۳۶۰ — فقط با کتابخانهٔ استاندارد پایتون

* ورود با نام کاربری/رمز سامانه‌ای → توکن ماندگار در حافظهٔ پروسه (نه روی دیسک)
* توکن برنامه‌یار قالب «payload.sign» دارد؛ مهلت اعتبار از exp داخل payload خوانده می‌شود
* در پاسخ ۴۰۱ یک‌بار ورود مجدد انجام می‌شود سپس درخواست تکرار می‌گردد
* هیچ وابستگی خارجی اضافه نمی‌شود (سازگار با نسخهٔ پرتیبل)
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from . import config


class IntegrationError(Exception):
    """خطای ارتباط با سامانهٔ برنامه‌یار۳۶۰ — پیام فارسی برای نمایش در رابط کاربری."""


def _decode_token_exp(token: str) -> int | None:
    """استخراج exp از توکن برنامه‌یار (payload به‌صورت base64url از JSON)."""
    try:
        payload = token.split(".")[0]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
        return int(data.get("exp")) if data.get("exp") else None
    except Exception:
        return None


def _request(method: str, url: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict | list]:
    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req, data=data, timeout=config.TIMEOUT) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8", "replace"))
        except Exception:
            payload = {}
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if e.code in (401, 403):
            raise IntegrationError(f"ورود به برنامه‌یار۳۶۰ ناموفق بود ({e.code}): {detail or 'احراز هویت پذیرفته نشد'}")
        raise IntegrationError(f"پاسخ خطا از برنامه‌یار۳۶۰ (کد {e.code}): {detail or '—'}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise IntegrationError(f"ارتباط با برنامه‌یار۳۶۰ برقرار نشد: {e}")


class BarnamehYarClient:
    """کلاینت نشست‌دار برنامه‌یار۳۶۰ با ورود مجدد خودکار."""

    def __init__(self, base_url: str | None = None, username: str | None = None, password: str | None = None):
        self.base_url = (base_url or config.BASE_URL).rstrip("/")
        self.username = username or config.USERNAME
        self.password = password or config.PASSWORD
        self._token: str | None = None
        self._token_exp: int | None = None
        self._logged_at: float = 0.0

    # ------------------------------------------------------------------ ورود
    def login(self, force: bool = False) -> str:
        """ورود و گرفتن توکن؛ اگر توکن معتبر موجود باشد دوباره وارد نمی‌شود."""
        now = time.time()
        if (
            not force
            and self._token
            and (self._token_exp is None or self._token_exp > now + config.TOKEN_MARGIN_SECONDS)
        ):
            return self._token
        status, data = _request(
            "POST",
            f"{self.base_url}/api/auth/login",
            body={"username": self.username, "password": self.password},
        )
        if status != 200 or not isinstance(data, dict) or not data.get("access_token"):
            raise IntegrationError("ورود به برنامه‌یار۳۶۰ ناموفق بود: توکن دریافت نشد.")
        self._token = data["access_token"]
        self._token_exp = _decode_token_exp(self._token)
        self._logged_at = now
        return self._token

    def auth_test(self) -> dict:
        """بررسی سلامت + احراز هویت — برای کارت وضعیت اتصال."""
        result = {"reachable": False, "auth": False, "version": None, "counts": [], "error": None}
        try:
            status, health = _request("GET", f"{self.base_url}/health")
            result["reachable"] = status == 200
        except IntegrationError as e:
            result["error"] = str(e)
            return result
        try:
            token = self.login()
            result["auth"] = bool(token)
        except IntegrationError as e:
            result["error"] = str(e)
            return result
        try:
            _, summary = _request("GET", f"{self.base_url}/api/data-summary", token=self._token)
            result["version"] = (summary or {}).get("version")
            result["counts"] = (summary or {}).get("counts") or []
        except IntegrationError as e:
            result["error"] = str(e)
        return result

    # ------------------------------------------------------------- درخواست‌ها
    def get_json(self, path: str, *, retry: bool = True) -> dict | list:
        token = self.login()
        try:
            status, data = _request("GET", f"{self.base_url}{path}", token=token)
        except IntegrationError:
            # یک‌بار ورود مجدد و تکرار درخواست (پوشش انقضای توکن)
            if not retry:
                raise
            token = self.login(force=True)
            status, data = _request("GET", f"{self.base_url}{path}", token=token)
        if status != 200:
            raise IntegrationError(f"درخواست «{path}» ناموفق بود (کد {status}).")
        return data

    def post_json(self, path: str, body: dict) -> dict | list:
        token = self.login()
        status, data = _request("POST", f"{self.base_url}{path}", token=token, body=body)
        if status not in (200, 201):
            raise IntegrationError(f"ارسال به «{path}» ناموفق بود (کد {status}).")
        return data

    # ------------------------------------------------------ منابع همگام‌سازی
    def fetch_source(self, source_key: str) -> list[dict]:
        """دریافت فهرست کامل یک منبع؛ هم پاسخ فهرست مستقیم و هم «items/total» پشتیبانی می‌شود."""
        meta = config.SOURCES[source_key]
        data = self.get_json(meta["path"])
        items = data
        if isinstance(data, dict):
            for key in ("items", "data", "records", "history", "results"):
                if isinstance(data.get(key), list):
                    items = data[key]
                    break
            else:
                # کلیدهای دیکشنری‌ای که خودشان فهرستِ رکوردها هستند
                for v in data.values():
                    if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                        items = v
                        break
        return [row for row in items if isinstance(row, dict)]


# کلاینت مشترک پروسه — توکن در حافظه نگه داشته می‌شود
shared_client = BarnamehYarClient()
