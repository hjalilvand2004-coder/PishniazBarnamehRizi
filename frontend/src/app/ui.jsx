// کامپوننت‌های پایه رابط — مستقل از هاست
const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

export function toFa(value) {
  return String(value).replace(/[0-9]/g, (d) => FA_DIGITS[Number(d)]);
}

export function Chip({ children, tone = "neutral", title }) {
  return (
    <span className={`dj-chip dj-tone-${tone}`} title={title}>
      {children}
    </span>
  );
}

export function PriorityBadge({ value }) {
  return <span className={`dj-priority dj-priority-${value}`} title={`اولویت ${toFa(value)}`}>{toFa(value)}</span>;
}

export function CapabilityChip({ capability, capKey, capsMeta }) {
  const fa = capsMeta?.faByEn?.[capability] || capability;
  return (
    <Chip tone={capKey || "neutral"} title={capability}>
      {fa}
    </Chip>
  );
}

export function SectionCard({ id, title, lead, children, actions, aside }) {
  return (
    <section className="dj-section" id={id} data-anchor={id}>
      <div className="dj-section-head">
        <div className="dj-section-titles">
          <h2 className="dj-h2">{title}</h2>
          {lead ? <p className="dj-lead">{lead}</p> : null}
        </div>
        {aside ? <div className="dj-section-aside">{aside}</div> : null}
        {actions ? <div className="dj-section-actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function Bullets({ items, ordered = false, tone }) {
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag className={`dj-bullets ${tone ? "dj-bullets-" + tone : ""} ${ordered ? "dj-ordered" : ""}`}>
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </Tag>
  );
}

export function Labeled({ label, children, wide = false, tone }) {
  return (
    <div className={`dj-block ${wide ? "dj-block-wide" : ""} ${tone ? "dj-block-" + tone : ""}`}>
      <div className="dj-block-label">{label}</div>
      {children}
    </div>
  );
}

export function Skeleton() {
  return (
    <div className="dj-loading" role="status" aria-label="در حال بارگذاری">
      <div className="dj-skeleton dj-skel-hero" />
      <div className="dj-skeleton dj-skel-line" />
      <div className="dj-skeleton dj-skel-line" />
      <div className="dj-skel-row">
        <div className="dj-skeleton dj-skel-card" />
        <div className="dj-skeleton dj-skel-card" />
        <div className="dj-skeleton dj-skel-card" />
      </div>
      <p className="dj-loading-text">در حال دریافت سند از سرور…</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="dj-error" role="alert">
      <h3>دریافت سند ناموفق بود</h3>
      <p>{message || "ارتباط با بک‌اند FastAPI برقرار نشد."}</p>
      {onRetry ? (
        <button type="button" className="dj-btn dj-btn-primary" onClick={onRetry}>
          تلاش دوباره
        </button>
      ) : null}
    </div>
  );
}

export function EmptyHint({ children }) {
  return <p className="dj-empty">{children}</p>;
}
