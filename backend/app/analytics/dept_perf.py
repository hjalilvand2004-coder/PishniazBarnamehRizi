# -*- coding: utf-8 -*-
"""سرویس ۶ — تحلیل عملکرد دانشکده‌ها

شاخص مرکب عملکرد با وزن‌های شفاف و نرمال‌سازی min-max بین دانشکده‌ها:
پرشدن ظرفیت (۲۰٪) + رضایت (۳۰٪) + نرخ قبولی (۳۰٪) + بهره‌وری هزینه (۲۰٪).

هدف ابزار «شفاف‌سازی» است، نه رتبه‌بندی رسمی؛ شرایط دانشکده‌ها با هم یکسان نیست.
"""
from ..models import Course, Department, Instructor, Major, Offering, Student
from .base import (
    ADJUNCT_FTE, OVERHEAD_PER_OFFERING, ROOM_HOURLY_COST, TEACHING_WEEKS,
    fa_int, ok, r1, wavg,
    real_basis_limitations, eval_missing_limitation, result_missing_limitation, student_missing_limitation
)


def _norm(values, v):
    lo, hi = min(values), max(values)
    if hi == lo:
        return 0.0
    return (v - lo) / (hi - lo)


def department_performance(db):
    from ..models import Term
    terms = sorted(db.query(Term).all(), key=lambda t: t.order_index)
    latest = terms[-1] if terms else None

    depts = db.query(Department).all()
    courses = db.query(Course).all()
    courses_by_dept = {}
    for c in courses:
        courses_by_dept.setdefault(c.department_id, []).append(c)
    course_credits = {c.id: c.credits for c in courses}
    instr_by_dept = {}
    for i in db.query(Instructor).all():
        instr_by_dept.setdefault(i.department_id, []).append(i)
    majors = db.query(Major).all()
    majors_by_dept = {}
    for m in majors:
        majors_by_dept.setdefault(m.department_id, []).append(m)
    student_counts = {}
    for s in db.query(Student).filter(Student.status == "active").all():
        student_counts[s.major_id] = student_counts.get(s.major_id, 0) + 1
    all_offs = db.query(Offering).all()

    metrics = []
    for d in depts:
        course_ids = {c.id for c in courses_by_dept.get(d.id, [])}
        offs_all = [o for o in all_offs if o.course_id in course_ids]
        offs_latest = [o for o in offs_all if latest and o.term_id == latest.id]

        students = sum(student_counts.get(m.id, 0) for m in majors_by_dept.get(d.id, []))
        fte = sum(1.0 if i.employment == "faculty" else ADJUNCT_FTE for i in instr_by_dept.get(d.id, []))

        cap = sum(o.capacity for o in offs_latest)
        enr = sum(o.enrolled for o in offs_latest)
        fill = (enr / cap * 100) if cap else None
        satisfaction = wavg([(o.satisfaction, o.evaluation_count) for o in offs_all])
        pass_rate = wavg([(o.passed / o.enrolled * 100, o.enrolled) for o in offs_all if o.enrolled])

        # هزینه هر ساعت-اعتبار دانشجویی در ترم جاری
        instr_map = {i.id: i for i in db.query(Instructor).all()}
        total_cost = 0
        for o in offs_latest:
            instr = instr_map.get(o.instructor_id)
            weekly = course_credits.get(o.course_id, 3)
            total_cost += weekly * TEACHING_WEEKS * (instr.hourly_cost if instr else 470000)
            total_cost += weekly * TEACHING_WEEKS * ROOM_HOURLY_COST
            total_cost += OVERHEAD_PER_OFFERING
        sch = sum(o.enrolled * course_credits.get(o.course_id, 3) for o in offs_latest)
        cost_per_sch = (total_cost / sch) if sch else None

        metrics.append({
            "id": d.id,
            "name": d.name,
            "students": students,
            "fte": r1(fte),
            "ratio": r1(students / fte) if fte else None,
            "fill_pct": r1(fill),
            "satisfaction": r1(satisfaction),
            "pass_pct": r1(pass_rate),
            "cost_per_sch": cost_per_sch,
        })

    fills = [m["fill_pct"] for m in metrics if m["fill_pct"] is not None]
    sats = [m["satisfaction"] for m in metrics if m["satisfaction"] is not None]
    passes = [m["pass_pct"] for m in metrics if m["pass_pct"] is not None]
    costs = [m["cost_per_sch"] for m in metrics if m["cost_per_sch"] is not None]

    rows = []
    for m in metrics:
        comp = 0.0
        if fills and m["fill_pct"] is not None:
            comp += 0.20 * _norm(fills, m["fill_pct"])
        if sats and m["satisfaction"] is not None:
            comp += 0.30 * _norm(sats, m["satisfaction"])
        if passes and m["pass_pct"] is not None:
            comp += 0.30 * _norm(passes, m["pass_pct"])
        if costs and m["cost_per_sch"] is not None:
            comp += 0.20 * (1 - _norm(costs, m["cost_per_sch"]))
        rows.append({
            "department": m["name"],
            "students": m["students"],
            "fte": m["fte"],
            "ratio": m["ratio"],
            "fill_pct": m["fill_pct"],
            "satisfaction": m["satisfaction"],
            "pass_pct": m["pass_pct"],
            "cost_per_sch": r1(m["cost_per_sch"]),
            "composite": r1(comp * 100),
        })
    rows.sort(key=lambda x: -(x["composite"] or 0))

    charts = [{
        "key": "composite",
        "type": "bar",
        "title": "شاخص مرکب عملکرد دانشکده‌ها (۰ تا ۱۰۰)",
        "data": [{"name": x["department"], "value": x["composite"]} for x in rows],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "شاخص مرکب"},
    }]

    ratios = [m["ratio"] for m in metrics if m["ratio"] is not None]
    kpis = [
        {"label": "دانشکده بررسی‌شده", "value": len(rows), "unit": "دانشکده"},
        {"label": "میانگین شاخص مرکب", "value": r1(sum(x["composite"] for x in rows) / len(rows)) if rows else None},
        {"label": "بهترین پرشدن ظرفیت",
         "value": f"{max(rows, key=lambda x: x['fill_pct'] or 0)['department']}" if rows else "—",
         "hint": "صرفاً گزارش وضعیت است، نه اعلام برتری"},
        {"label": "دامنه نسبت دانشجو/استاد",
         "value": f"{fa_int(min(ratios))} تا {fa_int(max(ratios))}" if ratios else "—"},
    ]

    extra_limits = list(real_basis_limitations(db))
    _m = student_missing_limitation(db)
    if _m: extra_limits.append(_m)
    _m = eval_missing_limitation(db, "رضایت نظرسنجی")
    if _m: extra_limits.append(_m)

    return ok(
        "department-performance", "تحلیل عملکرد دانشکده‌ها", 6,
        filters={},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "department", "label": "دانشکده"},
            {"key": "students", "label": "دانشجوی فعال", "format": "int"},
            {"key": "fte", "label": "استاد (FTE)"},
            {"key": "ratio", "label": "نسبت دانشجو/استاد"},
            {"key": "fill_pct", "label": "پرشدن ظرفیت ترم جاری", "format": "pct"},
            {"key": "satisfaction", "label": "رضایت (از ۵)"},
            {"key": "pass_pct", "label": "نرخ قبولی", "format": "pct"},
            {"key": "cost_per_sch", "label": "هزینه هر ساعت-اعتبار (تومان)", "format": "money"},
            {"key": "composite", "label": "شاخص مرکب"},
        ], "rows": rows},
        method="نرمال‌سازی min-max شاخص‌ها بین دانشکده‌ها و ترکیب با وزن‌های اعلام‌شده: پرشدن ظرفیت ۲۰٪، رضایت ۳۰٪، نرخ قبولی ۳۰٪ و بهره‌وری هزینه (معکوس) ۲۰٪؛ FTE = هیئت علمی تمام‌وقت + ۰٫۵ × حق‌التدریس.",
        limitations=[
            "شرایط دانشکده‌ها یکسان نیست (ماهیت رشته، کلاس عملی/آزمایشگاهی، نسبت هیئت علمی)؛ مقایسه مستقیم باید با احتیاط انجام شود.",
            "وزن‌های شاخص مرکب فرض مدیریتی‌اند و باید با اولویت‌های سازمان تنظیم شوند.",
            "این ابزار برای شفاف‌سازی است، نه رتبه‌بندی رسمی؛ تصمیم با شوراهای ذی‌صلاح است.",
            "هزینه‌ها بر مبنای نرخ‌های نمونه محاسبه شده و باید با نرخ‌های واقعی سازمان جایگزین شود.",
        ] + extra_limits,
    )
