/**
 * Small dependency-free SVG charts. Keeping these in-house avoids a charting
 * library and keeps the dashboard build tiny and deterministic.
 */

const COLORS = {
  original: "#8a9488",
  candidate: "#1f6f43",
  ai_only: "#5e4a9c",
  greencode: "#1f6f43",
  grid: "#e2e6dd",
};

export function PairedBars({
  rows,
  unit = "ms",
  height = 180,
}: {
  rows: { label: string; original: number | null; candidate: number | null }[];
  unit?: string;
  height?: number;
}) {
  const width = 520;
  const padL = 46;
  const padB = 28;
  const max = Math.max(1e-9, ...rows.flatMap((r) => [r.original ?? 0, r.candidate ?? 0]));
  const groupW = (width - padL - 10) / Math.max(rows.length, 1);
  const barW = Math.min(34, groupW / 2.6);
  const scaleY = (v: number) => (height - padB) - (v / max) * (height - padB - 14);
  const ticks = 4;
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`}>
      {Array.from({ length: ticks + 1 }).map((_, i) => {
        const v = (max / ticks) * i;
        const y = scaleY(v);
        return (
          <g key={i}>
            <line x1={padL} x2={width - 10} y1={y} y2={y} stroke={COLORS.grid} />
            <text x={padL - 6} y={y + 4} textAnchor="end">
              {v >= 100 ? v.toFixed(0) : v.toFixed(v >= 10 ? 1 : 2)}
            </text>
          </g>
        );
      })}
      {rows.map((r, i) => {
        const cx = padL + groupW * i + groupW / 2;
        return (
          <g key={r.label}>
            {r.original != null && (
              <rect x={cx - barW - 2} y={scaleY(r.original)} width={barW} height={height - padB - scaleY(r.original)} fill={COLORS.original} rx={2}>
                <title>original: {r.original.toFixed(3)} {unit}</title>
              </rect>
            )}
            {r.candidate != null && (
              <rect x={cx + 2} y={scaleY(r.candidate)} width={barW} height={height - padB - scaleY(r.candidate)} fill={COLORS.candidate} rx={2}>
                <title>candidate: {r.candidate.toFixed(3)} {unit}</title>
              </rect>
            )}
            <text x={cx} y={height - 8} textAnchor="middle">
              {r.label}
            </text>
          </g>
        );
      })}
      <text x={padL} y={10}>
        {unit}
      </text>
    </svg>
  );
}

/** Strip/dot plot of raw timing samples for two variants, with the median marked. */
export function SamplesPlot({ original, candidate }: { original: number[]; candidate: number[] }) {
  const width = 520;
  const height = 120;
  const padL = 70;
  const all = [...original, ...candidate];
  if (!all.length) return null;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const x = (v: number) => padL + ((v - min) / span) * (width - padL - 16);
  const median = (xs: number[]) => {
    const s = [...xs].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const rowsDef: [string, number[], string, number][] = [
    ["original", original, COLORS.original, 38],
    ["candidate", candidate, COLORS.candidate, 82],
  ];
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`}>
      {rowsDef.map(([label, xs, color, y]) => (
        <g key={label}>
          <text x={padL - 8} y={y + 4} textAnchor="end">
            {label}
          </text>
          <line x1={padL} x2={width - 16} y1={y} y2={y} stroke={COLORS.grid} />
          {xs.map((v, i) => (
            <circle key={i} cx={x(v)} cy={y + (i % 2 ? 5 : -5)} r={3.2} fill={color} fillOpacity={0.55}>
              <title>{v.toFixed(3)} ms</title>
            </circle>
          ))}
          {xs.length > 0 && <line x1={x(median(xs))} x2={x(median(xs))} y1={y - 12} y2={y + 12} stroke={color} strokeWidth={2} />}
        </g>
      ))}
      <text x={padL} y={height - 4}>
        {min.toFixed(2)} ms
      </text>
      <text x={width - 16} y={height - 4} textAnchor="end">
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
}: {
  items: { label: string; ai_only: number | null; greencode: number | null }[];
  format: (v: number) => string;
  max?: number;
}) {
  const width = 520;
  const rowH = 44;
  const padL = 150;
  const height = items.length * rowH + 10;
  const m = max ?? Math.max(1e-9, ...items.flatMap((i) => [i.ai_only ?? 0, i.greencode ?? 0]));
  const w = (v: number) => Math.max(0, (v / m) * (width - padL - 70));
  return (
    <svg className="chart" viewBox={`0 0 ${width} ${height}`}>
      {items.map((it, i) => {
        const y = i * rowH + 6;
        return (
          <g key={it.label}>
            <text x={padL - 10} y={y + 20} textAnchor="end" style={{ fill: "#1c211a" }}>
              {it.label}
            </text>
            {(["ai_only", "greencode"] as const).map((c, j) => {
              const v = it[c];
              return (
                <g key={c}>
                  <rect x={padL} y={y + j * 16} width={v == null ? 0 : w(v)} height={13} fill={COLORS[c]} rx={2} />
                  <text x={padL + (v == null ? 0 : w(v)) + 6} y={y + j * 16 + 11}>
                    {v == null ? "–" : format(v)}
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

export function Legend({ items }: { items: { label: string; color: keyof typeof COLORS }[] }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label}>
          <i style={{ background: COLORS[i.color] }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
