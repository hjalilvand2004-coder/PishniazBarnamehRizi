// اپ اصلی سند — طرح‌بندی، ناوبری، جستجو، فیلتر و وضعیت
import { useCallback, useEffect, useRef, useState } from "react";
import { AuthProvider, useAuth } from "./auth.jsx";
import Login from "./Login.jsx";
import { useHttp } from "./http.js";
import { Bullets, Chip, ErrorState, Skeleton, toFa } from "./ui.jsx";
import Dashboard from "./dashboard.jsx";
import IntegrationView from "./integration.jsx";
import {
  BoundarySection,
  CapabilitiesSection,
  DocFooter,
  GoalsSection,
  IndicatorsSection,
  IntroSection,
  PrerequisitesSection,
  RoadmapSection,
  ScenarioSection,
  ServiceDetailsSection,
  ServicesTableSection,
} from "./sections.jsx";

const TOC = [
  { id: "sec-intro", label: "معرفی دسته خدمات" },
  { id: "sec-goals", label: "اهداف و ارزش پیشنهادی" },
  { id: "sec-table", label: "جدول خدمات" },
  { id: "sec-capabilities", label: "راهنمای قابلیت‌ها" },
  { id: "sec-services", label: "تشریح سرویس‌ها" },
  { id: "sec-scenario", label: "سناریوی یکپارچه" },
  { id: "sec-boundary", label: "مرزبندی با دستیار آموزشی" },
  { id: "sec-prereqs", label: "پیش‌نیازهای داده‌ای و سازمانی" },
  { id: "sec-indicators", label: "شاخص‌های موفقیت" },
  { id: "sec-roadmap", label: "اجرای مرحله‌ای" },
];

function scrollToAnchor(anchor) {
  const el = document.getElementById(anchor);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    return true;
  }
  return false;
}

function SearchBox() {
  const http = useHttp();
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    function onDocClick(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const term = q.trim();
    if (term.length < 2) {
      setResults(null);
      setBusy(false);
      return;
    }
    setBusy(true);
    timerRef.current = setTimeout(async () => {
      try {
        const data = await http.get(`/api/search?q=${encodeURIComponent(term)}`);
        setResults(data.results || []);
        setOpen(true);
      } catch {
        setResults([]);
        setOpen(true);
      } finally {
        setBusy(false);
      }
    }, 300);
    return () => clearTimeout(timerRef.current);
  }, [q, http]);

  function go(r) {
    setOpen(false);
    if (r.anchor && r.anchor.startsWith("service-")) {
      const id = r.anchor.replace("service-", "");
      window.dispatchEvent(new CustomEvent("dj-open-service", { detail: id }));
      setTimeout(() => scrollToAnchor(r.anchor), 60);
    } else {
      scrollToAnchor(r.anchor);
    }
  }

  return (
    <div className="dj-search" ref={boxRef}>
      <input
        type="search"
        className="dj-search-input"
        placeholder="جستجو در سند و سرویس‌ها…"
        aria-label="جستجو در سند"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results && results.length > 0 && setOpen(true)}
      />
      {busy ? <span className="dj-search-busy" aria-hidden="true">…</span> : null}
      {open && results ? (
        <div className="dj-search-results" role="listbox" aria-label="نتایج جستجو">
          {results.length === 0 ? (
            <p className="dj-search-empty">نتیجه‌ای یافت نشد.</p>
          ) : (
            results.map((r, i) => (
              <button type="button" className="dj-search-item" key={i} onClick={() => go(r)}>
                <span className="dj-search-item-title">{r.title}</span>
                <span className="dj-search-item-snippet">{r.snippet}</span>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

function Toc({ active }) {
  return (
    <nav className="dj-toc" aria-label="فهرست سند">
      <ol className="dj-toc-list">
        {TOC.map((t, i) => (
          <li key={t.id}>
            <a
              href={`#${t.id}`}
              className={`dj-toc-item ${active === t.id ? "dj-toc-active" : ""}`}
              onClick={(e) => {
                e.preventDefault();
                scrollToAnchor(t.id);
              }}
            >
              <span className="dj-toc-num">{toFa(i + 1)}</span>
              {t.label}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// پوسته احراز هویت — پس از ورود، شروع سامانه روی داشبورد است
// ---------------------------------------------------------------------------

function Splash() {
  return (
    <div className="lg-root lg-splash" dir="rtl">
      <div className="lg-splash-card">
        <div className="lg-logo lg-splash-logo">۳۶۰</div>
        <p>در حال بررسی نشست ورود…</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  );
}

function AuthGate() {
  const { status } = useAuth();
  if (status === "loading") return <Splash />;
  if (status !== "authed") return <Login />;
  return <DocumentApp />;
}

function UserBox({ onLogout, user }) {
  return (
    <div className="dj-userbox">
      <div className="dj-userbox-info">
        <span className="dj-userbox-name">{user?.name}</span>
        <span className="dj-userbox-role">{user?.role_label}</span>
      </div>
      <button type="button" className="dj-btn dj-btn-light dj-btn-logout" onClick={onLogout} title="خروج یکپارچه (نشست مرکز احراز هم بسته می‌شود)">
        خروج
      </button>
    </div>
  );
}

export function DocumentApp() {
  const http = useHttp();
  const { user, logout } = useAuth();
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);
  const [active, setActive] = useState("sec-intro");
  const [view, setView] = useState("dash"); // پس از ورود: شروع روی داشبورد
  const [openIds, setOpenIds] = useState(() => new Set());
  const [filters, setFilters] = useState({ audience: "", capability: "", priority: "" });
  const [filtered, setFiltered] = useState(null);
  const [filtersLoading, setFiltersLoading] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await http.get("/api/document");
      // نقشه قابلیت‌ها (انگلیسی به فارسی و کلید رنگ) یک‌بار هنگام دریافت سند ساخته می‌شود
      const faByEn = {};
      const capKeyByEn = {};
      for (const item of data.capability_types.items) {
        for (const en of item.en.split("/")) {
          const key = en.trim();
          if (key) {
            faByEn[key] = item.fa;
            capKeyByEn[key] = item.key;
          }
        }
      }
      data.meta = { ...data.meta, faByEn, capKeyByEn };
      setDoc(data);
    } catch (e) {
      setError(e.message);
    }
  }, [http]);

  useEffect(() => {
    load();
  }, [load]);

  // فیلترهای جدول خدمات — پرس‌وجوی سمت سرور
  useEffect(() => {
    if (!doc) return;
    const params = new URLSearchParams();
    if (filters.audience) params.set("audience", filters.audience);
    if (filters.capability) params.set("capability", filters.capability);
    if (filters.priority) params.set("priority", filters.priority);
    const qs = params.toString();
    if (!qs) {
      setFiltered(null);
      return;
    }
    let alive = true;
    setFiltersLoading(true);
    http
      .get(`/api/services?${qs}`)
      .then((data) => {
        if (alive) setFiltered({ items: data.items });
      })
      .catch(() => {
        if (alive) setFiltered(null);
      })
      .finally(() => {
        if (alive) setFiltersLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [filters, doc, http]);

  // scroll-spy
  useEffect(() => {
    if (!doc) return;
    const sections = TOC.map((t) => document.getElementById(t.id)).filter(Boolean);
    if (!sections.length) return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id);
        }
      },
      { rootMargin: "-35% 0px -55% 0px", threshold: 0 }
    );
    sections.forEach((s) => obs.observe(s));
    return () => obs.disconnect();
  }, [doc]);

  const openService = useCallback((id) => {
    setOpenIds((prev) => new Set(prev).add(id));
    setTimeout(() => scrollToAnchor(`service-${id}`), 60);
  }, []);

  useEffect(() => {
    function onOpen(e) {
      openService(e.detail);
    }
    window.addEventListener("dj-open-service", onOpen);
    return () => window.removeEventListener("dj-open-service", onOpen);
  }, [openService]);

  function toggle(id) {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (error) {
    return (
      <div className="dj-root dj-root-center">
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }
  if (!doc) {
    return (
      <div className="dj-root">
        <Skeleton />
      </div>
    );
  }

  const { meta } = doc;

  return (
    <div className="dj-root">
      <header className="dj-header">
        <div className="dj-header-inner">
          <div className="dj-brand">
            <div className="dj-logo" aria-hidden="true">۳۶۰</div>
            <div className="dj-brand-text">
              <div className="dj-system-name">سامانه {meta.system} · {meta.doc_type}</div>
              <h1 className="dj-doc-title">{meta.category_title}</h1>
              <p className="dj-doc-subtitle">{meta.subtitle}</p>
            </div>
          </div>
          <div className="dj-header-side">
            <div className="dj-header-stats">
              {view === "doc" ? (
                <>
                  <Chip tone="teal">{toFa(meta.counts.services)} سرویس</Chip>
                  <Chip tone="gold">{toFa(meta.counts.capability_types)} نوع قابلیت</Chip>
                  <Chip tone="moss">{toFa(meta.counts.phases)} مرحله اجرا</Chip>
                </>
              ) : view === "sync" ? (
                <Chip tone="gold">یکپارچگی برخط با برنامه‌یار۳۶۰</Chip>
              ) : (
                <Chip tone="teal">داشبورد تحلیلی روی پایگاه داده</Chip>
              )}
            </div>
            <div className="dj-header-actions">
              <UserBox user={user} onLogout={logout} />
              <button
                type="button"
                className={`dj-btn ${view === "dash" ? "dj-btn-gold" : "dj-btn-primary"}`}
                onClick={() => setView(view === "dash" ? "doc" : "dash")}
                title="موتور ۱۱ سرویس تحلیلی روی پایگاه داده واقعی"
              >
                {view === "dash" ? "بازگشت به سند رسمی" : "داشبورد تحلیلی"}
              </button>
              <button
                type="button"
                className={`dj-btn ${view === "sync" ? "dj-btn-gold" : "dj-btn-light"}`}
                onClick={() => setView(view === "sync" ? "dash" : "sync")}
                title="یکپارچگی برخط با برنامه‌یار۳۶۰ — همگام‌سازی دادهٔ برنامه‌ریزی و ارسال برنامه‌ریزی اولیه"
              >
                {view === "sync" ? "بازگشت از یکپارچگی" : "یکپارچگی با برنامه‌یار"}
              </button>
              {view === "doc" ? (
                <>
                  <button type="button" className="dj-btn dj-btn-light" onClick={() => window.print()}>
                    چاپ / PDF
                  </button>
                  <a className="dj-btn dj-btn-gold" href={http.url("/api/export/markdown")} download="daneshjo360-em-services.md">
                    دریافت Markdown
                  </a>
                </>
              ) : null}
            </div>
          </div>
        </div>
        <div className="dj-header-scope">
          {meta.audiences.map((a) => (
            <span className="dj-audience" key={a}>{a}</span>
          ))}
        </div>
      </header>

      {view === "dash" ? (
        <Dashboard onBack={() => setView("doc")} />
      ) : view === "sync" ? (
        <IntegrationView onBack={() => setView("dash")} />
      ) : (
        <div className="dj-body">
          <aside className="dj-sidebar">
            <SearchBox />
            <Toc active={active} />
            <div className="dj-sidebar-note">
              <div className="dj-note-title">قرارداد سند</div>
              <Bullets items={meta.scope_notes} />
            </div>
          </aside>

          <main className="dj-main" id="dj-main">
            <IntroSection doc={doc} />
            <GoalsSection doc={doc} />
            <ServicesTableSection
              doc={doc}
              filtered={filtered}
              filters={filters}
              setFilters={setFilters}
              loading={filtersLoading}
              onOpenService={openService}
            />
            <CapabilitiesSection doc={doc} />
            <ServiceDetailsSection doc={doc} openIds={openIds} toggle={toggle} setOpenAll={(all) => setOpenIds(all ? new Set(doc.services.map((s) => s.id)) : new Set())} />
            <ScenarioSection doc={doc} onOpen={openService} />
            <BoundarySection doc={doc} />
            <PrerequisitesSection doc={doc} />
            <IndicatorsSection doc={doc} />
            <RoadmapSection doc={doc} onOpen={openService} />
            <DocFooter doc={doc} />
          </main>
        </div>
      )}
    </div>
  );
}
