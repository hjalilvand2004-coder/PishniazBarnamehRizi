# دانشجو۳۶۰ — سامانه پشتیبان تصمیم مدیریت آموزشی دانشگاه

نسخه کامل با **بک‌اند FastAPI**، **فرانت‌اند React** و **پایگاه داده SQLAlchemy**
(پیش‌فرض SQLite بدون نیاز به نصب سرویس جانبی؛ قابل اتصال به PostgreSQL/MySQL).

این مخزن دو بخش اصلی دارد که از یک مبدأ سرو می‌شوند:

1. **داشبورد تحلیلی** — موتور اجرایی ۱۱ سرویس مدیریت آموزشی که واقعاً روی پایگاه داده محاسبه می‌کند (KPI، نمودار، جدول، محدودیت‌ها و مرز تصمیم‌گیری).
2. **سند رسمی معرفی خدمات** — سند ۱۰‌بخشی فارسی با جدول خدمات، سناریوی یکپارچه، مرزبندی با دستیار آموزشی دانشجویی، پیش‌نیازها، شاخص‌های موفقیت و فازبندی استقرار.

---

## ۱) امکانات

| # | سرویس | نوع قابلیت | مخاطب |
|---|--------|-------------|--------|
| ۱ | تحلیل تقاضای دروس | Analytics | مدیر آموزشی |
| ۲ | پیش‌بینی ظرفیت کلاس‌ها | Forecasting | مدیر آموزشی |
| ۳ | تحلیل توزیع دانشجویان | BI | مدیر آموزشی / سیاست‌گذار |
| ۴ | تحلیل عملکرد اساتید | Analytics | مدیر آموزشی / رئیس دانشکده |
| ۵ | توصیه استاد برای ارائه درس | Recommender | رئیس دانشکده / گروه آموزشی |
| ۶ | تحلیل عملکرد دانشکده‌ها | BI | مدیر آموزشی / سیاست‌گذار |
| ۷ | تحلیل نرخ مردودی | Analytics | مدیر آموزشی / رئیس دانشکده |
| ۸ | تحلیل هزینه دروس | Cost Modeling | معاون آموزشی / مالی |
| ۹ | بهینه‌سازی نسبت استاد به دانشجو | Optimization | سیاست‌گذار |
| ۱۰ | تحلیل بهره‌وری آموزش | BI | مدیر آموزشی / سیاست‌گذار |
| ۱۱ | شبیه‌سازی افزودن/حذف رشته | Scenario Simulation | مدیر آموزشی / سیاست‌گذار |

ویژگی‌های مشترک همه سرویس‌ها:

* خروجی استاندارد: شاخص‌های کلیدی + نمودار + جدول + **روش محاسبه + محدودیت‌ها + مرز تصمیم‌گیری**
* رعایت اصول اعتبار داده: آستانه کفایت نمونه نظرسنجی، عدم قطعیت پیش‌بینی همراه بازه اطمینان، اعلام داده ناکافی، تفکیک همبستگی از علیت
* حریم خصوصی با طراحی: داده دانشجویان بدون هرگونه مشخصات هویتی و فقط تحلیل تجمیعی

## ۲) معماری

```
frontend (React + Vite + Recharts, RTL فارسی)
        │  build → backend/static
        ▼
FastAPI  ── /api/document, /api/services, /api/export/markdown   (سند رسمی)
         ── /api/analytics/*      (۱۱ موتور تحلیلی)
         ── /api/dashboard/*      (نمای کلی مدیریتی)
         ── /api/catalog/*        (کاتالوگ داده برای فیلترها)
        ▼
SQLAlchemy  →  SQLite (پیش‌فرض) | PostgreSQL | MySQL
```

* فرانت‌اند پس از build به‌صورت SPA از خود FastAPI سرو می‌شود؛ **یک فرمان اجرا، بدون CORS و بدون سرویس جانبی**.
* نسخه build شده از قبل در `backend/static` قرار دارد؛ برای اجرا فقط به Python نیاز دارید.

## ۳) راه‌اندازی سریع

### روش ۱ — فقط Python (توصیه‌شده)

پیش‌نیاز: Python 3.10+

```bash
# لینوکس/مک
bash scripts/start.sh
# ویندوز
scripts\start.bat
```

یا دستی:

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

سپس در مرورگر: **http://127.0.0.1:8000**

* پایگاه داده و داده نمونه در نخستین اجرا **به‌صورت خودکار** ساخته می‌شوند (`daneshjo360.db` کنار فایل اجرا).
* مستندات تعاملی API: http://127.0.0.1:8000/api/docs

### روش ۲ — حالت توسعه فرانت‌اند

پیش‌نیاز اضافه: Node.js 18+

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 با پروکسی /api به پورت ۸۰۰۰
npm run build      # خروجی به backend/static — برای استقرار هم‌مبدأ
```

## ۴) پایگاه داده

* پیش‌فرض: SQLite (`backend/daneshjo360.db` — در `.gitignore` است و ساخته‌شدنش خودکار است).
* اتصال به PostgreSQL یا MySQL با متغیر محیطی:

```bash
export DANESHJO360_DATABASE_URL="postgresql+psycopg://user:pass@host:5432/daneshjo360"
export DANESHJO360_DATABASE_URL="mysql+pymysql://user:pass@host:3306/daneshjo360"
```

* بازتولید داده نمونه: `DANESHJO360_RESEED=1` هنگام اجرا.
* مدل‌ها: دانشکده، رشته، درس، استاد، دانشجو (بدون هویت)، ترم، ارائه درس — در `backend/app/models.py`.
* داده نمونه سینتتیک با seed ثابت (تکرارپذیر): ۵ دانشکده، ۱۰ رشته، ۳۸ درس، ۳۶ استاد، ۶ ترم اخیر و بیش از ۲۲۰ ارائه درس با داده ثبت‌نام، نمره، مردودی، نظرسنجی و محرومیت ثبت‌نام.

> نرخ‌های هزینه (ساعت کلاس، سربار، شهریه) در `backend/app/analytics/base.py` **نمونه**‌اند و باید با نرخ‌های واقعی سازمان جایگزین شوند.

## ۵) ساختار پروژه

```
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py            # FastAPI + lifespan (ساخت DB خودکار)
│   │   ├── db.py              # موتور SQLAlchemy + تنظیم DATABASE URL
│   │   ├── models.py          # ۷ مدل ORM
│   │   ├── seed.py            # داده نمونه سینتتیک تکرارپذیر
│   │   ├── analytics/         # موتور ۱۱ سرویس + router
│   │   └── data/              # تک‌منبع حقیقت محتوای سند رسمی
│   └── static/                # خروجی build فرانت (committed؛ اجرا بدون Node)
├── frontend/
│   ├── package.json           # React 18 + Recharts + Vite
│   ├── vite.config.js         # proxy dev + outDir به backend/static
│   └── src/app/               # داشبورد تحلیلی + سند رسمی (RTL)
├── docs/
│   └── sanad-rasmi.md         # سند رسمی ۱۰‌بخشی (Markdown)
└── scripts/
    ├── start.sh
    └── start.bat
```

## ۶) خلاصه API

| مسیر | توضیح |
|------|--------|
| `GET /api/dashboard/overview` | نمای کلی مدیریتی |
| `GET /api/analytics/demand-analysis` | سرویس ۱ |
| `GET /api/analytics/capacity-forecast` | سرویس ۲ |
| `GET /api/analytics/student-distribution` | سرویس ۳ |
| `GET /api/analytics/instructor-performance` | سرویس ۴ |
| `GET /api/analytics/instructor-recommendation` | سرویس ۵ (پارامتر `course_id` الزامی) |
| `GET /api/analytics/department-performance` | سرویس ۶ |
| `GET /api/analytics/fail-rate` | سرویس ۷ |
| `GET /api/analytics/course-cost` | سرویس ۸ |
| `GET /api/analytics/ratio-optimization` | سرویس ۹ |
| `GET /api/analytics/teaching-efficiency` | سرویس ۱۰ |
| `POST /api/analytics/major-simulation` | سرویس ۱۱ (بدنه JSON) |
| `GET /api/document` | سند رسمی کامل (منبع رندر فرانت) |
| `GET /api/export/markdown` | خروجی Markdown سند |
| `GET /api/catalog/*` | کاتالوگ دانشکده/رشته/درس/استاد/ترم |

## ۷) مرز کاربرد و ملاحظات حاکمیتی

* این سامانه **پشتیبان تصمیم** است و جایگزین صلاحیت حرفه‌ای، مقررات سازمانی و اختیارات قانونی شوراها و مسئولان دانشگاه نیست.
* این سامانه برای **مدیران دانشگاه** است و با «دستیار آموزشی دانشجویی» (راهنمای درس‌گزینی فردی) تفاوت ماهوی دارد؛ جدول تفکیک در سند رسمی (بخش ۷) آمده است.
* داده‌های فعلی **سینتتیک و نمونه** هستند؛ در استقرار واقعی باید منبع داده رسمی سازمان متصل شود.
* تحلیل عملکرد اساتید برای خودارزیابی و پشتیبانی توسعه حرفه‌ای طراحی شده است، نه رتبه‌بندی تنبیهی.

## ۸) مجوز

MIT — متن کامل در [LICENSE](LICENSE).
