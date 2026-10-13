/**
 * Small dependency-free SVG charts. Keeping these in-house avoids a charting
 * library and keeps the dashboard build tiny and deterministic.
 *
 * Colours come from CSS variables so both themes work, every mark is labelled
 * directly (no colour-only encoding), and each chart exposes a text summary to
 * assistive technology.
 */

const FILL = {
  original: "var(--c-original)",
  candidate: "var(--c-gc)",
  ai_only: "var(--c-ai)",
  greencode: "var(--c-gc)",
} as const;

type SeriesKey = keyof typeof FILL;

const nice = (v: number) => (v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2));

export function PairedBars({
  rows,
  unit = "",
  height = 200,
  title,
}: {
  rows: { label: string; original: number | null; candidate: number | null }[];
  unit?: string;
  height?: number;
  title: string;
}) {
  const width = 520;
  const padL = 44;
  const padB = 28;
  const max = Math.max(1e-9, ...rows.flatMap((r) => [r.original ?? 0, r.candidate ?? 0]));
  const groupW = (width - padL - 10) / Math.max(rows.length, 1);
  const barW = Math.min(36, groupW / 2.8);
  const scaleY = (v: number) => height - padB - (v / max) * (height - padB - 22);
  const ticks = 4;
  const summary = rows
    .map((r) => `${r.label}: original ${r.original == null ? "n/a" : nice(r.original)}, candidate ${r.candidate == null ? "n/a" : nice(r.candidate)}`)
    .join("; ");
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${summary}`}>
      {Array.from({ length: ticks + 1 }).map((_, i) => {
        const v = (max / ticks) * i;
        const y = scaleY(v);
        return (
          <g key={i}>
            <line className="grid-line" x1={padL} x2={width - 10} y1={y} y2={y} />
            <text x={padL - 6} y={y + 4} textAnchor="end">
              {nice(v)}
            </text>
          </g>
        );
      })}
      {rows.map((r, i) => {
        const cx = padL + groupW * i + groupW / 2;
        return (
          <g key={r.label}>
            {r.original != null && (
              <g>
                <rect x={cx - barW - 2} y={scaleY(r.original)} width={barW} height={Math.max(0, height - padB - scaleY(r.original))} style={{ fill: FILL.original }} rx={3}>
                  <title>
                    {r.label}, original: {r.original.toFixed(3)} {unit}
                  </title>
                </rect>
                <text x={cx - barW / 2 - 2} y={scaleY(r.original) - 5} textAnchor="middle">
                  {nice(r.original)}
                </text>
              </g>
            )}
            {r.candidate != null && (
              <g>
                <rect x={cx + 2} y={scaleY(r.candidate)} width={barW} height={Math.max(0, height - padB - scaleY(r.candidate))} style={{ fill: FILL.candidate }} rx={3}>
                  <title>
                    {r.label}, candidate: {r.candidate.toFixed(3)} {unit}
                  </title>
                </rect>
                <text x={cx + barW / 2 + 2} y={scaleY(r.candidate) - 5} textAnchor="middle">
                  {nice(r.candidate)}
                </text>
              </g>
            )}
            <text className="strong" x={cx} y={height - 8} textAnchor="middle">
              {r.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Strip/dot plot of raw timing samples for two variants, with the median marked. */
export function SamplesPlot({ original, candidate }: { original: number[]; candidate: number[] }) {
  const width = 520;
  const height = 132;
  const padL = 74;
  const all = [...original, ...candidate];
  if (!all.length) return null;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const x = (v: number) => padL + ((v - min) / span) * (width - padL - 20);
  const median = (xs: number[]) => {
    const s = [...xs].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const rowsDef: [string, number[], SeriesKey, number][] = [
    ["Original", original, "original", 42],
    ["Candidate", candidate, "candidate", 90],
  ];
  const summary = rowsDef.map(([label, xs]) => `${label}: ${xs.length} samples, median ${median(xs).toFixed(3)} ms`).join("; ");
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Timing samples in milliseconds. ${summary}`}>
      {rowsDef.map(([label, xs, key, y]) => (
        <g key={label}>
          <text className="strong" x={padL - 10} y={y + 4} textAnchor="end">
            {label}
          </text>
          <line className="grid-line" x1={padL} x2={width - 20} y1={y} y2={y} />
          {xs.map((v, i) => (
            <circle key={i} cx={x(v)} cy={y + (i % 2 ? 6 : -6)} r={3.4} style={{ fill: FILL[key], fillOpacity: 0.6 }}>
              <title>{v.toFixed(3)} ms</title>
            </circle>
          ))}
          {xs.length > 0 && (
            <g>
              <line x1={x(median(xs))} x2={x(median(xs))} y1={y - 16} y2={y + 16} style={{ stroke: FILL[key], strokeWidth: 2.5 }} />
              <text x={x(median(xs))} y={y - 20} textAnchor="middle">
                median {median(xs).toFixed(2)}
              </text>
            </g>
          )}
        </g>
      ))}
      <text x={padL} y={height - 4}>
        {min.toFixed(2)} ms
      </text>
      <text x={width - 20} y={height - 4} textAnchor="end">
        {max.toFixed(2)} ms
      </text>
    </svg>
  );
}

/** Horizontal bars comparing one metric across the two experimental conditions. */
export function ConditionBars({
  items,
  format,
  max,
  title,
}: {
  items: { label: string; ai_only: number | null; greencode: number | null }[];
  format: (v: number) => string;
  max?: number;
  title: string;
}) {
  const width = 520;
  const rowH = 52;
  const padL = 156;
  const height = items.length * rowH + 8;
  const m = max ?? Math.max(1e-9, ...items.flatMap((i) => [i.ai_only ?? 0, i.greencode ?? 0]));
  const w = (v: number) => Math.max(0, (v / m) * (width - padL - 64));
  const summary = items
    .map((i) => `${i.label}: AI-only ${i.ai_only == null ? "n/a" : format(i.ai_only)}, GreenCode ${i.greencode == null ? "n/a" : format(i.greencode)}`)
    .join("; ");
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}. ${summary}`}>
      {items.map((it, i) => {
        const y = i * rowH + 8;
        return (
          <g key={it.label}>
            <text className="strong" x={padL - 12} y={y + 22} textAnchor="end">
              {it.label}
            </text>
            {(["ai_only", "greencode"] as const).map((c, j) => {
              const v = it[c];
              return (
                <g key={c}>
                  <rect x={padL} y={y + j * 19} width={v == null ? 0 : w(v)} height={15} style={{ fill: FILL[c] }} rx={3}>
                    <title>
                      {it.label}, {c === "ai_only" ? "AI-only" : "GreenCode"}: {v == null ? "no data" : format(v)}
                    </title>
                  </rect>
                  <text x={padL + (v == null ? 0 : w(v)) + 7} y={y + j * 19 + 12}>
                    {v == null ? "no data" : format(v)}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

export function Legend({ items }: { items: { label: string; color: SeriesKey }[] }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label}>
          <i style={{ background: FILL[i.color] }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
