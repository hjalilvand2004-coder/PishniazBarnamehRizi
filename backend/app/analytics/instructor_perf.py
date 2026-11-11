# -*- coding: utf-8 -*-
"""سرویس ۴ — تحلیل عملکرد اساتید

شاخص‌های تدریس (نمره، قبولی، رضایت) با میانگین وزنی و آستانه کفایت نمونه نظرسنجی.
نرخ مردودی متوسط درس‌های ارائه‌شده به‌عنوان «شاخص شرایط درس» برای قرائت زمینه‌ای گزارش می‌شود.

مرز استفاده: این خروجی برای رتبه‌بندی تنبیهی طراحی نشده است؛ کاربرد پیشنهادی آن
خودارزیابی اساتید و پشتیبانی از توسعه حرفه‌ای است.
"""
from ..models import Department, Instructor, Offering
from .base import (
    EMPLOYMENT_FA, MIN_EVAL_SAMPLE, RANK_FA, ok, r1, wavg,
)


def instructor_performance(db, department_id=None, instructor_id=None, min_sample=MIN_EVAL_SAMPLE):
    min_sample = int(min_sample or MIN_EVAL_SAMPLE)

    q = db.query(Instructor)
    if department_id:
        q = q.filter(Instructor.department_id == int(department_id))
    if instructor_id:
        q = q.filter(Instructor.id == int(instructor_id))
    instructors = q.all()

    dept_name = {d.id: d.name for d in db.query(Department).all()}
    offs_by_instr = {}
    for o in db.query(Offering).all():
        offs_by_instr.setdefault(o.instructor_id, []).append(o)

    rows = []
    for i in instructors:
        offs = offs_by_instr.get(i.id, [])
        if not offs:
            continue
        enrolled_total = sum(o.enrolled for o in offs)
        eval_total = sum(o.evaluation_count for o in offs)
        avg_grade = wavg([(o.avg_grade, o.enrolled) for o in offs])
        pass_rate = wavg([(o.passed / o.enrolled * 100, o.enrolled) for o in offs if o.enrolled])
        satisfaction = wavg([(o.satisfaction, o.evaluation_count) for o in offs])
        conditions_fail = wavg([(o.failed / o.enrolled * 100, o.enrolled) for o in offs if o.enrolled])
        rows.append({
            "instructor": i.name,
            "department": dept_name.get(i.department_id, "—"),
            "rank": RANK_FA.get(i.rank, i.rank),
            "employment": EMPLOYMENT_FA.get(i.employment, i.employment),
            "terms_n": len({o.term_id for o in offs}),
            "students_total": enrolled_total,
            "avg_grade": r1(avg_grade),
            "pass_pct": r1(pass_rate),
            "satisfaction": r1(satisfaction),
            "eval_total": eval_total,
            "conditions_fail_pct": r1(conditions_fail),
            "sample_ok": "کافی" if eval_total >= min_sample else "ناکافی",
        })
    rows.sort(key=lambda x: x["instructor"])  # مرتب بر اساس نام — بدون رتبه‌بندی ضمنی

    scatter = [{"x": x["conditions_fail_pct"], "y": x["satisfaction"], "name": x["instructor"],
                "z": 0 if x["sample_ok"] == "کافی" else 1} for x in rows if x["satisfaction"] is not None]
    charts = [{
        "key": "conditions",
        "type": "scatter",
        "title": "رضایت در برابر شرایط درس (نرخ مردودی متوسط درس‌های ارائه‌شده)",
        "data": scatter,
        "xKey": "x",
        "yKeys": ["y"],
        "xLabel": "نرخ مردودی متوسط درس‌ها (٪) — شاخص شرایط درس",
        "yLabel": "میانگین رضایت (از ۵)",
    }]

    sats = [x["satisfaction"] for x in rows if x["satisfaction"] is not None]
    insufficient = [x for x in rows if x["sample_ok"] == "ناکافی"]
    kpis = [
        {"label": "استاد دارای سابقه تدریس", "value": len(rows), "unit": "نفر"},
        {"label": "میانگین رضایت کل (وزنی)", "value": r1(sum(sats) / len(sats)) if sats else None, "unit": "از ۵"},
        {"label": "استاد با نمونه ناکافی", "value": len(insufficient), "unit": "نفر",
         "tone": "warn" if insufficient else "good",
         "hint": f"مجموع پاسخ نظرسنجی کمتر از {min_sample} — تفسیر عملکرد مجاز نیست"},
        {"label": "آستانه کفایت نمونه", "value": min_sample, "unit": "پاسخ", "hint": "پارامتر قابل تنظیم"},
    ]

    return ok(
        "instructor-performance", "تحلیل عملکرد اساتید", 4,
        filters={"department_id": department_id, "instructor_id": instructor_id, "min_sample": min_sample},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "instructor", "label": "استاد"},
            {"key": "department", "label": "دانشکده"},
            {"key": "rank", "label": "مرتبه"},
            {"key": "employment", "label": "نوع همکاری"},
            {"key": "terms_n", "label": "ترم‌های تدریس", "format": "int"},
            {"key": "students_total", "label": "جمع دانشجویان", "format": "int"},
            {"key": "avg_grade", "label": "میانگین نمره"},
            {"key": "pass_pct", "label": "نرخ قبولی", "format": "pct"},
            {"key": "satisfaction", "label": "رضایت (از ۵)"},
            {"key": "eval_total", "label": "پاسخ نظرسنجی", "format": "int"},
            {"key": "conditions_fail_pct", "label": "شرایط درس (مردودی متوسط)", "format": "pct"},
            {"key": "sample_ok", "label": "کفایت نمونه"},
        ], "rows": rows},
        method="میانگین وزنی شاخص‌ها (وزن: تعداد پاسخ نظرسنجی برای رضایت، تعداد ثبت‌نام برای نمره و قبولی)؛ محور افقی نمودار پراکندگی، نرخ مردودی متوسط درس‌های ارائه‌شده به‌عنوان شاخص «شرایط درس» است تا قرائت عملکرد زمینه‌مند شود.",
        limitations=[
            "رضایت و نمره تحت تأثیر شرایط درس است (سطح درس، ساعت برگزاری، ترکیب دانشجویان، سخت‌گیری ارزشیابی) و قابل انتساب صرف به استاد نیست.",
            "همبستگی شاخص‌ها به معنای رابطه علّی با عملکرد استاد نیست.",
            f"اساتیدی که مجموع پاسخ‌های نظرسنجی آن‌ها کمتر از {min_sample} است تفسیر نمی‌شوند؛ ستون «کفایت نمونه» را رعایت کنید.",
            "این خروجی برای رتبه‌بندی تنبیهی یا تصمیم‌های انضباطی طراحی نشده است؛ کاربرد پیشنهادی: خودارزیابی و پشتیبانی توسعه حرفه‌ای.",
        ],
    )
