# -*- coding: utf-8 -*-
"""موتور همگام‌سازی — آینه‌سازی کامل دادهٔ «برنامه‌ریزی واقعی» از برنامه‌یار۳۶۰

* هر منبع پس از دریافت کامل، بازسازی می‌شود (حذف و درج) تا آینه دقیق باشد
* کد نیم‌سال برنامه‌یار (نمونه: 4021) به برچسب خوانا («سال ۱۴۰۲ — ترم ۱») نگاشت می‌شود
* نتیجهٔ هر همگام‌سازی در by_sync_log ثبت می‌شود و مبنای وضعیت داشبورد است
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..db import SessionLocal
from . import config
from .client import IntegrationError, shared_client
from .models import ByInstructor, ByOfferedCourse, ByRoom, ByScheduleHistory, BySyncLog, ByTermCourse

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
TERM_WORDS = {"یک": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5, "شش": 6, "هفت": 7, "هشت": 8}


def semester_label(code: str | None) -> str | None:
    """برچسب خوانای نیم‌سال برنامه‌یار: 4021 → «سال ۱۴۰۲ — ترم ۱»"""
    if not code or len(code) != 4 or not code.isdigit() or code[0] != "4":
        return code
    try:
        year = 1400 + int(code[2])
        term = int(code[3])
        return f"سال {year} — ترم {term}".translate(FA_DIGITS)
    except ValueError:
        return code


def term_no_from_row(row: dict) -> int | None:
    if row.get("approximate_term"):
        try:
            return int(row["approximate_term"])
        except (TypeError, ValueError):
            pass
    term = (row.get("term") or "").strip()
    for word, no in TERM_WORDS.items():
        if term.startswith(f"ترم {word}"):
            return no
    return None


def _to_int(v) -> int | None:
    try:
        return int(v) if v not in (None, "", "یافت نشد") else None
    except (TypeError, ValueError):
        return None


def _to_str(v) -> str | None:
    return None if v is None else str(v)


# ---------------------------------------------------------------------------
# نگاشت رکورد مبدأ → رکورد آینه
# ---------------------------------------------------------------------------

def map_term_course(row: dict, now: int) -> ByTermCourse:
    return ByTermCourse(
        external_id=_to_int(row.get("id")) or 0,
        level=_to_str(row.get("level")),
        term=_to_str(row.get("term")),
        term_no=term_no_from_row(row),
        row_number=_to_int(row.get("row_number")),
        course_name=_to_str(row.get("course_name")) or "بدون نام",
        units=_to_int(row.get("units")),
        capacity=_to_int(row.get("capacity")),
        course_type=_to_str(row.get("course_type")),
        unique_course_code=None if row.get("unique_course_code") in (None, "یافت نشد") else _to_str(row.get("unique_course_code")),
        unique_course_name=None if row.get("unique_course_name") in (None, "یافت نشد") else _to_str(row.get("unique_course_name")),
        year_identified=_to_str(row.get("year_identified")),
        prerequisite_row_codes=_to_str(row.get("prerequisite_row_codes")),
        corequisite_row_codes=_to_str(row.get("corequisite_row_codes")),
        description=_to_str(row.get("description")),
        synced_at=now,
    )


def map_schedule_history(row: dict, now: int) -> ByScheduleHistory:
    sem = _to_str(row.get("semester")) or "?"
    return ByScheduleHistory(
        external_id=_to_int(row.get("id")) or 0,
        semester=sem,
        semester_label=semester_label(sem),
        faculty_code=_to_str(row.get("faculty_code")),
        faculty_name=_to_str(row.get("faculty_name_clean")) or _to_str(row.get("faculty_name")),
        department_code=_to_str(row.get("department_code")),
        department_name=_to_str(row.get("department_name_clean")) or _to_str(row.get("department_name")),
        level=_to_str(row.get("level")),
        course_name=_to_str(row.get("course_name")) or "بدون نام",
        ref_unique_course_title=_to_str(row.get("ref_unique_course_title")),
        day=_to_str(row.get("day")),
        start_time=_to_str(row.get("start_time")),
        end_time=_to_str(row.get("end_time")),
        class_code=_to_str(row.get("class_code")),
        class_name=_to_str(row.get("class_name")),
        instructor_code=_to_str(row.get("instructor_code")),
        instructor_name=_to_str(row.get("instructor_name_clean")) or _to_str(row.get("instructor_name")),
        max_capacity=_to_int(row.get("max_capacity")),
        exam_date=_to_str(row.get("exam_date")),
        exam_start_time=_to_str(row.get("exam_start_time")),
        exam_end_time=_to_str(row.get("exam_end_time")),
        synced_at=now,
    )


def map_room(row: dict, now: int) -> ByRoom:
    return ByRoom(
        external_id=_to_int(row.get("id")) or 0,
        code=_to_str(row.get("code")) or "؟",
        name=_to_str(row.get("name")),
        capacity=_to_int(row.get("capacity")),
        place_type=_to_str(row.get("place_type")),
        group_name=_to_str(row.get("group")),
        room_types=row.get("room_types") if isinstance(row.get("room_types"), list) else None,
        synced_at=now,
    )


def map_instructor(row: dict, now: int) -> ByInstructor:
    return ByInstructor(
        external_id=_to_int(row.get("id")) or 0,
        code=_to_str(row.get("code")),
        name=_to_str(row.get("name")) or "بدون نام",
        username=_to_str(row.get("username")),
        cooperation_type=_to_str(row.get("cooperation_type")),
        group_name=_to_str(row.get("group")),
        max_teaching_units=_to_int(row.get("max_teaching_units")),
        email=_to_str(row.get("email")),
        phone=_to_str(row.get("phone")),
        synced_at=now,
    )


def map_offered_course(row: dict, now: int) -> ByOfferedCourse:
    return ByOfferedCourse(
        external_id=_to_int(row.get("id")) or 0,
        unique_code=None if row.get("unique_code") in (None, "", "یافت نشد") else _to_str(row.get("unique_code")),
        unique_title=_to_str(row.get("unique_title")),
        offered_title=_to_str(row.get("offered_title")),
        course_type=_to_str(row.get("course_type")),
        type_course=_to_str(row.get("type_course")),
        year=_to_str(row.get("year")),
        theoretical_hours=_to_int(row.get("theoretical_hours")),
        practical_hours=_to_int(row.get("practical_hours")),
        prerequisite=_to_str(row.get("prerequisite")),
        corequisite=_to_str(row.get("corequisite")),
        enrollment_count=_to_int(row.get("enrollment_count")),
        demand_prediction=_to_int(row.get("demand_prediction")),
        is_active=1 if row.get("is_active") else 0,
        synced_at=now,
    )


MAPPERS = {
    "term_courses": (ByTermCourse, map_term_course),
    "schedule_history": (ByScheduleHistory, map_schedule_history),
    "rooms": (ByRoom, map_room),
    "instructors": (ByInstructor, map_instructor),
    "offered_courses": (ByOfferedCourse, map_offered_course),
}


# ---------------------------------------------------------------------------
# همگام‌سازی یک منبع
# ---------------------------------------------------------------------------

def sync_source(db: Session, source_key: str) -> dict:
    """آینه‌سازی کامل یک منبع: دریافت از مبدأ → بازسازی جدول محلی → ثبت لاگ

    داده و لاگ موفق در یک تراکنش ثبت می‌شوند؛ در خطا فقط یک رکورد لاگ خطا
    نوشته می‌شود و دادهٔ قبلی دست‌نخورده باقی می‌ماند.
    """
    if source_key not in MAPPERS:
        raise ValueError(f"منبع ناشناخته: {source_key}")
    model, mapper = MAPPERS[source_key]
    started = time.time()
    now = int(started)
    remote_url = config.BASE_URL + config.SOURCES[source_key]["path"]

    def _finish(log: BySyncLog, status: str, message: str, fetched: int = 0) -> None:
        log.status = status
        log.fetched = fetched
        log.inserted = fetched if status == "ok" else 0
        log.message = message
        log.finished_at = time.time()
        log.duration_ms = int((log.finished_at - started) * 1000)

    try:
        rows = shared_client.fetch_source(source_key)
        db.query(model).delete(synchronize_session=False)
        for row in rows:
            db.add(mapper(row, now))
        db.flush()

        log = BySyncLog(source=source_key, remote_url=remote_url, started_at=started)
        _finish(
            log, "ok",
            f"همگام‌سازی کامل «{config.SOURCES[source_key]['label']}» انجام شد — {len(rows)} رکورد.",
            len(rows),
        )
        db.add(log)
        db.commit()
        return {
            "source": source_key,
            "label": config.SOURCES[source_key]["label"],
            "status": "ok",
            "fetched": log.fetched,
            "inserted": log.inserted,
            "duration_ms": log.duration_ms,
        }
    except IntegrationError as e:
        db.rollback()
        log = BySyncLog(source=source_key, remote_url=remote_url, started_at=started)
        _finish(log, "error", str(e))
        db.add(log)
        db.commit()
        raise
    except Exception as e:  # خطای غیرمنتظره (نمونه: قالب دادهٔ مبدأ) هم لاگ می‌شود
        db.rollback()
        log = BySyncLog(source=source_key, remote_url=remote_url, started_at=started)
        _finish(log, "error", f"خطای غیرمنتظره در همگام‌سازی: {e}")
        db.add(log)
        db.commit()
        raise IntegrationError(f"همگام‌سازی «{config.SOURCES[source_key]['label']}» ناموفق بود: {e}") from e


def sync_all(db: Session) -> dict:
    """همگام‌سازی همهٔ منابع آینه — خطای هر منبع نتیجهٔ بقیه را خراب نمی‌کند

    پس از همگام‌سازی موفق، «دیتای مبنا» سامانه نیز به‌صورت خودکار از دادهٔ واقعی
    بازسازی می‌شود (قابل غیرفعال‌سازی با DANESHJO360_AUTO_REBASE=0).
    """
    results = []
    for key in config.MIRROR_SOURCES:
        try:
            results.append(sync_source(db, key))
        except IntegrationError as e:
            results.append({
                "source": key,
                "label": config.SOURCES[key]["label"],
                "status": "error",
                "fetched": 0,
                "inserted": 0,
                "duration_ms": 0,
                "error": str(e),
            })
    out = {
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "remote": config.BASE_URL,
        "results": results,
        "ok": all(r["status"] == "ok" for r in results),
    }

    # بازسازی خودکار دیتای مبنا — قلب «یک سامانهٔ یکپارچه روی دادهٔ واقعی»
    if os.getenv("DANESHJO360_AUTO_REBASE", "1") != "0" and out["ok"]:
        try:
            from .rebase import rebase_from_synced
            out["rebase"] = rebase_from_synced(db)
        except Exception as e:  # خطای بازسازی مانع گزارش همگام‌سازی نمی‌شود
            out["rebase"] = {"rebuilt": False, "reason": f"بازسازی دیتای مبنا ناموفق بود: {e}"}
    return out


def last_syncs(db: Session) -> dict[str, dict]:
    """آخرین همگام‌سازی موفق هر منبع برای نمایش وضعیت"""
    out: dict[str, dict] = {}
    logs = db.query(BySyncLog).order_by(BySyncLog.id.desc()).limit(200).all()
    for log in logs:
        key = log.source
        if key not in out and log.status == "ok":
            out[key] = {
                "finished_at": log.finished_at,
                "finished_label": datetime.fromtimestamp(log.finished_at).strftime("%Y-%m-%d %H:%M") if log.finished_at else "—",
                "inserted": log.inserted,
                "duration_ms": log.duration_ms,
            }
    last_error = next((l for l in logs if l.status == "error"), None)
    if last_error:
        out["_last_error"] = {
            "source": last_error.source,
            "message": last_error.message,
            "finished_label": datetime.fromtimestamp(last_error.finished_at).strftime("%Y-%m-%d %H:%M") if last_error.finished_at else "—",
        }
    return out


def local_counts(db: Session) -> dict[str, int]:
    return {
        "term_courses": db.query(ByTermCourse).count(),
        "schedule_history": db.query(ByScheduleHistory).count(),
        "rooms": db.query(ByRoom).count(),
        "instructors": db.query(ByInstructor).count(),
    }


def run_full_sync() -> dict:
    """همگام‌سازی کامل در نشست مستقل — برای فراخوانی از روتر"""
    db = SessionLocal()
    try:
        return sync_all(db)
    finally:
        db.close()
