// بخش «تنظیمات سامانه» — فقط ادمین سیستم: ورود یکپارچه (SSO) و اتصال به برنامه‌یار۳۶۰
import { useCallback, useEffect, useState } from "react";
import { useHttp } from "./http.js";
import { toFa } from "./ui.jsx";

const FIELD_ORDER = [
  { key: "barnameh_base_url", title: "اتصال به سامانهٔ برنامه‌یار۳۶۰", test: "barnameh", testLabel: "تست اتصال و ورود" },
  { key: "sso_issuer", title: "ورود یکپارچهٔ سازمانی (SSO)", test: "sso", testLabel: "تست مرکز احراز هویت" },
];

export default function SettingsPanel() {
  const http = useHttp();
  const [values, setValues] = useState(null);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [flash, setFlash] = useState(null);
  const [testing, setTesting] = useState(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const d = await http.get("/api/settings");
      const v = {}, m = {};
      Object.entries(d).forEach(([k, item]) => { v[k] = item.value; m[k] = item; });
      setValues(v);
      setMeta(m);
    } catch (e) {
      setError(e.message);
    }
  }, [http]);

  useEffect(() => { load(); }, [load]);

  if (error) return <div className="dj2-card dj2-error">{error}</div>;
  if (!values || !meta) return <div className="dj2-card dj2-hint">در حال دریافت تنظیمات…</div>;

  const set = (k) => (e) => setValues((p) => ({ ...p, [k]: e.target.value }));

  const save = async (keys) => {
    setSaving(true);
    setFlash(null);
    try {
      const patch = {};
      keys.forEach((k) => { patch[k] = values[k]; });
      const d = await http.put("/api/settings", patch);
      const v = {}, m = {};
      Object.entries(d).forEach(([k, item]) => { v[k] = item.value; m[k] = item; });
      setValues(v);
      setMeta(m);
      setFlash({ kind: "ok", text: "تنظیمات ذخیره و بلافاصله اعمال شد؛ برای به‌روزرسانی کامل آینه، همگام‌سازی مجدد را اجرا کنید." });
    } catch (e) {
      setFlash({ kind: "error", text: e.message });
    } finally {
      setSaving(false);
    }
  };

  const test = async (kind, fieldKey) => {
    setTesting(kind);
    setFlash(null);
    try {
      const body = kind === "barnameh" ? { base_url: values[fieldKey] } : { issuer: values[fieldKey] };
      const d = await http.post(`/api/settings/test/${kind}`, body);
      setFlash({ kind: d.ok ? "ok" : "error", text: d.message + (d.issuer_claim ? ` (issuer سرور: ${toFa(d.issuer_claim)})` : "") });
    } catch (e) {
      setFlash({ kind: "error", text: e.message });
    } finally {
      setTesting(null);
    }
  };

  const group = (fields) => (
    <div className="dj2-card st-card">
      {fields.map(({ key, title, test: testKind, testLabel }) => (
        <div key={key} className="st-group">
          <h4 className="st-title">{title}</h4>
          <label className="dj2-field st-field">
            <span>{meta[key].label} {meta[key].overridden ? <em className="st-over">ذخیره‌شده</em> : <em className="st-def">پیش‌فرض</em>}</span>
            <input type="text" dir="ltr" className="st-input" value={values[key]} onChange={set(key)} />
            <small className="st-hint">{meta[key].hint}</small>
          </label>
          <div className="st-actions">
            <button type="button" className="dj2-tab st-save" disabled={saving} onClick={() => save([key])}>{saving ? "…" : "ذخیره"}</button>
            <button type="button" className="dj2-tab st-test" disabled={testing === testKind} onClick={() => test(testKind, key)}>{testing === testKind ? "در حال تست…" : testLabel}</button>
            {meta[key].overridden ? (
              <button type="button" className="dj2-tab st-reset" onClick={() => { setValues((p) => ({ ...p, [key]: meta[key].default })); save([key]); }}>بازگشت به پیش‌فرض</button>
            ) : null}
          </div>
        </div>
      ))}
      {flash ? <div className={`st-flash ${flash.kind === "ok" ? "st-flash-ok" : "st-flash-err"}`}>{flash.text}</div> : null}
    </div>
  );

  return (
    <div>
      <div className="dj2-head">
        <div>
          <div className="dj2-head-num">مدیریت سامانه</div>
          <h2 className="dj2-head-title">تنظیمات ورود یکپارچه و اتصال‌ها</h2>
          <p className="dj2-head-desc">
            تنظیمات ذخیره‌شده بلافاصله اعمال می‌شود و پس از راه‌اندازی مجدد سامانه هم برقرار می‌ماند؛
            پیش‌فرض‌ها با متغیرهای محیطی DANESHJO360_SSO_* و BARNAMEHYAR_BASE_URL تعیین می‌شوند.
          </p>
        </div>
        <button type="button" className="dj2-basis-btn" onClick={load}>بازخوانی</button>
      </div>

      {group(FIELD_ORDER.filter((f) => f.test === "barnameh"))}
      {group(FIELD_ORDER.filter((f) => f.test === "sso"))}

      <div className="dj2-card st-note">
        <b>راهنمای ورود یکپارچه:</b> نشانی SSO باید دقیقاً برابر issuer ثبت‌شده در سرور مرکز احراز هویت باشد
        (تست اتصال یکسان‌بودن را بررسی می‌کند)؛ آدرس بازگشت (redirect_uri) هم باید کاراکتر به کاراکتر با مقدار
        ثبت‌شده در سرور یکی باشد. پس از تغییر SSO، کاربران باید از صفحه ورود «ورود با حساب سازمانی» را دوباره بزنند.
      </div>
    </div>
  );
}
