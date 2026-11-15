#!/usr/bin/env bash
# بازکردن پورت ۸۰۸۷/TCP روی سرور میزبان سامانهٔ مدیریار۳۶۰ (188.212.96.235)
# با root یا sudo اجرا شود:  sudo bash scripts/open-port-8087-linux.sh
# بسته به فایروال فعال، یکی از بخش‌های firewalld / ufw / iptables عمل می‌کند.
set -e

PORT=8087

echo "== تشخیص فایروال فعال =="

if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    echo "firewalld فعال است — بازکردن پورت $PORT/TCP ..."
    firewall-cmd --permanent --add-port=${PORT}/tcp
    firewall-cmd --reload
    if firewall-cmd --list-ports | grep -q "${PORT}/tcp"; then
        echo "OK: پورت ${PORT}/tcp در firewalld باز شد."
    fi
elif command -v ufw >/dev/null 2>&1 && ufw status >/dev/null 2>&1; then
    echo "ufw فعال است — بازکردن پورت $PORT/TCP ..."
    ufw allow "${PORT}/tcp"
    echo "OK: قاعدهٔ ufw برای ${PORT}/tcp ثبت شد."
elif command -v iptables >/dev/null 2>&1; then
    echo "iptables — افزودن قاعدهٔ پذیرش پورت $PORT/TCP ..."
    iptables -C INPUT -p tcp --dport ${PORT} -j ACCEPT 2>/dev/null \
        || iptables -A INPUT -p tcp --dport ${PORT} -j ACCEPT
    echo "OK: قاعدهٔ iptables اعمال شد."
    echo "نکته: برای پایداری پس از ری‌بوت، قواعد را ذخیره کنید:"
    echo "      (RHEL/CentOS) iptables-save > /etc/sysconfig/iptables"
    echo "      (Debian)      netfilter-persistent save"
else
    echo "هیچ فایروال شناخته‌شده‌ای یافت نشد؛ پورت احتمالاً از قبل باز است."
fi

echo
echo "نکتهٔ مهم (سرور ابری): اگر سرور روی یک سرویس ابری است — مانند مورد فعلی —"
echo "علاوه بر فایروال سیستم‌عامل، قانون Inbound برای TCP:${PORT} باید در"
echo "«گروه امنیتی / فایروال کنسول ابری» هم اضافه شود (مثل پورت‌های 8086/8082/8083)."

echo
if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
    echo "✓ سرویسی روی پورت $PORT در حال گوش‌دادن است."
else
    echo "! هنوز هیچ سرویسی روی پورت $PORT گوش نمی‌دهد — سامانه را اجرا کنید:"
    echo "    bash scripts/start.sh        (یا پرتیبل: RUN-ModirYar360.bat)"
    echo "  مستند کامل: docs/Deploy-8087-FA.md"
fi
