# -*- coding: utf-8 -*-
"""پیکربندی احراز هویت یکپارچه دانشجو۳۶۰ — خوانده از متغیرهای محیطی

مطابق «پرامت اتصال سامانه‌ها به SSO دانشجویار۳۶۰» — v3.0.0 (شرکت ماه‌افزار هوشمند رسا)
کلاینت نوع public است؛ احراز فقط با PKCE (S256) و بدون client_secret انجام می‌شود.
"""
import os

# --- ارائه‌دهنده هویت (issuer ثابت) ------------------------------------------
SSO_ISSUER = os.getenv("DANESHJO360_SSO_ISSUER", "http://188.212.96.235:8086")

# --- شناسه‌های این سامانه در کاتالوگ SSO --------------------------------------
CLIENT_ID = os.getenv("DANESHJO360_SSO_CLIENT_ID", "daneshjo360")    # کلاینت public — باید با ثبت پرتال یکی باشد
# پیشوند نقش‌های توکن طبق «راهنمای اتصال سامانه‌ها به ورود یکپارچهٔ دانشجویار۳۶۰» v1.0:
# نقش‌ها در resource_access.<client_id>.roles به شکل «<client_id>.<نقش» می‌آیند؛
# پس پیش‌فرض app_key همان client_id است (env می‌تواند آن را جدا کند).
APP_KEY = os.getenv("DANESHJO360_SSO_APP_KEY") or CLIENT_ID
APP_NAME = "دانشجو۳۶۰"

# redirect_uri باید کاراکتر به کاراکتر با مقدار ثبت‌شده در سرور SSO یکی باشد
SSO_REDIRECT_URI = os.getenv(
    "DANESHJO360_SSO_REDIRECT_URI",
    "http://127.0.0.1:8000/auth/sso/callback",
)
SSO_POST_LOGOUT_URI = os.getenv(
    "DANESHJO360_SSO_POST_LOGOUT_URI",
    "http://127.0.0.1:8000/login?logout=1",
)

# نقش مورد نیاز برای ورود به سامانه (تخصیص توسط مدیر SSO در پنل کاربران)
ACCESS_ROLE = f"{APP_KEY}.access"

# scope استاندارد ورود طبق راهنمای اتصال v1.0 (بخش ۵): openid profile email
SSO_SCOPE = os.getenv("DANESHJO360_SSO_SCOPE", "openid profile email")

# --- نشست محلی ---------------------------------------------------------------
SESSION_COOKIE = "d360_session"
SESSION_TTL_HOURS = int(os.getenv("DANESHJO360_SESSION_TTL_HOURS", "8"))  # حدود ۸ ساعت طبق پرامت
COOKIE_SECURE_ENV = os.getenv("DANESHJO360_COOKIE_SECURE", "")  # 1=اجباری، 0=خاموش، ""=خودکار (https)

# --- حالت نمایشی (ارزیابی سامانه بدون دسترسی به سرور SSO) ---------------------
# در استقرار رسمی با مقدار 0 خاموش شود تا ورود فقط از طریق SSO انجام شود.
DEMO_LOGIN_ENABLED = os.getenv("DANESHJO360_DEMO_LOGIN", "1").lower() not in ("0", "false", "no")

# نقش پیش‌فرض کاربران SSO که هیچ نقش مدیریتی ثبت‌شده‌ای در توکن ندارند
DEFAULT_ROLE = os.getenv("DANESHJO360_DEFAULT_ROLE", "edu_manager")

# --- محدودیت نرخ (مطابق قواعد سرور SSO: ورود ۱۰ در ۵ دقیقه از هر IP) ---------
LOGIN_RATE_LIMIT = int(os.getenv("DANESHJO360_LOGIN_RATE", "10"))
LOGIN_RATE_WINDOW = 300          # ثانیه
DEMO_RATE_LIMIT = 30
DEMO_RATE_WINDOW = 300
REFRESH_RATE_LIMIT = 60          # توکن: ۶۰ درخواست در دقیقه از هر IP
REFRESH_RATE_WINDOW = 60
RATE_MESSAGE = "تعداد تلاش‌ها بیش از حد مجاز است؛ لطفاً کمی بعد دوباره تلاش کنید."

# --- عمر تخمینی توکن‌ها طبق پرامت (برای نمایش و منطق نوسازی) ------------------
ACCESS_TOKEN_TTL = 30 * 60        # ۳۰ دقیقه
REFRESH_TOKEN_TTL = 8 * 3600      # ۸ ساعت — چرخش تک‌مصرف
AUTH_CODE_TTL = 120               # ۱۲۰ ثانیه — سمت سرور SSO

BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"
