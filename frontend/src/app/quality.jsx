// بخش «کیفیت داده» — چک‌های مشخص، امتیاز و توصیه‌های عملی برای همهٔ نقش‌ها
import { useCallback, useEffect, useState } from "react";
import { useHttp } from "./http.js";
import { toFa } from "./ui.jsx";

const SEV_FA = { good: "سالم", info: "اطلاع", warn: "هشدار", bad: "بحرانی" };
const SEV_CLASS = { good: "q-sev-good", info: "q-sev-info", warn: "q-sev-warn", bad: "q-sev-bad" };

const nf = (v) => (v == null ? "—" : new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(v));

export default function QualityPanel() {
  const http = useHttp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [openCat, setOpenCat] = useState(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await http.get("/api/integration/quality"));
    } catch (e) {
      setError(e.message);
    }
  }, [http]);

  useEffect(() => { load(); }, [load]);

  if (error) return <div className="dj2-card dj2-error">{error}</div>;
  if (!data) return <div className="dj2-card dj2-hint">در حال محاسبهٔ کیفیت داده…</div>;

  const sc = data.score || {};
  const cats = sc.categories || [];
  const checks = data.checks || [];
  // چک‌های تازگی: فیلد hours دارند؛ بقیه چک‌های موردی‌اند
  const freshChecks = checks.filter((c) => c.hours != null);
  const itemChecks = checks.filter((c) => c.hours == null);

  const catChecks = (ck) => {
    if (ck === "freshness") return freshChecks;
    if (ck === "courses") return itemChecks.filter((c) => c.key?.startsWith("course"));
    if (ck === "instructors") return itemChecks.filter((c) => c.key?.startsWith("instr"));
    if (ck === "offerings") return itemChecks.filter((c) => c.key?.startsWith("off"));
    return itemChecks.filter((c) => c.key === "src-missing");
  };

  return (
    <div>
      <div className="dj2-head">
        <div>
          <div className="dj2-head-num">سلامت داده</div>
          <h2 className="dj2-head-title">کیفیت دادهٔ سامانه</h2>
          <p className="dj2-head-desc">{data.note}</p>
        </div>
        <button type="button" className="dj2-basis-btn" onClick={load}>محاسبهٔ مجدد</button>
      </div>

      <div className="dj2-kpi-grid">
        {data.kpis.map((k, i) => (
          <div key={i} className={`dj2-kpi ${k.tone ? `dj2-kpi-${k.tone}` : ""}`}>
            <span className="dj2-kpi-label">{k.label}</span>
            <span className="dj2-kpi-value">{k.value != null ? toFa(k.value) : "—"}<small> {k.unit || ""}</small></span>
          </div>
        ))}
      </div>

      <div className="q-score">
        {cats.map((c) => (
          <button
            key={c.key}
            type="button"
            className={`q-cat ${openCat === c.key ? "q-cat-open" : ""}`}
            onClick={() => setOpenCat(openCat === c.key ? null : c.key)}
            title="برای دیدن چک‌های این دسته کلیک کنید"
          >
            <span className="q-cat-label">{c.label}</span>
            <span className="q-cat-bar"><span className="q-cat-fill" style={{ width: `${Math.max(0, Math.min(100, c.score * 100 / c.weight))}%` }} /></span>
            <span className="q-cat-score">{toFa(c.score)} / {toFa(c.weight)}</span>
          </button>
        ))}
      </div>

      {cats.map((c) => openCat === c.key ? (
        <div key={c.key} className="dj2-card q-checks">
          <h4 className="q-checks-title">چک‌های «{c.label}»</h4>
          <table className="q-table">
            <thead><tr><th>بررسی</th><th>مقدار</th><th>وضعیت</th></tr></thead>
            <tbody>
              {catChecks(c.key).map((it) => (
                <tr key={it.key} className={SEV_CLASS[it.severity]}>
                  <td>{it.label}<small className="q-hint">{it.hint}</small></td>
                  <td className="q-val">{nf(it.value)}</td>
                  <td><span className={`q-badge ${SEV_CLASS[it.severity]}`}>{SEV_FA[it.severity]}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null)}

      <div className="dj2-card q-reco">
        <h4 className="q-checks-title">توصیه‌های عملی برای دادهٔ تمیز</h4>
        <ul className="dj2-limit-list">
          {data.recommendations.map((r, i) => <li key={i}>{r}</li>)}
        </ul>
      </div>

      <p className="dj2-foot-note">امتیاز = مجموع دسته‌ها (تازگی ۲۵ + دروس ۲۰ + اساتید ۱۵ + گروه‌های کلاس ۲۵ + کامل‌بودن مبدأ ۱۵)؛ محاسبه در {toFa(data.generated_at || "—")}</p>
    </div>
  );
}
