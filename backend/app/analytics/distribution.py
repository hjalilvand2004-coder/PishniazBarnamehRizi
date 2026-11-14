# -*- coding: utf-8 -*-
"""سرویس ۳ — تحلیل توزیع دانشجویان

ترکیب جمعیت دانشجویی بر اساس رشته، دانشکده، مقطع، سال ورود یا وضعیت تحصیلی.
همه شمارش‌ها روی داده تجمیعی و بدون مشخصات هویتی انجام می‌شود.
"""
from ..models import Department, Major, Student
from .base import DEGREE_FA, STATUS_FA, ok, r1, real_basis_limitations, eval_missing_limitation, result_missing_limitation, student_missing_limitation

GROUP_BY_LABEL = {
    "major": "رشته",
    "department": "دانشکده",
    "degree": "مقطع",
    "entry_year": "سال ورود",
    "status": "وضعیت تحصیلی",
}


def student_distribution(db, group_by="major", department_id=None, status="active"):
    if group_by not in GROUP_BY_LABEL:
        group_by = "major"

    q = db.query(Student).join(Major, Student.major_id == Major.id)
    if status == "active":
        q = q.filter(Student.status == "active")
    if department_id:
        q = q.filter(Major.department_id == int(department_id))
    students = q.all()

    majors = {m.id: m for m in db.query(Major).all()}
    dept_name = {d.id: d.name for d in db.query(Department).all()}

    counts = {}
    for s in students:
        major = majors.get(s.major_id)
        if group_by == "major":
            key = major.name if major else "—"
        elif group_by == "department":
            key = dept_name.get(major.department_id, "—") if major else "—"
        elif group_by == "degree":
            key = DEGREE_FA.get(major.degree if major else "", "—")
        elif group_by == "entry_year":
            key = str(s.entry_year).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
        else:
            key = STATUS_FA.get(s.status, s.status)
        counts[key] = counts.get(key, 0) + 1

    total = sum(counts.values())
    rows = [{"group": k, "count": v, "pct": r1(v / total * 100) if total else 0} for k, v in counts.items()]
    if group_by == "entry_year":
        rows.sort(key=lambda x: x["group"])
    else:
        rows.sort(key=lambda x: -x["count"])

    chart_type = "pie" if 2 <= len(rows) <= 7 else "bar"
    charts = [{
        "key": "dist",
        "type": chart_type,
        "title": f"توزیع دانشجویان بر اساس «{GROUP_BY_LABEL[group_by]}»",
        "data": [{"name": x["group"], "value": x["count"]} for x in rows],
        "xKey": "name",
        "yKeys": ["value"],
        "seriesLabels": {"value": "تعداد دانشجو"},
    }]

    largest = rows[0] if rows else None
    kpis = [
        {"label": "جمع دانشجویان", "value": total, "unit": "نفر",
         "hint": "وضعیت در نظر گرفته‌شده: " + ("فعال" if status == "active" else "همه وضعیت‌ها")},
        {"label": "تعداد گروه‌ها", "value": len(rows), "unit": "گروه"},
        {"label": "بزرگ‌ترین گروه",
         "value": f"{largest['group']} ({largest['pct']}٪)" if largest else "—"},
    ]

    extra_limits = list(real_basis_limitations(db))
    _m = student_missing_limitation(db)
    if _m: extra_limits.append(_m)

    return ok(
        "student-distribution", "تحلیل توزیع دانشجویان", 3,
        filters={"group_by": group_by, "department_id": department_id, "status": status},
        kpis=kpis, charts=charts,
        table={"columns": [
            {"key": "group", "label": GROUP_BY_LABEL[group_by]},
            {"key": "count", "label": "تعداد", "format": "int"},
            {"key": "pct", "label": "سهم", "format": "pct"},
        ], "rows": rows},
        method="شمارش مستقیم رکوردهای دانشجو بر اساس وضعیت ثبت‌نامی جاری و گروه‌بندی انتخابی؛ سهم درصدی از جمع فیلترشده.",
        limitations=[
            "توزیع بر اساس وضعیت ثبت‌نامی فعلی است؛ مرخصی‌ها و انتقال‌های در جریان ممکن است وضعیت را در آینده تغییر دهند.",
            "داده دانشجویان فاقد هرگونه مشخصات هویتی است (حریم خصوصی با طراحی) و فقط تحلیل تجمیعی مجاز است.",
            "متغیرهای جمعیت‌شناختی حساس (جنسیت، منطقه، معلولیت و…) نیازمند مجوز قانونی و رضایت آگاهانه‌اند و در این نسخه گردآوری نمی‌شوند.",
        ] + extra_limits,
    )
