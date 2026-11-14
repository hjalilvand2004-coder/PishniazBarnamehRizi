# -*- coding: utf-8 -*-
"""سرویس ۱ — تحلیل تقاضای دروس

تقاضا = ثبت‌نام انجام‌شده + محروم‌شدگان ظرفیت؛ روند با برازش خطی روی ترم‌های اخیر
سنجیده و دروس به پرتقاضا/کم‌تقاضا/دارای ظرفیت ناکافی طبقه‌بندی می‌شوند.
"""
from ..models import Department
from .base import (
    fa_float, filtered_courses, ok, offerings_by_course, ordered_terms, r0, r1, slope_pct,
    real_basis_limitations, eval_missing_limitation, result_missing_limitation, student_missing_limitation
)


def demand_analysis(db, department_id=None, course_id=None):
    courses = filtered_courses(db, department_id, course_id)
    by_course = offerings_by_course(db)
    term_label = {t.id: t.label for t in ordered_terms(db)}
    dept_name = {d.id: d.name for d in db.query(Department).all()}

    rows = []
    for c in courses:
        offs = by_course.get(c.id, [])
        if not offs:
            continue
        demand = [o.enrolled + o.waiting for o in offs]
        growth = slope_pct(demand)
        unmet = sum(o.waiting for o in offs)
        cap = sum(o.capacity for o in offs)
        enr = sum(o.enrolled for o in offs)
        fill = (enr / cap * 100) if cap else None
        if growth is None or len(demand) < 3:
            trend = "داده ناکافی"
        elif growth >= 3:
            trend = "صعودی"
        elif growth <= -3:
            trend = "نزولی"
        else:
            trend = "ثابت"
        rows.append({
            "course": f"{c.code} — {c.title}",
            "department": dept_name.get(c.department_id, "—"),
            "demand_last": demand[-1],
            "demand_avg": r1(sum(demand) / len(demand)),
            "growth_pct": r1(growth),
            "unmet_total": unmet,
            "fill_pct": r1(fill),
            "trend": trend,
            "_growth": growth or 0.0,
            "_unmet": unmet,
        })

    rows.sort(key=lambda x: (-x["_unmet"], -x["_growth"]))
    total_unmet = sum(x["unmet_total"] for x in rows)
    fills = [x["fill_pct"] for x in rows if x["fill_pct"] is not None]
    top_growth = max(rows, key=lambda x: x["_growth"]) if rows else None

    charts = [{
        "key": "unmet",
        "type": "bar",
        "title": "تقاضای برآورده‌نشده (مجموع ۶ ترم اخیر) — ده درس نخست",
        "data": [{"name": x["course"].split(" — ")[0], "value": x["unmet_total"]} for x in rows[:10]],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "دانشجوی محروم‌شده"},
    }]
    if course_id:
        offs = by_course.get(int(course_id), [])
        charts.append({
            "key": "trend",
            "type": "line",
            "title": "روند تقاضا و ظرفیت درس انتخابی",
            "data": [{"term": term_label[o.term_id], "demand": o.enrolled + o.waiting, "capacity": o.capacity} for o in offs],
            "xKey": "term",
            "yKeys": ["demand", "capacity"],
            "seriesLabels": {"demand": "تقاضا (ثبت‌نام + محروم)", "capacity": "ظرفیت اعلامی"},
        })

    for x in rows:
        x.pop("_growth", None)
        x.pop("_unmet", None)

    kpis = [
        {"label": "درس بررسی‌شده", "value": len(rows), "unit": "درس"},
        {"label": "تقاضای برآورده‌نشده کل", "value": total_unmet, "unit": "نفر-ترم",
         "tone": "warn" if total_unmet else "good",
         "hint": "مجموع دانشجویانی که به دلیل کمبود ظرفیت ثبت‌نام نشده‌اند"},
        {"label": "میانگین پرشدن ظرفیت", "value": r1(sum(fills) / len(fills)) if fills else None, "unit": "٪"},
        {"label": "بیشترین رشد تقاضا",
         "value": f"{top_growth['course'].split(' — ')[0]} ({fa_float(top_growth['growth_pct'], signed=True)}٪ در هر ترم)" if top_growth else "—"},
    ]

    extra_limits = list(real_basis_limitations(db))

    return ok(
        "demand-analysis", "تحلیل تقاضای دروس", 1,
        filters={"department_id": department_id, "course_id": course_id},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "course", "label": "درس"},
            {"key": "department", "label": "دانشکده"},
            {"key": "demand_last", "label": "تقاضای آخرین ترم", "format": "int"},
            {"key": "demand_avg", "label": "میانگین تقاضا", "format": "float"},
            {"key": "growth_pct", "label": "رشد هر ترم", "format": "pct_signed"},
            {"key": "unmet_total", "label": "محروم‌شدگان کل", "format": "int"},
            {"key": "fill_pct", "label": "پرشدن ظرفیت", "format": "pct"},
            {"key": "trend", "label": "روند"},
        ], "rows": rows},
        method="تقاضا = ثبت‌نام انجام‌شده + محروم‌شدگان ظرفیت؛ روند با برازش خطی روی حداکثر ۶ ترم اخیر؛ آستانه طبقه‌بندی ±۳٪ در هر ترم (فرض قابل تنظیم سازمانی).",
        limitations=[
            "دانشجویانی که اصلاً برای درس ثبت‌نام نکرده‌اند در داده دیده نمی‌شوند؛ «تقاضا» بر پایه رفتار ثبت‌نام است.",
            "همبستگی روند به معنای رابطه علّی نیست؛ تغییر برنامه درسی، شهریه یا قواعد ثبت‌نام می‌تواند روند را جابه‌جا کند.",
            "درس‌های با کمتر از سه ترم داده، طبقه‌بندی روند نمی‌شوند.",
        ] + extra_limits,
    )
