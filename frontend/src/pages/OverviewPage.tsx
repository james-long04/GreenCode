import { api } from "../api";
import { ConditionBars, Legend } from "../components/charts";
import { Icon } from "../components/icons";
import { Alert, Badge, Command, ErrorBox, LoadingBlock, PageHeader, Section, Term, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { Health, ResultsSummary } from "../types";

type Fmt = (v: number) => string;

interface Row {
  hyp?: string;
  label: string;
  hint: string;
  ai: number | null | undefined;
  gc: number | null | undefined;
  format: Fmt;
  /** Which direction is better for this measure. */
  better: "higher" | "lower";
  diff: (ai: number, gc: number) => string;
}

export function OverviewPage({
  projectId,
  navigate,
  health,
}: {
  projectId: string | null;
  navigate: (p: string) => void;
  health: Health | null;
}) {
  const summary = useAsync<ResultsSummary>(() => api.resultsSummary(projectId ?? undefined), [projectId], 10000);
  const s = summary.data;
  const ai = s?.conditions.ai_only;
  const gc = s?.conditions.greencode;
  const hasData = !!s && s.total_runs > 0;

  const rows: Row[] = [
    {
      hyp: "H1",
      label: "Correctness rate",
      hint: "verified ÷ generated",
      ai: ai?.correctness_rate,
      gc: gc?.correctness_rate,
      format: fmt.rate,
      better: "higher",
      diff: (a, g) => `${g - a >= 0 ? "+" : "−"}${Math.abs((g - a) * 100).toFixed(0)} pp`,
    },
    {
      hyp: "H2",
      label: "Geomean speed-up",
      hint: "verified candidates only",
      ai: ai?.geomean_speedup,
      gc: gc?.geomean_speedup,
      format: fmt.x,
      better: "higher",
      diff: (a, g) => `${g - a >= 0 ? "+" : "−"}${Math.abs(g - a).toFixed(2)}×`,
    },
    {
      hyp: "H3",
      label: "Geomean energy ratio",
      hint: "original ÷ candidate energy",
      ai: ai?.geomean_energy_ratio,
      gc: gc?.geomean_energy_ratio,
      format: fmt.x,
      better: "higher",
      diff: (a, g) => `${g - a >= 0 ? "+" : "−"}${Math.abs(g - a).toFixed(2)}×`,
    },
    {
      label: "Significantly faster",
      hint: "share of benchmarked candidates",
      ai: ai && ai.benchmarked ? ai.faster_significant / ai.benchmarked : null,
      gc: gc && gc.benchmarked ? gc.faster_significant / gc.benchmarked : null,
      format: fmt.rate,
      better: "higher",
      diff: (a, g) => `${g - a >= 0 ? "+" : "−"}${Math.abs((g - a) * 100).toFixed(0)} pp`,
    },
    {
      label: "Unchanged candidates",
      hint: "model returned the code as it was",
      ai: ai && ai.runs ? ai.unchanged / ai.runs : null,
      gc: gc && gc.runs ? gc.unchanged / gc.runs : null,
      format: fmt.rate,
      better: "lower",
      diff: (a, g) => `${g - a >= 0 ? "+" : "−"}${Math.abs((g - a) * 100).toFixed(0)} pp`,
    },
  ];

  return (
    <div className="stack">
      <PageHeader
        title="Overview"
        lede="Don't just optimise. Prove the impact. GreenCode finds inefficient Python and SQL, asks a local model to fix it, checks the result is correct, and measures what changed."
        actions={
          <>
            <button onClick={() => navigate("/experiments")}>Run experiments</button>
            <button className="primary" onClick={() => navigate("/analyse")}>
              Analyse code
            </button>
          </>
        }
      />

      <ErrorBox error={summary.error} onRetry={() => void summary.reload()} />
      <Readiness health={health} />

      {summary.loading && !s ? (
        <LoadingBlock label="Loading results" rows={4} />
      ) : !hasData ? (
        <GettingStarted navigate={navigate} />
      ) : (
        <>
          <Section
            id="compare"
            title="AI-only vs GreenCode"
            hint={`${s.total_runs} pipeline runs ${projectId ? "in this project" : "across all projects"}`}
          >
            <div className="grid wide-left">
              <div className="panel flush">
                <div className="table-wrap" role="region" aria-label="Condition comparison" tabIndex={0}>
                  <table className="compare-table">
                    <thead>
                      <tr>
                        <th>Measure</th>
                        <th className="num">AI-only</th>
                        <th className="num">GreenCode</th>
                        <th className="num">Difference</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => {
                        const both = r.ai != null && r.gc != null;
                        const gcBetter = both && (r.better === "higher" ? r.gc! > r.ai! : r.gc! < r.ai!);
                        const aiBetter = both && (r.better === "higher" ? r.ai! > r.gc! : r.ai! < r.gc!);
                        return (
                          <tr key={r.label}>
                            <td>
                              <div>
                                {r.label} {r.hyp && <Badge>{r.hyp}</Badge>}
                              </div>
                              <div className="muted small">{r.hint}</div>
                            </td>
                            <td className={`num ${aiBetter ? "winner" : ""}`}>{r.ai == null ? "–" : r.format(r.ai)}</td>
                            <td className={`num ${gcBetter ? "winner" : ""}`}>{r.gc == null ? "–" : r.format(r.gc)}</td>
                            <td className="num muted">{both ? r.diff(r.ai!, r.gc!) : "–"}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="stack-sm">
                <ConditionBars
                  title="Share of runs by outcome"
                  items={[
                    { label: "Correct", ai_only: ai?.correctness_rate ?? null, greencode: gc?.correctness_rate ?? null },
                    { label: "Significantly faster", ai_only: rows[3].ai ?? null, greencode: rows[3].gc ?? null },
                    { label: "Unchanged", ai_only: rows[4].ai ?? null, greencode: rows[4].gc ?? null },
                  ]}
                  format={(v) => `${(v * 100).toFixed(0)}%`}
                  max={1}
                />
                <Legend items={[{ label: "AI-only", color: "ai_only" }, { label: "GreenCode (guided by static analysis)", color: "greencode" }]} />
              </div>
            </div>
            <p className="muted small" style={{ marginTop: 10 }}>
              Better values are highlighted. <Term id="geomean">Geomean</Term> is the geometric mean of per-case ratios. Energy values may be{" "}
              <Term id="estimated">estimated</Term> rather than <Term id="measured">measured</Term>; each run records which.
            </p>
          </Section>

          <Section id="hypotheses" title="Hypotheses" hint="α = 0.05">
            <div className="panel">
              <HypothesisList summary={s} />
            </div>
          </Section>
        </>
      )}

      {health && (
        <details className="disclosure">
          <summary>System details</summary>
          <div className="disclosure-body">
            <dl className="dl">
              <dt>Database</dt>
              <dd>{health.database ? "connected" : "unreachable"}</dd>
              <dt>Model</dt>
              <dd>
                {health.llm.provider} · {health.llm.model ?? health.settings.model}
                {health.llm.error && <span className="muted"> ({health.llm.error})</span>}
              </dd>
              <dt>Energy source</dt>
              <dd>
                {health.energy.selected} · <Term id="lhm">LibreHardwareMonitor</Term> {health.energy.lhm ? "running" : "not running"} · CodeCarbon {health.energy.codecarbon ? "installed" : "not installed"}
              </dd>
              <dt>Benchmark</dt>
              <dd>
                {health.settings.repetitions} repetitions, {health.settings.warmup} warm-up, carbon region {health.settings.region}
              </dd>
            </dl>
          </div>
        </details>
      )}
    </div>
  );
}

/** Tells the user what is not ready and exactly how to fix it. Renders nothing when everything is fine. */
function Readiness({ health }: { health: Health | null }) {
  if (!health) return null; // the API-offline error is already shown by ErrorBox
  if (!health.database) {
    return (
      <Alert kind="error" title="The database is not reachable">
        GreenCode stores all evidence in PostgreSQL. Check that the server is running and that <code>GREENCODE_DATABASE_URL</code> in <code>backend/.env</code> is correct.
      </Alert>
    );
  }
  if (health.llm.provider === "mock") {
    return (
      <Alert kind="warn" title="Using the mock model">
        The mock provider returns your code unchanged, so results are not meaningful. Set <code>GREENCODE_LLM_PROVIDER=ollama</code> for real experiments.
      </Alert>
    );
  }
  if (!health.llm.ok) {
    return (
      <Alert kind="warn" title={`${health.llm.provider} is not running`}>
        <div className="stack-sm">
          <span>Optimisations need a local model. Start Ollama, then reload this page.</span>
          <Command>ollama serve</Command>
        </div>
      </Alert>
    );
  }
  if (health.llm.model_available === false) {
    return (
      <Alert kind="warn" title={`Model ${health.settings.model} is not downloaded`}>
        <div className="stack-sm">
          <span>Download it once (about 5 GB), then reload this page.</span>
          <Command>{`ollama pull ${health.settings.model}`}</Command>
        </div>
      </Alert>
    );
  }
  return null;
}

function GettingStarted({ navigate }: { navigate: (p: string) => void }) {
  return (
    <Section id="start" title="Get started" hint="No experiment data yet">
      <div className="panel">
        <ol className="numbered">
          <li>
            <div>
              <strong>Try one piece of code.</strong>
              <p className="muted">Paste a Python function or SQL query, see which inefficiency rules fire, then optimise it with and without the findings.</p>
              <div style={{ marginTop: 8 }}>
                <button className="primary" onClick={() => navigate("/analyse")}>
                  Analyse code <Icon name="arrow-right" size={16} />
                </button>
              </div>
            </div>
          </li>
          <li>
            <div>
              <strong>Run the whole benchmark suite.</strong>
              <p className="muted">30 prepared cases run under both conditions. This is the data your hypotheses are tested on.</p>
              <div style={{ marginTop: 8 }}>
                <button onClick={() => navigate("/experiments")}>Open experiments</button>
              </div>
            </div>
          </li>
          <li>
            <div>
              <strong>Read the evidence.</strong>
              <p className="muted">This page then compares AI-only and GreenCode and reports whether H1 to H4 are supported so far.</p>
            </div>
          </li>
        </ol>
      </div>
    </Section>
  );
}

const HYP_TEXT: Record<string, string> = {
  H1: "Static-analysis-guided AI produces a higher proportion of functionally correct optimisations than AI-only.",
  H2: "Static-analysis-guided AI produces greater average execution-time improvements than AI-only.",
  H3: "Static-analysis-guided AI produces greater average energy-efficiency improvements than AI-only.",
  H4: "A reduction in execution time does not always correspond to an equivalent reduction in energy consumption.",
};

export function HypothesisList({ summary }: { summary: ResultsSummary }) {
  const h = summary.hypotheses;
  const detail = (id: keyof typeof h) => {
    const d = h[id] as Record<string, number | boolean | null | undefined>;
    switch (id) {
      case "H1":
        return `AI-only ${fmt.rate(d.ai_only_rate as number)} vs GreenCode ${fmt.rate(d.greencode_rate as number)} · Fisher ${fmt.p(d.fisher_p as number)}`;
      case "H2":
        return `${d.paired_cases} paired cases · geomean speed-up ${fmt.x(d.ai_only_geomean as number)} vs ${fmt.x(d.greencode_geomean as number)} · Wilcoxon ${fmt.p(d.wilcoxon_p as number)}`;
      case "H3":
        return `${d.paired_cases} paired cases · geomean energy ratio ${fmt.x(d.ai_only_geomean as number)} vs ${fmt.x(d.greencode_geomean as number)} · Wilcoxon ${fmt.p(d.wilcoxon_p as number)}`;
      case "H4":
        return `${d.cases} cases · median |Δtime − Δenergy| ${fmt.num(d.median_divergence_pp as number, 1)} pp · ${d.cases_diverging_over_10pp ?? 0} diverge by more than 10 pp · Spearman ρ ${fmt.num(d.spearman_rho as number)} (${fmt.p(d.spearman_p as number)})`;
    }
  };
  return (
    <div className="divided">
      {(["H1", "H2", "H3", "H4"] as const).map((id) => (
        <div className="hyp" key={id}>
          <div className="hyp-id">{id}</div>
          <div>
            <div className="hyp-text">{HYP_TEXT[id]}</div>
            <div className="hyp-stats">{detail(id)}</div>
          </div>
          <Badge kind={h[id].supported ? "ok" : "warn"}>{h[id].supported ? "Supported so far" : "Not supported yet"}</Badge>
        </div>
      ))}
      <div className="muted small" style={{ paddingTop: 12 }}>
        H2 and H3 use a one-sided paired <Term id="wilcoxon">Wilcoxon</Term> test on log ratios (needs at least 5 paired cases). H1 uses a one-sided{" "}
        <Term id="fisher">Fisher exact</Term> test.
      </div>
    </div>
  );
}
