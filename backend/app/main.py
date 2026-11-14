# -*- coding: utf-8 -*-
"""سامانه دانشجو۳۶۰ — بک‌اند FastAPI سند معرفی خدمات مدیریت آموزشی دانشگاه

منبع داده: backend/app/data (تک‌منبع حقیقت محتوا)
اجرا:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
import re
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from .analytics.router import router as analytics_router
from .auth.deps import require_authenticated
from .auth.router import router as auth_router
from .auth.sessions import ensure_demo_users
from .db import SessionLocal, init_db
from .integration.router import router as integration_router
from .data.document import (
    BOUNDARY,
    CAPABILITY_TYPES,
    FOOTER_NOTE,
    GOALS,
    INDICATORS,
    INTRO,
    META,
    PREREQUISITES,
    ROADMAP,
    SCENARIO,
    get_document,
)
from .data.services import SERVICES, get_service, get_services

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
STATIC_DIR = BASE_DIR / "static"

APP_VERSION = "2.2.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ایجاد جداول و بارگذاری خودکار داده نمونه در نخستین اجرا
    seeded = init_db()
    if seeded:
        print("دانشجو۳۶۰: پایگاه داده ایجاد و داده نمونه بارگذاری شد.")
    # حساب‌های نمایشی سه نقش (ادمین سیستم، مدیرگروه، مدیرآموزش)
    db = SessionLocal()
    try:
        ensure_demo_users(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="دانشجو۳۶۰ — API سرویس‌های مدیریت آموزشی دانشگاه",
    description="بک‌اند FastAPI با پایگاه داده SQLAlchemy: سند رسمی خدمات + موتور تحلیلی ۱۱ سرویس مدیریت آموزشی",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(integration_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(n) -> str:
    return str(n).translate(FA_DIGITS)


# ---------------------------------------------------------------------------

def service_summary(s: dict) -> dict:
    """خلاصه سرویس برای جدول خدمات."""
    return {
        "id": s["id"],
        "order": s["order"],
        "title": s["title"],
        "extended": s["extended"],
        "audience": s["audience"],
        "priority": s["priority"],
        "prerequisite": s["prerequisite"],
        "capability": s["capability"],
    }


def services_table_rows():
    return [service_summary(s) for s in SERVICES]


def build_document():
    doc = get_document()
    doc["services"] = SERVICES
    doc["services_table"] = {"columns": ["عنوان سرویس", "توضیحات تکمیلی", "جامعه هدف", "اولویت", "پیش‌نیاز", "قابلیت هوشمند"], "rows": services_table_rows()}
    doc["meta"]["counts"] = {
        "services": len(SERVICES),
        "capability_types": len(CAPABILITY_TYPES["items"]),
        "phases": len(ROADMAP["phases"]),
    }
    doc["meta"]["version"] = APP_VERSION
    doc["meta"]["today"] = date.today().isoformat()
    return doc


# ---------------------------------------------------------------------------
#Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "system": META["system"], "version": APP_VERSION}


@app.get("/api/meta")
def meta(user: object = Depends(require_authenticated)):
    doc = build_document()
    return doc["meta"]


@app.get("/api/document")
def document(user: object = Depends(require_authenticated)):
    """سند کامل معرفی خدمات؛ منبع اصلی رندر فرانت‌اند."""
    return build_document()


@app.get("/api/services")
def services(
    audience: Optional[str] = Query(default=None, description="فیلتر جامعه هدف"),
    capability: Optional[str] = Query(default=None, description="فیلتر قابلیت هوشمند"),
    priority: Optional[int] = Query(default=None, ge=1, le=3, description="فیلتر اولویت"),
    q: Optional[str] = Query(default=None, description="جستجوی متنی در عنوان و توضیحات"),
    user: object = Depends(require_authenticated),
):
    result = list(SERVICES)
    if audience:
        result = [s for s in result if s["audience"] == audience]
    if capability:
        result = [s for s in result if s["capability"] == capability]
    if priority is not None:
        result = [s for s in result if s["priority"] == priority]
    if q:
        needle = q.strip()
        result = [
            s for s in result
            if needle in s["title"] or needle in s["summary"] or needle in s["extended"] or needle in s["problem"]
        ]
    return {"count": len(result), "items": [service_summary(s) for s in result]}


@app.get("/api/services/{service_id}")
def service_detail(service_id: str, user: object = Depends(require_authenticated)):
    s = get_service(service_id)
    if s is None:
        raise HTTPException(status_code=404, detail="سرویس مورد نظر یافت نشد.")
    return s


@app.get("/api/search")
def search(q: str = Query(min_length=2, description="عبارت جستجو"),
           user: object = Depends(require_authenticated)):
    """جستجو در سرویس‌ها و بخش‌های سند."""
    needle = q.strip()
    if not needle:
        return {"count": 0, "results": []}

    results = []

    for s in SERVICES:
        hay = " ".join(
            [s["title"], s["summary"], s["extended"], s["problem"], s["capability"], s["audience"], s["prerequisite"]]
            + s["data"] + s["how"] + s["output"] + s["decisions"] + s["limitations"] + [s["example"]]
        )
        idx = hay.find(needle)
        if idx >= 0:
            start = max(0, idx - 60)
            snippet = hay[start: idx + 110].strip()
            results.append({
                "type": "service",
                "title": s["title"],
                "anchor": f"service-{s['id']}",
                "section_title": f"تشریح سرویس‌ها — {s['title']}",
                "snippet": "…" + snippet + "…",
            })

    section_sources = [
        ("sec-intro", INTRO["title"], INTRO["paragraph"]),
        ("sec-goals", GOALS["title"], GOALS["lead"] + " " + " ".join(i["title"] + ": " + i["text"] for i in GOALS["items"])),
        ("sec-capabilities", CAPABILITY_TYPES["title"], CAPABILITY_TYPES["lead"] + " " + " ".join(i["fa"] + " — " + i["desc"] for i in CAPABILITY_TYPES["items"])),
        ("sec-scenario", SCENARIO["title"], SCENARIO["lead"] + " " + " ".join(st["title"] + " " + st["text"] for st in SCENARIO["steps"])),
        ("sec-boundary", BOUNDARY["title"], BOUNDARY["lead"] + " " + " ".join(r["aspect"] + " " + r["services_side"] + " " + r["assistant_side"] for r in BOUNDARY["rows"])),
        ("sec-prereqs", PREREQUISITES["title"], PREREQUISITES["lead"] + " " + " ".join(PREREQUISITES["data"]["items"] + PREREQUISITES["org"]["items"] + PREREQUISITES["validity"]["items"])),
        ("sec-indicators", INDICATORS["title"], INDICATORS["lead"] + " " + " ".join(i["name"] + " " + i["what"] for i in INDICATORS["items"])),
        ("sec-roadmap", ROADMAP["title"], ROADMAP["lead"] + " " + " ".join(p["title"] + " " + p["note"] for p in ROADMAP["phases"])),
    ]
    for anchor, title, text in section_sources:
        idx = text.find(needle)
        if idx >= 0:
            start = max(0, idx - 60)
            snippet = text[start: idx + 110].strip()
            results.append({
                "type": "section",
                "title": title,
                "anchor": anchor,
                "section_title": title,
                "snippet": "…" + snippet + "…",
            })

    return {"count": len(results), "results": results[:20]}


# ---------------------------------------------------------------------------
# خروجی Markdown برای درج در سند معرفی خدمات
# ---------------------------------------------------------------------------

def md_escape_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


@app.get("/api/export/markdown", response_class=PlainTextResponse)
def export_markdown(user: object = Depends(require_authenticated)):
    lines = []
    add = lines.append

    add(f"# {META['category_title']}")
    add("")
    add(f"**سامانه {META['system']} — {META['doc_type']}**")
    add("")
    add(f"_{META['subtitle']}_")
    add("")
    for note in META["scope_notes"]:
        add(f"> {note}")
        add("")

    add(f"## ۱) {INTRO['title']}")
    add("")
    add(INTRO["paragraph"])
    add("")

    add(f"## ۲) {GOALS['title']}")
    add("")
    add(GOALS["lead"])
    add("")
    for i in GOALS["items"]:
        add(f"- **{i['title']}**: {i['text']}")
    add("")
    add(GOALS["closing"])
    add("")

    add("## ۳) جدول خدمات")
    add("")
    cols = ["عنوان سرویس", "توضیحات تکمیلی", "جامعه هدف", "اولویت", "پیش‌نیاز", "قابلیت هوشمند"]
    add("| " + " | ".join(cols) + " |")
    add("|" + "---|" * len(cols))
    for s in SERVICES:
        row = [s["title"], s["extended"], s["audience"], fa_num(s["priority"]), s["prerequisite"], s["capability"]]
        add("| " + " | ".join(md_escape_table(c) for c in row) + " |")
    add("")

    add(f"## ۴) {CAPABILITY_TYPES['title']}")
    add("")
    add(CAPABILITY_TYPES["lead"])
    add("")
    for i, item in enumerate(CAPABILITY_TYPES["items"], 1):
        add(f"{i}. **{item['fa']}** ({item['en']}) — پرسش: «{item['question']}» {item['desc']}")
    add("")
    add(CAPABILITY_TYPES["closing"])
    add("")

    add("## ۵) تشریح سرویس‌ها")
    add("")
    for s in SERVICES:
        add(f"### {fa_num(s['order'])}. {s['title']}")
        add("")
        add(f"*(جامعه هدف: {s['audience']} | اولویت: {fa_num(s['priority'])} | پیش‌نیاز: {s['prerequisite']} | قابلیت: {s['capability']})*")
        add("")
        add(f"**مسئله مدیریتی:** {s['problem']}")
        add("")
        add("**داده‌های مورد نیاز:**")
        for x in s["data"]:
            add(f"- {x}")
        add("")
        add("**نحوه عملکرد (سطح مفهومی):**")
        for x in s["how"]:
            add(f"- {x}")
        add("")
        add("**خروجی قابل استفاده برای مدیر:**")
        for x in s["output"]:
            add(f"- {x}")
        add("")
        add("**تصمیم‌های پشتیبانی‌شده:**")
        for x in s["decisions"]:
            add(f"- {x}")
        add("")
        add(f"**مثال کوتاه فرضی:** {s['example']}")
        add("")
        add("**محدودیت‌ها و شرایط اعتبار:**")
        for x in s["limitations"]:
            add(f"- {x}")
        add("")

    add(f"## ۶) {SCENARIO['title']}")
    add("")
    add(SCENARIO["lead"])
    add("")
    for st in SCENARIO["steps"]:
        add(f"{fa_num(st['order'])}. **{st['title']}** — {st['text']} *(خروجی به گام بعد: {st['output_to_next']})*")
    add("")
    add(SCENARIO["closing"])
    add("")

    add(f"## ۷) {BOUNDARY['title']}")
    add("")
    add(BOUNDARY["lead"])
    add("")
    cols = BOUNDARY["columns"]
    add("| " + " | ".join(cols) + " |")
    add("|" + "---|" * len(cols))
    for r in BOUNDARY["rows"]:
        add("| " + " | ".join(md_escape_table(v) for v in [r["aspect"], r["services_side"], r["assistant_side"]]) + " |")
    add("")
    for p in BOUNDARY["principles"]:
        add(f"- {p}")
    add("")

    add(f"## ۸) {PREREQUISITES['title']}")
    add("")
    add(PREREQUISITES["lead"])
    add("")
    for key in ("data", "org", "validity"):
        add(f"### {PREREQUISITES[key]['label']}")
        add("")
        for x in PREREQUISITES[key]["items"]:
            add(f"- {x}")
        add("")

    add(f"## ۹) {INDICATORS['title']}")
    add("")
    add(INDICATORS["lead"])
    add("")
    for i in INDICATORS["items"]:
        add(f"- **{i['name']}**: {i['what']} *({i['how']})*")
    add("")

    add(f"## ۱۰) {ROADMAP['title']}")
    add("")
    add(ROADMAP["lead"])
    add("")
    for p in ROADMAP["phases"]:
        add(f"### مرحله {fa_num(p['no'])} — {p['title']}")
        add("")
        add(f"**هدف:** {p['goal']}")
        add("")
        titles = []
        for sid in p["service_ids"]:
            s = get_service(sid)
            if s:
                titles.append(s["title"])
        add(f"**سرویس‌های این مرحله:** {'، '.join(titles)}")
        add("")
        add("**وابستگی‌های داده‌ای:**")
        for x in p["data_deps"]:
            add(f"- {x}")
        add("")
        add(f"**توضیح:** {p['note']}")
        add("")
    add("### جدول وابستگی‌های داده‌ای")
    add("")
    cols = ROADMAP["matrix_columns"]
    add("| " + " | ".join(cols) + " |")
    add("|" + "---|" * len(cols))
    for row in ROADMAP["matrix"]:
        add("| " + " | ".join(md_escape_table(c) for c in row) + " |")
    add("")
    add(ROADMAP["priority_note"])
    add("")
    add("---")
    add("")
    add(FOOTER_NOTE)
    add("")

    md = "\n".join(lines)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return PlainTextResponse(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="daneshjo360-em-services.md"'},
    )


# ---------------------------------------------------------------------------
# سرو استاتیک SPA (خروجی build فرانت React) — باید بعد از روت‌های API تعریف شود
# ---------------------------------------------------------------------------

if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    @app.get("/login", include_in_schema=False)
    def login_page():
        """صفحه ورود — همان SPA با مسیر مخصوص ورود (برای بازگشت از SSO)"""
        return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})

    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="spa")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        f = STATIC_DIR / "favicon.ico"
        if f.exists():
            return FileResponse(f)
        raise HTTPException(status_code=404)
