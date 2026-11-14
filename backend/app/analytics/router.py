# -*- coding: utf-8 -*-
"""مسیرهای API موتور تحلیلی + کاتالوگ داده + داشبورد کلی

همه سرویس‌ها خروجی استاندارد (kpis/charts/table/limitations/disclaimer) دارند.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth.deps import require_authenticated, require_service
from ..db import get_db
from ..integration.rebase import get_data_basis, is_real_basis
from ..models import Course, Department, Instructor, Major, Offering, Student, Term
from . import (
    capacity, cost, demand, dept_perf, distribution, efficiency, fail_rate,
    instructor_perf, ratio, recommend, simulation,
)
from .base import (
    DEFAULT_TARGET_RATIO, DEGREE_FA, EMPLOYMENT_FA, RANK_FA, STATUS_FA, fa_int, r1, wavg,
)
from .simulation import SimInput

router = APIRouter(prefix="/api", tags=["analytics"])


# ---------------------------------------------------------------------------
# کاتالوگ داده برای فیلترهای داشبورد
# ---------------------------------------------------------------------------

@router.get("/catalog/departments")
def catalog_departments(db: Session = Depends(get_db), _user=Depends(require_authenticated)):
    items = db.query(Department).order_by(Department.id).all()
    return [{"id": d.id, "code": d.code, "name": d.name} for d in items]


@router.get("/catalog/majors")
def catalog_majors(db: Session = Depends(get_db), department_id: int | None = None,
                   _user=Depends(require_authenticated)):
    q = db.query(Major)
    if department_id:
        q = q.filter(Major.department_id == int(department_id))
    depts = {d.id: d.name for d in db.query(Department).all()}
    return [{
        "id": m.id, "code": m.code, "name": m.name,
        "degree": m.degree, "degree_fa": DEGREE_FA.get(m.degree, m.degree),
        "department_id": m.department_id, "department": depts.get(m.department_id, "—"),
        "annual_intake": m.annual_intake, "active": m.active,
    } for m in q.order_by(Major.id).all()]


@router.get("/catalog/courses")
def catalog_courses(db: Session = Depends(get_db), department_id: int | None = None,
                    major_id: int | None = None, _user=Depends(require_authenticated)):
    q = db.query(Course).filter(Course.active.is_(True))
    if department_id:
        q = q.filter(Course.department_id == int(department_id))
    if major_id:
        q = q.filter(Course.major_id == int(major_id))
    depts = {d.id: d.name for d in db.query(Department).all()}
    majors = {m.id: m.name for m in db.query(Major).all()}
    return [{
        "id": c.id, "code": c.code, "title": c.title, "credits": c.credits,
        "degree": c.degree, "degree_fa": DEGREE_FA.get(c.degree, c.degree),
        "department_id": c.department_id, "department": depts.get(c.department_id, "—"),
        "major_id": c.major_id, "major": majors.get(c.major_id, "—") if c.major_id else "درس مشترک",
        "tags": c.tags or [],
    } for c in q.order_by(Course.code).all()]


@router.get("/catalog/instructors")
def catalog_instructors(db: Session = Depends(get_db), department_id: int | None = None,
                        _user=Depends(require_authenticated)):
    q = db.query(Instructor)
    if department_id:
        q = q.filter(Instructor.department_id == int(department_id))
    depts = {d.id: d.name for d in db.query(Department).all()}
    return [{
        "id": i.id, "name": i.name, "rank": i.rank, "rank_fa": RANK_FA.get(i.rank, i.rank),
        "employment": i.employment, "employment_fa": EMPLOYMENT_FA.get(i.employment, i.employment),
        "department_id": i.department_id, "department": depts.get(i.department_id, "—"),
        "max_weekly_hours": i.max_weekly_hours,
    } for i in q.order_by(Instructor.name).all()]


@router.get("/catalog/terms")
def catalog_terms(db: Session = Depends(get_db), _user=Depends(require_authenticated)):
    items = sorted(db.query(Term).all(), key=lambda t: t.order_index)
    return [{"id": t.id, "code": t.code, "label": t.label, "order_index": t.order_index} for t in items]


# ---------------------------------------------------------------------------
# داشبورد کلی
# ---------------------------------------------------------------------------

@router.get("/dashboard/overview")
def dashboard_overview(db: Session = Depends(get_db), _user=Depends(require_authenticated)):
    terms = sorted(db.query(Term).all(), key=lambda t: t.order_index)
    latest = terms[-1] if terms else None
    courses = {c.id: c for c in db.query(Course).all()}
    depts = {d.id: d.name for d in db.query(Department).all()}
    majors = db.query(Major).all()
    all_offs = db.query(Offering).all()

    latest_offs = [o for o in all_offs if latest and o.term_id == latest.id]
    cap = sum(o.capacity for o in latest_offs)
    enr = sum(o.enrolled for o in latest_offs)
    fill = r1(enr / cap * 100) if cap else None
    sat = r1(wavg([(o.satisfaction, o.evaluation_count) for o in latest_offs]))
    fail = r1(wavg([(o.failed / o.enrolled * 100, o.enrolled) for o in latest_offs if o.enrolled]))
    unmet = sum(o.waiting for o in latest_offs)
    students_active = db.query(Student).filter(Student.status == "active").count()
    instructors_n = db.query(Instructor).count()
    courses_n = db.query(Course).filter(Course.active.is_(True)).count()

    # مبنای داده: پس از همگام‌سازی با برنامه‌یار۳۶۰، دیتای مبنا واقعی است
    basis = get_data_basis(db)
    real = is_real_basis(db)

    trend = []
    for t in terms:
        offs = [o for o in all_offs if o.term_id == t.id]
        c_t = sum(o.capacity for o in offs)
        e_t = sum(o.enrolled for o in offs)
        trend.append({
            "term": t.label,
            "satisfaction": r1(wavg([(o.satisfaction, o.evaluation_count) for o in offs])),
            "fill_pct": r1((e_t / c_t * 100) if c_t else None),
        })

    students_by_dept = {}
    for s in db.query(Student).filter(Student.status == "active").all():
        major = next((m for m in majors if m.id == s.major_id), None)
        if major:
            students_by_dept[depts.get(major.department_id, "—")] = \
                students_by_dept.get(depts.get(major.department_id, "—"), 0) + 1

    unmet_by_course = {}
    for o in latest_offs:
        c = courses.get(o.course_id)
        if c:
            unmet_by_course[c.code] = unmet_by_course.get(c.code, 0) + o.waiting
    top_unmet = sorted(unmet_by_course.items(), key=lambda kv: -kv[1])[:6]

    kpis = [
        {"label": "دانشجویان فعال", "value": students_active, "unit": "نفر"},
        {"label": "اساتید", "value": instructors_n, "unit": "نفر"},
        {"label": "دروس فعال", "value": courses_n, "unit": "درس"},
        {"label": "ترم جاری", "value": latest.label if latest else "—"},
        {"label": "پرشدن ظرفیت ترم جاری", "value": fill, "unit": "٪",
         "hint": "ثبت‌نام برآوردی (ظرفیت واقعی × نرخ پرشدگی)" if real else None},
        {"label": "رضایت ترم جاری", "value": sat, "unit": "از ۵"},
        {"label": "نرخ مردودی ترم جاری", "value": fail, "unit": "٪", "tone": "warn"},
        {"label": "محرومیت ثبت‌نام ترم جاری", "value": unmet, "unit": "نفر",
         "tone": "warn" if unmet else "good"},
    ]
    if real:
        # روی مبنای واقعی، شاخص‌های بدون منبع با شاخص‌های واقعی جایگزین می‌شوند
        kpis = [k for k in kpis if k["label"] not in ("دانشجویان فعال", "نرخ مردودی ترم جاری")]
        kpis.insert(0, {"label": "گروه‌های کلاس ترم جاری", "value": len(latest_offs), "unit": "گروه",
                        "hint": "گروه‌های واقعی اجراشده در سوابق برنامه‌یار۳۶۰"})

    charts = [
        {
            "key": "trend",
            "type": "line",
            "title": "روند رضایت و پرشدن ظرفیت (۶ ترم اخیر)",
            "data": trend,
            "xKey": "term",
            "yKeys": ["satisfaction", "fill_pct"],
            "seriesLabels": {"satisfaction": "رضایت (از ۵)", "fill_pct": "پرشدن ظرفیت (٪)"},
        },
        {
            "key": "students",
            "type": "bar",
            "title": "دانشجویان فعال به تفکیک دانشکده",
            "data": [{"name": k, "value": v} for k, v in students_by_dept.items()],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "دانشجوی فعال"},
        },
        {
            "key": "unmet",
            "type": "bar",
            "title": "بیشترین محرومیت ثبت‌نام ترم جاری",
            "data": [{"name": k, "value": v} for k, v in top_unmet],
            "xKey": "name",
            "yKeys": ["value"],
            "seriesLabels": {"value": "نفر محروم"},
        },
    ]
    if real:
        charts = [c for c in charts if c["key"] != "students"]  # پروندهٔ دانشجو در منبع نیست
        # نمودار واقعی فعالیت برنامه‌ریزی از سوابق برنامه‌یار۳۶۰
        from ..integration.models import ByScheduleHistory

        hist_rows = db.query(
            ByScheduleHistory.semester, ByScheduleHistory.semester_label, ByScheduleHistory.course_name
        ).all()
        act = {}
        for sem, slabel, _c in hist_rows:
            a = act.setdefault(sem, {"label": slabel or sem, "sessions": 0, "courses": set()})
            a["sessions"] += 1
            if _c:
                a["courses"].add(_c)
        real_activity = [{
            "term": act[s]["label"],
            "sessions": act[s]["sessions"],
            "courses": len(act[s]["courses"]),
        } for s in sorted(act)]
        charts.append({
            "key": "real-activity",
            "type": "bar",
            "title": "فعالیت واقعی برنامه‌ریزی در هر نیم‌سال (دادهٔ برنامه‌یار۳۶۰)",
            "data": real_activity,
            "xKey": "term",
            "yKeys": ["sessions", "courses"],
            "seriesLabels": {"sessions": "رکورد کلاس واقعی", "courses": "درس یکتای واقعی"},
        })

    # جدول خلاصه دانشکده‌ها
    instr_by_dept = {}
    for i in db.query(Instructor).all():
        instr_by_dept.setdefault(i.department_id, []).append(i)
    ADJUNCT_FTE = 0.5
    summary_rows = []
    majors_by_dept = {}
    for m in majors:
        majors_by_dept.setdefault(m.department_id, []).append(m.id)
    for d_id, d_name in depts.items():
        fte = sum(1.0 if i.employment == "faculty" else ADJUNCT_FTE for i in instr_by_dept.get(d_id, []))
        st = sum(1 for s in db.query(Student).filter(Student.status == "active").all()
                 if s.major_id in majors_by_dept.get(d_id, []))
        offs_d = [o for o in latest_offs if o.course_id in courses and courses[o.course_id].department_id == d_id]
        cap_d = sum(o.capacity for o in offs_d)
        enr_d = sum(o.enrolled for o in offs_d)
        summary_rows.append({
            "department": d_name,
            "students": st,
            "fte": r1(fte),
            "ratio": r1(st / fte) if fte else None,
            "fill_pct": r1((enr_d / cap_d * 100) if cap_d else None),
            "satisfaction": r1(wavg([(o.satisfaction, o.evaluation_count) for o in offs_d])),
        })

    return {
        "kpis": kpis,
        "charts": charts,
        "table": {
            "columns": [
                {"key": "department", "label": "دانشکده"},
                {"key": "students", "label": "دانشجوی فعال", "format": "int"},
                {"key": "fte", "label": "استاد (FTE)"},
                {"key": "ratio", "label": "نسبت دانشجو/استاد"},
                {"key": "fill_pct", "label": "پرشدن ظرفیت", "format": "pct"},
                {"key": "satisfaction", "label": "رضایت", "format": "float"},
            ],
            "rows": summary_rows,
        },
        "note": (
            "مبنای داده: همگام‌شده و بازسازی‌شده از برنامه‌یار۳۶۰ — ظرفیت‌ها، گروه‌های کلاس، اساتید و ترم‌ها واقعی‌اند؛ "
            "ثبت‌نام برآوردی است و مؤلفه‌های بدون منبع (نظرسنجی، نتایج ارزشیابی، پروندهٔ دانشجو) صریحاً اعلام محدودیت می‌شوند."
            if real
            else "داده‌های نمونه سینتتیک برای نمایش قابلیت‌ها است؛ با نخستین همگام‌سازی از برنامه‌یار۳۶۰، دیتای مبنا واقعی می‌شود."
        ),
        "basis": basis,
        "disclaimer": "این داشبورد ابزار پشتیبان تصمیم‌گیری است و جایگزین اختیار قانونی و قضاوت حرفه‌ای مسئولان دانشگاه نیست.",
    }


# ---------------------------------------------------------------------------
# ۱۱ سرویس تحلیلی
# ---------------------------------------------------------------------------

@router.get("/analytics/demand-analysis")
def api_demand_analysis(db: Session = Depends(get_db),
                        department_id: int | None = None, course_id: int | None = None,
                        _user=Depends(require_service("demand-analysis"))):
    return demand.demand_analysis(db, department_id, course_id)


@router.get("/analytics/capacity-forecast")
def api_capacity_forecast(db: Session = Depends(get_db),
                          department_id: int | None = None, course_id: int | None = None,
                          _user=Depends(require_service("capacity-forecast"))):
    return capacity.capacity_forecast(db, department_id, course_id)


@router.get("/analytics/student-distribution")
def api_student_distribution(db: Session = Depends(get_db),
                             group_by: str = Query(default="major"),
                             department_id: int | None = None,
                             status: str = Query(default="active"),
                             _user=Depends(require_service("student-distribution"))):
    return distribution.student_distribution(db, group_by, department_id, status)


@router.get("/analytics/instructor-performance")
def api_instructor_performance(db: Session = Depends(get_db),
                               department_id: int | None = None,
                               instructor_id: int | None = None,
                               min_sample: int | None = None,
                               _user=Depends(require_service("instructor-performance"))):
    return instructor_perf.instructor_performance(db, department_id, instructor_id, min_sample)


@router.get("/analytics/instructor-recommendation")
def api_instructor_recommendation(db: Session = Depends(get_db), course_id: int = Query(...),
                                  _user=Depends(require_service("instructor-recommendation"))):
    result = recommend.instructor_recommendation(db, course_id)
    if result is None:
        raise HTTPException(status_code=404, detail="درس مورد نظر یافت نشد.")
    return result


@router.get("/analytics/department-performance")
def api_department_performance(db: Session = Depends(get_db),
                               _user=Depends(require_service("department-performance"))):
    return dept_perf.department_performance(db)


@router.get("/analytics/fail-rate")
def api_fail_rate(db: Session = Depends(get_db), department_id: int | None = None,
                  course_id: int | None = None, term_id: int | None = None,
                  threshold: float = 20, _user=Depends(require_service("fail-rate"))):
    return fail_rate.fail_rate(db, department_id, course_id, term_id, threshold)


@router.get("/analytics/course-cost")
def api_course_cost(db: Session = Depends(get_db), department_id: int | None = None,
                    course_id: int | None = None, room_hourly: int | None = None,
                    weeks: int | None = None, overhead: int | None = None,
                    tuition_per_credit: int | None = None,
                    _user=Depends(require_service("course-cost"))):
    return cost.course_cost(db, department_id, course_id, room_hourly, weeks, overhead, tuition_per_credit)


@router.get("/analytics/ratio-optimization")
def api_ratio_optimization(db: Session = Depends(get_db),
                           target: float = DEFAULT_TARGET_RATIO,
                           _user=Depends(require_service("ratio-optimization"))):
    return ratio.ratio_optimization(db, target)


@router.get("/analytics/teaching-efficiency")
def api_teaching_efficiency(db: Session = Depends(get_db),
                            _user=Depends(require_service("teaching-efficiency"))):
    return efficiency.teaching_efficiency(db)


@router.post("/analytics/major-simulation")
def api_major_simulation(payload: SimInput, db: Session = Depends(get_db),
                         _user=Depends(require_service("major-simulation"))):
    result = simulation.major_simulation(db, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="رشته مورد نظر یافت نشد.")
    return result
