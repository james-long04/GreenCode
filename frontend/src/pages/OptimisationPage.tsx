import { api } from "../api";
import { PairedBars, SamplesPlot } from "../components/charts";
import { Badge, ConditionLabel, Empty, ErrorBox, Stat, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { BenchmarkRun, EnergyEntry, Measurement, Optimisation } from "../types";

const ACTIVE = new Set(["pending", "generated", "verified"]);

export function OptimisationPage({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const q = useAsync<Optimisation>(() => api.optimisation(id), [id], 2500);
  const o = q.data;
  if (q.error) return <ErrorBox error={q.error} />;
  if (!o) return <Empty>Loading…</Empty>;
  const active = ACTIVE.has(o.status);
  const original = o.benchmark_runs.find((r) => r.variant === "original");
  const candidate = o.benchmark_runs.find((r) => r.variant === "candidate");
  const timing = o.summary.timing;
  const energyEntries = Object.entries(o.summary.energy ?? {}).filter(([k]) => k !== "time_vs_energy") as [string, EnergyEntry][];
  const tve = (o.summary.energy ?? {})["time_vs_energy"] as { time_percent_change: number; energy_percent_change: number; divergence_pp: number } | undefined;

  const rerun = async () => {
    await api.rerunOptimisation(o.id);
    await q.reload();
  };

  return (
    <div>
      <div className="row spread">
        <div>
          <h1>
            Optimisation <ConditionLabel condition={o.condition} />
          </h1>
          <div className="subtitle">
            <Badge kind={o.status}>{o.status}</Badge> · <a href={`#/analyses/${o.analysis_id}`} onClick={(e) => { e.preventDefault(); navigate(`/analyses/${o.analysis_id}`); }}>analysis</a> · {o.provider}/{o.model_name} · generated in {o.generation_ms ? `${(o.generation_ms / 1000).toFixed(1)} s` : "–"}
            {o.prompt_tokens != null && ` · ${o.prompt_tokens}→${o.completion_tokens ?? "?"} tokens`}
            {active && <span className="muted"> · pipeline running, refreshing…</span>}
          </div>
        </div>
        <button onClick={() => void rerun()} disabled={active}>
          Re-run pipeline
        </button>
      </div>
      {o.failure_reason && <div className="error">{o.failure_reason}</div>}

      <div className="grid four">
        <Stat label="Verification" value={<Badge kind={o.summary.verification ? (o.summary.verification.passed ? "ok" : "bad") : "warn"}>{o.summary.verification ? (o.summary.verification.passed ? "passed" : o.summary.verification.failure_type ?? "failed") : "pending"}</Badge>} hint={`${o.test_results.filter((t) => t.passed).length}/${o.test_results.length} tests${o.summary.unchanged ? " · candidate identical to original" : ""}`} />
        <Stat label="Speed-up (median)" value={fmt.x(timing?.speedup)} hint={timing ? `${fmt.pct(timing.percent_change)} · ${fmt.p(timing.mann_whitney_p)} · Cliff's δ ${fmt.num(timing.cliffs_delta)}` : "benchmark pending"} />
        <Stat label="Energy change" value={energyEntries.length ? fmt.pct(energyEntries[0][1].percent_change) : "–"} hint={energyEntries.length ? `${energyEntries[0][0]} (${energyEntries[0][1].method})` : ""} />
        <Stat label="CO₂e per run" value={energyEntries.length ? `${fmt.co2(energyEntries[0][1].original_co2e_g)} → ${fmt.co2(energyEntries[0][1].candidate_co2e_g)}` : "–"} hint="grid factor from carbon_factors" />
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <h3>Candidate vs original</h3>
        <div className="diff">
          <div>
            <div className="muted small" style={{ marginBottom: 6 }}>Original</div>
            <pre>{o.original_source}</pre>
          </div>
          <div>
            <div className="muted small" style={{ marginBottom: 6 }}>Candidate</div>
            <pre>{o.candidate_source ?? "(no candidate yet)"}</pre>
          </div>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Correctness tests</h3>
          {o.test_results.length ? (
            <table>
              <thead>
                <tr>
                  <th>Test</th>
                  <th>Result</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {o.test_results.map((t) => (
                  <tr key={t.id}>
                    <td className="mono">{t.test_name}</td>
                    <td>
                      <Badge kind={t.passed ? "ok" : "bad"}>{t.passed ? "pass" : t.failure_type ?? "fail"}</Badge>
                    </td>
                    <td className="muted small">{t.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty>{active ? "Waiting for verification…" : "No tests recorded."}</Empty>
          )}
        </div>
        <div className="card">
          <h3>Timing samples</h3>
          {original && candidate && original.samples_ms.length ? (
            <>
              <SamplesPlot original={original.samples_ms} candidate={candidate.samples_ms} />
              <RunStats original={original} candidate={candidate} />
            </>
          ) : (
            <Empty>{active ? "Waiting for benchmark…" : "No benchmark data (candidate was rejected or failed)."}</Empty>
          )}
        </div>
      </div>

      {original && candidate && (
        <div className="grid two">
          <div className="card">
            <h3>Resources & energy</h3>
            <MeasurementTable original={original} candidate={candidate} />
            {tve && (
              <div className="muted small" style={{ marginTop: 10 }}>
                H4 evidence: time {fmt.pct(tve.time_percent_change)} vs energy {fmt.pct(tve.energy_percent_change)} — divergence {fmt.num(tve.divergence_pp, 1)} pp.
              </div>
            )}
          </div>
          <div className="card">
            <h3>Comparison</h3>
            <PairedBars
              rows={[
                { label: "median ms", original: original.median_ms, candidate: candidate.median_ms },
                { label: "cpu ms", original: metric(original, "cpu_time_ms"), candidate: metric(candidate, "cpu_time_ms") },
                { label: "energy J", original: metric(original, "energy_joules"), candidate: metric(candidate, "energy_joules") },
              ]}
              unit=""
            />
            {o.summary.sql_plan && (
              <table style={{ marginTop: 8 }}>
                <thead>
                  <tr>
                    <th>PostgreSQL plan</th>
                    <th className="num">Original</th>
                    <th className="num">Candidate</th>
                  </tr>
                </thead>
                <tbody>
                  {["pg_total_cost", "pg_execution_ms", "pg_shared_hit_blocks", "pg_shared_read_blocks", "pg_seq_scans"].map((k) => (
                    <tr key={k}>
                      <td className="mono small">{k.replace("pg_", "")}</td>
                      <td className="num">{fmt.num(o.summary.sql_plan?.original[k], k.includes("ms") || k.includes("cost") ? 2 : 0)}</td>
                      <td className="num">{fmt.num(o.summary.sql_plan?.candidate[k], k.includes("ms") || k.includes("cost") ? 2 : 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <details>
          <summary>Prompt sent to the model ({o.prompt?.length ?? 0} chars)</summary>
          <pre className="light" style={{ marginTop: 8 }}>{o.prompt}</pre>
        </details>
        <details style={{ marginTop: 8 }}>
          <summary>Raw model response</summary>
          <pre className="light" style={{ marginTop: 8 }}>{o.raw_response}</pre>
        </details>
        <details style={{ marginTop: 8 }}>
          <summary>Benchmark environment</summary>
          <pre className="light" style={{ marginTop: 8 }}>{JSON.stringify(original?.environment ?? {}, null, 2)}</pre>
        </details>
      </div>
    </div>
  );
}

function metric(run: BenchmarkRun, name: string): number | null {
  const m = run.measurements.find((x) => x.metric === name);
  return m ? m.value : null;
}

function RunStats({ original, candidate }: { original: BenchmarkRun; candidate: BenchmarkRun }) {
  const row = (label: string, f: (r: BenchmarkRun) => number | null) => (
    <tr key={label}>
      <td>{label}</td>
      <td className="num">{fmt.ms(f(original))}</td>
      <td className="num">{fmt.ms(f(candidate))}</td>
    </tr>
  );
  return (
    <table style={{ marginTop: 8 }}>
      <thead>
        <tr>
          <th>
            n = {original.repetitions} (+{original.warmup_runs} warm-up)
          </th>
          <th className="num">Original</th>
          <th className="num">Candidate</th>
        </tr>
      </thead>
      <tbody>
        {row("median", (r) => r.median_ms)}
        {row("mean", (r) => r.mean_ms)}
        {row("std dev", (r) => r.stdev_ms)}
        {row("95% CI low", (r) => r.ci95_low_ms)}
        {row("95% CI high", (r) => r.ci95_high_ms)}
        {row("min", (r) => r.min_ms)}
        {row("max", (r) => r.max_ms)}
      </tbody>
    </table>
  );
}

function MeasurementTable({ original, candidate }: { original: BenchmarkRun; candidate: BenchmarkRun }) {
  const keys = Array.from(new Set([...original.measurements, ...candidate.measurements].map((m) => `${m.metric}|${m.source}`)));
  const find = (r: BenchmarkRun, key: string): Measurement | undefined => {
    const [metric, source] = key.split("|");
    return r.measurements.find((m) => m.metric === metric && m.source === source);
  };
  const order = ["cpu_time_ms", "peak_rss_mb", "energy_joules", "energy_joules_net", "co2e_grams"];
  keys.sort((a, b) => {
    const ia = order.indexOf(a.split("|")[0]);
    const ib = order.indexOf(b.split("|")[0]);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib) || a.localeCompare(b);
  });
  return (
    <table>
      <thead>
        <tr>
          <th>Metric</th>
          <th>Source</th>
          <th className="num">Original</th>
          <th className="num">Candidate</th>
          <th className="num">Δ</th>
        </tr>
      </thead>
      <tbody>
        {keys
          .filter((k) => !k.startsWith("pg_") && !k.startsWith("user_time") && !k.startsWith("system_time") && !k.startsWith("process_wall"))
          .map((k) => {
            const a = find(original, k);
            const b = find(candidate, k);
            const delta = a && b && a.value ? ((b.value - a.value) / a.value) * 100 : null;
            return (
              <tr key={k}>
                <td className="mono small">{k.split("|")[0]}</td>
                <td className="small">
                  {a?.source ?? b?.source} <Badge kind={(a ?? b)?.method === "measured" ? "ok" : "warn"}>{(a ?? b)?.method}</Badge>
                </td>
                <td className="num">{a ? `${fmt.num(a.value, 3)} ${a.unit}` : "–"}</td>
                <td className="num">{b ? `${fmt.num(b.value, 3)} ${b.unit}` : "–"}</td>
                <td className="num">{fmt.pct(delta)}</td>
              </tr>
            );
          })}
      </tbody>
    </table>
  );
}
