# -*- coding: utf-8 -*-
"""سرویس ۹ — بهینه‌سازی نسبت استاد به دانشجو

نسبت جاری دانشجو به استاد (FTE) در هر دانشکده، مقایسه با نسبت هدف و برآورد
کمبود نیروی هیئت علمی. نسبت هدف پارامتر ورودی است و باید با ضوابط رسمی سازمان
(سند آمایش یا مقررات وزارت‌خانه) تنظیم شود.
"""
import math

from ..models import Department, Instructor, Major, Student
from .base import ADJUNCT_FTE, DEFAULT_TARGET_RATIO, fa_int, ok, r1


def ratio_optimization(db, target=DEFAULT_TARGET_RATIO):
    target = float(target or DEFAULT_TARGET_RATIO)

    depts = db.query(Department).all()
    majors_by_dept = {}
    for m in db.query(Major).all():
        majors_by_dept.setdefault(m.department_id, []).append(m)
    student_counts = {}
    for s in db.query(Student).filter(Student.status == "active").all():
        student_counts[s.major_id] = student_counts.get(s.major_id, 0) + 1
    instr_by_dept = {}
    for i in db.query(Instructor).all():
        instr_by_dept.setdefault(i.department_id, []).append(i)

    rows = []
    for d in depts:
        students = sum(student_counts.get(m.id, 0) for m in majors_by_dept.get(d.id, []))
        instrs = instr_by_dept.get(d.id, [])
        faculty = sum(1 for i in instrs if i.employment == "faculty")
        adjunct = sum(1 for i in instrs if i.employment == "adjunct")
        fte = faculty + ADJUNCT_FTE * adjunct
        ratio = (students / fte) if fte else None
        needed_fte = math.ceil(students / target) if students else 0
        rows.append({
            "department": d.name,
            "students": students,
            "faculty": faculty,
            "adjunct": adjunct,
            "fte": r1(fte),
            "ratio": r1(ratio),
            "target": target,
            "gap": r1((ratio - target) if ratio is not None else None),
            "needed_hires": max(0, needed_fte - int(fte)) if fte else None,
        })
    rows.sort(key=lambda x: -(x["ratio"] or 0))

    charts = [{
        "key": "ratio",
        "type": "bar",
        "title": "نسبت دانشجو به استاد (FTE) به تفکیک دانشکده",
        "data": [{"name": x["department"], "value": x["ratio"]} for x in rows],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "نسبت دانشجو/استاد"},
        "refLine": target,
        "refLabel": f"نسبت هدف {fa_int(target)}",
    }]

    total_students = sum(x["students"] for x in rows)
    total_fte = sum(x["fte"] or 0 for x in rows)
    total_needed = sum(x["needed_hires"] or 0 for x in rows)
    overall_ratio = (total_students / total_fte) if total_fte else None
    kpis = [
        {"label": "نسبت کل دانشگاه", "value": r1(overall_ratio), "unit": "دانشجو/استاد FTE"},
        {"label": "نسبت هدف", "value": target, "unit": "دانشجو/استاد",
         "hint": "پارامتر ورودی — باید با ضوابط رسمی تنظیم شود"},
        {"label": "کمبود برآوردی FTE", "value": total_needed, "unit": "نفر",
         "tone": "warn" if total_needed else "good",
         "hint": "مجموع کمبود دانشکده‌ها نسبت به هدف"},
        {"label": "بالاترین نسبت",
         "value": f"{rows[0]['department']} ({fa_int(rows[0]['ratio'])})" if rows else "—"},
    ]

    return ok(
        "ratio-optimization", "بهینه‌سازی نسبت استاد به دانشجو", 9,
        filters={"target": target},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "department", "label": "دانشکده"},
            {"key": "students", "label": "دانشجوی فعال", "format": "int"},
            {"key": "faculty", "label": "هیئت علمی", "format": "int"},
            {"key": "adjunct", "label": "حق‌التدریس", "format": "int"},
            {"key": "fte", "label": "جمع FTE"},
            {"key": "ratio", "label": "نسبت جاری"},
            {"key": "target", "label": "نسبت هدف"},
            {"key": "gap", "label": "فاصله از هدف"},
            {"key": "needed_hires", "label": "کمبود برآوردی (نفر)", "format": "int"},
        ], "rows": rows},
        method="FTE = تعداد هیئت علمی تمام‌وقت + ۰٫۵ × تعداد حق‌التدریس؛ نسبت جاری = دانشجوی فعال ÷ FTE؛ کمبود برآوردی = کف(دانشجو ÷ نسبت هدف) − FTE جاری.",
        limitations=[
            "نسبت هدف باید بر اساس ضوابط رسمی سازمان یا مقررات وزارت‌خانه تنظیم شود؛ مقدار پیش‌فرض صرفاً نمونه است.",
            "یکنواخت‌بودن نسبت هدف برای همه رشته‌ها دقیق نیست؛ رشته‌های عملی/آزمایشگاهی نسبت پایین‌تری لازم دارند.",
            "«کمبود برآوردی» پیشنهاد برنامه‌ریزی است، نه مجوز استخدام؛ تصمیم با مراجع قانونی ذی‌صلاح است.",
            "جمعیت دانشجویی بر اساس وضعیت ثبت‌نامی جاری است و پیک تقاضای درسی هر ترم ممکن است متفاوت باشد.",
        ],
    )
