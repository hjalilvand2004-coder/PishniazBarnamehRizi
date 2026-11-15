# -*- coding: utf-8 -*-
"""تحلیل‌های «دادهٔ واقعی» بر پایهٔ آینهٔ برنامه‌یار۳۶۰

این تحلیل‌ها از سوابق واقعی برنامه‌ریزی (ترم‌های ۴۰۲۱ تا ۴۰۴۲)، دروس ترمیک و
اتاق‌های واقعی محاسبه می‌شوند و همان قرارداد خروجی موتور تحلیلی (kpis/charts/table)
را دارند تا در داشبورد مدیریار۳۶۰ نمایش داده شوند.

نقش در معماری: برنامه‌یار۳۶۰ مبنای برنامه‌ریزی اجرایی است؛ این تحلیل‌ها همان
واقعیتِ اجراشده را به مدیران مدیریار۳۶۰ برمی‌گردانند تا برنامه‌ریزی اولیه دقیق‌تر شود.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import ByInstructor, ByRoom, ByScheduleHistory, ByTermCourse

WEEK_DAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "آدینه"]


def _r1(v):
    return None if v is None else round(v, 1)


def overview_kpis(db: Session) -> list[dict]:
    n_hist = db.query(ByScheduleHistory).count()
    n_courses = db.query(ByTermCourse).count()
    n_rooms = db.query(ByRoom).count()
    n_inst = db.query(ByInstructor).count()
    semesters = db.query(ByScheduleHistory.semester).distinct().count()
    scheduled = db.query(ByScheduleHistory).filter(ByScheduleHistory.day.isnot(None)).count()
    exams = db.query(ByScheduleHistory).filter(ByScheduleHistory.exam_date.isnot(None)).count()
    kpis = [
        {"label": "سوابق برنامه‌ریزی واقعی", "value": n_hist, "hint": "کلاس‌های ثبت‌شده در برنامه‌یار۳۶۰"},
        {"label": "نیم‌سال‌های پوشش‌داده‌شده", "value": semesters, "hint": "پیشینهٔ برنامه‌ریزی موجود"},
        {"label": "کلاس‌های دارای برنامه هفتگی", "value": scheduled, "hint": "رکورد با روز و ساعت مشخص"},
        {"label": "دروس ترمیک کاتالوگ", "value": n_courses, "hint": "دروس طرح درسی همهٔ مقاطع"},
        {"label": "اتاق‌ها و سایت‌های واقعی", "value": n_rooms, "hint": "کلاس‌های درس و سایت‌های کامپیوتر"},
        {"label": "اساتید واقعی", "value": n_inst, "hint": "با سقف واحدهای تدریس"},
        {"label": "رکوردهای دارای تاریخ امتحان", "value": exams, "hint": "برای هماهنگی تقویم ارزشیابی"},
    ]
    return kpis


def semester_trend(db: Session) -> dict:
    """روند واقعی فعالیت آموزشی در هر نیم‌سال — مبنای مقایسه با برنامه‌ریزی اولیه"""
    rows = db.query(
        ByScheduleHistory.semester, ByScheduleHistory.semester_label,
        ByScheduleHistory.course_name, ByScheduleHistory.instructor_code,
        ByScheduleHistory.max_capacity, ByScheduleHistory.day,
    ).all()
    agg = {}
    for sem, label, course, icode, cap, day in rows:
        a = agg.setdefault(sem, {"semester": sem, "semester_label": label or sem, "sessions": 0,
                                 "courses": set(), "instructors": set(), "caps": [], "scheduled": 0})
        a["sessions"] += 1
        if course:
            a["courses"].add(course)
        if icode:
            a["instructors"].add(icode)
        if cap:
            a["caps"].append(cap)
        if day:
            a["scheduled"] += 1
    data = []
    for sem in sorted(agg):
        a = agg[sem]
        data.append({
            "semester": a["semester"],
            "label": a["semester_label"],
            "sessions": a["sessions"],
            "courses": len(a["courses"]),
            "instructors": len(a["instructors"]),
            "avg_capacity": _r1(sum(a["caps"]) / len(a["caps"])) if a["caps"] else None,
            "scheduled": a["scheduled"],
        })
    return {
        "key": "semester-trend",
        "type": "line",
        "title": "روند واقعی فعالیت آموزشی به تفکیک نیم‌سال (دادهٔ برنامه‌یار۳۶۰)",
        "xKey": "label",
        "yKeys": ["sessions", "courses", "instructors"],
        "seriesLabels": {"sessions": "رکورد کلاس", "courses": "درس یکتا", "instructors": "استاد فعال"},
        "data": data,
    }


def day_distribution(db: Session) -> dict:
    rows = db.query(ByScheduleHistory.day).filter(ByScheduleHistory.day.isnot(None)).all()
    counts = Counter(day for (day,) in rows)
    data = [{"day": d, "sessions": counts.get(d, 0)} for d in WEEK_DAYS if counts.get(d)]
    return {
        "key": "day-distribution",
        "type": "bar",
        "title": "توزیع واقعی کلاس‌ها در روزهای هفته",
        "xKey": "day",
        "yKeys": ["sessions"],
        "seriesLabels": {"sessions": "تعداد کلاس"},
        "data": data,
    }


def time_distribution(db: Session) -> dict:
    rows = db.query(ByScheduleHistory.start_time).filter(ByScheduleHistory.start_time.isnot(None)).all()
    counts = Counter(t for (t,) in rows)
    data = [{"slot": t, "sessions": c} for t, c in sorted(counts.items())]
    return {
        "key": "time-distribution",
        "type": "bar",
        "title": "توزیع واقعی شروع کلاس‌ها در طول روز",
        "xKey": "slot",
        "yKeys": ["sessions"],
        "seriesLabels": {"sessions": "تعداد کلاس"},
        "data": data,
    }


def room_utilization(db: Session) -> dict:
    """بهره‌برداری واقعی از هر اتاق — تعداد کلاس ثبت‌شده در سوابق + ظرفیت واقعی اتاق"""
    usage = dict(db.query(ByScheduleHistory.class_code, func.count()).group_by(ByScheduleHistory.class_code).all())
    rooms = db.query(ByRoom).order_by(ByRoom.capacity.desc()).all()
    data = []
    for r in rooms:
        used = usage.get(r.code, 0)
        data.append({
            "room": r.code,
            "capacity": r.capacity or 0,
            "sessions": used,
            "place_type": r.place_type or "—",
        })
    # اتاق‌هایی که در سوابق آمده‌اند ولی در فهرست اتاق‌ها نیستند (هشدار ارتباطی)
    known = {r.code for r in rooms}
    extra = sorted((c, n) for c, n in usage.items() if c and c not in known)
    return {
        "key": "room-utilization",
        "type": "bar",
        "title": "تعداد کلاس‌های برگزارشده در هر اتاق (سوابق واقعی)",
        "xKey": "room",
        "yKeys": ["sessions"],
        "seriesLabels": {"sessions": "کلاس‌های ثبت‌شده"},
        "data": data,
        "extra": {
            "rooms_without_history": [r.code for r in rooms if not usage.get(r.code)],
            "history_codes_not_in_rooms": [{"code": c, "count": n} for c, n in extra],
        },
    }


def instructor_load(db: Session, limit: int = 15) -> dict:
    """بار تدریس واقعی اساتید از سوابق + مقایسه با سقف واحدهای تدریس اعلامی"""
    rows = db.query(
        ByScheduleHistory.instructor_name, ByScheduleHistory.instructor_code,
        ByScheduleHistory.course_name, ByScheduleHistory.max_capacity,
    ).all()
    agg = {}
    for name, code, course, cap in rows:
        if not name:
            continue
        a = agg.setdefault((name, code), {"sessions": 0, "courses": set(), "caps": []})
        a["sessions"] += 1
        if course:
            a["courses"].add(course)
        if cap:
            a["caps"].append(cap)
    inst = {i.code: i for i in db.query(ByInstructor).all()}
    data = []
    for (name, code), a in sorted(agg.items(), key=lambda kv: -kv[1]["sessions"])[:limit]:
        max_units = inst.get(code).max_teaching_units if (code and inst.get(code)) else None
        data.append({
            "instructor": name,
            "code": code or "—",
            "sessions": a["sessions"],
            "courses": len(a["courses"]),
            "avg_capacity": _r1(sum(a["caps"]) / len(a["caps"])) if a["caps"] else None,
            "max_units": max_units,
        })
    return {
        "key": "instructor-load",
        "type": "bar",
        "title": f"پرکارترین اساتید بر پایهٔ سوابق واقعی ({limit} نفر نخست)",
        "xKey": "instructor",
        "yKeys": ["sessions", "courses"],
        "seriesLabels": {"sessions": "رکورد کلاس", "courses": "درس یکتا"},
        "data": data,
    }


def term_catalog(db: Session) -> dict:
    """ترکیب کاتالوگ دروس ترمیک واقعی: مقطع، نوع درس و ظرفیت"""
    rows = db.query(ByTermCourse.level, ByTermCourse.course_type, ByTermCourse.units, ByTermCourse.capacity).all()
    by_level = defaultdict(lambda: {"count": 0, "units": [], "caps": []})
    type_counts = Counter()
    for level, ctype, units, cap in rows:
        lv = by_level[level or "—"]
        lv["count"] += 1
        if units:
            lv["units"].append(units)
        if cap:
            lv["caps"].append(cap)
        type_counts[(ctype or "نامشخص")[:40]] += 1
    level_data = []
    for level, lv in sorted(by_level.items(), key=lambda kv: -kv[1]["count"]):
        level_data.append({
            "level": level or "—",
            "courses": lv["count"],
            "avg_units": _r1(sum(lv["units"]) / len(lv["units"])) if lv["units"] else None,
            "avg_capacity": _r1(sum(lv["caps"]) / len(lv["caps"])) if lv["caps"] else None,
        })
    return {
        "key": "term-catalog",
        "level_chart": {
            "type": "bar",
            "title": "دروس ترمیک به تفکیک مقطع (کاتالوگ واقعی)",
            "xKey": "level",
            "yKeys": ["courses"],
            "seriesLabels": {"courses": "تعداد درس"},
            "data": level_data,
        },
        "type_chart": {
            "type": "pie",
            "title": "ترکیب نوع دروس ترمیک",
            "nameKey": "type",
            "data": [{"type": t, "value": c} for t, c in type_counts.most_common(8)],
        },
        "level_table": {"columns": [
            {"key": "level", "label": "مقطع", "format": "text"},
            {"key": "courses", "label": "تعداد درس", "format": "int"},
            {"key": "avg_units", "label": "میانگین واحد", "format": "float"},
            {"key": "avg_capacity", "label": "میانگین ظرفیت", "format": "float"},
        ], "rows": level_data},
    }


def data_quality(db: Session) -> dict:
    """کیفیت ارتباط داده — چه رکوردهایی برای پیوند دقیق نیاز به پاکسازی دارند"""
    total = db.query(ByScheduleHistory).count()
    if not total:
        return {"ready": False}
    no_day = db.query(ByScheduleHistory).filter(ByScheduleHistory.day.is_(None)).count()
    no_room = db.query(ByScheduleHistory).filter(ByScheduleHistory.class_code.is_(None)).count()
    no_instructor = db.query(ByScheduleHistory).filter(ByScheduleHistory.instructor_name.is_(None)).count()
    n_term = db.query(ByTermCourse).count()
    unmatched = db.query(ByTermCourse).filter(ByTermCourse.unique_course_code.is_(None)).count() if n_term else 0
    return {
        "ready": True,
        "total_history": total,
        "no_day": no_day,
        "no_day_pct": _r1(no_day / total * 100),
        "no_room": no_room,
        "no_room_pct": _r1(no_room / total * 100),
        "no_instructor": no_instructor,
        "no_instructor_pct": _r1(no_instructor / total * 100),
        "term_unmatched": unmatched,
        "term_unmatched_pct": _r1(unmatched / n_term * 100) if n_term else None,
    }


def build_insights(db: Session) -> dict:
    return {
        "kpis": overview_kpis(db),
        "charts": [
            semester_trend(db),
            day_distribution(db),
            time_distribution(db),
            room_utilization(db),
            instructor_load(db),
        ],
        "term_catalog": term_catalog(db),
        "data_quality": data_quality(db),
    }
