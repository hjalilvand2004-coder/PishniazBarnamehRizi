# -*- coding: utf-8 -*-
"""مدل‌های یکپارچگی با برنامه‌یار۳۶۰ — آینهٔ دادهٔ «برنامه‌ریزی واقعی»

برنامه‌یار۳۶۰ مبنای برنامه‌ریزی اجرایی است (دروس ترمیک، سوابق برنامه‌ریزی،
کلاس‌ها و اتاق‌های درس، اساتید). این جداول آینهٔ همان داده‌ها هستند و پس از هر
همگام‌سازی به‌صورت کامل بازسازی می‌شوند تا همیشه با مبدأ یکی باشند.

جداول با پیشوند «by_» از جداول اصلی مدیریار۳۶۰ (دادهٔ پایهٔ برنامه‌ریزی اولیه)
جدا می‌شوند تا تحلیل‌های فعلی دست‌نخورده باقی بماند.
"""
from sqlalchemy import Column, Float, Integer, JSON, String, Text

from ..db import Base


class ByTermCourse(Base):
    """آینهٔ سرویس «دروس ترمیک» برنامه‌یار۳۶۰"""
    __tablename__ = "by_term_courses"

    id = Column(Integer, primary_key=True)          # کلید محلی
    external_id = Column(Integer, nullable=False, index=True)  # id در برنامه‌یار
    level = Column(String(64), nullable=True)        # نمونه: پیوسته 1394 / ناپیوسته
    term = Column(String(32), nullable=True)         # نمونه: ترم یک … ترم هشتم
    term_no = Column(Integer, nullable=True)         # شماره ترم استخراج‌شده از approximate_term
    row_number = Column(Integer, nullable=True)
    course_name = Column(String(200), nullable=False)
    units = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    course_type = Column(String(120), nullable=True)
    unique_course_code = Column(String(32), nullable=True, index=True)
    unique_course_name = Column(String(200), nullable=True)
    year_identified = Column(String(16), nullable=True)
    prerequisite_row_codes = Column(Text, nullable=True)
    corequisite_row_codes = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    synced_at = Column(Integer, nullable=False, default=0)


class ByScheduleHistory(Base):
    """آینهٔ سرویس «سوابق برنامه‌ریزی» — کلاس‌های اجرا‌شده در ترم‌های گذشته"""
    __tablename__ = "by_schedule_history"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, index=True)
    semester = Column(String(16), nullable=False, index=True)  # نمونه: 4021
    semester_label = Column(String(48), nullable=True)          # «سال ۱۴۰۲ ترم ۱»
    faculty_code = Column(String(32), nullable=True)
    faculty_name = Column(String(120), nullable=True)
    department_code = Column(String(32), nullable=True, index=True)
    department_name = Column(String(160), nullable=True)
    level = Column(String(64), nullable=True)
    course_name = Column(String(200), nullable=False, index=True)
    ref_unique_course_title = Column(String(200), nullable=True)
    day = Column(String(16), nullable=True, index=True)
    start_time = Column(String(8), nullable=True)
    end_time = Column(String(8), nullable=True)
    class_code = Column(String(32), nullable=True, index=True)  # کد اتاق برگزاری
    class_name = Column(String(32), nullable=True)
    instructor_code = Column(String(32), nullable=True, index=True)
    instructor_name = Column(String(120), nullable=True)
    max_capacity = Column(Integer, nullable=True)
    exam_date = Column(String(16), nullable=True)
    exam_start_time = Column(String(8), nullable=True)
    exam_end_time = Column(String(8), nullable=True)
    synced_at = Column(Integer, nullable=False, default=0)


class ByRoom(Base):
    """آینهٔ سرویس «کلاس‌ها و اتاق‌های درس»"""
    __tablename__ = "by_rooms"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, index=True)
    code = Column(String(32), nullable=False, index=True)
    name = Column(String(64), nullable=True)
    capacity = Column(Integer, nullable=True)
    place_type = Column(String(64), nullable=True)   # کلاس درس / سایت / سالن
    group_name = Column(String(120), nullable=True)
    room_types = Column(JSON, nullable=True)
    synced_at = Column(Integer, nullable=False, default=0)


class ByInstructor(Base):
    """آینهٔ سرویس «اساتید» برنامه‌یار۳۶۰ — بار تدریس واقعی برای تحلیل‌ها"""
    __tablename__ = "by_instructors"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, index=True)
    code = Column(String(32), nullable=True, index=True)
    name = Column(String(120), nullable=False)
    username = Column(String(64), nullable=True)
    cooperation_type = Column(String(64), nullable=True)
    group_name = Column(String(120), nullable=True)
    max_teaching_units = Column(Integer, nullable=True)
    email = Column(String(120), nullable=True)
    phone = Column(String(32), nullable=True)
    synced_at = Column(Integer, nullable=False, default=0)


class ByOfferedCourse(Base):
    """آینهٔ سرویس «دروس ارائه» — برای تطبیق کاتالوگ و غنی‌سازی دروس مبنای سامانه"""
    __tablename__ = "by_offered_courses"

    id = Column(Integer, primary_key=True)
    external_id = Column(Integer, nullable=False, index=True)
    unique_code = Column(String(32), nullable=True, index=True)
    unique_title = Column(String(200), nullable=True)
    offered_title = Column(String(200), nullable=True)
    course_type = Column(String(64), nullable=True)
    type_course = Column(String(32), nullable=True)
    year = Column(String(16), nullable=True)
    theoretical_hours = Column(Integer, nullable=True)
    practical_hours = Column(Integer, nullable=True)
    prerequisite = Column(String(200), nullable=True)
    corequisite = Column(String(200), nullable=True)
    enrollment_count = Column(Integer, nullable=True)
    demand_prediction = Column(Integer, nullable=True)
    is_active = Column(Integer, nullable=True, default=1)
    synced_at = Column(Integer, nullable=False, default=0)


class BySyncLog(Base):
    """لاگ همگام‌سازی — مبنای نمایش وضعیت «آخرین همگام‌سازی» در داشبورد"""
    __tablename__ = "by_sync_log"

    id = Column(Integer, primary_key=True)
    source = Column(String(32), nullable=False, index=True)   # term_courses / … / all
    status = Column(String(16), nullable=False)               # ok / error / partial
    remote_url = Column(String(200), nullable=True)
    fetched = Column(Integer, nullable=False, default=0)      # رکورد دریافتی از مبدأ
    inserted = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=True)
    started_at = Column(Float, nullable=False, default=0)
    finished_at = Column(Float, nullable=False, default=0)
    duration_ms = Column(Integer, nullable=False, default=0)
