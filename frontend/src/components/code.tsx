import { useMemo } from "react";

export type LineState = "same" | "add" | "del" | "mark";
export interface CodeLine {
  text: string;
  state: LineState;
}

/** Line-based diff (longest common subsequence). Returns the original side and the candidate side. */
export function diffLines(original: string, candidate: string): { original: CodeLine[]; candidate: CodeLine[] } {
  const a = original.replace(/\n$/, "").split("\n");
  const b = candidate.replace(/\n$/, "").split("\n");
  // Very large inputs fall back to an unmarked view rather than freezing the page.
  if (a.length * b.length > 250_000) {
    return {
      original: a.map((text) => ({ text, state: "same" })),
      candidate: b.map((text) => ({ text, state: "same" })),
    };
  }
  const n = a.length;
  const m = b.length;
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const left: CodeLine[] = [];
  const right: CodeLine[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      left.push({ text: a[i], state: "same" });
      right.push({ text: b[j], state: "same" });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      left.push({ text: a[i++], state: "del" });
    } else {
      right.push({ text: b[j++], state: "add" });
    }
  }
  while (i < n) left.push({ text: a[i++], state: "del" });
  while (j < m) right.push({ text: b[j++], state: "add" });
  return { original: left, candidate: right };
}

/** Source listing with line numbers. Lines can be marked (finding locations) or shown as added/removed. */
export function CodeBlock({
  source,
  lines,
  marks,
  label,
}: {
  source?: string;
  lines?: CodeLine[];
  marks?: Set<number>;
  label: string;
}) {
  const rows = useMemo<CodeLine[]>(() => {
    if (lines) return lines;
    return (source ?? "")
      .replace(/\n$/, "")
      .split("\n")
      .map((text, idx) => ({ text, state: marks?.has(idx + 1) ? "mark" : "same" }) as CodeLine);
  }, [lines, source, marks]);
  return (
    <div className="code" role="region" aria-label={label} tabIndex={0}>
      {rows.map((row, idx) => (
        <div className={`code-line ${row.state === "same" ? "" : row.state}`} key={idx}>
          <span className="ln mono" aria-hidden="true">
            {idx + 1}
          </span>
          <span className="src mono">
            {row.state === "add" && <span className="sr-only">added: </span>}
            {row.state === "del" && <span className="sr-only">removed: </span>}
            {row.state === "mark" && <span className="sr-only">flagged: </span>}
            {row.text || " "}
          </span>
        </div>
      ))}
    </div>
  );
}
