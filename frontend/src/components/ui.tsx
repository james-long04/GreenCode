import { useState, type ReactNode } from "react";

import { Icon, type IconName } from "./icons";

export const fmt = {
  ms: (v: number | null | undefined, digits = 2) => (v == null ? "–" : `${v.toFixed(digits)} ms`),
  num: (v: number | null | undefined, digits = 2) => (v == null ? "–" : v.toFixed(digits)),
  pct: (v: number | null | undefined, digits = 1) =>
    v == null ? "–" : `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(digits)}%`,
  x: (v: number | null | undefined) => (v == null ? "–" : `${v.toFixed(2)}×`),
  rate: (v: number | null | undefined) => (v == null ? "–" : `${(v * 100).toFixed(0)}%`),
  p: (v: number | null | undefined) => (v == null ? "–" : v < 0.001 ? "p < 0.001" : `p = ${v.toFixed(3)}`),
  joules: (v: number | null | undefined) => {
    if (v == null) return "–";
    if (v < 0.01) return `${(v * 1000).toFixed(2)} mJ`;
    if (v < 1000) return `${v.toFixed(3)} J`;
    return `${(v / 1000).toFixed(2)} kJ`;
  },
  co2: (v: number | null | undefined) => {
    if (v == null) return "–";
    if (v < 0.001) return `${(v * 1e6).toFixed(2)} µg`;
    if (v < 1) return `${(v * 1000).toFixed(3)} mg`;
    return `${v.toFixed(3)} g`;
  },
  date: (s: string | null | undefined) => (s ? new Date(s).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "–"),
  label: (s: string) => s.replace(/_/g, " "),
};

const CONDITION_NAME: Record<string, string> = { greencode: "GreenCode", ai_only: "AI-only", baseline: "Baseline" };

export function Badge({ kind, children, title }: { kind?: string; children: ReactNode; title?: string }) {
  return (
    <span className={`badge ${kind ?? ""}`} title={title}>
      {children}
    </span>
  );
}

export function ConditionLabel({ condition }: { condition: string }) {
  return <Badge kind={condition}>{CONDITION_NAME[condition] ?? condition}</Badge>;
}

/** Page title block. The document title is updated by the caller through useDocumentTitle. */
export function PageHeader({
  title,
  lede,
  meta,
  actions,
}: {
  title: ReactNode;
  lede?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        {lede && <p className="lede">{lede}</p>}
        {meta && <div className="meta">{meta}</div>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </header>
  );
}

export function Section({
  title,
  hint,
  actions,
  children,
  id,
}: {
  title: ReactNode;
  hint?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  return (
    <section aria-labelledby={id ? `${id}-h` : undefined}>
      <div className="section-head">
        <div className="row" style={{ gap: 12, alignItems: "baseline" }}>
          <h2 id={id ? `${id}-h` : undefined}>{title}</h2>
          {hint && <span className="hint">{hint}</span>}
        </div>
        {actions && <div className="row">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

type AlertKind = "error" | "warn" | "info" | "ok";
const ALERT_ICON: Record<AlertKind, IconName> = { error: "x-circle", warn: "warning", info: "info", ok: "check-circle" };

export function Alert({
  kind = "info",
  title,
  children,
  action,
}: {
  kind?: AlertKind;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={`alert ${kind}`} role={kind === "error" ? "alert" : "status"}>
      <Icon name={ALERT_ICON[kind]} className="alert-icon" size={18} />
      <div className="alert-body">
        {title && <div className="alert-title">{title}</div>}
        {children && <div>{children}</div>}
      </div>
      {action}
    </div>
  );
}

/** Backwards-compatible wrapper: renders nothing when there is no error. */
export function ErrorBox({ error, onRetry }: { error: string | null; onRetry?: () => void }) {
  if (!error) return null;
  const offline = /failed to fetch|networkerror|load failed|fetch/i.test(error);
  return (
    <Alert
      kind="error"
      title={offline ? "Can't reach the GreenCode API" : "Something went wrong"}
      action={
        onRetry && (
          <button className="small" onClick={onRetry}>
            Try again
          </button>
        )
      }
    >
      {offline ? (
        <>
          Start the backend (<code>python -m uvicorn app.main:app --port 8000</code> in <code>backend</code>) and check PostgreSQL is running.
        </>
      ) : (
        error
      )}
    </Alert>
  );
}

export function Empty({
  title,
  children,
  action,
}: {
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      {title && <div className="empty-title">{title}</div>}
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function Skeleton({ width = "100%", height = 14 }: { width?: number | string; height?: number | string }) {
  return <span className="skeleton" style={{ width, height }} aria-hidden="true" />;
}

export function LoadingBlock({ label = "Loading", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="stack-sm" role="status" aria-live="polite">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} width={`${92 - i * 14}%`} />
      ))}
    </div>
  );
}

export function Spinner({ size = 16 }: { size?: number }) {
  return <Icon name="circle-notch" size={size} className="spin" />;
}

/** One metric in a flat strip: label, value, note. */
export function Metric({ label, value, note }: { label: ReactNode; value: ReactNode; note?: ReactNode }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {note && <div className="metric-note">{note}</div>}
    </div>
  );
}

const GLOSSARY: Record<string, string> = {
  geomean: "Geometric mean: the right average for ratios, so one big speed-up cannot dominate.",
  "cliffs-delta": "Cliff's delta: effect size from −1 to 1. Near 0 means the two sets of timings overlap heavily.",
  "mann-whitney": "Mann–Whitney U test: compares two sets of timings without assuming a normal distribution.",
  wilcoxon: "Wilcoxon signed-rank test on paired cases, applied to log ratios.",
  fisher: "Fisher's exact test: compares two proportions, such as correctness rates.",
  rapl: "RAPL: the processor's built-in energy counter. Real measurement, machine-wide.",
  lhm: "LibreHardwareMonitor: reads the CPU package power from the processor's RAPL counter through a signed Windows driver. Real measurement, machine-wide, refreshed about once a second.",
  estimated: "Estimated from CPU time and TDP with a documented coefficient model. Not a hardware reading.",
  measured: "Read from hardware energy counters or CodeCarbon, not modelled.",
  derived: "Calculated from a measured value and a documented factor, for example measured joules × the grid carbon factor.",
  co2e: "Grams of CO₂ equivalent, from energy × the grid carbon factor stored for the region.",
};

/** Dotted-underline term with a native tooltip, for jargon that a reader may not know. */
export function Term({ id, children }: { id: keyof typeof GLOSSARY | string; children: ReactNode }) {
  const text = GLOSSARY[id];
  if (!text) return <>{children}</>;
  return (
    <abbr className="glossary" title={text} tabIndex={0} style={{ textDecoration: "none" }}>
      {children}
    </abbr>
  );
}

/** A shell command with a copy button. */
export function Command({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable: the text is selectable anyway */
    }
  };
  return (
    <div className="command">
      <code>{children}</code>
      <button className="small quiet" onClick={() => void copy()} aria-label={`Copy command: ${children}`}>
        {copied ? "Copied" : "Copy"}
      </button>
    </div>
  );
}

/** Table inside a keyboard-scrollable region so wide tables never break the page. */
export function TableWrap({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="table-wrap" role="region" aria-label={label} tabIndex={0}>
      {children}
    </div>
  );
}

/** First-cell link that makes the whole row clickable while staying keyboard accessible. */
export function RowLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <td className="link-cell">
      <a href={href}>{children}</a>
    </td>
  );
}
