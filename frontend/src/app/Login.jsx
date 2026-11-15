// صفحه ورود سامانه مدیریار۳۶۰ — ورود یکپارچه سازمانی (SSO) + ورود نمایشی برای ارزیابی
import { useState } from "react";
import { ERROR_TEXTS, useAuth } from "./auth.jsx";
import { toFa } from "./ui.jsx";
import "./login.css";

function IconShield() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 3l7 3v5c0 4.6-3 8.6-7 10-4-1.4-7-5.4-7-10V6l7-3z" />
      <path d="M9.5 12l1.8 1.8 3.4-3.6" />
    </svg>
  );
}

function IconOrg() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 19c.7-3 2.9-4.6 5.5-4.6s4.8 1.6 5.5 4.6" />
      <circle cx="17" cy="9.5" r="2.4" />
      <path d="M16 14.6c2.4.1 4 1.4 4.6 3.9" />
    </svg>
  );
}

function IconCap() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2.5 9.5L12 5l9.5 4.5L12 14l-9.5-4.5z" />
      <path d="M6.5 11.5v4c0 1.4 2.5 2.8 5.5 2.8s5.5-1.4 5.5-2.8v-4" />
      <path d="M21 10v4.5" />
    </svg>
  );
}

function IconKey() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8.5" cy="12" r="4.2" />
      <path d="M12.5 12H21" />
      <path d="M17.5 12v3.2" />
      <path d="M20 12v2.3" />
    </svg>
  );
}

const ROLE_ICONS = {
  shield: <IconShield />,
  org: <IconOrg />,
  cap: <IconCap />,
};

function Flash({ flash }) {
  if (!flash) return null;
  if (flash.kind === "no_access") {
    return (
      <div className="lg-alert lg-alert-noaccess" role="alert">
        <b>دسترسی به این سامانه ندارید</b>
        <p>
          حساب سازمانی شما شناسایی شد اما نقش دسترسی به «مدیریار۳۶۰» برای شما ثبت نشده است.
          برای فعال‌سازی دسترسی، از مدیر سامانه بخواهید نقش <code>daneshjo.access</code> را
          در پنل مدیریت کاربرانِ مرکز احراز هویت به شما تخصیص دهد.
        </p>
      </div>
    );
  }
  if (flash.kind === "ok") {
    return <div className="lg-alert lg-alert-ok" role="status">{flash.text}</div>;
  }
  if (flash.kind === "info") {
    return <div className="lg-alert lg-alert-info" role="status">{flash.text}</div>;
  }
  return <div className="lg-alert lg-alert-error" role="alert">{flash.text || ERROR_TEXTS.error}</div>;
}

export default function Login() {
  const { config, flash, loginDemo } = useAuth();
  const [ssoBusy, setSsoBusy] = useState(false);
  const roles = config?.roles || [];

  return (
    <div className="lg-root" dir="rtl">
      <div className="lg-decor" aria-hidden="true">
        <span className="lg-orb lg-orb-a" />
        <span className="lg-orb lg-orb-b" />
        <span className="lg-orb lg-orb-c" />
        <span className="lg-grid" />
      </div>

      <div className="lg-wrap">
        {/* ستون معرفی سامانه */}
        <aside className="lg-hero">
          <div className="lg-hero-badge">
            <IconKey />
            <span>ورود یکپارچه سازمانی بر پایه مرکز احراز هویت دانشجویار۳۶۰</span>
          </div>
          <h2 className="lg-hero-title">
            تصمیم‌های آموزشی بر پایه داده،<br />
            در یک نگاه ۳۶۰ درجه
          </h2>
          <ul className="lg-hero-list">
            <li>
              <span className="lg-hero-num">{toFa(11)}</span>
              <span>سرویس تحلیلی مدیریت آموزشی — از تقاضای دروس تا شبیه‌سازی رشته</span>
            </li>
            <li>
              <span className="lg-hero-num">{toFa(3)}</span>
              <span>نقش مدیریتی — ادمین سیستم، مدیرگروه و مدیرآموزش با دسترسی متمایز</span>
            </li>
            <li>
              <span className="lg-hero-num">SSO</span>
              <span>ورود بدون رمز عبور؛ توکن‌ها فقط سمت سرور نگهداری می‌شوند</span>
            </li>
          </ul>
          <p className="lg-hero-note">
            این سامانه ابزار پشتیبان تصمیم‌گیری است و جایگزین اختیار قانونی و قضاوت
            حرفه‌ای مسئولان دانشگاه نیست.
          </p>
        </aside>

        {/* کارت ورود */}
        <main className="lg-card" aria-label="صفحه ورود سامانه">
          <div className="lg-logo" aria-hidden="true">۳۶۰</div>
          <h1 className="lg-title">مدیریار۳۶۰</h1>
          <p className="lg-subtitle">
            سامانه هوشمند تحلیل و پشتیبانی تصمیم در برنامه‌ریزی آموزشی دانشگاه
          </p>

          <Flash flash={flash} />

          <a
            className={`lg-sso-btn ${ssoBusy ? "lg-sso-busy" : ""}`}
            href="/auth/sso/login"
            onClick={() => setSsoBusy(true)}
            aria-label="ورود با حساب سازمانی"
          >
            <IconKey />
            <span>{ssoBusy ? "در حال انتقال به مرکز احراز هویت…" : "ورود یکپارچه سازمانی (SSO)"}</span>
          </a>
          <p className="lg-sso-note">
            ورود بدون رمز عبور از طریق حساب سازمانی دانشگاه — هیچ رمزی در این سامانه ذخیره نمی‌شود.
          </p>

          {config?.demo_enabled ? (
            <>
              <div className="lg-divider" role="separator">
                <span>یا — ورود نمایشی برای ارزیابی سامانه</span>
              </div>
              <div className="lg-roles">
                {roles.map((r) => (
                  <button type="button" className="lg-role" key={r.id} onClick={() => loginDemo(r.id)}>
                    <span className={`lg-role-icon lg-role-${r.id}`}>{ROLE_ICONS[r.icon] || <IconShield />}</span>
                    <span className="lg-role-body">
                      <span className="lg-role-name">{r.label}</span>
                      <span className="lg-role-desc">{r.desc}</span>
                    </span>
                    <span className="lg-role-count">{toFa(r.services_count)} سرویس</span>
                  </button>
                ))}
              </div>
              <p className="lg-demo-note">
                حساب‌های نمایشی فقط برای بررسی قابلیت‌ها روی داده نمونه‌اند؛ در استقرار رسمی،
                ورود فقط از طریق حساب سازمانی انجام می‌شود.
              </p>
            </>
          ) : (
            <p className="lg-demo-note lg-demo-off">
              حالت نمایشی خاموش است؛ ورود فقط از طریق حساب سازمانی (SSO) انجام می‌شود.
            </p>
          )}

          <footer className="lg-foot">
            <span>نسخه {toFa("2.1.0")}</span>
            <span className="lg-foot-sep">·</span>
            <span>احراز هویت یکپارچه: پرتال دانشجویار۳۶۰ (MahAI.ir)</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
