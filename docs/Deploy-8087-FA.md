# استقرار سامانهٔ دانشجو۳۶۰ روی `http://188.212.96.235:8087/`

**هدف:** بالا آمدن سامانه روی پورت ۸۰۸۷ همان میزبانی که پرتال SSO (پورت ۸۰۸۶)، درسیار۳۶۰ (۸۰۸۲) و برنامه‌یار۳۶۰ (۸۰۸۳) روی آن فعال‌اند.

**وضعیت بررسی‌شده (از بیرون):** پورت‌های 8086/8082/8083 پاسخ می‌دهند؛ **8087 هیچ پاسخی نمی‌دهد** — یعنی باید (۱) پورت باز شود و (۲) سامانه روی آن پورت اجرا شود. هر دو در این نسخه از سورکد تنظیم شده است.

---

## ۱) پورت ۸۰۸۷ در سورکد

| مورد | مقدار جدید |
|---|---|
| اجرای سامانه | `uvicorn app.main:app --host 0.0.0.0 --port 8087` — در `scripts/start.sh`، `scripts/start.bat` و پرتیبل (`RUN-Daneshjo360.bat`) |
| مبدأ عمومی پیش‌فرض | `DANESHJO360_PUBLIC_ORIGIN` = `http://188.212.96.235:8087` — در `backend/app/auth/config.py` |
| redirect_uri پیش‌فرض | `http://188.212.96.235:8087/auth/sso/callback` (مشتق از PUBLIC_ORIGIN) |
| post_logout پیش‌فرض | `http://188.212.96.235:8087/login?logout=1` |
| backchannel logout | `http://188.212.96.235:8087/auth/sso/backchannel` |

اگر روی پرت استقرار تغییر کرد فقط `DANESHJO360_PUBLIC_ORIGIN` (یا از پنل تنظیمات سامانه) را عوض کنید؛ هر سه مقدار مشتق می‌شوند.

## ۲) بازکردن پورت ۸۰۸۷

### سرور لینوکس (بهترین حدس برای میزبان فعلی)
```bash
sudo bash scripts/open-port-8087-linux.sh
```
این اسکریپت فایروال فعال را تشخیص می‌دهد و معادل دستورات زیر را اجرا می‌کند:

```bash
# firewalld (RHEL/CentOS/Alibaba Linux)
sudo firewall-cmd --permanent --add-port=8087/tcp
sudo firewall-cmd --reload

# ufw (Ubuntu/Debian)
sudo ufw allow 8087/tcp

# iptables (در نبود firewalld/ufw)
sudo iptables -A INPUT -p tcp --dport 8087 -j ACCEPT
```

### سرور ویندوز
```bat
netsh advfirewall firewall add rule name="Daneshjo360-8087" dir=in action=allow protocol=TCP localport=8087
```

### گروه امنیتی ابری (حیاتی)
میزبان 188.212.96.235 روی یک سرویس ابری است؛ **علاوه بر فایروال سیستم‌عامل**، در کنسول ابری باید قانون Inbound اضافه شود:
- پروتکل `TCP`، پورت `8087`، مبدأ `0.0.0.0/0` (یا بازهٔ شبکهٔ سازمان)

مشابه همین کار برای 8086/8082/8083 قبلاً انجام شده است.

## ۳) اجرای سامانه روی سرور

### اجرای سریع (مخزن)
```bash
git clone <repo> && cd PishniazBarnamehRizi
bash scripts/start.sh          # نصب وابستگی‌ها + اجرا روی 0.0.0.0:8087
```

### اجرای پایدار با systemd (پیشنهادی)
فایل `/etc/systemd/system/daneshjo360.service`:
```ini
[Unit]
Description=Daneshjo360 (Samane Modiriat Amoozeshi) - port 8087
After=network.target

[Service]
WorkingDirectory=/opt/daneshjo360/server
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8087
Environment=DANESHJO360_DATABASE_URL=sqlite:////opt/daneshjo360/data/daneshjo360.db
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```
سپس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now daneshjo360
```

### پرتیبل ویندوز
`Daneshjo360-Portable-Windows.zip` را روی سرور باز کنید و `RUN-Daneshjo360.bat` را اجرا کنید — اکنون روی `0.0.0.0:8087` بالا می‌آید (در راهنمای داخل بسته هم توضیح داده شده).

## ۴) بررسی صحت

```bash
# از یک سیستم بیرونی:
curl -I http://188.212.96.235:8087/            # باید HTTP 200 برگرداند
curl http://188.212.96.235:8087/api/auth/config
```
سپس در سامانه: **داشبورد → تنظیمات سامانه → راستی‌آزمایی انطباق** — باید سبز شود و مقادیر ثبت کلاینت همان نشانی‌های ۸۰۸۷ را نشان دهد.

## ۵) گام پایانی SSO

مقادیر برگهٔ هماهنگی (docs/SSO-Coordination-FA.md) اکنون به‌صورت پیش‌فرض همین نشانی‌های ۸۰۸۷ هستند؛ به مدیر پرتال بدهید تا کلاینت را ثبت کند — سپس «ورود با حساب سازمانی» فعال می‌شود.
