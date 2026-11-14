# -*- coding: utf-8 -*-
"""سرویس ۲ — پیش‌بینی ظرفیت کلاس‌ها

پیش‌بینی تقاضای ترم بعد با هموارسازی نمایی ساده (α=۰٫۵) و حاشیه امنیت؛
عدم قطعیت از خطاهای درون‌نمونه‌ای برآورد و همراه بازه اطمینان گزارش می‌شود.
"""
import math

from .base import fa_int, filtered_courses, ok, offerings_by_course, ordered_terms, r0, r1, real_basis_limitations, eval_missing_limitation, result_missing_limitation, student_missing_limitation

ALPHA = 0.5
SAFETY_MARGIN = 0.10  # حاشیه امنیت ظرفیت پیشنهادی


def _ses_forecast(series):
    """هموارسازی نمایی ساده + برآورد عدم قطعیت نسبی از خطاهای یک‌گام جلوتر."""
    s = series[0]
    smooths = [s]
    for d in series[1:]:
        s = ALPHA * d + (1 - ALPHA) * s
        smooths.append(s)
    resid = [series[i] - smooths[i - 1] for i in range(1, len(series))]
    forecast = smooths[-1]
    mean = sum(series) / len(series)
    if resid and mean > 0:
        rbar = sum(resid) / len(resid)
        std = (sum((e - rbar) ** 2 for e in resid) / len(resid)) ** 0.5
        u = min(0.30, max(0.08, 1.28 * std / mean))
    else:
        u = 0.30
    return forecast, u


def _next_term_code(code):
    year, sem = code.rsplit("-", 1)
    return f"{year}-2" if sem == "1" else f"{int(year) + 1}-1"


def capacity_forecast(db, department_id=None, course_id=None):
    courses = filtered_courses(db, department_id, course_id)
    by_course = offerings_by_course(db)
    terms = ordered_terms(db)
    term_label = {t.id: t.label for t in terms}
    term_code = {t.id: t.code for t in terms}
    label_by_code = {t.code: t.label for t in terms}

    rows = []
    for c in courses:
        offs = by_course.get(c.id, [])
        if not offs:
            continue
        demand = [o.enrolled + o.waiting for o in offs]
        forecast, u = _ses_forecast(demand)
        low = max(0, forecast * (1 - u))
        high = forecast * (1 + u)
        recommended = math.ceil(high * (1 + SAFETY_MARGIN) / 5) * 5
        horizon_code = _next_term_code(term_code[offs[-1].term_id])
        horizon_label = label_by_code.get(horizon_code, "نیم‌سال بعد از آخرین داده")
        rows.append({
            "course": f"{c.code} — {c.title}",
            "terms_n": len(demand),
            "demand_last": demand[-1],
            "forecast": r0(forecast),
            "low": r0(low),
            "high": r0(high),
            "uncertainty_pct": r1(u * 100),
            "recommended": recommended,
            "horizon": horizon_label,
            "status": "داده ناکافی (حداقل ۳ ترم)" if len(demand) < 3 else "قابل استناد با عدم قطعیت",
        })
    rows.sort(key=lambda x: -(x["forecast"] or 0))

    charts = [{
        "key": "recommended",
        "type": "bar",
        "title": "ظرفیت پیشنهادی برای نیم‌سال بعد — ده درس نخست",
        "data": [{"name": x["course"].split(" — ")[0], "value": x["recommended"]} for x in rows[:10]],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "ظرفیت پیشنهادی"},
    }]
    if course_id:
        offs = by_course.get(int(course_id), [])
        hist = [{"term": term_label[o.term_id], "actual": o.enrolled + o.waiting,
                 "forecast": o.enrolled + o.waiting} for o in offs]
        if offs:
            hist.append({"term": label_by_code.get(_next_term_code(term_code[offs[-1].term_id]), "ترم بعد"),
                         "actual": None, "forecast": r0(rows[-1]["forecast"] if rows else None)})
        charts.append({
            "key": "trend",
            "type": "line",
            "title": "تقاضای تاریخی و پیش‌بینی ترم بعد — درس انتخابی",
            "data": hist,
            "xKey": "term",
            "yKeys": ["actual", "forecast"],
            "seriesLabels": {"actual": "تقاضای واقعی", "forecast": "پیش‌بینی"},
        })

    adequate = [x for x in rows if x["terms_n"] >= 3]
    insufficient = [x for x in rows if x["terms_n"] < 3]
    horizon_kpi = label_by_code.get(_next_term_code(term_code[terms[-1].id]), "—") if terms else "—"
    uncert = [x["uncertainty_pct"] for x in adequate if x["uncertainty_pct"] is not None]

    kpis = [
        {"label": "افق پیش‌بینی", "value": horizon_kpi, "hint": "پیش‌بینی فقط برای یک نیم‌سال تحصیلی بعد ارائه می‌شود"},
        {"label": "درس با داده کافی", "value": len(adequate), "unit": "درس"},
        {"label": "درس با داده ناکافی", "value": len(insufficient), "unit": "درس",
         "tone": "warn" if insufficient else "good", "hint": "کمتر از ۳ ترم سابقه — عدم قطعیت بالا (۳۰٪)"},
        {"label": "میانگین عدم قطعیت", "value": r1(sum(uncert) / len(uncert)) if uncert else None, "unit": "٪",
         "hint": "پهنای نسبی بازه اطمینان تقریبی ۸۰٪"},
    ]

    extra_limits = list(real_basis_limitations(db))

    return ok(
        "capacity-forecast", "پیش‌بینی ظرفیت کلاس‌ها", 2,
        filters={"department_id": department_id, "course_id": course_id},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "course", "label": "درس"},
            {"key": "terms_n", "label": "تعداد ترم داده", "format": "int"},
            {"key": "demand_last", "label": "تقاضای آخرین ترم", "format": "int"},
            {"key": "forecast", "label": "پیش‌بینی تقاضا", "format": "int"},
            {"key": "low", "label": "حد پایین بازه", "format": "int"},
            {"key": "high", "label": "حد بالای بازه", "format": "int"},
            {"key": "uncertainty_pct", "label": "عدم قطعیت", "format": "pct"},
            {"key": "recommended", "label": "ظرفیت پیشنهادی", "format": "int"},
            {"key": "horizon", "label": "افق"},
            {"key": "status", "label": "وضعیت اعتبار"},
        ], "rows": rows},
        method="هموارسازی نمایی ساده (α=۰٫۵) روی تقاضای ۶ ترم اخیر؛ بازه اطمینان تقریبی ۸۰٪ از خطاهای درون‌نمونه‌ای (×۱٫۲۸)؛ ظرفیت پیشنهادی = حد بالای بازه × حاشیه امنیت ۱۰٪ (گردش به مضرب ۵).",
        limitations=[
            "پیش‌بینی نقطه‌ای ذاتاً با عدم قطعیت همراه است و باید با بازه اطمینان خوانده شود، نه به‌تنهایی.",
            "فرض بنیادین، تداوم الگوی تاریخی است؛ تغییر برنامه درسی، شهریه یا قواعد ثبت‌نام اعتبار پیش‌بینی را کاهش می‌دهد.",
            "افق پیش‌بینی یک نیم‌سال تحصیلی است؛ پیش‌بینی چندساله با همین روش انجام نمی‌شود.",
            "برای درس با کمتر از سه ترم داده، پیش‌بینی اولیه با عدم قطعیت ۳۰٪ گزارش می‌شود و باید با احتیاط بهره‌برداری شود.",
        ] + extra_limits,
    )
