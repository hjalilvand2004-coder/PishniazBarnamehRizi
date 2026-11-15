# -*- coding: utf-8 -*-
"""بارگذاری داده نمونه سینتتیک — سامانه مدیریار۳۶۰

داده‌ها کاملاً فرضی و تولیدشده با seed ثابت‌اند تا نتایج تکرارپذیر بماند.
الگوها به‌گونه‌ای طراحی شده‌اند که هر ۱۱ سرویس تحلیلی خروجی معنادار داشته باشند:
  * دروس پرتقاضا با محرومیت ثبت‌نام (سرویس ۱ و ۲)
  * دروس حوزه هوش مصنوعی روند رشد و برخی دروس پایه روند افت دارند
  * تنوع رضایت و نرخ مردودی بین اساتید و دروس (سرویس ۴ و ۷)
  * برخی اساتید نمونه نظرسنجی کم دارند (نمایش آستانه کفایت نمونه)
  * تناسب دانشجو/استاد متفاوت بین دانشکده‌ها (سرویس ۹ و ۱۰)

نرخ‌های هزینه «نمونه» هستند و باید با نرخ‌های واقعی سازمان جایگزین شوند.
"""
import random

from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker

from .models import Course, Department, Instructor, Major, Offering, Student, Term

RNG = random.Random(2024)

# ---------------------------------------------------------------------------
# داده پایه
# ---------------------------------------------------------------------------

TERMS = [
    ("1401-2", "نیم‌سال دوم ۱۴۰۱-۱۴۰۲"),
    ("1402-1", "نیم‌سال اول ۱۴۰۲-۱۴۰۳"),
    ("1402-2", "نیم‌سال دوم ۱۴۰۲-۱۴۰۳"),
    ("1403-1", "نیم‌سال اول ۱۴۰۳-۱۴۰۴"),
    ("1403-2", "نیم‌سال دوم ۱۴۰۳-۱۴۰۴"),
    ("1404-1", "نیم‌سال اول ۱۴۰۴-۱۴۰۵"),
]

DEPARTMENTS = [
    ("ECE", "دانشکده مهندسی برق و کامپیوتر"),
    ("MEC", "دانشکده مهندسی مکانیک"),
    ("CE",  "دانشکده مهندسی عمران"),
    ("MGT", "دانشکده مدیریت و اقتصاد"),
    ("SCI", "دانشکده علوم پایه"),
]

# (کد، نام، دانشکده، مقطع، پذیرش سالانه)
MAJORS = [
    ("computer",   "مهندسی کامپیوتر",   "ECE", "bsc", 60),
    ("electrical", "مهندسی برق",        "ECE", "bsc", 50),
    ("ai",         "مهندسی هوش مصنوعی", "ECE", "msc", 20),
    ("mechanical", "مهندسی مکانیک",     "MEC", "bsc", 45),
    ("civil",      "مهندسی عمران",      "CE",  "bsc", 40),
    ("structures", "مهندسی سازه",       "CE",  "msc", 15),
    ("business",   "مدیریت بازرگانی",   "MGT", "bsc", 55),
    ("economics",  "علوم اقتصادی",      "MGT", "bsc", 35),
    ("math",       "ریاضیات کاربردی",   "SCI", "bsc", 25),
    ("physics",    "فیزیک",             "SCI", "bsc", 20),
]

# (کد، عنوان، واحد، دانشکده، رشته یا None، مقطع، تگ‌ها، تقاضای پایه، رشد هر ترم، سختی/میانگین نمره پایه)
COURSES = [
    ("ECE101", "مقدمات برنامه‌نویسی", 3, "ECE", None, "bsc", ["برنامه‌نویسی", "پایه"], 130, 0.05, 13.8),
    ("ECE102", "ساختمان داده‌ها", 3, "ECE", "computer", "bsc", ["ساختمان داده", "نرم‌افزار"], 95, 0.04, 13.2),
    ("ECE201", "طراحی الگوریتم‌ها", 3, "ECE", "computer", "bsc", ["الگوریتم", "نرم‌افزار"], 80, 0.03, 12.9),
    ("ECE202", "پایگاه داده", 3, "ECE", "computer", "bsc", ["پایگاه داده", "نرم‌افزار"], 85, 0.04, 14.0),
    ("ECE203", "سیستم‌عامل", 3, "ECE", "computer", "bsc", ["سیستم‌عامل", "سخت‌افزار"], 70, 0.02, 12.8),
    ("ECE204", "شبکه‌های کامپیوتری", 3, "ECE", "computer", "bsc", ["شبکه", "نرم‌افزار"], 65, 0.03, 13.5),
    ("ECE205", "هوش مصنوعی", 3, "ECE", None, "bsc", ["هوش مصنوعی", "داده"], 75, 0.08, 13.0),
    ("ECE301", "یادگیری ماشین", 3, "ECE", "ai", "msc", ["هوش مصنوعی", "داده"], 38, 0.09, 13.4),
    ("ECE302", "مهندسی نرم‌افزار پیشرفته", 3, "ECE", "ai", "msc", ["نرم‌افزار"], 30, 0.03, 14.2),
    ("ECE111", "مدارهای الکتریکی ۱", 3, "ECE", "electrical", "bsc", ["مدار", "برق"], 90, 0.01, 12.2),
    ("ECE112", "سیگنال‌ها و سیستم‌ها", 3, "ECE", "electrical", "bsc", ["سیگنال", "برق"], 70, 0.00, 12.0),
    ("ECE113", "الکترونیک ۱", 3, "ECE", "electrical", "bsc", ["الکترونیک", "برق"], 60, -0.02, 11.8),
    ("ECE114", "معماری کامپیوتر", 3, "ECE", "electrical", "bsc", ["سخت‌افزار"], 55, 0.01, 12.6),
    ("ME101", "استاتیک", 3, "MEC", None, "bsc", ["استاتیک", "پایه"], 110, 0.01, 12.4),
    ("ME102", "دینامیک", 3, "MEC", "mechanical", "bsc", ["دینامیک"], 80, 0.00, 12.1),
    ("ME201", "ترمودینامیک ۱", 3, "MEC", "mechanical", "bsc", ["ترمودینامیک"], 75, 0.00, 11.9),
    ("ME202", "مکانیک سیالات", 3, "MEC", "mechanical", "bsc", ["سیالات"], 60, -0.01, 11.7),
    ("ME203", "عناصر ماشین‌ها", 3, "MEC", "mechanical", "bsc", ["طراحی"], 55, 0.01, 12.8),
    ("ME204", "کنترل اتوماتیک", 3, "MEC", None, "bsc", ["کنترل"], 50, 0.02, 12.5),
    ("CE101", "مقاومت مصالح", 3, "CE", None, "bsc", ["مقاومت", "پایه"], 100, 0.01, 12.3),
    ("CE201", "تحلیل سازه‌ها", 3, "CE", "civil", "bsc", ["سازه"], 70, 0.00, 12.0),
    ("CE202", "بتن آرمه ۱", 3, "CE", "civil", "bsc", ["بتن", "سازه"], 60, 0.01, 12.6),
    ("CE203", "مکانیک خاک", 3, "CE", "civil", "bsc", ["خاک"], 50, -0.01, 12.2),
    ("CE204", "راه‌سازی", 2, "CE", "civil", "bsc", ["راه"], 45, 0.00, 13.4),
    ("MG101", "حسابداری مالی ۱", 3, "MGT", None, "bsc", ["حسابداری", "پایه"], 120, 0.02, 14.1),
    ("MG102", "اقتصاد خرد", 3, "MGT", "economics", "bsc", ["اقتصاد"], 85, 0.01, 13.2),
    ("MG103", "اقتصاد کلان", 3, "MGT", "economics", "bsc", ["اقتصاد"], 70, 0.00, 13.0),
    ("MG201", "مدیریت منابع انسانی", 2, "MGT", "business", "bsc", ["منابع انسانی", "مدیریت"], 75, 0.03, 14.6),
    ("MG202", "مدیریت بازاریابی", 2, "MGT", "business", "bsc", ["بازاریابی", "مدیریت"], 65, 0.02, 14.8),
    ("MG301", "اقتصادسنجی", 3, "MGT", "economics", "msc", ["اقتصاد", "داده"], 28, 0.04, 12.9),
    ("SC101", "ریاضی عمومی ۱", 3, "SCI", None, "bsc", ["ریاضی", "پایه"], 150, 0.02, 11.6),
    ("SC102", "ریاضی عمومی ۲", 3, "SCI", None, "bsc", ["ریاضی", "پایه"], 120, -0.01, 11.4),
    ("SC103", "معادلات دیفرانسیل", 3, "SCI", None, "bsc", ["ریاضی"], 85, -0.02, 11.2),
    ("SC104", "جبر خطی", 3, "SCI", "math", "bsc", ["جبر", "ریاضی"], 70, 0.01, 11.9),
    ("SC105", "آمار و احتمال مهندسی", 3, "SCI", None, "bsc", ["آمار", "داده"], 95, 0.04, 12.7),
    ("SC106", "فیزیک پایه ۱", 3, "SCI", None, "bsc", ["فیزیک", "پایه"], 110, -0.03, 11.5),
    ("SC107", "فیزیک پایه ۲", 3, "SCI", "physics", "bsc", ["فیزیک"], 85, -0.04, 11.3),
    ("SC108", "شیمی عمومی", 2, "SCI", None, "bsc", ["شیمی"], 90, -0.05, 12.9),
]

# (نام، مرتبه، نوع همکاری، سقف ساعت هفتگی، تخصص‌ها، سابقه)
INSTRUCTORS = {
    "ECE": [
        ("دکتر علی رضایی", "prof", "faculty", 14, ["هوش مصنوعی", "داده", "الگوریتم"], 22),
        ("دکتر مریم حسینی", "assoc", "faculty", 14, ["ساختمان داده", "نرم‌افزار", "پایگاه داده"], 18),
        ("دکتر محمد کاظمی", "assistant", "faculty", 12, ["برنامه‌نویسی", "پایه", "نرم‌افزار"], 10),
        ("دکتر سارا نوری", "assistant", "faculty", 12, ["پایگاه داده", "شبکه", "نرم‌افزار"], 8),
        ("دکتر حسن شریفی", "lecturer", "adjunct", 8, ["برنامه‌نویسی", "پایه"], 6),
        ("دکتر لیلا احمدی", "assistant", "faculty", 12, ["مدار", "برق", "سیگنال"], 9),
        ("دکتر امیرحسین رضوان", "assoc", "faculty", 12, ["سیگنال", "برق", "کنترل"], 15),
        ("دکتر نگین تابان", "assistant", "faculty", 12, ["الکترونیک", "مدار", "برق"], 7),
        ("دکتر بهزاد کاویانی", "assistant", "faculty", 12, ["هوش مصنوعی", "داده", "سیستم‌عامل"], 9),
    ],
    "MEC": [
        ("دکتر رضا کریمی", "prof", "faculty", 14, ["ترمودینامیک", "سیالات"], 24),
        ("دکتر فاطمه موسوی", "assoc", "faculty", 12, ["دینامیک", "استاتیک"], 16),
        ("دکتر امیر جلالی", "assistant", "faculty", 12, ["استاتیک", "پایه"], 9),
        ("دکتر نگار صادقی", "assistant", "faculty", 12, ["طراحی", "دینامیک"], 7),
        ("دکتر مهدی عباسی", "lecturer", "adjunct", 8, ["کنترل", "ترمودینامیک"], 5),
        ("دکتر پریسا نادری", "assistant", "faculty", 12, ["سیالات", "طراحی"], 8),
    ],
    "CE": [
        ("دکتر محمدحسین طاهری", "prof", "faculty", 14, ["سازه", "بتن"], 25),
        ("دکتر زهرا ملکی", "assoc", "faculty", 12, ["سازه", "مقاومت"], 17),
        ("دکتر آرش قاسمی", "assistant", "faculty", 12, ["مقاومت", "پایه"], 10),
        ("دکتر شیما رستمی", "assistant", "faculty", 12, ["خاک", "سازه"], 8),
        ("دکتر کیان مرتضوی", "lecturer", "adjunct", 8, ["راه", "پایه"], 6),
        ("دکتر هما افشار", "assistant", "faculty", 12, ["بتن", "خاک"], 9),
    ],
    "MGT": [
        ("دکتر فرشاد یزدانی", "prof", "faculty", 14, ["اقتصاد", "داده"], 21),
        ("دکتر الهام رحیمی", "assoc", "faculty", 12, ["مدیریت", "منابع انسانی"], 15),
        ("دکتر پویا اسدی", "assistant", "faculty", 12, ["حسابداری", "پایه"], 9),
        ("دکتر مینا دهقان", "assistant", "faculty", 12, ["بازاریابی", "مدیریت"], 8),
        ("دکتر کاوه سرایی", "lecturer", "adjunct", 8, ["اقتصاد", "حسابداری"], 7),
        ("دکتر آتنا صالحی", "assistant", "faculty", 12, ["اقتصاد", "داده"], 6),
        ("دکتر سامان رحمانی", "assoc", "faculty", 12, ["منابع انسانی", "مدیریت"], 13),
    ],
    "SCI": [
        ("دکتر جواد فرهادی", "prof", "faculty", 14, ["ریاضی", "پایه"], 26),
        ("دکتر نرگس اکبری", "assoc", "faculty", 12, ["آمار", "داده", "ریاضی"], 18),
        ("دکتر بهنام خسروی", "assistant", "faculty", 12, ["فیزیک", "پایه"], 11),
        ("دکتر آیدا سلطانی", "assistant", "faculty", 12, ["فیزیک", "جبر", "ریاضی"], 8),
        ("دکتر سعید مرادی", "assistant", "faculty", 12, ["شیمی", "پایه"], 9),
        ("دکتر ترانه قنبری", "lecturer", "adjunct", 8, ["ریاضی", "آمار"], 5),
        ("دکتر فرهاد نویدی", "assistant", "faculty", 12, ["جبر", "ریاضی"], 7),
        ("دکتر النا میرزایی", "assistant", "faculty", 12, ["آمار", "فیزیک"], 6),
    ],
}

# نرخ ساعتی هزینه تدریس نمونه (تومان) بر اساس مرتبه — حق‌التدریس نرخ ثابت دارد
RANK_HOURLY = {"prof": 650000, "assoc": 550000, "assistant": 470000, "lecturer": 380000}
RANK_QUALITY = {"prof": 4.25, "assoc": 4.00, "assistant": 3.75, "lecturer": 3.45}

BSC_YEARS = [1400, 1401, 1402, 1403, 1404]
BSC_RETENTION = [0.45, 0.60, 0.75, 0.85, 0.95]  # نرخ دانشجویان فعال هر کوهورت
MSC_YEARS = [1402, 1403, 1404]
MSC_RETENTION = [0.55, 0.80, 0.95]


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def seed_if_empty(engine, force: bool = False) -> bool:
    """در صورت خالی بودن پایگاه داده (یا force=True) داده نمونه بارگذاری می‌شود."""
    if not inspect(engine).has_table("departments"):
        return False  # جداول هنوز ساخته نشده‌اند؛ ابتدا init_db اجرا شود
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        if not force and db.query(Department).count() > 0:
            return False
        if force:
            for t in (Offering, Student, Course, Instructor, Major, Term, Department):
                db.query(t).delete()
            db.commit()
        _populate(db)
        db.commit()
        return True
    finally:
        db.close()


def _populate(db) -> None:
    terms = [Term(code=c, label=l, order_index=i + 1) for i, (c, l) in enumerate(TERMS)]
    db.add_all(terms)

    depts = [Department(code=c, name=n) for c, n in DEPARTMENTS]
    db.add_all(depts)
    db.flush()
    dept_id = {d.code: d.id for d in depts}

    majors = [
        Major(code=mc, name=mn, degree=dg, annual_intake=ai, department_id=dept_id[dc], active=True)
        for mc, mn, dc, dg, ai in MAJORS
    ]
    db.add_all(majors)
    db.flush()
    major_id = {m.code: m.id for m in majors}

    instructors = []
    for dc, people in INSTRUCTORS.items():
        for name, rank, employment, max_h, expertise, years in people:
            hourly = RANK_HOURLY[rank] if employment == "faculty" else 300000
            instructors.append(Instructor(
                name=name, rank=rank, employment=employment,
                department_id=dept_id[dc], max_weekly_hours=max_h,
                expertise=expertise, experience_years=years, hourly_cost=hourly,
            ))
    db.add_all(instructors)
    db.flush()
    instr_by_dept = {}
    for i in instructors:
        instr_by_dept.setdefault(i.department_id, []).append(i)

    courses = [
        Course(code=code, title=title, credits=credits, degree=degree,
               department_id=dept_id[dc], major_id=major_id.get(mcode), tags=tags, active=True)
        for (code, title, credits, dc, mcode, degree, tags, base_demand, growth, diff) in COURSES
    ]
    db.add_all(courses)
    db.flush()

    # ---- ارائه دروس در ۶ ترم اخیر ----
    for (code, _title, _credits, dc, _mcode, _degree, tags, base_demand, growth, diff) in COURSES:
        course = next(c for c in courses if c.code == code)
        pool = instr_by_dept[dept_id[dc]]
        scored = sorted(pool, key=lambda i: (-len(set(tags) & set(i.expertise or [])), RNG.random()))
        for t in terms:
            idx = t.order_index - 1
            demand = int(base_demand * ((1 + growth) ** idx) * RNG.uniform(0.93, 1.07))
            capacity = int(demand / RNG.uniform(0.85, 1.0) / 5 + 0.5) * 5
            enrolled = min(capacity, demand)
            waiting = demand - capacity
            instr = scored[RNG.randrange(0, min(3, len(scored)))]
            q = RANK_QUALITY[instr.rank] + RNG.uniform(-0.25, 0.25)
            if instr.employment == "adjunct":
                q -= 0.15
            avg_grade = _clamp(diff + RNG.uniform(-0.6, 0.6) + (q - 3.8) * 0.4, 9.5, 19.5)
            pass_rate = _clamp(0.50 + (avg_grade - 10) * 0.062, 0.45, 0.97)
            passed = round(enrolled * pass_rate)
            failed = enrolled - passed
            satisfaction = _clamp(q - (13.5 - diff) * 0.04 + RNG.uniform(-0.2, 0.2), 2.2, 4.9)
            eval_count = max(1, int(enrolled * RNG.uniform(0.2, 0.75)))
            r = RNG.random()
            mode = "حضوری" if r < 0.70 else ("ترکیبی" if r < 0.92 else "مجازی")
            db.add(Offering(
                term_id=t.id, course_id=course.id, instructor_id=instr.id,
                capacity=capacity, enrolled=enrolled, waiting=waiting,
                avg_grade=round(avg_grade, 2), passed=passed, failed=failed,
                satisfaction=round(satisfaction, 2), evaluation_count=eval_count, mode=mode,
            ))

    # ---- دانشجویان (بدون مشخصات هویتی) ----
    seq = 0
    for m in majors:
        is_bsc = m.degree == "bsc"
        years = BSC_YEARS if is_bsc else MSC_YEARS
        retention = BSC_RETENTION if is_bsc else MSC_RETENTION
        for yi, y in enumerate(years):
            # دانشجویان فعال
            for _ in range(round(m.annual_intake * retention[yi])):
                seq += 1
                db.add(Student(code=f"{seq:08d}", major_id=m.id, entry_year=y, status="active"))
            # فارغ‌التحصیلان (کوهورت‌های قدیمی)
            if is_bsc and y <= 1402:
                graduated_factor = {1400: 0.50, 1401: 0.35, 1402: 0.15}[y]
                for _ in range(round(m.annual_intake * graduated_factor)):
                    seq += 1
                    db.add(Student(code=f"{seq:08d}", major_id=m.id, entry_year=y, status="graduated"))
            if not is_bsc and y == 1402:
                for _ in range(round(m.annual_intake * 0.40)):
                    seq += 1
                    db.add(Student(code=f"{seq:08d}", major_id=m.id, entry_year=y, status="graduated"))
            # انصراف/اضمحلال
            if (is_bsc and y <= 1403) or (not is_bsc and y <= 1403):
                for _ in range(round(m.annual_intake * 0.05)):
                    seq += 1
                    db.add(Student(code=f"{seq:08d}", major_id=m.id, entry_year=y, status="withdrawn"))
