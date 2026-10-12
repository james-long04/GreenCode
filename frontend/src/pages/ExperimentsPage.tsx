import { useEffect, useMemo, useState } from "react";

import { api } from "../api";
import { ConditionBars, Legend } from "../components/charts";
import { Badge, ConditionLabel, Empty, ErrorBox, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { Condition, Language, ResultRow, ResultsSummary, SuiteCase, SuiteJob } from "../types";
import { HypothesisList } from "./OverviewPage";

export function ExperimentsPage({ projectId, navigate }: { projectId: string | null; navigate: (p: string) => void }) {
  const cases = useAsync<SuiteCase[]>(() => api.suiteCases(), []);
  const jobs = useAsync<SuiteJob[]>(() => api.suiteJobs(), [], 2000);
  const [language, setLanguage] = useState<Language | "">("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [conditions, setConditions] = useState<Condition[]>(["ai_only", "greencode"]);
  const [err, setErr] = useState<string | null>(null);
  const results = useAsync<ResultRow[]>(() => api.results(projectId ?? undefined, language || undefined), [projectId, language], 5000);
  const summary = useAsync<ResultsSummary>(() => api.resultsSummary(projectId ?? undefined, language || undefined), [projectId, language], 5000);

  const visible = useMemo(() => (cases.data ?? []).filter((c) => !language || c.language === language), [cases.data, language]);
  useEffect(() => {
    if (cases.data && selected.size === 0) setSelected(new Set(cases.data.map((c) => c.id)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cases.data]);

  const running = jobs.data?.find((j) => j.status === "running");

  const run = async () => {
    if (!projectId) {
      setErr("Select a project first.");
      return;
    }
    setErr(null);
    try {
      const ids = visible.filter((c) => selected.has(c.id)).map((c) => c.id);
      await api.runSuite({ project_id: projectId, case_ids: ids, conditions });
      await jobs.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const toggleCond = (c: Condition) =>
    setConditions((cs) => (cs.includes(c) ? cs.filter((x) => x !== c) : [...cs, c]));

  const s = summary.data;
  const ai = s?.conditions.ai_only;
  const gc = s?.conditions.greencode;

  return (
    <div>
      <h1>Experiments</h1>
      <div className="subtitle">Run the controlled benchmark suite under the AI-only and GreenCode conditions, then compare against the baseline.</div>
      <ErrorBox error={err ?? cases.error ?? results.error} />

      <div className="grid two">
        <div className="card">
          <div className="row spread" style={{ marginBottom: 10 }}>
            <h3 style={{ margin: 0 }}>Benchmark suite ({visible.filter((c) => selected.has(c.id)).length}/{visible.length} selected)</h3>
            <div className="row">
              <select value={language} onChange={(e) => setLanguage(e.target.value as Language | "")}>
                <option value="">all languages</option>
                <option value="python">python</option>
                <option value="sql">sql</option>
              </select>
              <button className="small" onClick={() => setSelected(new Set(visible.map((c) => c.id)))}>all</button>
              <button className="small" onClick={() => setSelected(new Set())}>none</button>
            </div>
          </div>
          <div style={{ maxHeight: 360, overflow: "auto" }}>
            <table>
              <tbody>
                {visible.map((c) => (
                  <tr key={c.id}>
                    <td style={{ width: 24 }}>
                      <input
                        type="checkbox"
                        checked={selected.has(c.id)}
                        onChange={() =>
                          setSelected((prev) => {
                            const n = new Set(prev);
                            if (n.has(c.id)) n.delete(c.id);
                            else n.add(c.id);
                            return n;
                          })
                        }
                      />
                    </td>
                    <td>
                      <div className="mono small">{c.id}</div>
                      <div className="muted small">{c.title}</div>
                    </td>
                    <td>
                      {c.expected_rules.map((r) => (
                        <Badge key={r}>{r}</Badge>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row spread" style={{ marginTop: 12 }}>
            <div className="row">
              <label>
                <input type="checkbox" checked={conditions.includes("ai_only")} onChange={() => toggleCond("ai_only")} /> AI-only
              </label>
              <label>
                <input type="checkbox" checked={conditions.includes("greencode")} onChange={() => toggleCond("greencode")} /> GreenCode
              </label>
            </div>
            <button className="primary" onClick={() => void run()} disabled={!!running || !conditions.length || !projectId}>
              {running ? "Suite running…" : "Run suite"}
            </button>
          </div>
        </div>

        <div className="card">
          <h3>Runs</h3>
          {jobs.data?.length ? (
            jobs.data.slice(0, 4).map((j) => (
              <div key={j.job_id} style={{ marginBottom: 12 }}>
                <div className="row spread small">
                  <span>
                    <Badge kind={j.status === "completed" ? "ok" : j.status === "failed" ? "bad" : "warn"}>{j.status}</Badge> {fmt.date(j.started_at)}
                  </span>
                  <span className="muted">
                    {j.done}/{j.total}
                  </span>
                </div>
                <div className="progress" style={{ marginTop: 4 }}>
                  <div style={{ width: `${j.total ? (100 * j.done) / j.total : 0}%` }} />
                </div>
                {j.error && <div className="error" style={{ marginTop: 6 }}>{j.error}</div>}
                {j.status === "running" && j.results.length > 0 && (
                  <div className="muted small" style={{ marginTop: 4 }}>
                    last: {j.results[j.results.length - 1].case_id} · {j.results[j.results.length - 1].condition} · {j.results[j.results.length - 1].status}
                  </div>
                )}
              </div>
            ))
          ) : (
            <Empty>No suite runs in this server session.</Empty>
          )}
          <div className="muted small">Job progress is kept in memory; completed evidence is always in PostgreSQL and listed below.</div>
        </div>
      </div>

      {s && s.total_runs > 0 && (
        <div className="grid two">
          <div className="card">
            <h3>Condition summary</h3>
            <table>
              <thead>
                <tr>
                  <th />
                  <th className="num">AI-only</th>
                  <th className="num">GreenCode</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Runs", ai?.runs, gc?.runs, (v: number) => String(v)],
                  ["Correct (verified)", ai?.correct, gc?.correct, (v: number) => String(v)],
                  ["Correctness rate", ai?.correctness_rate, gc?.correctness_rate, fmt.rate],
                  ["Unchanged candidates", ai?.unchanged, gc?.unchanged, (v: number) => String(v)],
                  ["Significantly faster", ai?.faster_significant, gc?.faster_significant, (v: number) => String(v)],
                  ["Significantly slower", ai?.slower_significant, gc?.slower_significant, (v: number) => String(v)],
                  ["Median speed-up", ai?.median_speedup, gc?.median_speedup, fmt.x],
                  ["Geomean speed-up", ai?.geomean_speedup, gc?.geomean_speedup, fmt.x],
                  ["Median time change", ai?.median_time_change_pct, gc?.median_time_change_pct, fmt.pct],
                  ["Geomean energy ratio", ai?.geomean_energy_ratio, gc?.geomean_energy_ratio, fmt.x],
                  ["Median energy change", ai?.median_energy_change_pct, gc?.median_energy_change_pct, fmt.pct],
                ].map(([label, a, b, f]) => (
                  <tr key={label as string}>
                    <td>{label as string}</td>
                    <td className="num">{a == null ? "–" : (f as (v: number) => string)(a as number)}</td>
                    <td className="num">{b == null ? "–" : (f as (v: number) => string)(b as number)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="small muted" style={{ marginTop: 8 }}>
              Failures — AI-only: {Object.entries(ai?.failures ?? {}).map(([k, v]) => `${k} ×${v}`).join(", ") || "none"} · GreenCode: {Object.entries(gc?.failures ?? {}).map(([k, v]) => `${k} ×${v}`).join(", ") || "none"}
            </div>
          </div>
          <div className="card">
            <h3>Hypotheses</h3>
            <HypothesisList summary={s} />
            <div style={{ marginTop: 14 }}>
              <ConditionBars
                items={[
                  { label: "Geomean speed-up", ai_only: ai?.geomean_speedup ?? null, greencode: gc?.geomean_speedup ?? null },
                  { label: "Geomean energy ratio", ai_only: ai?.geomean_energy_ratio ?? null, greencode: gc?.geomean_energy_ratio ?? null },
                ]}
                format={(v) => `${v.toFixed(2)}×`}
              />
              <Legend items={[{ label: "AI-only", color: "ai_only" }, { label: "GreenCode", color: "greencode" }]} />
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h3>Per-case results {projectId ? "" : "(all projects)"}</h3>
        {results.data?.length ? (
          <ResultsTable rows={results.data} navigate={navigate} />
        ) : (
          <Empty>No results yet.</Empty>
        )}
      </div>
    </div>
  );
}

function ResultsTable({ rows, navigate }: { rows: ResultRow[]; navigate: (p: string) => void }) {
  const sorted = [...rows].sort((a, b) => (a.case_id ?? a.name).localeCompare(b.case_id ?? b.name) || a.condition.localeCompare(b.condition));
  return (
    <div style={{ overflow: "auto" }}>
      <table>
        <thead>
          <tr>
            <th>Case</th>
            <th>Cond.</th>
            <th>Status</th>
            <th>Rules</th>
            <th className="num">Speed-up</th>
            <th className="num">Δ time</th>
            <th>Verdict</th>
            <th className="num">Δ energy</th>
            <th>Energy src</th>
            <th>Failure</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.optimisation_id} className="clickable" onClick={() => navigate(`/optimisations/${r.optimisation_id}`)}>
              <td>
                <div className="mono small">{r.case_id ?? r.name}</div>
                <div className="muted small">{r.language}{r.unchanged ? " · unchanged" : ""}</div>
              </td>
              <td>
                <ConditionLabel condition={r.condition} />
              </td>
              <td>
                <Badge kind={r.status}>{r.status}</Badge>
              </td>
              <td className="small">{r.rules.join(" ")}</td>
              <td className="num">{fmt.x(r.speedup)}</td>
              <td className="num">{fmt.pct(r.time_percent_change)}</td>
              <td>{r.verdict && <Badge kind={r.verdict}>{r.verdict.replace(/_/g, " ")}</Badge>}</td>
              <td className="num">{fmt.pct(r.energy_percent_change)}</td>
              <td className="small">
                {r.energy_source} {r.energy_method && <Badge kind={r.energy_method === "measured" ? "ok" : "warn"}>{r.energy_method}</Badge>}
              </td>
              <td className="muted small">{r.failure_reason?.slice(0, 80)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
