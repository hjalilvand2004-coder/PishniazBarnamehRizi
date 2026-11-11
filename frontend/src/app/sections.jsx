// بخش‌های سند معرفی خدمات — همه بخش‌های ده‌گانه ساختار خروجی
import { useMemo } from "react";
import { Bullets, CapabilityChip, Chip, Labeled, PriorityBadge, SectionCard, toFa } from "./ui.jsx";

function serviceTitleById(doc, id) {
  const s = (doc?.services || []).find((x) => x.id === id);
  return s ? s.title : id;
}

function ServiceChips({ ids, doc, capsMeta, onOpen }) {
  if (!ids?.length) return null;
  return (
    <span className="dj-service-chip-row">
      {ids.map((id) => (
        <button
          key={id}
          type="button"
          className="dj-chip dj-tone-teal dj-chip-btn"
          onClick={() => onOpen && onOpen(id)}
          title="رفتن به تشریح این سرویس"
        >
          {serviceTitleById(doc, id)}
        </button>
      ))}
    </span>
  );
}

/* ۱) معرفی دسته خدمات */
export function IntroSection({ doc }) {
  return (
    <SectionCard id="sec-intro" title={doc.intro.title}>
      <p className="dj-paragraph">{doc.intro.paragraph}</p>
      <div className="dj-note-box" role="note">
        <div className="dj-note-title">یادداشت دامنه</div>
        <Bullets items={doc.meta.scope_notes} />
      </div>
    </SectionCard>
  );
}

/* ۲) اهداف و ارزش پیشنهادی */
export function GoalsSection({ doc }) {
  return (
    <SectionCard id="sec-goals" title={doc.goals.title} lead={doc.goals.lead}>
      <div className="dj-goal-grid">
        {doc.goals.items.map((g, i) => (
          <article className="dj-goal-card" key={i}>
            <div className="dj-goal-num">{toFa(i + 1)}</div>
            <h3 className="dj-goal-title">{g.title}</h3>
            <p className="dj-goal-text">{g.text}</p>
          </article>
        ))}
      </div>
      <p className="dj-closing">{doc.goals.closing}</p>
    </SectionCard>
  );
}

/* ۳) جدول خدمات */
export function ServicesTableSection({ doc, filtered, filters, setFilters, loading, onOpenService }) {
  const audiences = useMemo(() => {
    const set = new Set((doc.services || []).map((s) => s.audience));
    return Array.from(set);
  }, [doc.services]);
  const capabilities = useMemo(() => {
    const set = new Set((doc.services || []).map((s) => s.capability));
    return Array.from(set);
  }, [doc.services]);

  const rows = filtered?.items || doc.services_table.rows;
  const hasFilter = filters.audience || filters.capability || filters.priority;

  return (
    <SectionCard
      id="sec-table"
      title="جدول خدمات"
      lead="عنوان، توضیحات تکمیلی، جامعه هدف، اولویت، پیش‌نیاز و قابلیت هوشمند هر یک از یازده سرویس این دسته:"
      aside={<span className="dj-count-pill">{toFa(rows.length)} سرویس</span>}
      actions={
        <div className="dj-filters">
          <label className="dj-filter">
            <span>جامعه هدف</span>
            <select value={filters.audience} onChange={(e) => setFilters({ ...filters, audience: e.target.value })}>
              <option value="">همه</option>
              {audiences.map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </label>
          <label className="dj-filter">
            <span>قابلیت</span>
            <select value={filters.capability} onChange={(e) => setFilters({ ...filters, capability: e.target.value })}>
              <option value="">همه</option>
              {capabilities.map((c) => (
                <option key={c} value={c}>{doc.meta.capFaByEn?.[c] || c}</option>
              ))}
            </select>
          </label>
          <label className="dj-filter">
            <span>اولویت</span>
            <select value={filters.priority} onChange={(e) => setFilters({ ...filters, priority: e.target.value })}>
              <option value="">همه</option>
              <option value="1">۱</option>
              <option value="2">۲</option>
              <option value="3">۳</option>
            </select>
          </label>
          {hasFilter ? (
            <button type="button" className="dj-btn dj-btn-ghost" onClick={() => setFilters({ audience: "", capability: "", priority: "" })}>
              حذف فیلترها
            </button>
          ) : null}
        </div>
      }
    >
      <div className="dj-table-wrap">
        <table className="dj-table">
          <thead>
            <tr>
              {doc.services_table.columns.map((c) => (
                <th key={c} scope="col">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="dj-table-empty">در حال دریافت…</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={6} className="dj-table-empty">سرویسی با این فیلترها یافت نشد.</td></tr>
            ) : (
              rows.map((s) => (
                <tr key={s.id} onClick={() => onOpenService(s.id)} className="dj-row-click" title="رفتن به تشریح سرویس">
                  <th scope="row" className="dj-row-title">{s.title}</th>
                  <td className="dj-row-desc">{s.extended}</td>
                  <td><Chip tone="slate">{s.audience}</Chip></td>
                  <td><PriorityBadge value={s.priority} /></td>
                  <td className="dj-row-prereq">{s.prerequisite}</td>
                  <td><CapabilityChip capability={s.capability} capKey={doc.meta.capKeyByEn?.[s.capability]} capsMeta={doc.meta} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="dj-table-hint">برای مشاهده تشریح کامل هر سرویس، روی ردیف آن کلیک کنید.</p>
    </SectionCard>
  );
}

/* راهنمای قابلیت‌ها */
export function CapabilitiesSection({ doc }) {
  return (
    <SectionCard id="sec-capabilities" title={doc.capability_types.title} lead={doc.capability_types.lead}>
      <div className="dj-cap-grid">
        {doc.capability_types.items.map((c) => (
          <article className={`dj-cap-card dj-cap-${c.key}`} key={c.key}>
            <div className="dj-cap-head">
              <h3 className="dj-cap-fa">{c.fa}</h3>
              <span className="dj-cap-en">{c.en}</span>
            </div>
            <p className="dj-cap-question">«{c.question}»</p>
            <p className="dj-cap-desc">{c.desc}</p>
            <div className="dj-cap-services">
              {c.service_ids.map((id) => (
                <span className="dj-cap-service" key={id}>{serviceTitleById(doc, id)}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
      <p className="dj-closing">{doc.capability_types.closing}</p>
    </SectionCard>
  );
}

/* ۵) تشریح سرویس‌ها */
export function ServiceDetailsSection({ doc, openIds, toggle, setOpenAll }) {
  const allOpen = openIds.size === doc.services.length;
  return (
    <SectionCard
      id="sec-services"
      title="تشریح سرویس‌ها"
      lead="برای هر سرویس، مسئله مدیریتی، داده‌های مورد نیاز، نحوه عملکرد، خروجی، تصمیم‌های پشتیبانی‌شده، مثال فرضی و محدودیت‌های اعتبار آمده است."
      actions={
        <button type="button" className="dj-btn dj-btn-ghost" onClick={() => setOpenAll(!allOpen)}>
          {allOpen ? "بستن همه" : "بازکردن همه"}
        </button>
      }
    >
      <div className="dj-services">
        {doc.services.map((s) => {
          const open = openIds.has(s.id);
          return (
            <article className={`dj-service ${open ? "dj-open" : ""}`} id={`service-${s.id}`} key={s.id}>
              <button
                type="button"
                className="dj-service-head"
                aria-expanded={open}
                onClick={() => toggle(s.id)}
              >
                <span className="dj-service-num">{toFa(s.order)}</span>
                <span className="dj-service-name">
                  <span className="dj-service-title">{s.title}</span>
                  <span className="dj-service-summary">{s.summary}</span>
                </span>
                <span className="dj-service-meta">
                  <Chip tone="slate">{s.audience}</Chip>
                  <PriorityBadge value={s.priority} />
                  <CapabilityChip capability={s.capability} capKey={doc.meta.capKeyByEn?.[s.capability]} capsMeta={doc.meta} />
                  <span className={`dj-caret ${open ? "dj-caret-open" : ""}`} aria-hidden="true">▾</span>
                </span>
              </button>
              <div className={`dj-service-body ${open ? "" : "dj-collapsed"}`}>
                <div className="dj-service-prereq">پیش‌نیاز: <strong>{s.prerequisite}</strong></div>
                <div className="dj-service-grid">
                  <Labeled label="مسئله مدیریتی که حل می‌کند" wide>
                    <p className="dj-paragraph dj-paragraph-tight">{s.problem}</p>
                  </Labeled>
                  <Labeled label="داده‌های مورد نیاز">
                    <Bullets items={s.data} />
                  </Labeled>
                  <Labeled label="نحوه عملکرد در سطح مفهومی">
                    <Bullets items={s.how} ordered />
                  </Labeled>
                  <Labeled label="خروجی قابل استفاده برای مدیر">
                    <Bullets items={s.output} />
                  </Labeled>
                  <Labeled label="تصمیم‌هایی که پشتیبانی می‌کند">
                    <Bullets items={s.decisions} />
                  </Labeled>
                  <Labeled label="مثال کوتاه فرضی از کاربرد" wide tone="example">
                    <p className="dj-example">{s.example}</p>
                  </Labeled>
                  <Labeled label="محدودیت‌ها و شرایط اعتبار نتیجه" wide tone="limit">
                    <Bullets items={s.limitations} tone="warn" />
                  </Labeled>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </SectionCard>
  );
}

/* ۶) سناریوی یکپارچه */
export function ScenarioSection({ doc, onOpen }) {
  return (
    <SectionCard id="sec-scenario" title={doc.scenario.title} lead={doc.scenario.lead}>
      <ol className="dj-timeline">
        {doc.scenario.steps.map((st) => (
          <li className="dj-step" key={st.order}>
            <div className="dj-step-num">{toFa(st.order)}</div>
            <div className="dj-step-card">
              <h3 className="dj-step-title">{st.title}</h3>
              <p className="dj-step-text">{st.text}</p>
              <div className="dj-step-foot">
                <ServiceChips ids={st.service_ids} doc={doc} onOpen={onOpen} />
              </div>
              <div className="dj-step-output">
                <span className="dj-step-output-label">خروجی به گام بعد:</span> {st.output_to_next}
              </div>
            </div>
          </li>
        ))}
      </ol>
      <p className="dj-closing">{doc.scenario.closing}</p>
    </SectionCard>
  );
}

/* ۷) جدول مرزبندی */
export function BoundarySection({ doc }) {
  return (
    <SectionCard id="sec-boundary" title={doc.boundary.title} lead={doc.boundary.lead}>
      <div className="dj-table-wrap">
        <table className="dj-table dj-table-boundary">
          <thead>
            <tr>
              <th scope="col">{doc.boundary.columns[0]}</th>
              <th scope="col" className="dj-col-services">{doc.boundary.columns[1]}</th>
              <th scope="col" className="dj-col-assistant">{doc.boundary.columns[2]}</th>
            </tr>
          </thead>
          <tbody>
            {doc.boundary.rows.map((r, i) => (
              <tr key={i}>
                <th scope="row" className="dj-row-title">{r.aspect}</th>
                <td className="dj-cell-services">{r.services_side}</td>
                <td className="dj-cell-assistant">{r.assistant_side}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="dj-note-box dj-note-principles">
        <div className="dj-note-title">اصول حاکم بر مرزبندی</div>
        <Bullets items={doc.boundary.principles} />
      </div>
    </SectionCard>
  );
}

/* ۸) پیش‌نیازها */
export function PrerequisitesSection({ doc }) {
  const p = doc.prerequisites;
  return (
    <SectionCard id="sec-prereqs" title={p.title} lead={p.lead}>
      <div className="dj-prereq-grid">
        <div className="dj-prereq-card">
          <h3>{p.data.label}</h3>
          <Bullets items={p.data.items} />
        </div>
        <div className="dj-prereq-card">
          <h3>{p.org.label}</h3>
          <Bullets items={p.org.items} />
        </div>
      </div>
      <div className="dj-prereq-card dj-prereq-validity">
        <h3>{p.validity.label}</h3>
        <Bullets items={p.validity.items} />
      </div>
    </SectionCard>
  );
}

/* ۹) شاخص‌های موفقیت */
export function IndicatorsSection({ doc }) {
  return (
    <SectionCard id="sec-indicators" title={doc.indicators.title} lead={doc.indicators.lead}>
      <div className="dj-indicator-list">
        {doc.indicators.items.map((k, i) => (
          <article className="dj-indicator" key={i}>
            <h3 className="dj-indicator-name">
              <span className="dj-indicator-dot" aria-hidden="true" />
              {k.name}
            </h3>
            <p className="dj-indicator-what">{k.what}</p>
            <p className="dj-indicator-how">نحوه سنجش: {k.how}</p>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}

/* ۱۰) اجرای مرحله‌ای */
export function RoadmapSection({ doc, onOpen }) {
  return (
    <SectionCard id="sec-roadmap" title={doc.roadmap.title} lead={doc.roadmap.lead}>
      <div className="dj-phases">
        {doc.roadmap.phases.map((p) => (
          <article className="dj-phase" key={p.no}>
            <div className="dj-phase-head">
              <span className="dj-phase-num">مرحله {toFa(p.no)}</span>
              <h3 className="dj-phase-title">{p.title}</h3>
            </div>
            <p className="dj-phase-goal">{p.goal}</p>
            <div className="dj-phase-services">
              {p.service_ids.map((id) => (
                <button key={id} type="button" className="dj-chip dj-tone-teal dj-chip-btn" onClick={() => onOpen(id)}>
                  {serviceTitleById(doc, id)}
                </button>
              ))}
            </div>
            <div className="dj-phase-deps">
              <span className="dj-block-label">وابستگی‌های داده‌ای</span>
              <Bullets items={p.data_deps} />
            </div>
            <p className="dj-phase-note">{p.note}</p>
          </article>
        ))}
      </div>

      <h3 className="dj-subtitle">جدول وابستگی‌های داده‌ای</h3>
      <div className="dj-table-wrap">
        <table className="dj-table">
          <thead>
            <tr>
              {doc.roadmap.matrix_columns.map((c) => (
                <th key={c} scope="col">{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {doc.roadmap.matrix.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j} className={j === 0 ? "dj-row-title" : ""}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="dj-closing">{doc.roadmap.priority_note}</p>
    </SectionCard>
  );
}

/* پانوشت */
export function DocFooter({ doc }) {
  return (
    <footer className="dj-footer">
      <p>{doc.footer_note}</p>
      <p className="dj-footer-meta">
        سامانه {doc.meta.system} · نسخه سند {toFa(doc.meta.version)} · دسته {doc.meta.category_title}
      </p>
    </footer>
  );
}
