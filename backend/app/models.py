# -*- coding: utf-8 -*-
"""مدل‌های پایگاه داده سامانه دانشجو۳۶۰ (نسخه مدیریت آموزشی)

اصل حریم خصوصی با طراحی (Privacy by Design): جدول دانشجویان هیچ مشخصات هویتی
(نام، کد ملی، شماره تماس و…) ندارد؛ تنها یک کد بی‌معنای نمونه، رشته، سال ورود
و وضعیت تحصیلی نگهداری می‌شود تا همه تحلیل‌ها روی داده تجمیعی و بدون هویت انجام شود.
"""
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String

from .db import Base


class Department(Base):
    """دانشکده / گروه آموزشی"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    name = Column(String(120), nullable=False)


class Major(Base):
    """رشته تحصیلی"""
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    degree = Column(String(16), nullable=False, default="bsc")  # bsc / msc / phd
    annual_intake = Column(Integer, nullable=False, default=50)  # ظرفیت پذیرش سالانه
    active = Column(Boolean, nullable=False, default=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)


class Course(Base):
    """درس"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)
    title = Column(String(160), nullable=False)
    credits = Column(Integer, nullable=False, default=3)  # تعداد واحد
    degree = Column(String(16), nullable=False, default="bsc")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    major_id = Column(Integer, ForeignKey("majors.id"))  # برای دروس مشترک می‌تواند تهی باشد
    tags = Column(JSON, default=list)  # حوزه‌های تخصصی برای تطبیق استاد/درس
    active = Column(Boolean, nullable=False, default=True)


class Instructor(Base):
    """استاد"""
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    rank = Column(String(16), nullable=False, default="assistant")  # prof / assoc / assistant / lecturer
    employment = Column(String(16), nullable=False, default="faculty")  # faculty / adjunct
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    max_weekly_hours = Column(Integer, nullable=False, default=12)  # سقف ساعت تدریس هفتگی
    expertise = Column(JSON, default=list)  # حوزه‌های تخصصی
    experience_years = Column(Integer, nullable=False, default=5)
    hourly_cost = Column(Integer, nullable=False, default=470000)  # تومان به‌ازای هر ساعت تدریس


class Student(Base):
    """دانشجو — بدون مشخصات هویتی (حریم خصوصی با طراحی)"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)  # کد بی‌معنای نمونه
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False)
    entry_year = Column(Integer, nullable=False)  # سال ورود
    status = Column(String(16), nullable=False, default="active")  # active / graduated / withdrawn


class Term(Base):
    """نیم‌سال تحصیلی"""
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True)
    code = Column(String(16), unique=True, nullable=False)  # نمونه: 1403-1
    label = Column(String(64), nullable=False)
    order_index = Column(Integer, nullable=False)


class Offering(Base):
    """ارائه یک درس در یک نیم‌سال توسط یک استاد — جدول اصلی تحلیل‌ها"""
    __tablename__ = "offerings"

    id = Column(Integer, primary_key=True)
    term_id = Column(Integer, ForeignKey("terms.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("instructors.id"), nullable=False)
    capacity = Column(Integer, nullable=False)          # ظرفیت اعلام‌شده
    enrolled = Column(Integer, nullable=False)          # ثبت‌نام انجام‌شده
    waiting = Column(Integer, nullable=False, default=0)  # محروم‌شدگان ثبت‌نام به دلیل ظرفیت
    avg_grade = Column(Float)                           # میانگین نمره درس
    passed = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    satisfaction = Column(Float)                        # میانگین نظرسنجی ۱ تا ۵
    evaluation_count = Column(Integer, nullable=False, default=0)  # تعداد پاسخ نظرسنجی
    mode = Column(String(16), nullable=False, default="حضوری")  # حضوری/ترکیبی/مجازی
