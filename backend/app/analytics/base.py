# -*- coding: utf-8 -*-
"""ابزارها و ثابت‌های مشترک موتورهای تحلیلی

ساختار خروجی استاندارد هر سرویس:
{
  service_id, title, order, generated_at, filters,
  kpis:    [{label, value, unit, hint, tone}],
  charts:  [{key, type: line|bar|pie|scatter, title, data, xKey, yKeys, seriesLabels, refLine}],
  table:   {columns: [{key, label, format}], rows: [...]},
  method:  "…", limitations: ["…"], disclaimer: "…"
}
"""
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# ثابت‌های نمونه — باید با نرخ‌های واقعی سازمان جایگزین شوند
# ---------------------------------------------------------------------------
ROOM_HOURLY_COST = 150000          # تومان به‌ازای هر ساعت استفاده از کلاس
TEACHING_WEEKS = 16                # تعداد هفته‌های آموزشی هر نیم‌سال
OVERHEAD_PER_OFFERING = 15000000   # سربار ثابت فرضی هر ارائه (تومان)
TUITION_PER_CREDIT = 800000        # شهریه هر واحد-اعتبار (تومان) — فقط در صورت فعال‌شدن درآمد
ADJUNCT_FTE = 0.5                  # وزن FTE اساتید حق‌التدریس
DEFAULT_TARGET_RATIO = 30          # نسبت دانشجو به استاد هدف (پارامتر قابل تنظیم)
MIN_EVAL_SAMPLE = 15               # حداقل پاسخ نظرسنجی برای تفسیر عملکرد استاد
CRITICAL_FAIL_RATE = 30.0          # آستانه «بحرانی» نرخ مردودی (فرض قابل تنظیم)

DISCLAIMER = (
    "این خروجی صرفاً برای پشتیبانی تصمیم‌گیری مدیریت آموزشی تهیه شده است و جایگزین "
    "صلاحیت حرفه‌ای، مقررات سازمانی و اختیارات قانونی شوراها و مسئولان دانشگاه نیست."
)

FA_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

DEGREE_FA = {"bsc": "کارشناسی", "msc": "کارشناسی ارشد", "phd": "دکتری"}
STATUS_FA = {"active": "فعال", "graduated": "فارغ‌التحصیل", "withdrawn": "انصراف/اضمحلال"}
RANK_FA = {"prof": "استاد تمام", "assoc": "دانشیار", "assistant": "استادیار", "lecturer": "مربی"}
EMPLOYMENT_FA = {"faculty": "هیئت علمی", "adjunct": "حق‌التدریس"}


def ok(service_id, title, order, *, filters=None, kpis=None, charts=None,
       table=None, method=None, limitations=None, extra=None):
    """ساخت پاسخ استاندارد سرویس."""
    return {
        "service_id": service_id,
        "title": title,
        "order": order,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filters": filters or {},
        "kpis": kpis or [],
        "charts": charts or [],
        "table": table or {"columns": [], "rows": []},
        "method": method or "",
        "limitations": limitations or [],
        "disclaimer": DISCLAIMER,
        "extra": extra or {},
    }


# ---------------------------------------------------------------------------
# قالب‌بندی اعداد فارسی برای KPI‌های متنی
# ---------------------------------------------------------------------------

def fa_int(v):
    if v is None:
        return "—"
    return f"{int(v):,}".replace(",", "٬").translate(FA_MAP)


def fa_float(v, dec=1, signed=False):
    if v is None:
        return "—"
    s = f"{v:+.{dec}f}" if signed else f"{v:.{dec}f}"
    return s.translate(FA_MAP)


def fa_pct(v, dec=1, signed=False):
    return "—" if v is None else f"{fa_float(v, dec, signed)}٪"


# ---------------------------------------------------------------------------
# محاسبات آماری سبک
# ---------------------------------------------------------------------------

def slope_pct(values):
    """درصد تغییر خطی به‌ازای هر گام ترم (برازش کمینه مربعات)؛ برای داده ناکافی None."""
    n = len(values)
    if n < 2:
        return None
    xs = list(range(n))
    ybar = sum(values) / n
    xbar = sum(xs) / n
    den = sum((x - xbar) ** 2 for x in xs)
    if den == 0 or ybar == 0:
        return None
    num = sum((x - xbar) * (y - ybar) for x, y in zip(xs, values))
    return (num / den) / ybar * 100.0


def wavg(pairs):
    """میانگین وزنی؛ جفت‌های (مقدار، وزن) با مقدار تهی یا وزن صفر کنار گذاشته می‌شوند."""
    pairs = [(v, w) for v, w in pairs if v is not None and w]
    total_w = sum(w for _, w in pairs)
    if not total_w:
        return None
    return sum(v * w for v, w in pairs) / total_w


def r1(v):
    return round(v, 1) if v is not None else None


def r0(v):
    return round(v) if v is not None else None


# ---------------------------------------------------------------------------
# دستیارهای پرس‌وجو
# ---------------------------------------------------------------------------

def ordered_terms(db):
    from ..models import Term
    return sorted(db.query(Term).all(), key=lambda t: t.order_index)


def offerings_by_course(db):
    """دیکشنری course_id → لیست ارائه‌های آن درس، مرتب بر اساس ترتیب ترم."""
    from ..models import Offering
    torder = {t.id: t.order_index for t in ordered_terms(db)}
    out = {}
    for o in db.query(Offering).all():
        out.setdefault(o.course_id, []).append(o)
    for lst in out.values():
        lst.sort(key=lambda o: torder.get(o.term_id, 0))
    return out


def filtered_courses(db, department_id=None, course_id=None):
    from ..models import Course
    q = db.query(Course).filter(Course.active.is_(True))
    if department_id:
        q = q.filter(Course.department_id == int(department_id))
    if course_id:
        q = q.filter(Course.id == int(course_id))
    return q.all()
