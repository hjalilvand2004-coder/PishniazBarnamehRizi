# -*- coding: utf-8 -*-
"""مسیرهای API یکپارچگی با برنامه‌یار۳۶۰

دسترسی‌ها:
  * مشاهدهٔ وضعیت و داده‌های همگام‌شده — همهٔ کاربران واردشده (سه نقش)
  * اجرای همگام‌سازی — ادمین سیستم و مدیرآموزش (مدیرگروه فقط مشاهده می‌کند)
  * ارسال برنامه‌ریزی اولیه به برنامه‌یار — فقط ادمین سیستم
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.deps import require_authenticated
from ..db import get_db
from . import config, insights, initial_plan, sync
from .client import IntegrationError, shared_client
from .models import ByInstructor, ByOfferedCourse, ByRoom, ByScheduleHistory, ByTermCourse
from .rebase import get_data_basis, rebase_from_synced

SYNC_ROLES = {"sysadmin", "edu_manager"}
PUSH_ROLES = {"sysadmin"}

router = APIRouter(prefix="/api/integration", tags=["integration"])


def _require_role(user, allowed: set[str], action_fa: str):
    if user.role not in allowed:
        from ..auth.roles import role_label
        raise HTTPException(
            status_code=403,
            detail=f"«{action_fa}» برای نقش «{role_label(user.role)}» فعال نیست؛ "
                   f"این عملیات در اختیار مدیران مجاز است.",
        )
    return user


def _ensure_enabled():
    if not config.ENABLED:
        raise HTTPException(status_code=503, detail="ماژول یکپارچگی با برنامه‌یار۳۶۰ غیرفعال است (BARNAMEHYAR_ENABLED=0).")


@router.get("/status")
def integration_status(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """وضعیت اتصال به برنامه‌یار۳۶۰ + وضعیت آینهٔ محلی"""
    _ensure_enabled()
    remote = None
    error = None
    try:
        remote = shared_client.auth_test()
    except IntegrationError as e:
        error = str(e)
    return {
        "enabled": config.ENABLED,
        "base_url": config.BASE_URL,
        "source_system": "برنامه‌یار۳۶۰ — سامانه هوشمند برنامه‌ریزی درسی (مبنای برنامه‌ریزی اجرایی)",
        "this_system": "مدیریار۳۶۰ — مبنای برنامه‌ریزی اولیه",
        "remote": remote,
        "error": error,
        "last_syncs": sync.last_syncs(db),
        "local_counts": sync.local_counts(db),
        "sync_allowed": user.role in SYNC_ROLES,
        "push_allowed": user.role in PUSH_ROLES,
    }


@router.post("/sync/{source}")
def run_sync(source: str, db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """همگام‌سازی یک منبع یا همهٔ منابع («all»)"""
    _ensure_enabled()
    _require_role(user, SYNC_ROLES, "همگام‌سازی با برنامه‌یار۳۶۰")
    if source not in (config.MIRROR_SOURCES + ["all"]):
        raise HTTPException(status_code=404, detail="منبع همگام‌سازی ناشناخته است.")
    try:
        if source == "all":
            return sync.sync_all(db)
        return sync.sync_source(db, source)
    except IntegrationError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/basis")
def basis(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """مبنای دادهٔ فعلی سامانه — برای بنر داشبورد و شفافیت تحلیل‌ها"""
    return get_data_basis(db)


@router.post("/rebase")
def run_rebase(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """بازسازی دیتای مبنا از دادهٔ همگام‌شدهٔ برنامه‌یار۳۶۰ — ادمین سیستم و مدیرآموزش

    کل جداول مبنای تحلیل (دانشکده، درس، استاد، ترم، ارائه) از آینهٔ واقعی برنامه‌یار
    بازسازی می‌شود؛ پس از هر همگام‌سازی کامل این کار خودکار انجام می‌شود.
    """
    _require_role(user, SYNC_ROLES, "بازسازی دیتای مبنا از برنامه‌یار۳۶۰")
    return rebase_from_synced(db)


@router.get("/quality")
def data_quality(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """گزارش کیفیت داده — چک‌های مشخص، امتیاز دسته‌بندی‌شده و توصیه‌های عملی؛ برای همهٔ نقش‌ها"""
    from . import quality

    return quality.build_quality_report(db)


@router.get("/term-courses")
def term_courses(
    db: Session = Depends(get_db),
    user=Depends(require_authenticated),
    q: str | None = Query(default=None, description="جستجو در نام درس"),
    level: str | None = Query(default=None),
    term_no: int | None = Query(default=None),
    limit: int = Query(default=60, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """دروس ترمیک همگام‌شده از برنامه‌یار۳۶۰"""
    query = db.query(ByTermCourse)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(ByTermCourse.course_name.like(like) | ByTermCourse.unique_course_name.like(like))
    if level:
        query = query.filter(ByTermCourse.level == level)
    if term_no:
        query = query.filter(ByTermCourse.term_no == term_no)
    total = query.count()
    items = query.order_by(ByTermCourse.level, ByTermCourse.term_no, ByTermCourse.row_number).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id": t.external_id, "level": t.level, "term": t.term, "term_no": t.term_no,
            "course_name": t.course_name, "units": t.units, "capacity": t.capacity,
            "course_type": t.course_type, "unique_course_code": t.unique_course_code,
            "unique_course_name": t.unique_course_name, "year_identified": t.year_identified,
        } for t in items],
    }


@router.get("/schedule-history")
def schedule_history(
    db: Session = Depends(get_db),
    user=Depends(require_authenticated),
    q: str | None = Query(default=None, description="جستجو در نام درس"),
    semester: str | None = Query(default=None, description="کد نیم‌سال مثل 4041"),
    limit: int = Query(default=60, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """سوابق برنامه‌ریزی همگام‌شده — با خلاصهٔ نیم‌سال‌ها"""
    query = db.query(ByScheduleHistory)
    if q:
        query = query.filter(ByScheduleHistory.course_name.like(f"%{q.strip()}%"))
    if semester:
        query = query.filter(ByScheduleHistory.semester == semester)
    total = query.count()
    items = query.order_by(ByScheduleHistory.external_id.desc()).offset(offset).limit(limit).all()
    semesters = db.query(
        ByScheduleHistory.semester, ByScheduleHistory.semester_label,
    ).distinct().order_by(ByScheduleHistory.semester).all()
    return {
        "total": total,
        "semesters": [{"code": s, "label": l or s} for s, l in semesters],
        "items": [{
            "id": h.external_id, "semester": h.semester, "semester_label": h.semester_label,
            "faculty_name": h.faculty_name, "department_name": h.department_name,
            "level": h.level, "course_name": h.course_name, "day": h.day,
            "start_time": h.start_time, "end_time": h.end_time,
            "class_code": h.class_code, "instructor_name": h.instructor_name,
            "max_capacity": h.max_capacity, "exam_date": h.exam_date,
        } for h in items],
    }


@router.get("/rooms")
def rooms(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """کلاس‌ها و اتاق‌های درس همگام‌شده"""
    items = db.query(ByRoom).order_by(ByRoom.code).all()
    return {"total": len(items), "items": [{
        "id": r.external_id, "code": r.code, "name": r.name, "capacity": r.capacity,
        "place_type": r.place_type, "group": r.group_name, "room_types": r.room_types,
    } for r in items]}


@router.get("/instructors")
def instructors(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """اساتید همگام‌شده از برنامه‌یار۳۶۰"""
    items = db.query(ByInstructor).order_by(ByInstructor.name).all()
    return {"total": len(items), "items": [{
        "id": i.external_id, "code": i.code, "name": i.name, "cooperation_type": i.cooperation_type,
        "group": i.group_name, "max_teaching_units": i.max_teaching_units,
    } for i in items]}


@router.get("/insights")
def integration_insights(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """تحلیل‌های دادهٔ واقعی برنامه‌ریزی (بر پایهٔ آینهٔ برنامه‌یار۳۶۰)"""
    return insights.build_insights(db)


@router.get("/initial-plan")
def get_initial_plan(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """برنامه‌ریزی اولیهٔ نیم‌سال بعد — خروجی مدیریار۳۶۰ برای برنامه‌یار۳۶۰"""
    plan = initial_plan.build_initial_plan(db)
    if not plan.get("ready"):
        return plan
    try:
        match = initial_plan.match_with_remote(plan)
        plan["remote_match"] = {
            "matched_count": len(match["matched"]),
            "remote_offered_count": match["remote_offered_count"],
            "matched_preview": [{"course_title": m["course_title"], "remote_title": m["remote_title"],
                                 "remote_unique_code": m["remote_unique_code"]}
                                for m in match["matched"][:20]],
            "unmatched": match["unmatched"][:30],
        }
    except IntegrationError as e:
        plan["remote_match"] = {"error": str(e)}
    return plan


@router.post("/initial-plan/push")
def push_plan(db: Session = Depends(get_db), user=Depends(require_authenticated)):
    """ثبت برنامه‌ریزی اولیه به‌صورت «پیشنهاد دروس» در برنامه‌یار۳۶۰ — فقط ادمین سیستم"""
    _ensure_enabled()
    _require_role(user, PUSH_ROLES, "ارسال برنامه‌ریزی اولیه به برنامه‌یار۳۶۰")
    try:
        return initial_plan.push_initial_plan(db)
    except IntegrationError as e:
        raise HTTPException(status_code=502, detail=str(e))
