# -*- coding: utf-8 -*-
"""سرویس کیفیت داده — سلامت دادهٔ آینهٔ برنامه‌یار۳۶۰ و دیتای مبنا

برای همهٔ نقش‌ها (ادمین سیستم، مدیرآموزش، مدیرگروه): چک‌های مشخص، امتیاز
دسته‌بندی‌شده و توصیه‌های عملی برای رسیدن به دادهٔ تمیز در مبدأ و سامانه.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Course, Instructor, Offering, Term
from . import config
from .models import ByInstructor, ByRoom, ByScheduleHistory, BySyncLog, ByTermCourse

STALE_HOURS = 48          # بیشتر از این فاصله = داده کهنه
CAP_MAX_REALISTIC = 200   # ظرفیت بیش از این در یک گروه کلاس غیرواقعی فرض می‌شود
MAX_UNITS = 8             # بیشینهٔ واحد معتبر درس
DETAIL_LIMIT = 200        # سقف ردیف‌های جزئیات هر چک (تعداد کامل در items_total اعلام می‌شود)

SEV_FA = {"good": "سالم", "info": "اطلاع", "warn": "هشدار", "bad": "بحرانی"}


def _sev(n: int, warn_from: int, bad_from: int) -> str:
    if n <= 0:
        return "good"
    if n >= bad_from:
        return "bad"
    if n >= warn_from:
        return "warn"
    return "info"


def _cap(items: list[dict]) -> tuple[list[dict], int]:
    """سقف‌گذاری فهرست موارد — خروجی: (موارد نمایش‌داده‌شده، تعداد کامل؛ ۰ یعنی بدون برش)"""
    if len(items) <= DETAIL_LIMIT:
        return items, 0
    return items[:DETAIL_LIMIT], len(items)


def build_quality_report(db: Session) -> dict:
    now = time.time()
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---------- ۱) تازگی همگام‌سازی هر منبع
    last_ok: dict[str, BySyncLog] = {}
    for log in db.query(BySyncLog).filter(BySyncLog.status == "ok").order_by(BySyncLog.id.desc()).limit(100).all():
        if log.source not in last_ok:
            last_ok[log.source] = log

    freshness = []
    for key in config.MIRROR_SOURCES:
        label = config.SOURCES[key]["label"]
        log = last_ok.get(key)
        if log is None:
            freshness.append({"key": key, "label": label, "hours": None, "severity": "bad",
                              "hint": "هرگز همگام‌سازی نشده؛ از «منبع دادهٔ برنامه‌یار۳۶۰» همگام‌سازی کامل اجرا کنید."})
        else:
            hours = round((now - log.finished_at) / 3600, 1)
            sev = "good" if hours <= 24 else ("warn" if hours <= STALE_HOURS else "bad")
            freshness.append({
                "key": key, "label": label, "hours": hours, "severity": sev,
                "hint": ("تازه است." if sev == "good" else
                         f"دادهٔ «{label}» {hours:g} ساعت پیش همگام شده؛ برای دادهٔ تمیز همگام‌سازی مجدد اجرا کنید."
                         if sev == "warn" else
                         f"دادهٔ «{label}» بیش از {STALE_HOURS} ساعت است؛ همگام‌سازی فوری لازم است."),
            })
    fresh_n = sum(1 for f in freshness if f["severity"] == "good")
    freshness_score = round(25 * (fresh_n / max(1, len(freshness))))

    # ---------- ۲) کیفیت دروس مبنای داده
    courses = db.query(Course).all()
    code_fallback = [c for c in courses if c.code.startswith("BY")]
    code_groups: dict[str, list[str]] = {}
    for c in courses:
        code_groups.setdefault(c.code, []).append(c.title)
    dup_map = {k: v for k, v in code_groups.items() if len(v) > 1}
    dup_codes = len(dup_map)
    bad_units = [c for c in courses if not c.credits or c.credits <= 0 or c.credits > MAX_UNITS]
    course_score = max(0, 20 - min(8, len(code_fallback) * 8 / max(1, len(courses)) * 8) - dup_codes * 2 - min(4, len(bad_units)))

    # ---------- ۳) کیفیت اساتید (آینه + مبنای داده)
    instr = db.query(Instructor).all()
    mirror_instr = db.query(ByInstructor).all()
    no_code_rows = [i for i in mirror_instr if not i.code]
    no_code_mirror = len(no_code_rows)
    names_seen: dict[str, int] = {}
    for i in instr:
        names_seen[i.name] = names_seen.get(i.name, 0) + 1
    dup_names_map = {n: v for n, v in names_seen.items() if v > 1 and n != "بدون استاد مشخص"}
    dup_names = len(dup_names_map)
    zero_cap_rows = [i for i in instr if not i.max_weekly_hours]
    zero_cap = len(zero_cap_rows)
    instr_score = max(0, 15 - min(5, no_code_mirror) - min(4, dup_names) - min(3, zero_cap))

    # ---------- ۴) کیفیت گروه‌های کلاس (ارائه‌ها)
    offs = db.query(Offering).all()
    course_by_id = {c.id: c for c in courses}
    term_label = {t.id: t.label for t in db.query(Term).all()}
    unknown_ids = {i.id for i in db.query(Instructor).filter(Instructor.name == "بدون استاد مشخص").all()}
    unknown_rows = [o for o in offs if o.instructor_id in unknown_ids]
    unknown_inst = len(unknown_rows)
    zero_cap_off_rows = [o for o in offs if o.capacity <= 0]
    zero_cap_offs = len(zero_cap_off_rows)
    big_cap_rows = [o for o in offs if o.capacity > CAP_MAX_REALISTIC]
    big_cap = len(big_cap_rows)
    unsched_rows = db.query(ByScheduleHistory).filter(ByScheduleHistory.day.is_(None)).all()
    unscheduled_rows = len(unsched_rows)
    unsched_groups: dict[str, int] = {}
    for r in unsched_rows:
        key = r.ref_unique_course_title or r.course_name
        unsched_groups[key] = unsched_groups.get(key, 0) + 1
    offer_score = max(0, 25 - min(8, zero_cap_offs * 8 / max(1, len(offs)) * 8) - min(5, unknown_inst) - min(4, big_cap) - min(5, unscheduled_rows * 5 / max(1, db.query(ByScheduleHistory).count()) * 5))

    # ---------- ۵) کامل‌بودن مبدأ (فیلدهای غایبِ ذات منبع)
    from ..analytics.base import get_data_basis

    basis = get_data_basis(db)
    missing = basis.get("missing_fields", []) if basis.get("mode") == "barnameh_yar" else []
    completeness_score = max(0, 15 - 5 * len(missing))

    overall = round(freshness_score + course_score + instr_score + offer_score + completeness_score)
    tone = "good" if overall >= 80 else ("warn" if overall >= 55 else "bad")

    checks = [
        *freshness,
        {"key": "course-no-code", "label": "دروس بدون کد یکتای معتبر در مبدأ (کد موقت BY)", "value": len(code_fallback),
         "severity": _sev(len(code_fallback), 1, 11),
         "hint": "کاتالوگ «دروس یکتا» برنامه‌یار۳۶۰ همگام و کدها از آن تطبیق می‌یابند؛ این موارد در هیچ سرویس مبدأ کد ندارند — کد یکتا در مبدأ ثبت شود؛ سپس همگام‌سازی کامل + بازسازی مبنا."},
        {"key": "course-dup-code", "label": "کدهای یکتای به‌اشتراک‌گذاشته‌شده بین دو عنوان", "value": dup_codes,
         "severity": _sev(dup_codes, 1, 4), "hint": "کد یکتا در مبدأ باید برای هر عنوان یکتا باشد؛ موارد با پسوند x به‌صورت موقت متمایز شده‌اند."},
        {"key": "course-bad-units", "label": f"دروس با واحد نامعتبر (۰ یا بیش از {MAX_UNITS})", "value": len(bad_units),
         "severity": _sev(len(bad_units), 1, 6), "hint": "تعداد واحد دروس در مبدأ اصلاح شود."},
        {"key": "instr-no-code", "label": "اساتید بدون کد در مبدأ", "value": no_code_mirror,
         "severity": _sev(no_code_mirror, 1, 6), "hint": "کد استاد در برنامه‌یار۳۶۰ ثبت شود؛ تطبیق تخصص و بار تدریس به کد وابسته است."},
        {"key": "instr-dup-name", "label": "نام‌های تکراری استاد (کد متفاوت)", "value": dup_names,
         "severity": _sev(dup_names, 1, 4), "hint": "اگر دو نفر با نام یکسان‌اند نام‌گذاری را متمایز کنید؛ اگر یک نفر است، در مبدأ ادغام شود."},
        {"key": "instr-zero-cap", "label": "اساتید با سقف تدریس صفر", "value": zero_cap,
         "severity": _sev(zero_cap, 1, 6), "hint": "سقف واحد تدریس برای برنامه‌ریزی باید ثبت شود."},
        {"key": "off-unknown-inst", "label": "گروه‌های کلاس با استادِ نامطبیق (کد خارج از فهرست)", "value": unknown_inst,
         "severity": _sev(unknown_inst, 1, 21), "hint": "کد استاد در سوابق باید در فهرست اساتید مبدأ موجود باشد."},
        {"key": "off-zero-cap", "label": "گروه‌های کلاس با ظرفیت صفر", "value": zero_cap_offs,
         "severity": _sev(zero_cap_offs, 1, 11), "hint": "ظرفیت گروه‌ها در برنامه‌یار۳۶۰ ثبت شود؛ ظرفیت صفر تحلیل ظرفیت را بی‌اثر می‌کند."},
        {"key": "off-big-cap", "label": f"گروه‌های با ظرفیت غیرواقعی (بیش از {CAP_MAX_REALISTIC})", "value": big_cap,
         "severity": _sev(big_cap, 1, 6), "hint": "ظرفیت این گروه‌ها را در مبدأ بازبینی کنید."},
        {"key": "off-unscheduled", "label": "رکوردهای سوابق بدون روز/ساعت (برنامه‌ریزی در سطح درس)", "value": unscheduled_rows,
         "severity": "info" if unscheduled_rows < len(offs) else "warn",
         "hint": "این رکوردها برنامه‌ریزی درس‌محور هستند و به‌صورت یک گروه بدون زمان‌بندی لحاظ شده‌اند؛ برای تحلیل اتاق/زمان دقیق‌تر، زمان‌بندی کلاس‌ها را در مبدأ کامل کنید."},
    ]
    if missing:
        checks.append({"key": "src-missing", "label": "فیلدهای ذاتاً غایب در منبع برنامه‌یار۳۶۰", "value": len(missing),
                       "severity": "info", "hint": "؛ ".join(missing) + " — تا ثبت در مبدأ، سرویس‌های وابسته محدودیت را صریح اعلام می‌کنند و عدد ساختگی تولید نمی‌شود."})

    # ---------- فهرست جزئیات هر چک — موارد دقیقِ تعارض برای مسئول داده
    def _off_item(o: Offering, info: str, note: str) -> dict:
        crs = course_by_id.get(o.course_id)
        return {"code": f"گروه #{o.id}",
                "title": (f"{crs.code} — {crs.title}" if crs else f"درس #{o.course_id}"),
                "info": info, "note": note}

    item_lists: dict[str, list[dict]] = {
        "course-no-code": [
            {"code": c.code, "title": c.title, "info": f"{c.credits} واحد",
             "note": "کد موقت BY — کد یکتای رسمی در مبدأ ثبت نشده"}
            for c in code_fallback
        ],
        "course-dup-code": [
            {"code": k, "title": "؛ ".join(v), "info": f"{len(v)} عنوان",
             "note": "یک کد یکتا بین چند عنوان درس مشترک است"}
            for k, v in sorted(dup_map.items())
        ],
        "course-bad-units": [
            {"code": c.code, "title": c.title, "info": f"واحد {c.credits}",
             "note": f"واحد باید بین ۱ تا {MAX_UNITS} باشد"}
            for c in bad_units
        ],
        "instr-no-code": [
            {"code": f"#{i.external_id}", "title": i.name, "info": i.cooperation_type or "—",
             "note": "کد استاد در مبدأ خالی است"}
            for i in no_code_rows
        ],
        "instr-dup-name": [
            {"code": "—", "title": n, "info": f"{v} رکورد",
             "note": "نام تکراری — دو نفر متمایز یا یک نفر دوبار ثبت شده"}
            for n, v in sorted(dup_names_map.items())
        ],
        "instr-zero-cap": [
            {"code": "—", "title": i.name, "info": "سقف ۰ ساعت",
             "note": "سقف واحد تدریس هفتگی ثبت نشده"}
            for i in zero_cap_rows
        ],
        "off-unknown-inst": [
            _off_item(o, term_label.get(o.term_id, f"ترم {o.term_id}"),
                      "استادِ گروه کد معتبری در فهرست اساتید مبدأ ندارد")
            for o in unknown_rows
        ],
        "off-zero-cap": [
            _off_item(o, "ظرفیت ۰", "ظرفیت گروه باید در برنامه‌یار۳۶۰ ثبت شود")
            for o in zero_cap_off_rows
        ],
        "off-big-cap": [
            _off_item(o, f"ظرفیت {o.capacity}", f"بیش از {CAP_MAX_REALISTIC} — در مبدأ بازبینی شود")
            for o in big_cap_rows
        ],
        "off-unscheduled": [
            {"code": "—", "title": k, "info": f"{v} رکورد",
             "note": "سوابق بدون روز/ساعت — برنامه‌ریزی درس‌محور"}
            for k, v in sorted(unsched_groups.items(), key=lambda kv: -kv[1])
        ],
        "src-missing": [
            {"code": "—", "title": m, "info": "—", "note": "فیلد غایب در منبع برنامه‌یار۳۶۰"}
            for m in missing
        ],
    }
    for ch in checks:
        shown, total = _cap(item_lists.get(ch["key"], []))
        ch["items"] = shown
        ch["items_total"] = total

    recommendations = []
    for f in freshness:
        if f["severity"] in ("warn", "bad"):
            recommendations.append(f"همگام‌سازی مجدد «{f['label']}» — {f['hint']}")
    if len(code_fallback):
        recommendations.append(f"{len(code_fallback)} درس در مبدأ کد یکتای معتبر ندارند؛ ثبت کد در برنامه‌یار و سپس «همگام‌سازی کامل + بازسازی مبنا» باعث تطبیق دقیق درس و پیش‌نیازها می‌شود.")
    if unknown_inst:
        recommendations.append("کدهای استادِ خارج از فهرست در سوابق باید در برنامه‌یار اصلاح شود تا بار تدریس و عملکرد به استاد درست نسبت داده شود.")
    if zero_cap_offs or big_cap:
        recommendations.append("ظرفیت گروه‌های صفر/غیرواقعی در مبدأ اصلاح شود؛ تحلیل ظرفیت و پیش‌بینی تقاضا به ظرفیت واقعی وابسته است.")
    if missing:
        recommendations.append("برای فعال‌شدن کامل تحلیل‌ها (مردودی، رضایت، توزیع دانشجو)، ثبت نتایج ارزشیابی و پروندهٔ دانشجو (بدون هویت) در منبع برنامه‌یار۳۶۰ لازم است.")
    if basis.get("mode") == "barnameh_yar":
        recommendations.append(f"ثبت‌نام تحلیل‌ها برآوردی است (نرخ پرشدگی {basis.get('fill_rate', 0.85):.0%})؛ با دادهٔ واقعی ثبت‌نام، متغیر DANESHJO360_FILL_RATE را دقیق تنظیم کنید.")
    else:
        recommendations.append("هنوز همگام‌سازی از برنامه‌یار۳۶۰ انجام نشده؛ از بخش «منبع دادهٔ برنامه‌یار۳۶۰» همگام‌سازی کامل اجرا کنید تا دیتای مبنا واقعی شود.")
    if not recommendations:
        recommendations.append("داده در وضعیت تمیز است؛ همگام‌سازی دوره‌ای (مثلاً هفتگی) را ادامه دهید.")

    kpis = [
        {"label": "امتیاز کلی کیفیت داده", "value": overall, "unit": "از ۱۰۰", "tone": tone},
        {"label": "منابع تازه (≤۲۴ ساعت)", "value": fresh_n, "unit": f"از {len(freshness)}", "tone": "good" if fresh_n == len(freshness) else "warn"},
        {"label": "گروه‌های کلاس مبنای تحلیل", "value": len(offs), "unit": "گروه"},
        {"label": "دروس مبنای تحلیل", "value": len(courses), "unit": "درس"},
        {"label": "اساتید مبنای تحلیل", "value": len(instr), "unit": "نفر"},
        {"label": "اتاق‌های ثبت‌شدهٔ مبدأ", "value": db.query(ByRoom).count(), "unit": "اتاق"},
    ]

    return {
        "generated_at": generated,
        "score": {
            "overall": overall,
            "tone": tone,
            "categories": [
                {"key": "freshness", "label": "تازگی دادهٔ همگام‌شده", "score": freshness_score, "weight": 25},
                {"key": "courses", "label": "کیفیت دروس", "score": round(course_score), "weight": 20},
                {"key": "instructors", "label": "کیفیت اساتید", "score": instr_score, "weight": 15},
                {"key": "offerings", "label": "کیفیت گروه‌های کلاس", "score": round(offer_score), "weight": 25},
                {"key": "completeness", "label": "کامل‌بودن مبدأ", "score": completeness_score, "weight": 15},
            ],
        },
        "kpis": kpis,
        "checks": checks,
        "recommendations": recommendations,
        "basis": basis,
        "note": "کیفیت داده = سلامت دادهٔ همگام‌شدهٔ برنامه‌یار۳۶۰ و دیتای مبنا؛ برای هر چک، فهرست کامل موارد تعارض با «نمایش موارد» قابل مشاهده و خروجی CSV دارد.",
    }
