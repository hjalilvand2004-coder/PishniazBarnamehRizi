// یکپارچگی با برنامه‌یار۳۶۰ — وضعیت اتصال، همگام‌سازی برخط، تحلیل دادهٔ واقعی و برنامه‌ریزی اولیه
// قرارداد معماری: مدیریار۳۶۰ مبنای برنامه‌ریزی اولیه؛ برنامه‌یار۳۶۰ مبنای برنامه‌ریزی اجرایی
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { useHttp } from "./http.js";
import { useAuth } from "./auth.jsx";
import { toFa } from "./ui.jsx";
import "./integration.css";

const PALETTE = ["#0e6b63", "#1c5a96", "#d68910", "#c0392b", "#7d3c98", "#148f77", "#2874a6", "#8e44ad"];

const nf = (v, dec = 0) => (v == null || v === "" ? "—" : new Intl.NumberFormat("fa-IR", { maximumFractionDigits: dec }).format(v));

const SOURCES = [
  { key: "term_courses", label: "دروس ترمیک", desc: "کاتالوگ طرح درسی همهٔ مقاطع (سرویس دروس ترمیک)" },
  { key: "schedule_history", label: "سوابق برنامه‌ریزی", desc: "کلاس‌های اجراشدهٔ ترم‌های گذشته با روز/ساعت/اتاق/استاد" },
  { key: "rooms", label: "کلاس‌ها و اتاق‌های درس", desc: "فهرست واقعی اتاق‌ها و سایت‌ها با ظرفیت" },
  { key: "instructors", label: "اساتید", desc: "اساتید واقعی با سقف واحدهای تدریس" },
];

const TABS = [
  { id: "term", label: "دروس ترمیک" },
  { id: "history", label: "سوابق برنامه‌ریزی" },
  { id: "rooms", label: "کلاس‌ها و اتاق‌ها" },
  { id: "instructors", label: "اساتید" },
  { id: "insights", label: "تحلیل دادهٔ واقعی" },
  { id: "plan", label: "برنامه‌ریزی اولیه" },
];

function Dot({ ok }) {
  return <span className={`by-dot ${ok ? "by-dot-ok" : "by-dot-bad"}`} aria-hidden="true" />;
}

function Flash({ flash }) {
  if (!flash) return null;
  return <div className={`by-flash by-flash-${flash.kind}`}>{flash.text}</div>;
}

// ---------------------------------------------------------------------------
// کارت وضعیت اتصال
// ---------------------------------------------------------------------------
function ConnectionCard({ status, onCheck, checking }) {
  const remote = status?.remote;
  const ok = remote?.reachable && remote?.auth;
  return (
    <div className="by-card by-conn">
      <div className="by-conn-head">
        <div className="by-conn-title">
          <Dot ok={ok} />
          <div>
            <div className="by-conn-name">اتصال به برنامه‌یار۳۶۰</div>
            <div className="by-conn-url" dir="ltr">{status?.base_url || "—"}</div>
          </div>
        </div>
        <button type="button" className="by-btn by-btn-light" onClick={onCheck} disabled={checking}>
          {checking ? "در حال بررسی…" : "بررسی اتصال"}
        </button>
      </div>
      <div className="by-conn-body">
        <div className="by-conn-item">
          <span className="by-conn-key">وضعیت سرویس</span>
          <span className="by-conn-val">{remote ? (remote.reachable ? "در دسترس" : "بی‌پاسخ") : "—"}</span>
        </div>
        <div className="by-conn-item">
          <span className="by-conn-key">احراز هویت سامانه‌ای</span>
          <span className="by-conn-val">{remote ? (remote.auth ? "برقرار" : "ناموفق") : "—"}</span>
        </div>
        <div className="by-conn-item">
          <span className="by-conn-key">نسخهٔ برنامه‌یار</span>
          <span className="by-conn-val" dir="ltr">{remote?.version ? toFa(remote.version) : "—"}</span>
        </div>
        {status?.error ? <div className="by-conn-item by-conn-error" title={status.error}><span className="by-conn-key">خطا</span><span className="by-conn-val">{status.error}</span></div> : null}
      </div>
      {remote?.counts?.length ? (
        <div className="by-remote-counts">
          {remote.counts.slice(0, 8).map((c) => (
            <span className="by-remote-chip" key={c.key} title={c.label}>{c.label}: <b>{toFa(c.count)}</b></span>
          ))}
        </div>
      ) : null}
      <p className="by-conn-note">
        نقش سامانه‌ها: <b>مدیریار۳۶۰</b> مبنای برنامه‌ریزی اولیه (تقاضا، ظرفیت، استاد پیشنهادی) و
        <b> برنامه‌یار۳۶۰</b> مبنای برنامه‌ریزی اجرایی (چینش کلاس‌ها، اتاق‌ها و ترم). این صفحه دو سامانه را برخط به هم پیوند می‌دهد.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// کارت همگام‌سازی
// ---------------------------------------------------------------------------
function SyncPanel({ status, onSync, syncing, flash }) {
  const allowed = status?.sync_allowed;
  return (
    <div className="by-card by-sync">
      <div className="by-sync-head">
        <h3 className="by-card-title">همگام‌سازی برخط دادهٔ برنامه‌ریزی</h3>
        {allowed ? (
          <button type="button" className="by-btn by-btn-primary" onClick={() => onSync("all")} disabled={syncing}>
            {syncing ? "در حال همگام‌سازی…" : "همگام‌سازی کامل"}
          </button>
        ) : (
          <span className="by-readonly-hint">اجراهای همگام‌سازی در اختیار ادمین سیستم و مدیرآموزش است؛ شما فقط مشاهده می‌کنید.</span>
        )}
      </div>
      <Flash flash={flash} />
      <div className="by-sync-grid">
        {SOURCES.map((s) => {
          const last = status?.last_syncs?.[s.key];
          const count = status?.local_counts?.[s.key];
          return (
            <div className="by-sync-item" key={s.key}>
              <div className="by-sync-name">{s.label}</div>
              <div className="by-sync-desc">{s.desc}</div>
              <div className="by-sync-meta">
                <span><b>{toFa(count ?? 0)}</b> رکورد محلی</span>
                <span>آخرین همگام‌سازی: {last?.finished_label || "هیچ"}</span>
              </div>
              {allowed ? (
                <button type="button" className="by-btn by-btn-ghost" onClick={() => onSync(s.key)} disabled={syncing}>
                  همگام‌سازی
                </button>
              ) : null}
            </div>
          );
        })}
      </div>
      {status?.last_syncs?._last_error ? (
        <div className="by-flash by-flash-error">
          آخرین خطای همگام‌سازی ({status.last_syncs._last_error.source}): {status.last_syncs._last_error.message}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// جدول‌های دادهٔ آینه
// ---------------------------------------------------------------------------
function DataTable({ columns, rows, emptyText }) {
  if (!rows?.length) return <p className="by-empty">{emptyText || "داده‌ای برای نمایش نیست؛ ابتدا همگام‌سازی کنید."}</p>;
  return (
    <div className="by-table-wrap">
      <table className="by-table">
        <thead>
          <tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key} className={c.tone ? "by-td-" + c.tone : ""}>
                  {c.format === "fa" ? (r[c.key] == null ? "—" : toFa(r[c.key])) : (r[c.key] == null || r[c.key] === "" ? "—" : r[c.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TermCoursesTab() {
  const http = useHttp();
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);

  const load = useCallback(async (query) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      params.set("limit", "80");
      const d = await http.get(`/api/integration/term-courses?${params.toString()}`);
      setData(d);
    } catch (e) {
      setData({ total: 0, items: [], error: e.message });
    } finally {
      setLoading(false);
    }
  }, [http]);

  useEffect(() => { load(""); }, [load]);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!q.trim()) return;
    timerRef.current = setTimeout(() => load(q.trim()), 350);
    return () => clearTimeout(timerRef.current);
  }, [q, load]);

  return (
    <div>
      <div className="by-toolbar">
        <input className="by-input" type="search" placeholder="جستجوی نام درس…" value={q}
          onChange={(e) => setQ(e.target.value)} aria-label="جستجوی درس" />
        <span className="by-toolbar-info">{data ? `${toFa(data.total)} درس ترمیک` : "…"}</span>
      </div>
      {loading ? <p className="by-empty">در حال بارگذاری…</p> : data?.error ? <p className="by-empty">{data.error}</p> : (
        <DataTable
          columns={[
            { key: "course_name", label: "درس" },
            { key: "level", label: "مقطع" },
            { key: "term", label: "ترم" },
            { key: "units", label: "واحد", format: "fa" },
            { key: "capacity", label: "ظرفیت", format: "fa" },
            { key: "course_type", label: "نوع" },
            { key: "unique_course_code", label: "کد یکتا" },
          ]}
          rows={data?.items || []}
        />
      )}
    </div>
  );
}

function HistoryTab() {
  const http = useHttp();
  const [semester, setSemester] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const timerRef = useRef(null);

  const load = useCallback(async (sem, query) => {
    const params = new URLSearchParams();
    if (sem) params.set("semester", sem);
    if (query) params.set("q", query);
    params.set("limit", "80");
    try {
      setData(await http.get(`/api/integration/schedule-history?${params.toString()}`));
    } catch (e) {
      setData({ total: 0, items: [], semesters: [], error: e.message });
    }
  }, [http]);

  useEffect(() => { load("", ""); }, [load]);
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => load(semester, q.trim()), 350);
    return () => clearTimeout(timerRef.current);
  }, [semester, q, load]);

  return (
    <div>
      <div className="by-toolbar">
        <select className="by-input by-select" value={semester} onChange={(e) => setSemester(e.target.value)} aria-label="نیم‌سال">
          <option value="">همهٔ نیم‌سال‌ها</option>
          {(data?.semesters || []).map((s) => <option key={s.code} value={s.code}>{s.label} ({toFa(s.code)})</option>)}
        </select>
        <input className="by-input" type="search" placeholder="جستجوی نام درس…" value={q}
          onChange={(e) => setQ(e.target.value)} aria-label="جستجو در سوابق" />
        <span className="by-toolbar-info">{data ? `${toFa(data.total)} رکورد` : "…"}</span>
      </div>
      <DataTable
        columns={[
          { key: "semester_label", label: "نیم‌سال" },
          { key: "course_name", label: "درس" },
          { key: "day", label: "روز" },
          { key: "start_time", label: "شروع" },
          { key: "end_time", label: "پایان" },
          { key: "class_code", label: "اتاق" },
          { key: "instructor_name", label: "استاد" },
          { key: "max_capacity", label: "ظرفیت", format: "fa" },
          { key: "exam_date", label: "امتحان" },
        ]}
        rows={data?.items || []}
        emptyText="سوابق برنامه‌ریزی هنوز همگام نشده است."
      />
    </div>
  );
}

function RoomsTab() {
  const http = useHttp();
  const [data, setData] = useState(null);
  useEffect(() => {
    http.get("/api/integration/rooms").then(setData).catch((e) => setData({ items: [], error: e.message }));
  }, [http]);
  return (
    <DataTable
      columns={[
        { key: "code", label: "کد" },
        { key: "name", label: "نام" },
        { key: "capacity", label: "ظرفیت", format: "fa" },
        { key: "place_type", label: "نوع مکان" },
        { key: "group", label: "گروه" },
      ]}
      rows={data?.items || []}
      emptyText="فهرست اتاق‌ها هنوز همگام نشده است."
    />
  );
}

function InstructorsTab() {
  const http = useHttp();
  const [data, setData] = useState(null);
  useEffect(() => {
    http.get("/api/integration/instructors").then(setData).catch((e) => setData({ items: [], error: e.message }));
  }, [http]);
  return (
    <DataTable
      columns={[
        { key: "name", label: "نام استاد" },
        { key: "code", label: "کد" },
        { key: "cooperation_type", label: "نوع همکاری" },
        { key: "group", label: "گروه" },
        { key: "max_teaching_units", label: "سقف واحد", format: "fa" },
      ]}
      rows={data?.items || []}
      emptyText="فهرست اساتید هنوز همگام نشده است."
    />
  );
}

// ---------------------------------------------------------------------------
// تحلیل دادهٔ واقعی
// ---------------------------------------------------------------------------
function trimLabel(v) {
  const s = String(v ?? "");
  return s.length > 14 ? s.slice(0, 13) + "…" : s;
}

// عرض صریح به‌جای ResponsiveContainer — در بستر RTL اندازه‌گیری اولیهٔ
// recharts ناپایدار است؛ با ResizeObserver عرض واقعی داده می‌شود
function useChartWidth(fallback = 540) {
  const ref = useRef(null);
  const [width, setWidth] = useState(fallback);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const w = Math.round(e.contentRect.width) - 4;
        if (w > 80) setWidth(w);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

function ChartBox({ chart, height = 300 }) {
  const data = chart.data || [];
  const rotate = data.length > 8;
  const [boxRef, width] = useChartWidth();
  const axes = {
    cartesianGrid: <CartesianGrid strokeDasharray="3 3" stroke="#dbe4ee" />,
    xAxis: <XAxis dataKey={chart.xKey} tick={{ fontSize: 10 }} tickFormatter={trimLabel}
      interval={rotate ? 0 : "auto"} angle={rotate ? -45 : 0} textAnchor={rotate ? "end" : "middle"}
      height={rotate ? 84 : 30} tickMargin={rotate ? 6 : 0} />,
    yAxis: <YAxis tick={{ fontSize: 11 }} width={44} />,
    tooltip: <Tooltip formatter={(v) => nf(v)} />,
    legend: <Legend />,
  };
  return (
    <div className="by-chart">
      <div className="by-chart-title">{chart.title}</div>
      <div className="by-chart-canvas" ref={boxRef}>
        {chart.type === "pie" ? (
          <PieChart width={width} height={height}>
            <Pie data={data} dataKey="value" nameKey={chart.nameKey || "name"} outerRadius={95} innerRadius={42} paddingAngle={2} label={false}>
              {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
            </Pie>
            {axes.tooltip}
            <Legend formatter={trimLabel} />
          </PieChart>
        ) : chart.type === "line" ? (
          <LineChart data={data} width={width} height={height} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
            {axes.cartesianGrid}
            {axes.xAxis}
            {axes.yAxis}
            {axes.tooltip}
            {axes.legend}
            {(chart.yKeys || []).map((k, i) => (
              <Line key={k} type="monotone" dataKey={k} name={(chart.seriesLabels || {})[k] || k}
                stroke={PALETTE[i % PALETTE.length]} strokeWidth={2.4} dot={{ r: 2.5 }} connectNulls />
            ))}
          </LineChart>
        ) : (
          <BarChart data={data} width={width} height={height} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
            {axes.cartesianGrid}
            {axes.xAxis}
            {axes.yAxis}
            {axes.tooltip}
            {axes.legend}
            {(chart.yKeys || []).map((k, i) => (
              <Bar key={k} dataKey={k} name={(chart.seriesLabels || {})[k] || k} fill={PALETTE[i % PALETTE.length]} radius={[3, 3, 0, 0]} />
            ))}
          </BarChart>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// تحلیل دادهٔ واقعی
// ---------------------------------------------------------------------------
function InsightsTab() {
  const http = useHttp();
  const [data, setData] = useState(null);
  useEffect(() => {
    http.get("/api/integration/insights").then(setData).catch((e) => setData({ error: e.message }));
  }, [http]);
  if (!data) return <p className="by-empty">در حال محاسبهٔ تحلیل‌های دادهٔ واقعی…</p>;
  if (data.error) return <p className="by-empty">{data.error}</p>;
  const dq = data.data_quality || {};
  return (
    <div>
      <div className="by-kpi-grid">
        {(data.kpis || []).map((k, i) => (
          <div className="by-kpi" key={i}>
            <div className="by-kpi-label">{k.label}</div>
            <div className="by-kpi-value">{typeof k.value === "number" ? nf(k.value) : k.value}</div>
            {k.hint ? <div className="by-kpi-hint">{k.hint}</div> : null}
          </div>
        ))}
      </div>
      <div className="by-charts">
        {(data.charts || []).map((c) => <ChartBox chart={c} key={c.key} />)}
      </div>
      {data.term_catalog ? (
        <div className="by-charts">
          {data.term_catalog.level_chart ? <ChartBox chart={data.term_catalog.level_chart} /> : null}
          {data.term_catalog.type_chart ? <ChartBox chart={data.term_catalog.type_chart} /> : null}
        </div>
      ) : null}
      {dq.ready ? (
        <div className="by-card by-dq">
          <div className="by-card-title">کیفیت پیوند داده — هشدارهای پاکسازی</div>
          <ul className="by-dq-list">
            <li>{toFa(dq.no_day)} رکورد ({nf(dq.no_day_pct, 1)}٪) بدون روز هفته — برای چینش برنامهٔ هفتگی قابل استفاده نیستند</li>
            <li>{toFa(dq.no_room)} رکورد ({nf(dq.no_room_pct, 1)}٪) بدون کد اتاق — پیوند با فهرست اتاق‌ها ناقص است</li>
            <li>{toFa(dq.no_instructor)} رکورد ({nf(dq.no_instructor_pct, 1)}٪) بدون نام استاد</li>
            {dq.term_unmatched != null ? <li>{toFa(dq.term_unmatched)} درس ترمیک ({nf(dq.term_unmatched_pct, 1)}٪) بدون کد درس یکتا — تطبیق کاتالوگ ناقص است</li> : null}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// برنامه‌ریزی اولیه
// ---------------------------------------------------------------------------
function PlanTab() {
  const http = useHttp();
  const { user } = useAuth();
  const [plan, setPlan] = useState(null);
  const [flash, setFlash] = useState(null);
  const [pushing, setPushing] = useState(false);

  const load = useCallback(() => {
    http.get("/api/integration/initial-plan").then(setPlan).catch((e) => setPlan({ ready: false, reason: e.message }));
  }, [http]);
  useEffect(() => { load(); }, [load]);

  async function push() {
    if (!window.confirm("برنامه‌ریزی اولیه به‌صورت «پیشنهاد دروس» در برنامه‌یار۳۶۰ ثبت می‌شود. ادامه می‌دهید؟")) return;
    setPushing(true);
    setFlash(null);
    try {
      const res = await http.post("/api/integration/initial-plan/push", {});
      setFlash(res.pushed
        ? { kind: "ok", text: `ارسال شد: ${toFa(res.pushed_count)} درس برای نیم‌سال ${toFa(res.remote_term)} در برنامه‌یار۳۶۰ ثبت شد.` }
        : { kind: "error", text: res.reason || "ارسال انجام نشد." });
    } catch (e) {
      setFlash({ kind: "error", text: e.message });
    } finally {
      setPushing(false);
      load();
    }
  }

  if (!plan) return <p className="by-empty">در حال ساخت برنامه‌ریزی اولیه…</p>;
  if (!plan.ready) return <p className="by-empty">{plan.reason || "برنامه‌ریزی اولیه آماده نیست."}</p>;
  const match = plan.remote_match || {};

  return (
    <div>
      <div className="by-plan-head">
        <div>
          <div className="by-plan-term">نیم‌سال هدف: <b>{plan.term?.label}</b> <span className="by-plan-code" dir="ltr">({toFa(plan.term?.code)})</span></div>
          <div className="by-plan-basis">{plan.basis?.demand_definition} · {plan.basis?.instructor_note}</div>
        </div>
        <div className="by-plan-actions">
          <button type="button" className="by-btn by-btn-light" onClick={() => {
            const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = `daneshjo360-initial-plan-${plan.term?.code}.json`;
            a.click();
            URL.revokeObjectURL(a.href);
          }}>دریافت JSON</button>
          {user?.role === "sysadmin" ? (
            <button type="button" className="by-btn by-btn-primary" onClick={push} disabled={pushing}>
              {pushing ? "در حال ارسال…" : "ارسال به برنامه‌یار۳۶۰"}
            </button>
          ) : (
            <span className="by-readonly-hint">ارسال به برنامه‌یار در اختیار ادمین سیستم است.</span>
          )}
        </div>
      </div>
      <Flash flash={flash} />
      {match.matched_count != null ? (
        <div className="by-flash by-flash-info">
          تطبیق با کاتالوگ برنامه‌یار۳۶۰: <b>{toFa(match.matched_count)}</b> درس هم‌نام یافت شد از {toFa(match.remote_offered_count)} درس ارائهٔ برنامه‌یار؛
          {match.unmatched?.length ? ` ${toFa(match.unmatched.length)} درس بدون هم‌نام — فقط درس‌های تطبیق‌شده ارسال می‌شوند.` : " همهٔ دروس قابل ارسال‌اند."}
        </div>
      ) : match.error ? <div className="by-flash by-flash-error">تطبیق با برنامه‌یار ناموفق: {match.error}</div> : null}
      <DataTable
        columns={[
          { key: "course_code", label: "کد" },
          { key: "course_title", label: "درس" },
          { key: "credits", label: "واحد", format: "fa" },
          { key: "expected_demand", label: "تقاضای مورد انتظار", format: "fa" },
          { key: "suggested_capacity_per_section", label: "ظرفیت هر گروه", format: "fa" },
          { key: "suggested_sections", label: "تعداد گروه", format: "fa" },
          { key: "instructor_fa", label: "استاد پیشنهادی" },
        ]}
        rows={(plan.items || []).map((it) => ({ ...it, instructor_fa: it.suggested_instructor?.name || "برای گروه آموزشی" }))}
        emptyText="درسی با سابقهٔ ارائه برای برنامه‌ریزی یافت نشد."
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// پنل «منبع دادهٔ برنامه‌یار۳۶۰» — بخشی از همان داشبورد واحد (نه نرم‌افزار جدا)
// ---------------------------------------------------------------------------
export default function DataSourcePanel() {
  const http = useHttp();
  const [status, setStatus] = useState(null);
  const [tab, setTab] = useState("term");
  const [syncing, setSyncing] = useState(false);
  const [checking, setChecking] = useState(false);
  const [flash, setFlash] = useState(null);
  const autoTried = useRef(false);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await http.get("/api/integration/status"));
    } catch (e) {
      setStatus({ error: e.message, local_counts: {}, last_syncs: {}, sync_allowed: false, push_allowed: false });
    }
  }, [http]);

  useEffect(() => { loadStatus(); }, [loadStatus]);

  // همگام‌سازی خودکار نخستین بار اگر هیچ داده‌ای همگام نشده باشد
  useEffect(() => {
    if (!status || autoTried.current) return;
    autoTried.current = true;
    const counts = status.local_counts || {};
    const empty = Object.values(counts).every((v) => !v);
    if (empty && status.sync_allowed && status.remote?.auth) {
      runSync("all");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  const runSync = useCallback(async (source) => {
    setSyncing(true);
    setFlash({ kind: "info", text: source === "all" ? "همگام‌سازی کامل در حال اجرا…" : "در حال همگام‌سازی…" });
    try {
      const res = await http.post(`/api/integration/sync/${source}`, {});
      const results = res.results || [res];
      const bad = results.filter((r) => r.status !== "ok");
      const rebase = res.rebase;
      const rebaseTxt = rebase?.rebuilt
        ? ` — دیتای مبنا بازسازی شد: ${toFa(rebase.counts?.offerings ?? 0)} گروه کلاس، ${toFa(rebase.counts?.courses ?? 0)} درس، ${toFa(rebase.counts?.instructors ?? 0)} استاد`
        : (rebase?.reason ? ` — بازسازی مبنا: ${rebase.reason}` : "");
      setFlash(bad.length
        ? { kind: "error", text: bad.map((b) => `${b.label || b.source}: ${b.error || "ناموفق"}`).join(" | ") }
        : { kind: "ok", text: `همگام‌سازی انجام شد — ${results.map((r) => `${r.label}: ${toFa(r.inserted)} رکورد`).join("، ")}${rebaseTxt}` });
    } catch (e) {
      setFlash({ kind: "error", text: e.message });
    } finally {
      setSyncing(false);
      loadStatus();
    }
  }, [http, loadStatus]);

  const checkConnection = useCallback(async () => {
    setChecking(true);
    await loadStatus();
    setChecking(false);
  }, [loadStatus]);

  if (!status) return <div className="by-root by-embedded"><p className="by-empty">در حال دریافت وضعیت منبع داده…</p></div>;

  return (
    <div className="by-root by-embedded">
      <header className="by-header">
        <div>
          <h2 className="by-title">منبع دادهٔ برنامه‌یار۳۶۰</h2>
          <p className="by-subtitle">
            همگام‌سازی برخط دروس ترمیک، سوابق برنامه‌ریزی و کلاس‌ها و اتاق‌های درس — و بازسازی خودکار دیتای مبنا و ارسال برنامه‌ریزی اولیه به برنامه‌یار۳۶۰
          </p>
        </div>
      </header>

      <div className="by-two-col">
        <ConnectionCard status={status} onCheck={checkConnection} checking={checking} />
        <SyncPanel status={status} onSync={runSync} syncing={syncing} flash={flash} />
      </div>

      <nav className="by-tabs" aria-label="بخش‌های یکپارچگی">
        {TABS.map((t) => (
          <button key={t.id} type="button" className={`by-tab ${tab === t.id ? "by-tab-active" : ""}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      <div className="by-tab-body">
        {tab === "term" ? <TermCoursesTab /> : null}
        {tab === "history" ? <HistoryTab /> : null}
        {tab === "rooms" ? <RoomsTab /> : null}
        {tab === "instructors" ? <InstructorsTab /> : null}
        {tab === "insights" ? <InsightsTab /> : null}
        {tab === "plan" ? <PlanTab /> : null}
      </div>
    </div>
  );
}
