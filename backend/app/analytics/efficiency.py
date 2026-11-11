# -*- coding: utf-8 -*-
"""سرویس ۱۰ — تحلیل بهره‌وری آموزش

خروجی آموزشی = «ساعت-اعتبار دانشجویی» (SCH = ثبت‌نام × واحد درس).
بهره‌وری = SCH به‌ازای هر استاد FTE؛ در کنار پرشدن ظرفیت و رضایت در یک شاخص مرکب.

هشدار: بهره‌وری پایین لزوماً ضعف نیست (کلاس کوچک عملی می‌تواند انتخاب آگاهانه باشد)؛
این خروجی باید همراه شاخص‌های کیفیت خوانده شود.
"""
from ..models import Course, Department, Instructor, Offering
from .base import (
    ADJUNCT_FTE, fa_int, ok, r1, wavg,
)


def _norm(values, v):
    lo, hi = min(values), max(values)
    if hi == lo:
        return 0.0
    return (v - lo) / (hi - lo)


def teaching_efficiency(db):
    from ..models import Term
    terms = sorted(db.query(Term).all(), key=lambda t: t.order_index)
    latest = terms[-1] if terms else None

    depts = db.query(Department).all()
    courses = {c.id: c for c in db.query(Course).all()}
    instr_by_dept = {}
    for i in db.query(Instructor).all():
        instr_by_dept.setdefault(i.department_id, []).append(i)
    all_offs = db.query(Offering).all()

    metrics = []
    trend_rows = []
    for d in depts:
        instrs = instr_by_dept.get(d.id, [])
        fte = sum(1.0 if i.employment == "faculty" else ADJUNCT_FTE for i in instrs)
        course_ids = {c.id for c in courses.values() if c.department_id == d.id}

        offs_latest = [o for o in all_offs if latest and o.term_id == latest.id and o.course_id in course_ids]
        sch = sum(o.enrolled * courses[o.course_id].credits for o in offs_latest)
        cap = sum(o.capacity for o in offs_latest)
        enr = sum(o.enrolled for o in offs_latest)
        utilization = (enr / cap * 100) if cap else None
        satisfaction = wavg([(o.satisfaction, o.evaluation_count) for o in all_offs if o.course_id in course_ids])
        sch_per_fte = (sch / fte) if fte else None
        metrics.append({
            "name": d.name,
            "sch": sch,
            "utilization": r1(utilization),
            "satisfaction": r1(satisfaction),
            "sch_per_fte": r1(sch_per_fte),
            "fte": r1(fte),
        })

        # روند پرشدن ظرفیت چند ترم اخیر برای قرائت کیفیت
        for t in terms[-3:]:
            offs_t = [o for o in all_offs if o.term_id == t.id and o.course_id in course_ids]
            cap_t = sum(o.capacity for o in offs_t)
            enr_t = sum(o.enrolled for o in offs_t)
            trend_rows.append({
                "term": t.label,
                "department": d.name,
                "fill_pct": r1((enr_t / cap_t * 100) if cap_t else None),
            })

    schs = [m["sch_per_fte"] for m in metrics if m["sch_per_fte"] is not None]
    utils = [m["utilization"] for m in metrics if m["utilization"] is not None]
    sats = [m["satisfaction"] for m in metrics if m["satisfaction"] is not None]

    rows = []
    for m in metrics:
        idx = 0.0
        if schs and m["sch_per_fte"] is not None:
            idx += 0.5 * _norm(schs, m["sch_per_fte"])
        if utils and m["utilization"] is not None:
            idx += 0.3 * _norm(utils, m["utilization"])
        if sats and m["satisfaction"] is not None:
            idx += 0.2 * _norm(sats, m["satisfaction"])
        rows.append({
            "department": m["name"],
            "fte": m["fte"],
            "sch": m["sch"],
            "sch_per_fte": m["sch_per_fte"],
            "utilization": m["utilization"],
            "satisfaction": m["satisfaction"],
            "efficiency_index": r1(idx * 100),
        })
    rows.sort(key=lambda x: -(x["efficiency_index"] or 0))

    charts = [
        {
            "key": "sch_per_fte",
            "type": "bar",
            "title": "ساعت-اعتبار دانشجویی به‌ازای هر استاد FTE (ترم جاری)",
            "data": [{"name": x["department"], "value": x["sch_per_fte"]} for x in rows],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "SCH به‌ازای FTE"},
        },
        {
            "key": "efficiency",
            "type": "bar",
            "title": "شاخص مرکب بهره‌وری (۰ تا ۱۰۰)",
            "data": [{"name": x["department"], "value": x["efficiency_index"]} for x in rows],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "شاخص بهره‌وری"},
        },
    ]

    total_sch = sum(x["sch"] for x in rows)
    avg_util = r1(sum(x["utilization"] for x in rows if x["utilization"] is not None)
                  / max(1, sum(1 for x in rows if x["utilization"] is not None)))
    avg_idx = r1(sum(x["efficiency_index"] for x in rows) / len(rows)) if rows else None
    kpis = [
        {"label": "ساعت-اعتبار دانشجویی ترم جاری", "value": fa_int(total_sch), "hint": "SCH = ثبت‌نام × واحد درس"},
        {"label": "میانگین پرشدن ظرفیت", "value": avg_util, "unit": "٪"},
        {"label": "میانگین شاخص بهره‌وری", "value": avg_idx},
        {"label": "بهترین بهره‌وری ظاهری", "value": rows[0]["department"] if rows else "—",
         "hint": "باید همراه رضایت و قبولی خوانده شود"},
    ]

    return ok(
        "teaching-efficiency", "تحلیل بهره‌وری آموزش", 10,
        filters={},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "department", "label": "دانشکده"},
            {"key": "fte", "label": "استاد (FTE)"},
            {"key": "sch", "label": "SCH ترم جاری", "format": "int"},
            {"key": "sch_per_fte", "label": "SCH به‌ازای FTE"},
            {"key": "utilization", "label": "پرشدن ظرفیت", "format": "pct"},
            {"key": "satisfaction", "label": "رضایت (از ۵)"},
            {"key": "efficiency_index", "label": "شاخص بهره‌وری"},
        ], "rows": rows},
        method="SCH = Σ(ثبت‌نام × واحد درس) در ترم جاری؛ بهره‌وری = SCH ÷ FTE (هیئت علمی + ۰٫۵ × حق‌التدریس)؛ شاخص مرکب = نرمال‌سازی min-max با وزن‌های SCH/FTE (۵۰٪)، پرشدن ظرفیت (۳۰٪) و رضایت (۲۰٪).",
        limitations=[
            "بهره‌وری پایین لزوماً ضعف نیست؛ کلاس‌های کوچک عملی/آزمایشگاهی می‌توانند انتخاب آگاهانه کیفیت باشند.",
            "این شاخص باید همراه رضایت و نرخ قبولی خوانده شود؛ بهبود بهره‌وری به‌تنهایی مبنای کاهش نیرو نیست.",
            "وزن‌های شاخص مرکب فرض مدیریتی‌اند و قابل تنظیم‌اند.",
            "داده نمونه سینتتیک است؛ تصمیم‌های واقعی باید روی داده رسمی سازمان انجام شود.",
        ],
    )
