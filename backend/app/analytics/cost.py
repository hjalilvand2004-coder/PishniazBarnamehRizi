# -*- coding: utf-8 -*-
"""سرویس ۸ — تحلیل هزینه دروس

هزینه تمام‌شده هر ارائه: هزینه استاد (ساعت × نرخ ساعتی پایه) + هزینه کلاس + سربار ثابت.
خروجی: هزینه هر دانشجو، هر ساعت-اعتبار دانشجویی و در صورت فعال‌سازی، درآمد/سود شهریه.

نرخ‌ها «پارامتر ورودی» هستند و مقادیر پیش‌فرض صرفاً نمونه‌اند.
"""
from ..models import Instructor
from .base import (
    OVERHEAD_PER_OFFERING, ROOM_HOURLY_COST, TEACHING_WEEKS, TUITION_PER_CREDIT,
    fa_int, filtered_courses, ok, offerings_by_course, ordered_terms, r0, r1,
)


def course_cost(db, department_id=None, course_id=None, room_hourly=None, weeks=None,
                overhead=None, tuition_per_credit=None):
    room_hourly = int(room_hourly) if room_hourly else ROOM_HOURLY_COST
    weeks = int(weeks) if weeks else TEACHING_WEEKS
    overhead = int(overhead) if overhead else OVERHEAD_PER_OFFERING
    tuition = int(tuition_per_credit) if tuition_per_credit else None

    courses = filtered_courses(db, department_id, course_id)
    by_course = offerings_by_course(db)
    terms = ordered_terms(db)
    latest = terms[-1] if terms else None
    instr_map = {i.id: i for i in db.query(Instructor).all()}

    rows = []
    for c in courses:
        offs = by_course.get(c.id, [])
        if latest:
            offs = [o for o in offs if o.term_id == latest.id]
        if not offs:
            continue
        o = offs[-1]
        instr = instr_map.get(o.instructor_id)
        weekly_hours = c.credits
        total_hours = c.credits * weeks
        instructor_cost = total_hours * (instr.hourly_cost if instr else 470000)
        room_cost = weekly_hours * weeks * room_hourly
        total = instructor_cost + room_cost + overhead
        enrolled = max(o.enrolled, 1)
        per_student = total / enrolled
        sch = o.enrolled * c.credits
        cost_per_sch = (total / sch) if sch else None
        row = {
            "course": f"{c.code} — {c.title}",
            "term": latest.label if latest else "—",
            "instructor": instr.name if instr else "—",
            "enrolled": o.enrolled,
            "weekly_hours": weekly_hours,
            "instructor_cost": instructor_cost,
            "room_cost": room_cost,
            "overhead": overhead,
            "total_cost": total,
            "per_student": per_student,
            "cost_per_sch": cost_per_sch,
        }
        if tuition:
            revenue = o.enrolled * c.credits * tuition
            row["revenue"] = revenue
            row["net"] = revenue - total
        rows.append(row)

    rows.sort(key=lambda x: -(x["per_student"] or 0))

    charts = [{
        "key": "per_student",
        "type": "bar",
        "title": "هزینه هر دانشجو (میلیون تومان) — ده درس پرهزینه",
        "data": [{"name": x["course"].split(" — ")[0], "value": r1(x["per_student"] / 1e6)} for x in rows[:10]],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "هزینه هر دانشجو (میلیون تومان)"},
    }]
    if tuition:
        nets = sorted(rows, key=lambda x: (x["net"] or 0))
        charts.append({
            "key": "net",
            "type": "bar",
            "title": "خالص درآمد − هزینه (میلیون تومان) — درس‌های زیان‌ده",
            "data": [{"name": x["course"].split(" — ")[0], "value": r1(x["net"] / 1e6)} for x in nets[:10]],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "خالص (میلیون تومان)"},
        })

    totals = [x["total_cost"] for x in rows]
    pers = [x["per_student"] for x in rows]
    schs = [x["cost_per_sch"] for x in rows if x["cost_per_sch"]]
    kpis = [
        {"label": "میانگین هزینه هر دانشجو", "value": r1(sum(pers) / len(pers) / 1e6) if pers else None,
         "unit": "میلیون تومان"},
        {"label": "پرهزینه‌ترین درس",
         "value": f"{rows[0]['course'].split(' — ')[0]} ({fa_int(rows[0]['per_student'] / 1e6)} م.ت)" if rows else "—"},
        {"label": "میانگین هزینه هر ساعت-اعتبار", "value": r0(sum(schs) / len(schs) / 1e6) if schs else None,
         "unit": "میلیون تومان"},
        {"label": "جمع هزینه ارائه‌های ترم جاری", "value": fa_int(sum(totals) / 1e6) if totals else "—",
         "unit": "میلیون تومان"},
    ]

    columns = [
        {"key": "course", "label": "درس"},
        {"key": "instructor", "label": "استاد"},
        {"key": "enrolled", "label": "ثبت‌نام", "format": "int"},
        {"key": "weekly_hours", "label": "ساعت/هفته", "format": "int"},
        {"key": "instructor_cost", "label": "هزینه استاد", "format": "money"},
        {"key": "room_cost", "label": "هزینه کلاس", "format": "money"},
        {"key": "overhead", "label": "سربار ثابت", "format": "money"},
        {"key": "total_cost", "label": "جمع هزینه", "format": "money"},
        {"key": "per_student", "label": "هزینه هر دانشجو", "format": "money"},
        {"key": "cost_per_sch", "label": "هزینه هر ساعت-اعتبار", "format": "money"},
    ]
    if tuition:
        columns += [
            {"key": "revenue", "label": "درآمد شهریه", "format": "money"},
            {"key": "net", "label": "خالص", "format": "money"},
        ]

    return ok(
        "course-cost", "تحلیل هزینه دروس", 8,
        filters={"department_id": department_id, "course_id": course_id, "room_hourly": room_hourly,
                 "weeks": weeks, "overhead": overhead, "tuition_per_credit": tuition},
        kpis=kpis, charts=charts,
        table={"columns": columns, "rows": rows},
        method="هزینه استاد = ساعت کل (واحد × هفته‌ها) × نرخ ساعتی پایه استاد؛ هزینه کلاس = ساعت هفتگی × هفته‌ها × نرخ سالن؛ به‌علاوه سربار ثابت هر ارائه. محاسبه بر اساس ارائه ترم جاری؛ نرخ‌ها پارامتر ورودی و پیش‌فرض‌ها نمونه‌اند.",
        limitations=[
            "نرخ‌های پیش‌فرض نمونه‌اند و باید با نرخ‌های واقعی سازمان (قراردادها، آب، برق، استهلاک) جایگزین شوند.",
            "تفاوت هزینه درس‌های عملی/آزمایشگاهی/تزی با دروس نظری لحاظ نشده است.",
            "هزینه‌های غیرمستقیم کامل نیستند؛ خروجی برای پشتیبانی بودجه‌ریزی است، نه سند مالی رسمی.",
            "درآمد شهریه تنها در صورت فعال‌سازی پارامتر محاسبه می‌شود و برای دانشگاه‌های نوبشهری معنا ندارد.",
        ],
    )
