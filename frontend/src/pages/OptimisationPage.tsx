import { useMemo, useState } from "react";

import { api } from "../api";
import { PairedBars, SamplesPlot } from "../components/charts";
import { CodeBlock, diffLines } from "../components/code";
import { Icon } from "../components/icons";
import {
  Alert,
  Badge,
  ConditionLabel,
  Empty,
  ErrorBox,
  LoadingBlock,
  Metric,
  PageHeader,
  Section,
  Spinner,
  TableWrap,
  Term,
  fmt,
} from "../components/ui";
import { useAsync, useDocumentTitle } from "../hooks";
import type { BenchmarkRun, EnergyEntry, Measurement, Optimisation } from "../types";

const ACTIVE = new Set(["pending", "generated", "verified"]);

type StepState = "done" | "active" | "failed" | "todo";

function pipelineSteps(o: Optimisation, active: boolean): { label: string; state: StepState }[] {
  const hasCandidate = !!o.candidate_source;
  const verification = o.summary.verification;
  const benchmarked = o.benchmark_runs.some((r) => r.variant === "candidate");
  const energy = Object.keys(o.summary.energy ?? {}).length > 0;
  const stop = (done: boolean, failedHere: boolean): StepState => (done ? "done" : failedHere ? "failed" : "todo");

  const steps: { label: string; done: boolean }[] = [
    { label: "Generate", done: hasCandidate },
    { label: "Verify", done: !!verification?.passed },
    { label: "Benchmark", done: benchmarked },
    { label: "Measure energy", done: energy },
  ];
  const firstOpen = steps.findIndex((s) => !s.done);
  return steps.map((s, i) => {
    if (s.done) return { label: s.label, state: "done" };
    if (i === firstOpen) return { label: s.label, state: active ? "active" : stop(false, o.status !== "completed") };
    return { label: s.label, state: "todo" };
  });
}

function verdictSentence(o: Optimisation, active: boolean): string {
  const v = o.summary.verification;
  const t = o.summary.timing;
  if (active) return "The pipeline is still running. This page refreshes on its own.";
  if (o.summary.unchanged) return "The model returned code identical to the original, so there is nothing to compare.";
  if (v && !v.passed) return `The candidate was rejected: it failed verification${v.failure_type ? ` (${fmt.label(v.failure_type)})` : ""}. It was not benchmarked.`;
  if (!o.candidate_source) return o.failure_reason ?? "No candidate was produced.";
  if (!t) return "The candidate passed verification but has no benchmark result.";
  if (t.verdict === "faster") return `The candidate is correct and ${fmt.x(t.speedup)} as fast at the median (${fmt.pct(t.percent_change)} time), a statistically significant difference.`;
  if (t.verdict === "slower") return `The candidate is correct but slower: ${fmt.pct(t.percent_change)} time at the median, a statistically significant difference.`;
  return `The candidate is correct, but the timing difference (${fmt.pct(t.percent_change)}) is not statistically significant.`;
}

export function OptimisationPage({ id, navigate }: { id: string; navigate: (p: string) => void }) {
  const q = useAsync<Optimisation>(() => api.optimisation(id), [id], 2500);
  const [busy, setBusy] = useState(false);
  const o = q.data;
  useDocumentTitle(o ? `Optimisation, ${o.status}` : "Optimisation");

  const diff = useMemo(() => (o?.candidate_source ? diffLines(o.original_source, o.candidate_source) : null), [o?.original_source, o?.candidate_source]);

  if (q.error && !o) return <ErrorBox error={q.error} onRetry={() => void q.reload()} />;
  if (!o) return (
    <>
      <PageHeader title="Optimisation" />
      <LoadingBlock label="Loading optimisation" rows={4} />
    </>
  );

  const active = ACTIVE.has(o.status);
  const original = o.benchmark_runs.find((r) => r.variant === "original");
  const candidate = o.benchmark_runs.find((r) => r.variant === "candidate");
  const timing = o.summary.timing;
  const energyEntries = Object.entries(o.summary.energy ?? {}).filter(([k]) => k !== "time_vs_energy") as [string, EnergyEntry][];
  const firstEnergy = energyEntries[0];
  const tve = (o.summary.energy ?? {})["time_vs_energy"] as { time_percent_change: number; energy_percent_change: number; divergence_pp: number } | undefined;
  const v = o.summary.verification;
  const passedTests = o.test_results.filter((t) => t.passed).length;

  const rerun = async () => {
    setBusy(true);
    try {
      await api.rerunOptimisation(o.id);
      await q.reload();
    } finally {
      setBusy(false);
    }
  };

  const steps = pipelineSteps(o, active);

  return (
    <div className="stack">
      <PageHeader
        title={
          <>
            Optimisation <ConditionLabel condition={o.condition} />
          </>
        }
        meta={
          <>
            <a href={`#/analyses/${o.analysis_id}`} onClick={(e) => { e.preventDefault(); navigate(`/analyses/${o.analysis_id}`); }}>
              Back to analysis
            </a>
            <span>
              {o.provider} / {o.model_name}
            </span>
            <span>generated in {o.generation_ms ? `${(o.generation_ms / 1000).toFixed(1)} s` : "–"}</span>
            {o.prompt_tokens != null && (
              <span>
                {o.prompt_tokens} → {o.completion_tokens ?? "?"} tokens
              </span>
            )}
          </>
        }
        actions={
          <button onClick={() => void rerun()} disabled={active || busy}>
            {busy || active ? <Spinner /> : <Icon name="arrow-clockwise" />}
            Re-run pipeline
          </button>
        }
      />

      {q.error && <ErrorBox error={q.error} onRetry={() => void q.reload()} />}

      <div className="stack-sm">
        <ol className="pipeline" aria-label="Pipeline progress">
          {steps.map((s, i) => (
            <li key={s.label} data-state={s.state}>
              {s.state === "done" && <Icon name="check-circle" size={14} />}
              {s.state === "active" && <Spinner size={14} />}
              {s.state === "failed" && <Icon name="x-circle" size={14} />}
              {s.label}
              <span className="sr-only">: {s.state === "todo" ? "not reached" : s.state === "active" ? "in progress" : s.state}</span>
              {i < steps.length - 1 && <span className="sep" aria-hidden="true"><Icon name="caret-right" size={12} /></span>}
            </li>
          ))}
        </ol>
        <p className="verdict">{verdictSentence(o, active)}</p>
      </div>

      {o.failure_reason && !active && (
        <Alert kind="error" title="Why it stopped">
          {o.failure_reason}
        </Alert>
      )}

      <div className="metrics">
        <Metric
          label="Verification"
          value={<Badge kind={v ? (v.passed ? "ok" : "bad") : "warn"}>{v ? (v.passed ? "Passed" : fmt.label(v.failure_type ?? "failed")) : "Pending"}</Badge>}
          note={`${passedTests} of ${o.test_results.length} tests`}
        />
        <Metric
          label="Speed-up (median)"
          value={fmt.x(timing?.speedup)}
          note={timing ? `${fmt.pct(timing.percent_change)} time, ${fmt.p(timing.mann_whitney_p)}` : "No benchmark yet"}
        />
        <Metric
          label="Energy change"
          value={firstEnergy ? fmt.pct(firstEnergy[1].percent_change) : "–"}
          note={firstEnergy ? <>{firstEnergy[0]}, <Term id={firstEnergy[1].method === "measured" ? "measured" : "estimated"}>{firstEnergy[1].method}</Term></> : "No energy data"}
        />
        <Metric
          label={<Term id="co2e">CO₂e per run</Term>}
          value={firstEnergy ? `${fmt.co2(firstEnergy[1].original_co2e_g)} → ${fmt.co2(firstEnergy[1].candidate_co2e_g)}` : "–"}
          note="Grid factor for the configured region"
        />
      </div>

      <Section title="Original and candidate" hint="Changed lines are marked with + and −" id="code">
        <div className="grid two">
          <div className="stack-sm">
            <h3>Original</h3>
            <CodeBlock label="Original source" lines={diff?.original} source={o.original_source} />
          </div>
          <div className="stack-sm">
            <h3>Candidate</h3>
            {diff ? <CodeBlock label="Candidate source" lines={diff.candidate} /> : <Empty>{active ? "The model is still generating." : "No candidate was produced."}</Empty>}
          </div>
        </div>
      </Section>

      <div className="grid two">
        <Section title="Correctness tests" id="tests">
          {o.test_results.length ? (
            <div className="panel flush">
              <TableWrap label="Correctness tests">
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
                          <Badge kind={t.passed ? "ok" : "bad"}>{t.passed ? "Pass" : fmt.label(t.failure_type ?? "fail")}</Badge>
                        </td>
                        <td className="muted">{t.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </div>
          ) : (
            <Empty>{active ? "Waiting for verification." : "No tests were recorded."}</Empty>
          )}
        </Section>

        <Section title="Timing samples" id="samples">
          {original && candidate && original.samples_ms.length ? (
            <div className="stack-sm">
              <SamplesPlot original={original.samples_ms} candidate={candidate.samples_ms} />
              <RunStats original={original} candidate={candidate} />
            </div>
          ) : (
            <Empty>{active ? "Waiting for the benchmark." : "No benchmark data. The candidate was rejected or failed."}</Empty>
          )}
        </Section>
      </div>

      {original && candidate && (
        <div className="grid two">
          <Section title="Resources and energy" id="resources">
            <div className="stack-sm">
              <div className="panel flush">
                <MeasurementTable original={original} candidate={candidate} />
              </div>
              {tve && (
                <p className="muted">
                  Time changed {fmt.pct(tve.time_percent_change)} while energy changed {fmt.pct(tve.energy_percent_change)}, a gap of {fmt.num(tve.divergence_pp, 1)} percentage points. This is the evidence for hypothesis H4.
                </p>
              )}
            </div>
          </Section>
          <Section title="Comparison" id="comparison">
            <div className="stack-sm">
              <PairedBars
                title="Median time, CPU time and energy, original against candidate"
                rows={[
                  { label: "median ms", original: original.median_ms, candidate: candidate.median_ms },
                  { label: "cpu ms", original: metric(original, "cpu_time_ms"), candidate: metric(candidate, "cpu_time_ms") },
                  { label: "energy J", original: metric(original, "energy_joules"), candidate: metric(candidate, "energy_joules") },
                ]}
              />
              {o.summary.sql_plan && (
                <div className="panel flush">
                  <TableWrap label="PostgreSQL plan">
                    <table>
                      <thead>
                        <tr>
                          <th>PostgreSQL plan</th>
                          <th className="num">Original</th>
                          <th className="num">Candidate</th>
                        </tr>
                      </thead>
                      <tbody>
                        {["pg_total_cost", "pg_execution_ms", "pg_shared_hit_blocks", "pg_shared_read_blocks", "pg_seq_scans"].map((k) => {
                          const digits = k.includes("ms") || k.includes("cost") ? 2 : 0;
                          return (
                            <tr key={k}>
                              <td className="mono">{k.replace("pg_", "")}</td>
                              <td className="num">{fmt.num(o.summary.sql_plan?.original[k], digits)}</td>
                              <td className="num">{fmt.num(o.summary.sql_plan?.candidate[k], digits)}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </TableWrap>
                </div>
              )}
            </div>
          </Section>
        </div>
      )}

      <Section title="Raw record" hint="Exactly what was sent, received and measured" id="raw">
        <div className="stack-sm">
          <details className="disclosure">
            <summary>Prompt sent to the model ({o.prompt?.length ?? 0} characters)</summary>
            <div className="disclosure-body">
              <pre className="plain">{o.prompt}</pre>
            </div>
          </details>
          <details className="disclosure">
            <summary>Raw model response</summary>
            <div className="disclosure-body">
              <pre className="plain">{o.raw_response}</pre>
            </div>
          </details>
          <details className="disclosure">
            <summary>Benchmark environment</summary>
            <div className="disclosure-body">
              <pre className="plain">{JSON.stringify(original?.environment ?? {}, null, 2)}</pre>
            </div>
          </details>
        </div>
      </Section>
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
    <div className="panel flush">
      <TableWrap label="Timing statistics">
        <table>
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
      </TableWrap>
    </div>
  );
}

/** For machine-wide energy meters, show the mean and idle power behind the figure. */
function wattsNote(a?: Measurement, b?: Measurement) {
  const d = (m?: Measurement) => (m?.details ?? {}) as Record<string, unknown>;
  const idle = d(a).idle_watts ?? d(b).idle_watts;
  const ma = d(a).mean_watts;
  const mb = d(b).mean_watts;
  if (typeof idle !== "number" && typeof ma !== "number") return null;
  const f = (v: unknown) => (typeof v === "number" ? `${v.toFixed(1)} W` : "–");
  return (
    <div className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 4 }}>
      mean {f(ma)} / {f(mb)}{typeof idle === "number" ? `, idle floor ${f(idle)}` : ""}
    </div>
  );
}

function MeasurementTable({ original, candidate }: { original: BenchmarkRun; candidate: BenchmarkRun }) {
  const keys = Array.from(new Set([...original.measurements, ...candidate.measurements].map((m) => `${m.metric}|${m.source}`)));
  const find = (r: BenchmarkRun, key: string): Measurement | undefined => {
    const [name, source] = key.split("|");
    return r.measurements.find((m) => m.metric === name && m.source === source);
  };
  const order = ["cpu_time_ms", "peak_rss_mb", "energy_joules", "energy_joules_net", "co2e_grams"];
  keys.sort((a, b) => {
    const ia = order.indexOf(a.split("|")[0]);
    const ib = order.indexOf(b.split("|")[0]);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib) || a.localeCompare(b);
  });
  return (
    <TableWrap label="Resource measurements">
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Source</th>
            <th className="num">Original</th>
            <th className="num">Candidate</th>
            <th className="num">Change</th>
          </tr>
        </thead>
        <tbody>
          {keys
            .filter((k) => !k.startsWith("pg_") && !k.startsWith("user_time") && !k.startsWith("system_time") && !k.startsWith("process_wall"))
            .map((k) => {
              const a = find(original, k);
              const b = find(candidate, k);
              const method = (a ?? b)?.method;
              const delta = a && b && a.value ? ((b.value - a.value) / a.value) * 100 : null;
              return (
                <tr key={k}>
                  <td className="mono">{k.split("|")[0]}</td>
                  <td>
                    {a?.source ?? b?.source}{" "}
                    <Badge kind={method === "measured" ? "ok" : method === "derived" ? "info" : "warn"}>
                      <Term id={method === "measured" ? "measured" : method === "derived" ? "derived" : "estimated"}>{method}</Term>
                    </Badge>
                    {wattsNote(a, b)}
                  </td>
                  <td className="num">{a ? `${fmt.num(a.value, 3)} ${a.unit}` : "–"}</td>
                  <td className="num">{b ? `${fmt.num(b.value, 3)} ${b.unit}` : "–"}</td>
                  <td className="num">{fmt.pct(delta)}</td>
                </tr>
              );
            })}
        </tbody>
      </table>
    </TableWrap>
  );
}
