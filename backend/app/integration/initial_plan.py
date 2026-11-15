# -*- coding: utf-8 -*-
"""مبنای برنامه‌ریزی اولیه — خروجی مدیریار۳۶۰ برای ورود به برنامه‌یار۳۶۰

قرارداد معماری (به انتخاب کاربر):
  * مدیریار۳۶۰   → مبنای «برنامه‌ریزی اولیه»: کدام درس، تقاضای مورد انتظار،
                  ظرفیت و تعداد گروه پیشنهادی و استاد پیشنهادی (سرویس‌های تحلیلی)
  * برنامه‌یار۳۶۰ → مبنای «خود برنامه‌ریزی»: چینش واقعی کلاس‌ها، اتاق‌ها، اساتید و ترم

این ماژول برنامه‌ریزی اولیهٔ نیم‌سال بعد را از پایگاه دادهٔ مدیریار۳۶۰ می‌سازد،
با کاتالوگ واقعی برنامه‌یار۳۶۰ تطبیق می‌دهد و در صورت اجازهٔ مدیر، به‌صورت
«پیشنهاد دروس» در برنامه‌یار۳۶۰ ثبت می‌کند (POST /api/proposals/).
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..analytics.recommend import instructor_recommendation
from ..models import Course, Offering, Term
from .client import IntegrationError, shared_client

ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200f\u202a-\u202e]")


def normalize_title(title: str | None) -> str:
    """نرمال‌سازی عنوان برای تطبیق درس‌ها بین دو سامانه"""
    if not title:
        return ""
    s = ZERO_WIDTH.sub("", str(title))
    s = s.replace("ي", "ی").replace("ك", "ک").replace("ٔ", "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def next_term(latest: Term) -> tuple[str, str]:
    """نیم‌سال بعدی از الگوی کد ترم‌های مدیریار۳۶۰ (نمونه: 1403-2 → 1404-1)"""
    try:
        year, no = latest.code.split("-")
        no = int(no)
        if no == 1:
            code, label = f"{year}-2", f"نیم‌سال دوم {year}-{int(year) + 1}"
        else:
            code, label = f"{int(year) + 1}-1", f"نیم‌سال اول {int(year) + 1}-{int(year) + 2}"
        return code, label
    except (ValueError, AttributeError):
        return latest.code, latest.label


def build_initial_plan(db: Session, *, lookback_terms: int = 3) -> dict:
    """ساخت برنامه‌ریزی اولیهٔ نیم‌سال بعد بر پایهٔ تحلیل‌های مدیریار۳۶۰

    برای هر درس فعال با سابقهٔ ارائه:
      * تقاضای مورد انتظار = میانگین (ثبت‌نام + محرومیت) در ۳ نیم‌سال اخیر
      * ظرفیت پیشنهادی هر گروه = میانگین ظرفیت اعلام‌شدهٔ اخیر
      * تعداد گروه پیشنهادی = سقف تقاضا ÷ ظرفیت
      * استاد پیشنهادی = نخستین نامزد سرویس «توصیه استاد»
    """
    terms = sorted(db.query(Term).all(), key=lambda t: t.order_index)
    if not terms:
        return {"ready": False, "reason": "پایگاه دادهٔ مدیریار۳۶۰ هنوز ترمی ندارد."}
    latest = terms[-1]
    next_code, next_label = next_term(latest)
    recent = terms[-lookback_terms:]

    courses = db.query(Course).filter(Course.active.is_(True)).all()
    offers = db.query(Offering).filter(Offering.term_id.in_([t.id for t in recent])).all()

    by_course_term: dict[int, dict[int, dict]] = {}
    for o in offers:
        slot = by_course_term.setdefault(o.course_id, {}).setdefault(o.term_id, {
            "enrolled": 0, "waiting": 0, "capacity": 0, "sections": 0})
        slot["enrolled"] += o.enrolled
        slot["waiting"] += o.waiting
        slot["capacity"] += o.capacity
        slot["sections"] += 1

    items = []
    for course in courses:
        hist = by_course_term.get(course.id) or {}
        if not hist:
            continue
        demands, caps, sections = [], [], []
        for tid in [t.id for t in recent]:
            slot = hist.get(tid)
            if not slot:
                continue
            demands.append(slot["enrolled"] + slot["waiting"])
            if slot["capacity"]:
                caps.append(slot["capacity"])
            sections.append(slot["sections"])
        if not demands:
            continue
        expected = math.ceil(sum(demands) / len(demands))
        avg_cap = math.ceil(sum(caps) / len(caps)) if caps else max(30, expected)
        suggested_sections = max(1, math.ceil(expected / max(1, avg_cap)))

        # استاد پیشنهادی از سرویس ۵ — تصمیم نهایی با گروه آموزشی است
        suggested = None
        try:
            rec = instructor_recommendation(db, course.id, top=1)
            rows = (rec or {}).get("table", {}).get("rows") or []
            if rows:
                suggested = {"name": rows[0].get("instructor"), "score": rows[0].get("score"),
                             "basis": rows[0].get("basis")}
        except Exception:
            suggested = None

        items.append({
            "course_code": course.code,
            "course_title": course.title,
            "credits": course.credits,
            "degree": course.degree,
            "recent_terms": len(demands),
            "expected_demand": expected,
            "suggested_capacity_per_section": avg_cap,
            "suggested_sections": suggested_sections,
            "suggested_instructor": suggested,
        })

    items.sort(key=lambda x: (-x["expected_demand"], x["course_code"]))
    return {
        "ready": True,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_system": "مدیریار۳۶۰ — مبنای برنامه‌ریزی اولیه",
        "target_system": "برنامه‌یار۳۶۰ — مبنای برنامه‌ریزی اجرایی",
        "term": {"code": next_code, "label": next_label},
        "basis": {
            "lookback_terms": lookback_terms,
            "demand_definition": "میانگین (ثبت‌نام + محرومیت) در نیم‌سال‌های اخیر",
            "capacity_definition": "میانگین ظرفیت اعلام‌شدهٔ هر گروه در نیم‌سال‌های اخیر",
            "instructor_note": "پیشنهاد پشتیبان است؛ تصمیم نهایی با گروه آموزشی و شورا",
        },
        "items_count": len(items),
        "items": items,
    }


def match_with_remote(plan: dict) -> dict:
    """تطبیق برنامه‌ریزی اولیه با کاتالوگ واقعی دروس ارائه برنامه‌یار۳۶۰"""
    remote = shared_client.fetch_source("offered_courses")
    by_title = {}
    for row in remote:
        for key in ("offered_title", "unique_title"):
            n = normalize_title(row.get(key))
            if n and n not in by_title:
                by_title[n] = {"id": row.get("id"), "unique_code": row.get("unique_code"), "title": row.get("offered_title") or row.get("unique_title")}

    matched, unmatched = [], []
    for item in plan.get("items", []):
        hit = by_title.get(normalize_title(item["course_title"]))
        if hit:
            matched.append({**item, "remote_course_id": hit["id"], "remote_unique_code": hit["unique_code"],
                            "remote_title": hit["title"]})
        else:
            unmatched.append({"course_code": item["course_code"], "course_title": item["course_title"],
                              "reason": "در کاتالوگ دروس ارائهٔ برنامه‌یار۳۶۰ هم‌نام یافت نشد"})
    return {"matched": matched, "unmatched": unmatched,
            "remote_offered_count": len(remote)}


def push_initial_plan(db: Session) -> dict:
    """ثبت برنامه‌ریزی اولیه به‌صورت «سبد برنامه‌ریزی» در برنامه‌یار۳۶۰

    برنامه‌یار۳۶۰ سبد را نقطهٔ ورود گردش‌کار برنامه‌ریزی اجرایی می‌داند
    (سبد → برنامه هفتگی → اتاق‌ها → بهینه‌سازی). فقط درس‌های هم‌نام‌شده با
    کاتالوگ دروس ارائه ارسال می‌شوند و آیتم‌ها با from_manager=true ثبت می‌گردند
    تا مبدأشان متمایز باشد.
    """
    plan = build_initial_plan(db)
    if not plan.get("ready"):
        return {"pushed": False, "reason": plan.get("reason")}
    match = match_with_remote(plan)
    matched = [m for m in match["matched"] if m.get("remote_unique_code")]
    if not matched:
        return {
            "pushed": False,
            "reason": "هیچ درسی با کاتالوگ برنامه‌یار۳۶۰ تطبیق نشد؛ ارسال انجام نشد.",
            "match": {"matched_count": len(match["matched"]), "unmatched": match["unmatched"],
                      "remote_offered_count": match["remote_offered_count"]},
            "plan_term": plan["term"],
        }

    # نگاشت نیم‌سال هدف به قالب سبد برنامه‌یار (semester_1/semester_2 + سال)
    year = plan["term"]["code"].split("-")[0]
    semester_code = plan["term"]["code"].split("-")[-1]
    semester = "semester_1" if semester_code == "1" else "semester_2"
    term_label = plan["term"]["label"]

    basket = shared_client.post_json("/api/baskets/", {
        "title": f"برنامه‌ریزی اولیه از مدیریار۳۶۰ — {term_label}",
        "semester": semester,
        "year": year,
    })
    basket_id = basket.get("id") if isinstance(basket, dict) else None
    if not basket_id:
        return {"pushed": False, "reason": "ایجاد سبد در برنامه‌یار۳۶۰ ناموفق بود.", "remote_response": basket}

    sent, failed = [], []
    for m in matched:
        item = {
            "level": {"bsc": "پیوسته", "msc": "کارشناسی ارشد", "phd": "دکتری"}.get(m.get("degree"), "پیوسته"),
            "term": term_label,
            "course_name": m["course_title"],
            "unique_code": str(m["remote_unique_code"]),
            "units": m.get("credits"),
            "course_type": "برنامه‌ریزی اولیه مدیریار۳۶۰",
            "estimated_capacity": m.get("suggested_capacity_per_section"),
            "required_classes": m.get("suggested_sections"),
            "from_manager": True,
            "semester": semester,
        }
        try:
            shared_client.post_json(f"/api/baskets/{basket_id}/items", item)
            sent.append(m["course_title"])
        except IntegrationError as e:
            failed.append({"course": m["course_title"], "error": str(e)})

    return {
        "pushed": bool(sent),
        "remote_term": f"{semester} / {year}",
        "basket_id": basket_id,
        "basket_title": basket.get("title"),
        "pushed_count": len(sent),
        "failed": failed,
        "match": {"matched_count": len(match["matched"]), "unmatched": match["unmatched"],
                  "remote_offered_count": match["remote_offered_count"]},
        "plan_term": plan["term"],
    }
