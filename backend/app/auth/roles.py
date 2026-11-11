# -*- coding: utf-8 -*-
"""مدل نقش‌های سامانه دانشجو۳۶۰ و نگاشت دسترسی نقش‌ها به سرویس‌های تحلیلی

سه نقش مدیریتی:
  * sysadmin      — ادمین سیستم: دسترسی کامل به همه سرویس‌ها (شامل شبیه‌سازی رشته)
  * edu_manager   — مدیرآموزش: سرویس‌های سطح دانشگاه/آموزش کل
  * dept_manager  — مدیرگروه: سرویس‌های سطح گروه آموزشی

نقش‌های SSO در توکن به شکل «daneshjo.sysadmin»، «daneshjo.edu_manager» و
«daneshjo.dept_manager» منتقل می‌شوند؛ در نبود هر سه، نقش پیش‌فرض اعمال می‌شود.
"""

ROLES = {
    "sysadmin": {
        "label": "ادمین سیستم",
        "desc": "دسترسی کامل به همه سرویس‌های تحلیلی، شبیه‌سازی رشته و مدیریت سامانه",
        "icon": "shield",
    },
    "dept_manager": {
        "label": "مدیرگروه",
        "desc": "سرویس‌های سطح گروه: تقاضای دروس، ظرفیت، توزیع دانشجو، عملکرد و توصیه استاد",
        "icon": "org",
    },
    "edu_manager": {
        "label": "مدیرآموزش",
        "desc": "سرویس‌های سطح دانشگاه: عملکرد دانشکده‌ها، مردودی، هزینه، نسبت و بهره‌وری",
        "icon": "cap",
    },
}

# ترتیب تقدم هنگام داشتن چند نقش در توکن
ROLE_PRECEDENCE = ["sysadmin", "edu_manager", "dept_manager"]

VALID_ROLES = set(ROLES.keys())

# نگاشت سرویس‌های تحلیلی به نقش‌های مجاز — جامعه هدف هر سرویس در سند رسمی ملاک است
SERVICE_ROLES = {
    # جامعه هدف: مدیران (سطح گروه و آموزش)
    "demand-analysis":       {"dept_manager", "edu_manager", "sysadmin"},
    "capacity-forecast":     {"dept_manager", "edu_manager", "sysadmin"},
    "student-distribution":  {"dept_manager", "edu_manager", "sysadmin"},
    # جامعه هدف: مدیرگروه
    "instructor-performance":     {"dept_manager", "sysadmin"},
    "instructor-recommendation":  {"dept_manager", "sysadmin"},
    # جامعه هدف: دانشگاه / مدیرآموزش
    "department-performance": {"edu_manager", "sysadmin"},
    "fail-rate":              {"edu_manager", "sysadmin"},
    "course-cost":            {"edu_manager", "sysadmin"},
    "ratio-optimization":     {"edu_manager", "sysadmin"},
    "teaching-efficiency":    {"edu_manager", "sysadmin"},
    # جامعه هدف: سیاست‌گذار — با نقش ادمین سیستم پوشش داده می‌شود
    "major-simulation":       {"sysadmin"},
}

SERVICE_TITLES = {
    "demand-analysis": "تحلیل تقاضای دروس",
    "capacity-forecast": "پیش‌بینی ظرفیت کلاس‌ها",
    "student-distribution": "تحلیل توزیع دانشجویان",
    "instructor-performance": "تحلیل عملکرد اساتید",
    "instructor-recommendation": "توصیه استاد برای ارائه درس",
    "department-performance": "تحلیل عملکرد دانشکده‌ها",
    "fail-rate": "تحلیل نرخ مردودی",
    "course-cost": "تحلیل هزینه دروس",
    "ratio-optimization": "بهینه‌سازی نسبت استاد به دانشجو",
    "teaching-efficiency": "تحلیل بهره‌وری آموزش",
    "major-simulation": "شبیه‌سازی افزودن/حذف رشته",
}

# سرویس‌های پایه در دسترس همه نقش‌ها
BASE_SERVICES = ["dashboard"]


def role_services(role: str) -> list[str]:
    """فهرست سرویس‌های مجاز برای یک نقش (داشبورد + سرویس‌های تحلیلی)"""
    return BASE_SERVICES + [sid for sid, roles in SERVICE_ROLES.items() if role in roles]


def resolve_role_from_token(token_roles: list[str], access_role: str, default_role: str) -> str | None:
    """تعیین نقش محلی از روی نقش‌های توکن؛ None یعنی نقش .access ندارد (دسترسی ندارید)"""
    if access_role not in (token_roles or []):
        return None
    for key in ROLE_PRECEDENCE:
        if f".{key}" in (token_roles or []):
            return key
    return default_role


def role_label(role: str) -> str:
    return ROLES.get(role, {}).get("label", role)
