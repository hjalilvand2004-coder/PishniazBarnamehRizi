# -*- coding: utf-8 -*-
"""سرویس ۷ — تحلیل نرخ مردودی

شناسایی دروس بحرانی و روند مردودی؛ همه داده‌ها تجمیعی و بدون هویت است.
نسبت‌دادن مستقیم مردودی به استاد مجاز نیست؛ مردودی نتیجه عوامل متعدد است.
"""
from .base import (
    CRITICAL_FAIL_RATE, fa_int, fa_pct, filtered_courses, ok,
    offerings_by_course, ordered_terms, r0, r1, slope_pct, wavg,
)


def fail_rate(db, department_id=None, course_id=None, term_id=None, threshold=20):
    threshold = float(threshold or 20)
    courses = filtered_courses(db, department_id, course_id)
    by_course = offerings_by_course(db)
    term_label = {t.id: t.label for t in ordered_terms(db)}

    rows = []
    for c in courses:
        offs = by_course.get(c.id, [])
        if term_id:
            offs = [o for o in offs if o.term_id == int(term_id)]
        offs = [o for o in offs if o.enrolled > 0]
        if not offs:
            continue
        series = [o.failed / o.enrolled * 100 for o in offs]
        fail_avg = wavg([(s, o.enrolled) for s, o in zip(series, offs)])
        fail_last = series[-1]
        slope = slope_pct(series)
        if fail_avg is None:
            continue
        if fail_avg > CRITICAL_FAIL_RATE:
            level = "بحرانی"
        elif fail_avg > threshold:
            level = "هشدار"
        else:
            level = "قابل قبول"
        rows.append({
            "course": f"{c.code} — {c.title}",
            "terms_n": len(series),
            "enrolled_total": sum(o.enrolled for o in offs),
            "fail_avg_pct": r1(fail_avg),
            "fail_last_pct": r1(fail_last),
            "slope_pct": r1(slope),
            "level": level,
        })
    rows.sort(key=lambda x: -(x["fail_avg_pct"] or 0))

    charts = [{
        "key": "top",
        "type": "bar",
        "title": "بالاترین نرخ مردودی متوسط — ده درس نخست",
        "data": [{"name": x["course"].split(" — ")[0], "value": x["fail_avg_pct"]} for x in rows[:10]],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "نرخ مردودی متوسط (٪)"},
        "refLine": threshold,
        "refLabel": f"آستانه هشدار {fa_int(threshold)}٪",
    }]
    if course_id:
        offs = [o for o in by_course.get(int(course_id), []) if o.enrolled > 0]
        if term_id:
            offs = [o for o in offs if o.term_id == int(term_id)]
        charts.append({
            "key": "trend",
            "type": "line",
            "title": "روند نرخ مردودی درس انتخابی",
            "data": [{"term": term_label[o.term_id], "fail_pct": r1(o.failed / o.enrolled * 100)} for o in offs],
            "xKey": "term",
            "yKeys": ["fail_pct"],
            "seriesLabels": {"fail_pct": "نرخ مردودی (٪)"},
            "refLine": threshold,
        })

    critical = [x for x in rows if x["level"] == "بحرانی"]
    overall = wavg([(x["fail_avg_pct"], x["enrolled_total"]) for x in rows])
    kpis = [
        {"label": "میانگین نرخ مردودی کل (وزنی)", "value": r1(overall), "unit": "٪"},
        {"label": "دروس بحرانی", "value": len(critical), "unit": "درس",
         "tone": "bad" if critical else "good", "hint": f"مردودی متوسط بیش از {fa_int(CRITICAL_FAIL_RATE)}٪"},
        {"label": "دروس در وضعیت هشدار", "value": sum(1 for x in rows if x["level"] == "هشدار"), "unit": "درس",
         "tone": "warn"},
        {"label": "بیشترین مردودی",
         "value": f"{rows[0]['course'].split(' — ')[0]} ({fa_pct(rows[0]['fail_avg_pct'])})" if rows else "—"},
    ]

    return ok(
        "fail-rate", "تحلیل نرخ مردودی", 7,
        filters={"department_id": department_id, "course_id": course_id, "term_id": term_id, "threshold": threshold},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "course", "label": "درس"},
            {"key": "terms_n", "label": "تعداد ترم", "format": "int"},
            {"key": "enrolled_total", "label": "جمع ثبت‌نام", "format": "int"},
            {"key": "fail_avg_pct", "label": "مردودی متوسط", "format": "pct"},
            {"key": "fail_last_pct", "label": "مردودی آخرین ترم", "format": "pct"},
            {"key": "slope_pct", "label": "روند هر ترم", "format": "pct_signed"},
            {"key": "level", "label": "وضعیت"},
        ], "rows": rows},
        method="نرخ مردودی هر ارائه = مردودین ÷ ثبت‌نامی؛ میانگین وزنی به وزن ثبت‌نام؛ طبقه‌بندی: بحرانی > ۳۰٪ (فرض)، هشدار > آستانه انتخابی (پیش‌فرض ۲۰٪)، در غیر این صورت قابل قبول.",
        limitations=[
            "مردودی نتیجه عوامل متعدد است (پیش‌زمینه ورودی، پیش‌نیازها، سخت‌گیری ارزشیابی، شرایط ترم) و نسبت‌دادن مستقیم به استاد مجاز نیست.",
            "داده تجمیعی و بدون هویت است؛ هرگونه تحلیل در سطح دانشجوی منفرد از دامنه این سامانه خارج است.",
            "مقایسه نرخ مردودی فقط «درون یک درس» یا بین دروس با ماهیت مشابه معنادار است.",
            "آستانه‌های بحرانی/هشدار فرض مدیریتی‌اند و باید با ضوابط آموزشی سازمان تنظیم شوند.",
        ],
    )
