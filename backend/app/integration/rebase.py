# -*- coding: utf-8 -*-
"""بازسازی «دیتای مبنا» سامانه از دادهٔ واقعی همگام‌شدهٔ برنامه‌یار۳۶۰

قرارداد شفافیت:
  * هرچه منبع (برنامه‌یار۳۶۰) واقعاً دارد — دانشکده/گروه، دروس ترمیک، دروس ارائه،
    اساتید، ترم‌ها، سوابق کلاس‌ها با ظرفیت — «واقعی» می‌ماند.
  * ثبت‌نام مبنای تحلیل = ظرفیت × نرخ پرشدگی (DANESHJO360_FILL_RATE، پیش‌فرض ۸۵٪)
    چون منبع فقط ظرفیت برنامه‌ریزی‌شده دارد؛ این برآورد در خروجی‌ها اعلام می‌شود.
  * نتایج ارزشیابی (قبولی/مردودی/رضایت) در منبع وجود ندارد؛ ساختگی تولید نمی‌شود و
    سرویس‌های وابسته محدودیت را صریحاً اعلام می‌کنند.

هر بار پس از همگام‌سازی کامل اجرا می‌شود تا دیتای مبنا همیشه همگام بماند.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import AppMeta, Course, Department, Instructor, Major, Offering, Student, Term
from ..analytics.base import (
    get_data_basis, has_evaluation_data, has_result_data, is_real_basis,
    real_basis_limitations, eval_missing_limitation, result_missing_limitation,  # noqa: F401 (بازصادری)
)
from . import config
from .initial_plan import normalize_title
from .models import ByInstructor, ByOfferedCourse, ByRoom, ByScheduleHistory, ByTermCourse

# نگاشت مقطع دروس ترمیک به مقطع داخلی
DEGREE_MAP = {"پیوسته": "bsc", "ناپیوسته": "bsc"}

# نگاشت نوع همکاری استاد به وضعیت اشتغال
EMPLOYMENT_MAP = {
    "دستیار آموزشی": "adjunct",
    "حق التدریس": "adjunct",
    "حق‌التدریس": "adjunct",
    "مهمان": "adjunct",
    "مدعو": "adjunct",
}

STOP_WORDS = {"و", "در", "به", "از", "با", "برای", "های", "یک", "دو", "ی"}


def title_tokens(title: str | None) -> list[str]:
    """توکن‌های کلیدی عنوان برای تطبیق تخصص استاد و درس"""
    s = normalize_title(title)
    return [w for w in s.split() if len(w) > 2 and w not in STOP_WORDS][:8]


def semester_to_term_code(sem: str) -> tuple[str, str] | None:
    """4021 → («1402-1»، «نیم‌سال اول ۱۴۰۲-۱۴۰۳»)"""
    if not sem or len(sem) != 4 or not sem.isdigit() or sem[0] != "4":
        return None
    try:
        year = 1400 + int(sem[2])
        no = int(sem[3])
    except ValueError:
        return None
    if no == 1:
        return f"{year}-1", f"نیم‌سال اول {year}-{year + 1}"
    if no == 2:
        return f"{year}-2", f"نیم‌سال دوم {year}-{year + 1}"
    return None


def _level_base(level: str | None) -> str:
    """«پیوسته 1394» / «پیوسته 1403» → «پیوسته»؛ «ناپیوسته» → «ناپیوسته»"""
    s = (level or "").strip()
    if s.startswith("ناپیوسته"):
        return "ناپیوسته"
    if s.startswith("پیوسته"):
        return "پیوسته"
    return s or "نامشخص"


def _first_or_default(v, default):
    return v if v not in (None, "", 0) else default


# ---------------------------------------------------------------------------
# بازسازی کامل
# ---------------------------------------------------------------------------

def rebase_from_synced(db: Session, *, fill_rate: float | None = None) -> dict:
    """بازسازی جداول دیتای مبنا از آینهٔ برنامه‌یار۳۶۰ (تمام‌جایگزینی)"""
    fill_rate = fill_rate if fill_rate and 0 < fill_rate <= 1 else config.DEFAULT_FILL_RATE
    started = datetime.now(timezone.utc)

    # ---------- ۰) پاک‌سازی جداول مبنا (ترتیب به‌دلیل کلیدهای خارجی)
    db.query(Offering).delete(synchronize_session=False)
    db.query(Student).delete(synchronize_session=False)
    db.query(Course).delete(synchronize_session=False)
    db.query(Instructor).delete(synchronize_session=False)
    db.query(Major).delete(synchronize_session=False)
    db.query(Term).delete(synchronize_session=False)
    db.query(Department).delete(synchronize_session=False)
    db.flush()

    history = db.query(ByScheduleHistory).all()
    term_courses = db.query(ByTermCourse).all()
    offered = db.query(ByOfferedCourse).all()
    instructors_src = db.query(ByInstructor).all()
    rooms_src = db.query(ByRoom).all()

    if not history and not term_courses:
        return {"rebuilt": False, "reason": "دادهٔ همگام‌شده‌ای از برنامه‌یار۳۶۰ موجود نیست؛ ابتدا همگام‌سازی کنید."}

    # ---------- ۱) دانشکده/گروه‌های آموزشی (واقعی از سوابق)
    depts: dict[str, Department] = {}
    for code in sorted({h.department_code or "?" for h in history}):
        name = next((h.department_name for h in history if h.department_code == code), None) or f"گروه آموزشی {code}"
        depts[code] = Department(code=code[:16], name=name[:120])
        db.add(depts[code])
    if not depts:
        depts["GEN"] = Department(code="GEN", name="گروه عمومی")
        db.add(depts["GEN"])
    default_dept = next(iter(depts.values()))
    db.flush()
    dept_ids = {code: d.id for code, d in depts.items()}

    # ---------- ۲) رشته‌ها (از مقاطع واقعی دروس ترمیک؛ پذیرش در منبع نیست → صفر)
    majors: dict[str, Major] = {}
    level_bases = sorted({_level_base(t.level) for t in term_courses} | {_level_base(h.level) for h in history})
    for lv in level_bases:
        m = Major(
            code=lv[:16],
            name=f"کارشناسی {lv}" if lv != "نامشخص" else "برنامهٔ نیم‌سال جاری",
            degree=DEGREE_MAP.get(lv, "bsc"),
            annual_intake=0,  # پذیرش سالانه در منبع برنامه‌یار موجود نیست
            department_id=default_dept.id,
        )
        majors[lv] = m
        db.add(m)
    db.flush()
    major_ids = {lv: m.id for lv, m in majors.items()}

    # ---------- ۳) ترم‌ها (از نیم‌سال‌های واقعی سوابق)
    terms: dict[str, Term] = {}
    sem_to_code: dict[str, str] = {}
    for sem in sorted({h.semester for h in history}):
        mapped = semester_to_term_code(sem)
        if not mapped:
            continue
        code, label = mapped
        sem_to_code[sem] = code
        if code not in terms:
            terms[code] = Term(code=code, label=label, order_index=0)
    ordered = sorted(terms.items())
    for i, (code, t) in enumerate(ordered, start=1):
        t.order_index = i
        db.add(t)
    db.flush()
    term_ids = {sem: terms[code].id for sem, code in sem_to_code.items()}

    # ---------- ۴) دروس (کاتالوگ دروس ترمیک + عناوین واقعی سوابق + غنی‌سازی از دروس ارائه)
    offered_by_title: dict[str, ByOfferedCourse] = {}
    for oc in offered:
        for key in (oc.offered_title, oc.unique_title):
            n = normalize_title(key)
            if n and n not in offered_by_title:
                offered_by_title[n] = oc

    courses: dict[str, Course] = {}          # normalized title → Course
    course_objs: list[Course] = []
    used_codes: set[str] = set()

    def add_course(title: str, *, code: str | None, units: int | None, level: str | None,
                   ctype: str | None) -> Course:
        n = normalize_title(title)
        oc = offered_by_title.get(n)
        hours = (oc.theoretical_hours or 0) + (oc.practical_hours or 0) if oc else 0
        cand = (code or (oc.unique_code if oc else None) or f"BY{len(course_objs) + 1:04d}")[:16]
        # کاتالوگ مبدأ ممکن است یک کد یکتا را بین دو عنوان به‌اشتراک بگذارد؛ تداخل با پسوند حل می‌شود
        if cand in used_codes:
            cand = f"{cand[:12]}x{len(course_objs) + 1:03d}"
        used_codes.add(cand)
        c = Course(
            code=cand,
            title=title[:160],
            credits=int(units or hours or 3),
            degree=DEGREE_MAP.get(_level_base(level), "bsc"),
            department_id=default_dept.id,
            major_id=major_ids.get(_level_base(level)),
            tags=[ctype] + title_tokens(title) if ctype else title_tokens(title),
            active=True,
        )
        course_objs.append(c)
        courses[n] = c
        db.add(c)
        return c

    # کاتالوگ رسمی دروس ترمیک — ترجیح کد یکتای معتبر
    for t in sorted(term_courses, key=lambda x: (x.unique_course_code not in (None, ""), x.external_id)):
        n = normalize_title(t.course_name)
        if n in courses:
            continue
        add_course(t.course_name, code=t.unique_course_code, units=t.units, level=t.level, ctype=t.course_type)

    # عناوین تدریس‌شدهٔ واقعی سوابق که در کاتالوگ نیستند
    for title in sorted({h.course_name for h in history}):
        n = normalize_title(title)
        if n and n not in courses:
            add_course(title, code=None, units=None, level="نامشخص", ctype=None)
    db.flush()
    course_ids = {n: c.id for n, c in courses.items()}

    # ---------- ۵) اساتید (واقعی) + تخصص استخراج‌شده از عناوین تدریس واقعی
    taught: dict[str, set[str]] = {}
    for h in history:
        if h.instructor_code:
            taught.setdefault(h.instructor_code, set()).update(title_tokens(h.course_name))

    instr_by_code: dict[str, Instructor] = {}
    instr_by_name: dict[str, Instructor] = {}
    for i_src in sorted(instructors_src, key=lambda x: x.external_id):
        coop = i_src.cooperation_type or ""
        inst = Instructor(
            name=i_src.name[:120],
            rank="lecturer",
            employment=EMPLOYMENT_MAP.get(coop.strip(), "adjunct" if coop else "faculty"),
            department_id=default_dept.id,
            max_weekly_hours=int(i_src.max_teaching_units or 12),
            expertise=sorted(taught.get(i_src.code or "", set()))[:12],
            experience_years=5,
            hourly_cost=350000 if EMPLOYMENT_MAP.get(coop.strip()) == "adjunct" else 470000,
        )
        instr_by_code[i_src.code or f"?{i_src.external_id}"] = inst
        instr_by_name[normalize_title(i_src.name)] = inst
        db.add(inst)
    # برخی کدهای استاد در سوابق خارج از فهرست اساتید مبدأ هستند → نگهدارندهٔ «نامشخص»
    unknown_inst = Instructor(
        name="بدون استاد مشخص", rank="lecturer", employment="adjunct",
        department_id=default_dept.id, max_weekly_hours=0,
        expertise=[], experience_years=0, hourly_cost=0,
    )
    db.add(unknown_inst)
    db.flush()

    # ---------- ۶) ارائه‌ها از سوابق واقعی برنامه‌ریزی (بدون دوبرابرکردن گروه‌ها)
    groups: dict[tuple, list[ByScheduleHistory]] = {}
    for h in history:
        key = (normalize_title(h.course_name), h.semester, h.instructor_code or h.instructor_name or "?")
        groups.setdefault(key, []).append(h)

    n_offs = 0
    for (ctitle, sem, icode), rows in groups.items():
        course = courses.get(ctitle)
        if course is None:
            continue
        term_id = term_ids.get(sem)
        if term_id is None:
            continue
        inst = instr_by_code.get(icode or "") or instr_by_name.get(normalize_title(icode))
        scheduled = [r for r in rows if r.day or r.class_code]
        if scheduled:
            seen = set()
            for r in scheduled:
                key2 = (r.day, r.start_time, r.end_time, r.class_code)
                if key2 in seen:
                    continue
                seen.add(key2)
                cap = int(_first_or_default(r.max_capacity, 30))
                db.add(Offering(
                    course_id=course.id, instructor_id=inst.id if inst else unknown_inst.id,
                    term_id=term_id, capacity=cap,
                    enrolled=round(cap * fill_rate), waiting=0,
                    passed=0, failed=0, satisfaction=None, evaluation_count=0,
                    mode="حضوری",
                ))
                n_offs += 1
        else:
            caps = [r.max_capacity for r in rows if r.max_capacity]
            cap = int(sum(caps) / len(caps)) if caps else 30
            db.add(Offering(
                course_id=course.id, instructor_id=inst.id if inst else unknown_inst.id,
                term_id=term_id, capacity=cap,
                enrolled=round(cap * fill_rate), waiting=0,
                passed=0, failed=0, satisfaction=None, evaluation_count=0,
                mode="حضوری",
            ))
            n_offs += 1
    db.flush()

    # ---------- ۷) ثبت مبنای داده (شفافیت تحلیل‌ها)
    meta = {
        "mode": "barnameh_yar",
        "source": "برنامه‌یار۳۶۰ — سامانه هوشمند برنامه‌ریزی درسی",
        "source_url": config.BASE_URL,
        "fill_rate": fill_rate,
        "rebuilt_at": started.isoformat(timespec="seconds"),
        "counts": {
            "departments": len(depts),
            "majors": len(majors),
            "courses": len(course_objs),
            "instructors": len(instructors_src),
            "terms": len(terms),
            "offerings": n_offs,
            "rooms": len(rooms_src),
            "history_rows": len(history),
        },
        "real_fields": ["دانشکده/گروه", "دروس", "اساتید", "ترم‌ها", "ظرفیت کلاس‌ها", "گروه‌های اجراشده", "اتاق‌ها"],
        "estimated_fields": [f"ثبت‌نام (ظرفیت × نرخ پرشدگی {fill_rate:.0%})"],
        "missing_fields": ["نتایج ارزشیابی (قبولی/مردودی)", "رضایت نظرسنجی", "پروندهٔ دانشجویان", "پذیرش سالانه رشته"],
    }
    for k, v in [("data_basis", meta), ("fill_rate", fill_rate)]:
        row = db.get(AppMeta, k)
        if row:
            row.value = v
        else:
            db.add(AppMeta(key=k, value=v))
    db.commit()

    return {
        "rebuilt": True,
        "fill_rate": fill_rate,
        "counts": meta["counts"],
        "rebuilt_at": meta["rebuilt_at"],
        "note": "دیتای مبنا از دادهٔ واقعی برنامه‌یار۳۶۰ بازسازی شد؛ ثبت‌نام بر پایهٔ نرخ پرشدگی برآورد و نتایج ارزشیابی خالی مانده است.",
    }
