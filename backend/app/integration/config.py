# -*- coding: utf-8 -*-
"""پیکربندی یکپارچگی با سامانهٔ برنامه‌یار۳۶۰

همهٔ تنظیمات با متغیر محیطی قابل تغییر است؛ مقادیر پیش‌فرض برای استقرار نمایشی
سامانهٔ برنامه‌یار۳۶۰ تنظیم شده است. رمز عبور هرگز در کد جاسازی نمایشی به‌جز
پیش‌فرض مستند نگهداری نمی‌شود و توکن ورود فقط در حافظهٔ پروسه نگه داشته می‌شود.
"""
import os

# فعال/غیرفعال بودن ماژول یکپارچگی
ENABLED = os.getenv("BARNAMEHYAR_ENABLED", "1") != "0"

# نشانی پایهٔ سامانهٔ برنامه‌یار۳۶۰
BASE_URL = os.getenv("BARNAMEHYAR_BASE_URL", "http://188.212.96.235:8083").rstrip("/")

# حساب سامانه‌ای برای همگام‌سازی (کاربر «سامانه»؛ شخصی نیست)
USERNAME = os.getenv("BARNAMEHYAR_USERNAME", "admin")
PASSWORD = os.getenv("BARNAMEHYAR_PASSWORD", "admin123")

TIMEOUT = int(os.getenv("BARNAMEHYAR_TIMEOUT", "30"))

# مهلت توکن ورود برنامه‌یار بر پایهٔ exp خود توکن خوانده می‌شود؛
# چند ثانیه زودتر برای اطمینان منقضی فرض می‌کنیم.
TOKEN_MARGIN_SECONDS = 60

# منابع همگام‌سازی — مبنای «برنامه‌ریزی واقعی» در برنامه‌یار۳۶۰
SOURCES = {
    "term_courses": {
        "path": "/api/term-courses/",
        "label": "دروس ترمیک",
        "remote_id": "id",
    },
    "schedule_history": {
        "path": "/api/schedule-history/",
        "label": "سوابق برنامه‌ریزی",
        "remote_id": "id",
    },
    "rooms": {
        "path": "/api/professors-rooms/rooms/list",
        "label": "کلاس‌ها و اتاق‌های درس",
        "remote_id": "id",
    },
    "instructors": {
        "path": "/api/professors-rooms/instructors/list",
        "label": "اساتید",
        "remote_id": "id",
    },
    "offered_courses": {
        "path": "/api/courses/offered",
        "label": "دروس ارائه (برای نگاشت پیشنهاد)",
        "remote_id": "id",
    },
}

# منابعی که به‌صورت کامل آینه می‌شوند (سوابق برنامه‌ریزی، دروس ترمیک، اتاق‌ها، اساتید)
MIRROR_SOURCES = ["term_courses", "schedule_history", "rooms", "instructors"]
