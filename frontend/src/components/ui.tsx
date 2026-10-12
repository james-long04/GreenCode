import type { ReactNode } from "react";

export const fmt = {
  ms: (v: number | null | undefined, digits = 2) => (v == null ? "–" : `${v.toFixed(digits)} ms`),
  num: (v: number | null | undefined, digits = 2) => (v == null ? "–" : v.toFixed(digits)),
  pct: (v: number | null | undefined, digits = 1) =>
    v == null ? "–" : `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`,
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
  date: (s: string | null | undefined) => (s ? new Date(s).toLocaleString() : "–"),
};

export function Badge({ kind, children }: { kind?: string; children: ReactNode }) {
  return <span className={`badge ${kind ?? ""}`}>{children}</span>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  return error ? <div className="error">{error}</div> : null;
}

export function ConditionLabel({ condition }: { condition: string }) {
  return <Badge kind={condition}>{condition === "greencode" ? "GreenCode" : condition === "ai_only" ? "AI-only" : condition}</Badge>;
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="muted" style={{ padding: "18px 0", textAlign: "center" }}>
      {children}
    </div>
  );
}
