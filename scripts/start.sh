#!/usr/bin/env bash
# راه‌اندازی سریع سامانه دانشجو۳۶۰ — بک‌اند FastAPI + فرانت آماده (backend/static)
set -e
cd "$(dirname "$0")/../backend"

if ! command -v python3 >/dev/null 2>&1; then
  echo "خطا: Python 3 نصب نیست." >&2
  exit 1
fi

echo "نصب وابستگی‌ها…"
python3 -m pip install -q -r requirements.txt

echo "اجرای سامانه روی http://0.0.0.0:8087 از همهٔ کارت‌های شبکه (برای توقف: Ctrl+C)"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8087
