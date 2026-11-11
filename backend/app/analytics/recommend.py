# -*- coding: utf-8 -*-
"""سرویس ۵ — توصیه استاد برای ارائه درس

نامزدهای مناسب هر درس بر پایه چهار مؤلفه: تطبیق تخصص، سابقه ارائه همان درس
(رضایت و نرخ قبولی تاریخی)، بار آموزشی جاری و ظرفیت باقی‌مانده ساعت تدریس.

خروجی «توصیه پشتیبان» است؛ تصمیم نهایی با گروه آموزشی و شورای مربوطه است.
"""
from ..models import Course, Instructor, Offering
from .base import EMPLOYMENT_FA, RANK_FA, fa_int, fa_pct, ok, r1, wavg


def instructor_recommendation(db, course_id, top=5):
    course = db.get(Course, int(course_id))
    if course is None:
        return None
    top = max(1, min(int(top or 5), 10))
    ctags = set(course.tags or [])

    terms = sorted(db.query(Offering.term_id).distinct(), key=lambda x: x[0])
    from ..models import Term
    latest = sorted(db.query(Term).all(), key=lambda t: t.order_index)[-1]

    cands = db.query(Instructor).filter(Instructor.department_id == course.department_id).all()

    by_instr_course = {}
    by_instr_term = {}
    by_instr = {}
    course_by_id = {c.id: c for c in db.query(Course).all()}
    for o in db.query(Offering).all():
        by_instr_course.setdefault((o.instructor_id, o.course_id), []).append(o)
        by_instr_term.setdefault((o.instructor_id, o.term_id), []).append(o)
        by_instr.setdefault(o.instructor_id, []).append(o)

    rows = []
    for i in cands:
        itags = set(i.expertise or [])
        match = (len(ctags & itags) / len(ctags)) if ctags else 0.0

        hist = by_instr_course.get((i.id, course.id), [])
        hist_n = len(hist)
        hist_sat = wavg([(o.satisfaction, o.evaluation_count) for o in hist])
        hist_pass = wavg([(o.passed / o.enrolled * 100, o.enrolled) for o in hist if o.enrolled])

        all_offs = by_instr.get(i.id, [])
        overall_sat = wavg([(o.satisfaction, o.evaluation_count) for o in all_offs])
        overall_pass = wavg([(o.passed / o.enrolled * 100, o.enrolled) for o in all_offs if o.enrolled])

        load = sum(course_by_id[o.course_id].credits for o in by_instr_term.get((i.id, latest.id), [])
                   if o.course_id in course_by_id)
        headroom = max(0, i.max_weekly_hours - load)
        headroom_n = min(1.0, headroom / 6)

        if hist_n:
            score = 100 * (0.35 * match
                           + 0.30 * ((hist_sat or 0) / 5)
                           + 0.25 * ((hist_pass or 0) / 100)
                           + 0.10 * headroom_n)
            basis = f"{fa_int(hist_n)} بار سابقه ارائه این درس"
        else:
            score = 100 * (0.45 * match
                           + 0.30 * ((overall_sat or 0) / 5)
                           + 0.15 * ((overall_pass or 0) / 100)
                           + 0.10 * headroom_n)
            basis = "بدون سابقه ارائه این درس (پیشنهاد بر پایه تخصص)"

        rows.append({
            "instructor": i.name,
            "rank": RANK_FA.get(i.rank, i.rank),
            "employment": EMPLOYMENT_FA.get(i.employment, i.employment),
            "match_pct": r1(match * 100),
            "history_n": hist_n,
            "hist_satisfaction": r1(hist_sat),
            "hist_pass_pct": r1(hist_pass),
            "current_load_h": load,
            "headroom_h": headroom,
            "score": r1(score),
            "basis": basis,
        })

    rows.sort(key=lambda x: -x["score"])
    rows = rows[:top]

    charts = [{
        "key": "score",
        "type": "bar",
        "title": "امتیاز تطبیق نامزدها",
        "data": [{"name": x["instructor"], "value": x["score"]} for x in rows],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "امتیاز (از ۱۰۰)"},
    }]

    with_history = [x for x in rows if x["history_n"] > 0]
    best_match = max((x["match_pct"] for x in rows), default=None)
    kpis = [
        {"label": "درس هدف", "value": f"{course.code} — {course.title}"},
        {"label": "تعداد نامزدها", "value": len(rows), "unit": "نفر", "hint": "اساتید همان دانشکده"},
        {"label": "بهترین تطبیق تخصص", "value": fa_pct(best_match)},
        {"label": "دارای سابقه ارائه این درس", "value": len(with_history), "unit": "نفر"},
    ]

    return ok(
        "instructor-recommendation", "توصیه استاد برای ارائه درس", 5,
        filters={"course_id": course_id, "top": top},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "instructor", "label": "استاد"},
            {"key": "rank", "label": "مرتبه"},
            {"key": "employment", "label": "نوع همکاری"},
            {"key": "match_pct", "label": "تطبیق تخصص", "format": "pct"},
            {"key": "history_n", "label": "سابقه این درس", "format": "int"},
            {"key": "hist_satisfaction", "label": "رضایت در این درس"},
            {"key": "hist_pass_pct", "label": "قبولی در این درس", "format": "pct"},
            {"key": "current_load_h", "label": "بار ترم جاری (ساعت/هفته)", "format": "int"},
            {"key": "headroom_h", "label": "ظرفیت باقی‌مانده", "format": "int"},
            {"key": "score", "label": "امتیاز", "format": "float"},
            {"key": "basis", "label": "مبنای پیشنهاد"},
        ], "rows": rows},
        method="امتیاز ترکیبی: تطبیق تخصص (۳۵٪) + رضایت تاریخی همان درس (۳۰٪) + نرخ قبولی همان درس (۲۵٪) + ظرفیت باقی‌مانده بار آموزشی (۱۰٪)؛ برای اساتید بدون سابقه همان درس، وزن‌ها بر تخصص و عملکرد کلی جابه‌جا شده و پایه پیشنهاد صراحتاً اعلام می‌شود.",
        limitations=[
            "خروجی یک «توصیه پشتیبان» است؛ تصمیم نهایی درباره استاد درس با گروه آموزشی و شورای مربوطه است.",
            "وزن‌ها فرض مدیریتی قابل تنظیم‌اند و باید با سیاست گروه آموزشی هم‌راستا شوند.",
            "رضایت و قبولی تاریخی، تضمین عملکرد آینده نیست و به شرایط هر ترم وابسته است.",
            "معیارهای دیگر مانند بار پژوهشی، تنوع تدریس و توازن بار آموزشی گروه در امتیاز لحاظ نشده است.",
        ],
    )
