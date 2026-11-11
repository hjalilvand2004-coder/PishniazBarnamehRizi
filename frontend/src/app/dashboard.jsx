// داشبورد تحلیلی سامانه دانشجو۳۶۰ — موتور ۱۱ سرویس روی پایگاه داده واقعی
import { useCallback, useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { useHttp } from "./http.js";
import { toFa } from "./ui.jsx";
import "./dashboard.css";

const PALETTE = ["#0e6b63", "#1c5a96", "#d68910", "#c0392b", "#7d3c98", "#148f77", "#b9770e", "#2874a6", "#8e44ad", "#117864", "#5d6d7e"];

// ---------------------------------------------------------------------------
// پیکربندی ۱۱ سرویس تحلیلی
// ---------------------------------------------------------------------------
const SERVICES = [
  { id: "demand-analysis", num: 1, title: "تحلیل تقاضای دروس", desc: "روند تقاضا، محرومیت ثبت‌نام و نرخ پرشدن ظرفیت هر درس در ۶ ترم اخیر", endpoint: "/api/analytics/demand-analysis", filters: [{ param: "department_id", label: "دانشکده", source: "departments" }, { param: "course_id", label: "درس", source: "courses" }] },
  { id: "capacity-forecast", num: 2, title: "پیش‌بینی ظرفیت کلاس‌ها", desc: "پیش‌بینی تقاضای نیم‌سال بعد با بازه عدم قطعیت و ظرفیت پیشنهادی", endpoint: "/api/analytics/capacity-forecast", filters: [{ param: "department_id", label: "دانشکده", source: "departments" }, { param: "course_id", label: "درس", source: "courses" }] },
  { id: "student-distribution", num: 3, title: "تحلیل توزیع دانشجویان", desc: "ترکیب جمعیت دانشجویی بر اساس رشته، دانشکده، مقطع، سال ورود و وضعیت", endpoint: "/api/analytics/student-distribution", filters: [{ param: "group_by", label: "گروه‌بندی", options: [{ value: "major", label: "رشته" }, { value: "department", label: "دانشکده" }, { value: "degree", label: "مقطع" }, { value: "entry_year", label: "سال ورود" }, { value: "status", label: "وضعیت تحصیلی" }], default: "major" }, { param: "department_id", label: "دانشکده", source: "departments" }, { param: "status", label: "وضعیت", options: [{ value: "active", label: "فقط فعال" }, { value: "all", label: "همه وضعیت‌ها" }], default: "active" }] },
  { id: "instructor-performance", num: 4, title: "تحلیل عملکرد اساتید", desc: "شاخص‌های تدریس با آستانه کفایت نمونه نظرسنجی و قرائت زمینه‌ای شرایط درس", endpoint: "/api/analytics/instructor-performance", filters: [{ param: "department_id", label: "دانشکده", source: "departments" }, { param: "instructor_id", label: "استاد", source: "instructors" }, { param: "min_sample", label: "حداقل نمونه نظرسنجی", options: [{ value: "10", label: "۱۰ پاسخ" }, { value: "15", label: "۱۵ پاسخ" }, { value: "30", label: "۳۰ پاسخ" }, { value: "50", label: "۵۰ پاسخ" }] }] },
  { id: "instructor-recommendation", num: 5, title: "توصیه استاد برای ارائه درس", desc: "نامزدهای مناسب هر درس بر پایه تخصص، سابقه ارائه و بار آموزشی جاری", endpoint: "/api/analytics/instructor-recommendation", filters: [{ param: "course_id", label: "درس", source: "courses", required: true }] },
  { id: "department-performance", num: 6, title: "تحلیل عملکرد دانشکده‌ها", desc: "شاخص مرکب عملکرد با وزن‌های شفاف و نرمال‌سازی بین دانشکده‌ها", endpoint: "/api/analytics/department-performance", filters: [] },
  { id: "fail-rate", num: 7, title: "تحلیل نرخ مردودی", desc: "شناسایی دروس بحرانی، روند مردودی و آستانه هشدار قابل تنظیم", endpoint: "/api/analytics/fail-rate", filters: [{ param: "department_id", label: "دانشکده", source: "departments" }, { param: "course_id", label: "درس", source: "courses" }, { param: "term_id", label: "ترم", source: "terms" }, { param: "threshold", label: "آستانه هشدار", options: [{ value: "15", label: "۱۵٪" }, { value: "20", label: "۲۰٪" }, { value: "25", label: "۲۵٪" }, { value: "30", label: "۳۰٪" }] }] },
  { id: "course-cost", num: 8, title: "تحلیل هزینه دروس", desc: "هزینه تمام‌شده هر درس و هر دانشجو با نرخ‌های قابل تنظیم", endpoint: "/api/analytics/course-cost", filters: [{ param: "department_id", label: "دانشکده", source: "departments" }, { param: "course_id", label: "درس", source: "courses" }] },
  { id: "ratio-optimization", num: 9, title: "بهینه‌سازی نسبت استاد به دانشجو", desc: "نسبت جاری، نسبت هدف قابل تنظیم و کمبود برآوردی نیروی هیئت علمی", endpoint: "/api/analytics/ratio-optimization", filters: [{ param: "target", label: "نسبت هدف", options: [{ value: "25", label: "۲۵" }, { value: "30", label: "۳۰" }, { value: "35", label: "۳۵" }] }] },
  { id: "teaching-efficiency", num: 10, title: "تحلیل بهره‌وری آموزش", desc: "ساعت-اعتبار دانشجویی به‌ازای هر استاد FTE همراه شاخص مرکب بهره‌وری", endpoint: "/api/analytics/teaching-efficiency", filters: [] },
  { id: "major-simulation", num: 11, title: "شبیه‌سازی افزودن/حذف رشته", desc: "اثر مالی چندساله سناریوهای ایجاد یا انحلال رشته با تحلیل حساسیت", endpoint: "/api/analytics/major-simulation", special: "simulation", filters: [] },
];

const nf = (v, dec = 1) => (v == null || v === "" ? "—" : new Intl.NumberFormat("fa-IR", { maximumFractionDigits: dec }).format(v));

function fmtCell(v, f) {
  if (v == null || v === "") return "—";
  if (f === "int") return nf(v, 0);
  if (f === "float") return nf(v, 1);
  if (f === "pct") return nf(v, 1) + "٪";
  if (f === "pct_signed") return (v > 0 ? "+" : "") + nf(v, 1) + "٪";
  if (f === "money") return nf(v, 0);
  return String(v);
}

// ---------------------------------------------------------------------------
// بلوک‌های نمایشی
// ---------------------------------------------------------------------------
function Kpis({ kpis }) {
  if (!kpis?.length) return null;
  return (
    <div className="dj2-kpi-grid">
      {kpis.map((k, i) => (
        <div className={`dj2-kpi ${k.tone ? "dj2-kpi-" + k.tone : ""}`} key={i}>
          <div className="dj2-kpi-label">{k.label}</div>
          <div className="dj2-kpi-value">
            {typeof k.value === "number" ? nf(k.value) : (k.value ?? "—")}
            {k.unit ? <span className="dj2-kpi-unit">{k.unit}</span> : null}
          </div>
          {k.hint ? <div className="dj2-kpi-hint">{k.hint}</div> : null}
        </div>
      ))}
    </div>
  );
}

function ChartBox({ spec }) {
  const data = spec.data || [];
  return (
    <div className="dj2-card">
      <div className="dj2-card-title">{spec.title}</div>
      <div className="dj2-chart">
        <ResponsiveContainer width="100%" height={300}>
          {spec.type === "line" ? (
            <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
              <XAxis dataKey={spec.xKey} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => nf(v)} />
              <Legend />
              {spec.refLine != null ? (
                <ReferenceLine y={spec.refLine} stroke="#c0392b" strokeDasharray="5 4"
                  label={{ value: spec.refLabel || "", fontSize: 11, fill: "#c0392b" }} />
              ) : null}
              {(spec.yKeys || []).map((k, i) => (
                <Line key={k} type="monotone" dataKey={k} name={(spec.seriesLabels || {})[k] || k}
                  stroke={PALETTE[i % PALETTE.length]} strokeWidth={2.4} dot={{ r: 2.5 }} connectNulls />
              ))}
            </LineChart>
          ) : spec.type === "bar" ? (
            <BarChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
              <XAxis dataKey={spec.xKey} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => nf(v)} />
              <Legend />
              {spec.refLine != null ? (
                <ReferenceLine y={spec.refLine} stroke="#c0392b" strokeDasharray="5 4"
                  label={{ value: spec.refLabel || "", fontSize: 11, fill: "#c0392b" }} />
              ) : null}
              {(spec.yKeys || []).map((k, i) => (
                <Bar key={k} dataKey={k} name={(spec.seriesLabels || {})[k] || k}
                  fill={PALETTE[i % PALETTE.length]} radius={[5, 5, 0, 0]} />
              ))}
            </BarChart>
          ) : spec.type === "pie" ? (
            <PieChart>
              <Tooltip formatter={(v) => nf(v, 0)} />
              <Legend />
              <Pie data={data} dataKey={(spec.yKeys || ["value"])[0]} nameKey={spec.xKey}
                outerRadius={105} innerRadius={45} paddingAngle={2}
                label={(e) => `${e.name} (${toFa(Math.round(e.percent * 100))}٪)`}>
                {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
            </PieChart>
          ) : (
            <ScatterChart margin={{ top: 8, right: 16, left: 4, bottom: 12 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />
              <XAxis dataKey="x" type="number" name={spec.xLabel || ""} tick={{ fontSize: 11 }} label={{ value: spec.xLabel || "", fontSize: 11, position: "insideBottom", offset: -6 }} />
              <YAxis dataKey="y" type="number" name={spec.yLabel || ""} tick={{ fontSize: 11 }} label={{ value: spec.yLabel || "", fontSize: 11, angle: -90, position: "insideLeft" }} />
              <Tooltip cursor={{ strokeDasharray: "4 4" }} formatter={(v) => nf(v)} />
              <Scatter data={data} fill={PALETTE[0]} />
            </ScatterChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function DataTable({ table }) {
  if (!table?.rows?.length) return <div className="dj2-card dj2-empty">داده‌ای برای نمایش وجود ندارد.</div>;
  return (
    <div className="dj2-card">
      <div className="dj2-table-wrap">
        <table className="dj2-table">
          <thead>
            <tr>{table.columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {table.rows.map((r, i) => (
              <tr key={i}>{table.columns.map((c) => <td key={c.key}>{fmtCell(r[c.key], c.format)}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LimitBox({ data }) {
  if (!data) return null;
  return (
    <div className="dj2-card dj2-limit">
      <div className="dj2-limit-title">محدودیت‌ها و مرز تصمیم‌گیری</div>
      {data.method ? <p className="dj2-method"><b>روش محاسبه:</b> {data.method}</p> : null}
      {data.limitations?.length ? (
        <ul className="dj2-limit-list">{data.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      ) : null}
      {data.disclaimer ? <p className="dj2-disclaimer">{data.disclaimer}</p> : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// پنل عمومی سرویس (فیلتر + اجرا + نمودار + جدول)
// ---------------------------------------------------------------------------
function ServicePanel({ svc, catalog }) {
  const http = useHttp();
  const [values, setValues] = useState(() => {
    const init = {};
    (svc.filters || []).forEach((f) => { init[f.param] = f.default ?? ""; });
    return init;
  });
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      (svc.filters || []).forEach((f) => {
        const v = values[f.param];
        if (v !== undefined && v !== "" && v !== null) params.set(f.param, v);
      });
      const qs = params.toString();
      setData(await http.get(`${svc.endpoint}${qs ? "?" + qs : ""}`));
    } catch (e) {
      setError(e.message);
      setData(null);
    } finally {
      setBusy(false);
    }
  }, [http, svc, values]);

  useEffect(() => {
    setData(null);
    setError(null);
    const requiredMissing = (svc.filters || []).some((f) => f.required && !values[f.param]);
    if (!requiredMissing) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [svc.id]);

  const requiredMissing = (svc.filters || []).some((f) => f.required && !values[f.param]);

  return (
    <div>
      <div className="dj2-head">
        <div>
          <div className="dj2-head-num">سرویس {toFa(svc.num)} از {toFa(11)}</div>
          <h2 className="dj2-head-title">{svc.title}</h2>
          <p className="dj2-head-desc">{svc.desc}</p>
        </div>
      </div>

      <div className="dj2-card dj2-filters">
        {(svc.filters || []).map((f) => {
          const options = f.options || (catalog ? catalog[f.source] || [] : []);
          return (
            <label className="dj2-field" key={f.param}>
              <span>{f.label}{f.required ? " (الزامی)" : ""}</span>
              <select value={values[f.param] ?? ""} onChange={(e) => setValues((p) => ({ ...p, [f.param]: e.target.value }))}>
                <option value="">{f.required ? "— انتخاب کنید —" : "همه"}</option>
                {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
          );
        })}
        <button type="button" className="dj2-btn" onClick={run} disabled={busy || requiredMissing}>
          {busy ? "در حال محاسبه…" : "اجرا و به‌روزرسانی"}
        </button>
      </div>

      {requiredMissing ? <div className="dj2-card dj2-hint">برای اجرای این سرویس، ابتدا پارامتر الزامی را از فیلترها انتخاب کنید.</div> : null}
      {error ? <div className="dj2-card dj2-error">{error}</div> : null}

      {data ? (
        <>
          <Kpis kpis={data.kpis} />
          {(data.charts || []).map((c, i) => <ChartBox key={c.key || i} spec={c} />)}
          <DataTable table={data.table} />
          <LimitBox data={data} />
        </>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// پنل شبیه‌سازی افزودن/حذف رشته (فرم اختصاصی)
// ---------------------------------------------------------------------------
function SimulationPanel({ svc, catalog }) {
  const http = useHttp();
  const [form, setForm] = useState({
    action: "add", name: "", department_id: "", degree: "bsc", annual_intake: 80,
    tuition_m: 15, variable_cost_m: 6.5, fixed_setup_m: 2500, fixed_annual_m: 600,
    dropout: 0.08, discount: 0.2, horizon: 5, major_id: "", transition_cost_m: 1200, phase_years: 4,
  });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = {
        action: form.action, degree: form.degree, horizon: Number(form.horizon),
        annual_intake: Number(form.annual_intake), tuition_m: Number(form.tuition_m),
        variable_cost_m: Number(form.variable_cost_m), fixed_setup_m: Number(form.fixed_setup_m),
        fixed_annual_m: Number(form.fixed_annual_m), dropout: Number(form.dropout),
        discount: Number(form.discount), transition_cost_m: Number(form.transition_cost_m),
        phase_years: Number(form.phase_years),
      };
      if (form.action === "add") {
        body.name = form.name || "رشته پیشنهادی";
        if (form.department_id) body.department_id = Number(form.department_id);
      } else {
        if (!form.major_id) throw new Error("انتخاب رشته برای حذف الزامی است.");
        body.major_id = Number(form.major_id);
      }
      setResult(await http.post("/api/analytics/major-simulation", body));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="dj2-head">
        <div>
          <div className="dj2-head-num">سرویس {toFa(svc.num)} از {toFa(11)}</div>
          <h2 className="dj2-head-title">{svc.title}</h2>
          <p className="dj2-head-desc">{svc.desc}</p>
        </div>
      </div>

      <form className="dj2-card dj2-sim-form" onSubmit={submit}>
        <div className="dj2-sim-actions">
          <button type="button" className={`dj2-tab ${form.action === "add" ? "dj2-tab-active" : ""}`} onClick={() => setForm((p) => ({ ...p, action: "add" }))}>افزودن رشته جدید</button>
          <button type="button" className={`dj2-tab ${form.action === "remove" ? "dj2-tab-active" : ""}`} onClick={() => setForm((p) => ({ ...p, action: "remove" }))}>حذف رشته موجود</button>
        </div>

        {form.action === "add" ? (
          <div className="dj2-form-grid">
            <label className="dj2-field"><span>نام رشته پیشنهادی</span><input type="text" value={form.name} onChange={set("name")} placeholder="نمونه: مهندسی داده" /></label>
            <label className="dj2-field"><span>دانشکده</span>
              <select value={form.department_id} onChange={set("department_id")}>
                <option value="">— انتخاب کنید —</option>
                {(catalog?.departments || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label className="dj2-field"><span>مقطع</span>
              <select value={form.degree} onChange={set("degree")}>
                <option value="bsc">کارشناسی</option>
                <option value="msc">کارشناسی ارشد</option>
              </select>
            </label>
            <label className="dj2-field"><span>پذیرش سالانه (نفر)</span><input type="number" min="1" max="1000" value={form.annual_intake} onChange={set("annual_intake")} /></label>
            <label className="dj2-field"><span>شهریه سالانه هر دانشجو (میلیون تومان)</span><input type="number" min="0" step="0.5" value={form.tuition_m} onChange={set("tuition_m")} /></label>
            <label className="dj2-field"><span>هزینه متغیر سالانه هر دانشجو (میلیون تومان)</span><input type="number" min="0" step="0.5" value={form.variable_cost_m} onChange={set("variable_cost_m")} /></label>
            <label className="dj2-field"><span>هزینه راه‌اندازی سال اول (میلیون تومان)</span><input type="number" min="0" value={form.fixed_setup_m} onChange={set("fixed_setup_m")} /></label>
            <label className="dj2-field"><span>هزینه ثابت سالانه رشته (میلیون تومان)</span><input type="number" min="0" value={form.fixed_annual_m} onChange={set("fixed_annual_m")} /></label>
            <label className="dj2-field"><span>نرخ خروج سالانه</span>
              <select value={form.dropout} onChange={set("dropout")}>
                <option value="0.05">۵٪</option><option value="0.08">۸٪</option><option value="0.1">۱۰٪</option><option value="0.15">۱۵٪</option>
              </select>
            </label>
            <label className="dj2-field"><span>نرخ تنزیل (NPV)</span>
              <select value={form.discount} onChange={set("discount")}>
                <option value="0.15">۱۵٪</option><option value="0.2">۲۰٪</option><option value="0.25">۲۵٪</option><option value="0.3">۳۰٪</option>
              </select>
            </label>
          </div>
        ) : (
          <div className="dj2-form-grid">
            <label className="dj2-field"><span>رشته هدف حذف</span>
              <select value={form.major_id} onChange={set("major_id")}>
                <option value="">— انتخاب کنید —</option>
                {(catalog?.majors || []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <label className="dj2-field"><span>شهریه سالانه هر دانشجو (میلیون تومان)</span><input type="number" min="0" step="0.5" value={form.tuition_m} onChange={set("tuition_m")} /></label>
            <label className="dj2-field"><span>هزینه متغیر سالانه هر دانشجو (میلیون تومان)</span><input type="number" min="0" step="0.5" value={form.variable_cost_m} onChange={set("variable_cost_m")} /></label>
            <label className="dj2-field"><span>هزینه ثابت سالانه رشته (میلیون تومان)</span><input type="number" min="0" value={form.fixed_annual_m} onChange={set("fixed_annual_m")} /></label>
            <label className="dj2-field"><span>هزینه انتقال/تعدیل (میلیون تومان)</span><input type="number" min="0" value={form.transition_cost_m} onChange={set("transition_cost_m")} /></label>
            <label className="dj2-field"><span>طول فاز خروج (سال)</span>
              <select value={form.phase_years} onChange={set("phase_years")}>
                <option value="2">۲ سال</option><option value="3">۳ سال</option><option value="4">۴ سال</option><option value="5">۵ سال</option>
              </select>
            </label>
          </div>
        )}

        <button type="submit" className="dj2-btn" disabled={busy}>{busy ? "در حال شبیه‌سازی…" : "اجرای شبیه‌سازی"}</button>
      </form>

      {error ? <div className="dj2-card dj2-error">{error}</div> : null}

      {result ? (
        <>
          {result.extra?.verdict ? <div className="dj2-card dj2-verdict"><b>نتیجه سناریو:</b> {result.extra.verdict}</div> : null}
          {result.extra?.flags?.length ? (
            <div className="dj2-card dj2-warnbox">
              {result.extra.flags.map((f, i) => <div key={i}>• {f}</div>)}
            </div>
          ) : null}
          <Kpis kpis={result.kpis} />
          {(result.charts || []).map((c, i) => <ChartBox key={c.key || i} spec={c} />)}
          <DataTable table={result.table} />
          <LimitBox data={result} />
        </>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// نمای کلی داشبورد
// ---------------------------------------------------------------------------
function Overview({ go }) {
  const http = useHttp();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    http.get("/api/dashboard/overview").then(setData).catch((e) => setError(e.message));
  }, [http]);

  if (error) return <div className="dj2-card dj2-error">{error}</div>;
  if (!data) return <div className="dj2-card dj2-hint">در حال بارگذاری نمای کلی…</div>;

  return (
    <div>
      <div className="dj2-head">
        <div>
          <div className="dj2-head-num">نمای کلی مدیریتی</div>
          <h2 className="dj2-head-title">داشبورد وضعیت آموزش</h2>
          <p className="dj2-head-desc">{data.note}</p>
        </div>
      </div>
      <Kpis kpis={data.kpis} />
      {(data.charts || []).map((c, i) => <ChartBox key={c.key || i} spec={c} />)}
      <DataTable table={data.table} />
      <div className="dj2-quick-title">دسترسی سریع به ۱۱ سرویس تحلیلی</div>
      <div className="dj2-quick-grid">
        {SERVICES.map((s) => (
          <button type="button" className="dj2-quick" key={s.id} onClick={() => go(s.id)}>
            <span className="dj2-quick-num">{toFa(s.num)}</span>
            <span className="dj2-quick-body">
              <span className="dj2-quick-title-item">{s.title}</span>
              <span className="dj2-quick-desc">{s.desc}</span>
            </span>
          </button>
        ))}
      </div>
      <div className="dj2-disclaimer dj2-foot-note">{data.disclaimer}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// داشبورد اصلی
// ---------------------------------------------------------------------------
export default function Dashboard({ onBack }) {
  const http = useHttp();
  const [catalog, setCatalog] = useState(null);
  const [active, setActive] = useState("overview");

  useEffect(() => {
    Promise.all([
      http.get("/api/catalog/departments"),
      http.get("/api/catalog/courses"),
      http.get("/api/catalog/instructors"),
      http.get("/api/catalog/majors"),
      http.get("/api/catalog/terms"),
    ]).then(([d, c, i, m, t]) => {
      setCatalog({
        departments: d.map((x) => ({ value: String(x.id), label: x.name })),
        courses: c.map((x) => ({ value: String(x.id), label: `${x.code} — ${x.title}` })),
        instructors: i.map((x) => ({ value: String(x.id), label: x.name })),
        majors: m.map((x) => ({ value: String(x.id), label: `${x.name} (${x.degree_fa})` })),
        terms: t.map((x) => ({ value: String(x.id), label: x.label })),
      });
    }).catch(() => setCatalog({ departments: [], courses: [], instructors: [], majors: [], terms: [] }));
  }, [http]);

  const svc = SERVICES.find((s) => s.id === active);

  return (
    <div className="dj2-root">
      <aside className="dj2-side">
        <button type="button" className="dj2-brand" onClick={onBack} title="بازگشت به سند رسمی">
          <span className="dj2-logo">۳۶۰</span>
          <span>
            <span className="dj2-brand-name">دانشجو۳۶۰</span>
            <span className="dj2-brand-sub">داشبورد تحلیلی مدیریت آموزشی</span>
          </span>
        </button>
        <nav className="dj2-nav">
          <button type="button" className={`dj2-nav-item ${active === "overview" ? "dj2-nav-active" : ""}`} onClick={() => setActive("overview")}>
            نمای کلی مدیریتی
          </button>
          {SERVICES.map((s) => (
            <button type="button" key={s.id} className={`dj2-nav-item ${active === s.id ? "dj2-nav-active" : ""}`} onClick={() => setActive(s.id)}>
              <span className="dj2-nav-num">{toFa(s.num)}</span>
              {s.title}
            </button>
          ))}
        </nav>
        <div className="dj2-side-foot">
          <button type="button" className="dj2-btn dj2-btn-ghost" onClick={onBack}>بازگشت به سند رسمی</button>
        </div>
      </aside>
      <main className="dj2-main">
        {active === "overview" || !svc ? (
          <Overview go={setActive} />
        ) : svc.special === "simulation" ? (
          <SimulationPanel key={svc.id} svc={svc} catalog={catalog} />
        ) : (
          <ServicePanel key={svc.id} svc={svc} catalog={catalog} />
        )}
      </main>
    </div>
  );
}
