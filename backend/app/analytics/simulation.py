# -*- coding: utf-8 -*-
"""سرویس ۱۱ — شبیه‌سازی افزودن/حذف رشته

سناریوسازی مالی چندساله بر پایه فرض‌های کاربر (پذیرش، شهریه، هزینه ثابت/متغیر،
نرخ خروج، نرخ تنزیل). خروجی «شبیه‌سازی سناریو» است، نه امکان‌سنجی رسمی؛
مجوز ایجاد یا انحلال رشته تابع ضوابط شورای گسترش دانشگاه‌ها و وزارت‌خانه است.
"""
from pydantic import BaseModel, Field

from ..models import Major, Student
from .base import fa_int, ok, r1

MONEY_HINT = "همه مبالغ بر حسب «میلیون تومان» هستند"


class SimInput(BaseModel):
    action: str = Field(default="add", description="add یا remove")

    # --- افزودن رشته ---
    name: str | None = Field(default=None, description="نام رشته پیشنهادی")
    department_id: int | None = None
    degree: str = "bsc"
    annual_intake: int = Field(default=80, ge=1, le=1000, description="پذیرش سالانه فرضی")
    tuition_m: float = Field(default=15.0, ge=0, description="شهریه سالانه هر دانشجو (میلیون تومان)")
    variable_cost_m: float = Field(default=6.5, ge=0, description="هزینه متغیر سالانه هر دانشجو")
    fixed_setup_m: float = Field(default=2500.0, ge=0, description="هزینه راه‌اندازی سال اول (طرح درسی، آزمایشگاه و…)")
    fixed_annual_m: float = Field(default=600.0, ge=0, description="هزینه ثابت سالانه رشته")
    dropout: float = Field(default=0.08, ge=0, le=0.9, description="نرخ خروج/انصراف سالانه")
    discount: float = Field(default=0.20, ge=0, le=2, description="نرخ تنزیل برای NPV")
    horizon: int = Field(default=5, ge=1, le=10, description="افق شبیه‌سازی (سال)")

    # --- حذف رشته ---
    major_id: int | None = None
    transition_cost_m: float = Field(default=1200.0, ge=0, description="هزینه تعدیل/انتقال اساتید و توقیف امکانات")
    phase_years: int = Field(default=4, ge=1, le=10, description="طول فاز خروج (پایان تحصیل دانشجویان جاری)")


def _project_add(inp, intake):
    """پروجکشن چندساله افزودن رشته با پذیرش فرضی معین."""
    rows = []
    cum = 0.0
    npv = 0.0
    for y in range(1, inp.horizon + 1):
        active = sum(intake * ((1 - inp.dropout) ** (y - k)) for k in range(1, y + 1))
        revenue = active * inp.tuition_m
        cost = inp.fixed_annual_m + active * inp.variable_cost_m + (inp.fixed_setup_m if y == 1 else 0)
        net = revenue - cost
        cum += net
        npv += net / ((1 + inp.discount) ** y)
        rows.append({
            "year": f"سال {fa_int(y)}",
            "active": round(active),
            "revenue": r1(revenue),
            "cost": r1(cost),
            "net": r1(net),
            "cum": r1(cum),
        })
    return rows, cum, npv


def _sim_add(db, inp):
    rows, cum, npv = _project_add(inp, inp.annual_intake)
    _, cum_hi, npv_hi = _project_add(inp, inp.annual_intake * 1.2)
    _, cum_lo, npv_lo = _project_add(inp, inp.annual_intake * 0.8)

    break_even = next((x["year"] for x in rows if x["cum"] > 0), None)
    flags = []
    if npv_lo < 0:
        flags.append("در سناریوی افت ۲۰٪ پذیرش، خالص ارزش فعلی منفی می‌شود — ریسک پذیرش بالاست.")
    if break_even is None:
        flags.append(f"سربه‌سر تجمعی در افق {fa_int(inp.horizon)} ساله دیده نشد.")
    if inp.tuition_m <= 0:
        flags.append("شهریه صفر فرض شده؛ برای دانشگاه‌های دولتی بدون شهریه، مدل هزینه/منفعت باید بازطراحی شود.")

    if npv > 0 and break_even:
        verdict = (f"سناریو در افق {fa_int(inp.horizon)} سال مثبت است؛ سربه‌سر تجمعی در «{break_even}» و "
                   f"NPV با نرخ تنزیل {fa_int(inp.discount * 100)}٪ حدود {fa_int(npv)} میلیون تومان.")
    elif npv > 0:
        verdict = f"NPV مثبت است ({fa_int(npv)} میلیون تومان) اما سربه‌سر تجمعی در افق دیده نشد — افق یا پذیرش را بازبینی کنید."
    else:
        verdict = f"NPV منفی است ({fa_int(npv)} میلیون تومان)؛ سناریو با فرض‌های فعلی اقتصاد ندارد."

    kpis = [
        {"label": "NPV افق", "value": fa_int(npv), "unit": "میلیون تومان",
         "hint": f"نرخ تنزیل {fa_int(inp.discount * 100)}٪"},
        {"label": "سربه‌سر تجمعی", "value": break_even or "در افق محقق نشد"},
        {"label": "خالص تجمعی پایان افق", "value": fa_int(cum), "unit": "میلیون تومان",
         "tone": "good" if cum > 0 else "bad"},
        {"label": "دامنه حساسیت NPV", "value": f"{fa_int(npv_lo)} تا {fa_int(npv_hi)}",
         "hint": "پذیرش ±۲۰٪"},
    ]

    charts = [
        {
            "key": "cum",
            "type": "bar",
            "title": "خالص تجمعی سناریو افزودن رشته (میلیون تومان)",
            "data": [{"name": x["year"], "value": x["cum"]} for x in rows],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "خالص تجمعی"},
        },
        {
            "key": "revcost",
            "type": "line",
            "title": "درآمد و هزینه سالانه (میلیون تومان)",
            "data": [{"name": x["year"], "revenue": x["revenue"], "cost": x["cost"]} for x in rows],
            "xKey": "name",
            "yKeys": ["revenue", "cost"],
            "seriesLabels": {"revenue": "درآمد", "cost": "هزینه"},
        },
    ]

    return ok(
        "major-simulation", "شبیه‌سازی افزودن رشته", 11,
        filters=inp.model_dump(),
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "year", "label": "سال"},
            {"key": "active", "label": "دانشجویان فعال", "format": "int"},
            {"key": "revenue", "label": "درآمد", "format": "float"},
            {"key": "cost", "label": "هزینه", "format": "float"},
            {"key": "net", "label": "خالص سالانه", "format": "float"},
            {"key": "cum", "label": "خالص تجمعی", "format": "float"},
        ], "rows": rows},
        method="هر کوهورت ورودی با نرخ خروج سالانه جمع می‌شود (دانشجویان فعال = Σ پذیرش × (۱−خروج)^سن)؛ درآمد = دانشجوی فعال × شهریه؛ هزینه = ثابت سالانه + متغیر × دانشجو + راه‌اندازی سال اول؛ NPV با نرخ تنزیل ورودی؛ حساسیت با تغییر ±۲۰٪ پذیرش.",
        limitations=[
            "تمام اعداد از فرض‌های ورودی کاربر می‌آید؛ اعتبار خروجی به اعتبار فرض‌ها است.",
            "عدم قطعیت بازار پذیرش، قواعد شهریه و هزینه‌ها بالاست؛ سناریو جای مطالعه امکان‌سنجی رسمی را نمی‌گیرد.",
            "مجوز ایجاد رشته تابع ضوابط شورای گسترش دانشگاه‌ها/وزارت‌خانه است و این شبیه‌سازی هیچ مجوزی ایجاد نمی‌کند.",
            f"{MONEY_HINT}؛ نرخ تورم و افزایش سالانه نرخ‌ها در این نسخه لحاظ نشده است.",
        ],
        extra={"verdict": verdict, "flags": flags},
    )


def _sim_remove(db, inp):
    major = db.get(Major, inp.major_id)
    if major is None:
        return None
    active_n = db.query(Student).filter(Student.major_id == major.id, Student.status == "active").count()

    rows = []
    cum = 0.0
    npv = 0.0
    for y in range(1, inp.phase_years + 1):
        remaining = active_n * max(0.0, 1 - y / inp.phase_years)
        revenue_lost = remaining * inp.tuition_m
        cost_avoided = (remaining * inp.variable_cost_m
                        + inp.fixed_annual_m * max(0.0, 1 - y / inp.phase_years)
                        + (inp.transition_cost_m if y == 1 else 0))
        net = cost_avoided - revenue_lost
        cum += net
        npv += net / ((1 + inp.discount) ** y)
        rows.append({
            "year": f"سال {fa_int(y)}",
            "remaining": round(remaining),
            "revenue_lost": r1(revenue_lost),
            "cost_avoided": r1(cost_avoided),
            "net": r1(net),
            "cum": r1(cum),
        })

    flags = [
        "دانشجویان جاری باید تا فارغ‌التحصیلی با همان کیفیت آموزش ببینند — توقف تحصیل فعالان مجاز نیست.",
        "اساتید متخصص رشته باید از طریق انتقال/بازآموزی مدیریت شوند؛ هزینه تعدیل در فرض «transition_cost_m» است.",
    ]
    verdict = (f"صرفه‌جویی خالص در فاز {fa_int(inp.phase_years)} ساله حدود {fa_int(cum)} میلیون تومان "
               f"(NPV ≈ {fa_int(npv)}) برآورد می‌شود؛ ریسک اصلی: از دست رفتن تنوع رشته‌ای و اثر بر پیش‌نیازهای دروس مشترک.")

    kpis = [
        {"label": "رشته هدف", "value": f"{major.name} ({major.code})"},
        {"label": "دانشجویان فعال", "value": active_n, "unit": "نفر"},
        {"label": "صرفه‌جویی تجمعی فاز خروج", "value": fa_int(cum), "unit": "میلیون تومان",
         "tone": "good" if cum > 0 else "bad"},
        {"label": "NPV صرفه‌جویی", "value": fa_int(npv), "unit": "میلیون تومان",
         "hint": f"نرخ تنزیل {fa_int(inp.discount * 100)}٪"},
    ]

    charts = [{
        "key": "cum",
        "type": "bar",
        "title": "اثر نقدی تجمعی فاز خروج رشته (مثبت = صرفه‌جویی)",
        "data": [{"name": x["year"], "value": x["cum"]} for x in rows],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "اثر تجمعی"},
    }]

    return ok(
        "major-simulation", "شبیه‌سازی حذف رشته", 11,
        filters=inp.model_dump(),
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "year", "label": "سال"},
            {"key": "remaining", "label": "دانشجویان باقی‌مانده", "format": "int"},
            {"key": "revenue_lost", "label": "درآمد از دست رفته", "format": "float"},
            {"key": "cost_avoided", "label": "هزینه صرفه‌جویی‌شده", "format": "float"},
            {"key": "net", "label": "اثر نقدی سالانه", "format": "float"},
            {"key": "cum", "label": "اثر تجمعی", "format": "float"},
        ], "rows": rows},
        method="فاز خروج خطی فرض شده است: دانشجویان فعال به‌تدریج فارغ‌التحصیل می‌شوند (باقی‌مانده = فعال × (۱ − سال/طول فاز))؛ درآمد از دست رفته = باقی‌مانده × شهریه؛ صرفه‌جویی = هزینه متغیر + ثابت در حال حذف + هزینه انتقال سال اول.",
        limitations=[
            "فاز خروج خطی فرض شده؛ واقعیت به جدول گذراندن واحد دانشجویان وابسته است.",
            "اثر غیرمالی (تنوع رشته‌ای، اعتبار دانشکده، وابستگی دروس مشترک و پیش‌نیازها) در مدل نیست.",
            "مجوز انحلال رشته تابع ضوابط شوراهای آموزشی و وزارت‌خانه است؛ این خروجی صرفاً پشتیبان بحث است.",
            f"{MONEY_HINT}؛ فرض‌ها باید با داده واقعی سازمان جایگزین شوند.",
        ],
        extra={"verdict": verdict, "flags": flags},
    )


def major_simulation(db, inp: SimInput):
    if inp.action == "remove":
        return _sim_remove(db, inp)
    return _sim_add(db, inp)
