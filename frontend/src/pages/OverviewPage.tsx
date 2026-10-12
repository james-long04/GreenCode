import { api } from "../api";
import { ConditionBars, Legend } from "../components/charts";
import { Badge, Empty, ErrorBox, Stat, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { Health, ResultsSummary } from "../types";

export function OverviewPage({ projectId, navigate }: { projectId: string | null; navigate: (p: string) => void }) {
  const health = useAsync<Health>(() => api.health(), [], 15000);
  const summary = useAsync<ResultsSummary>(() => api.resultsSummary(projectId ?? undefined), [projectId], 10000);
  const s = summary.data;
  const ai = s?.conditions.ai_only;
  const gc = s?.conditions.greencode;

  return (
    <div>
      <h1>GreenCode</h1>
      <div className="subtitle">Don't just optimise. Prove the impact. — Detect → Explain → Optimise → Test → Benchmark → Measure → Verify</div>
      <ErrorBox error={health.error ?? summary.error} />

      <div className="grid four">
        <Stat label="Pipeline runs" value={s?.total_runs ?? "–"} hint={projectId ? "in selected project" : "across all projects"} />
        <Stat
          label="Correctness · AI-only vs GreenCode"
          value={`${fmt.rate(ai?.correctness_rate)} · ${fmt.rate(gc?.correctness_rate)}`}
          hint="verified / generated (H1)"
        />
        <Stat
          label="Geomean speed-up · AI-only vs GreenCode"
          value={`${fmt.x(ai?.geomean_speedup)} · ${fmt.x(gc?.geomean_speedup)}`}
          hint="verified candidates only (H2)"
        />
        <Stat
          label="Geomean energy ratio · AI-only vs GreenCode"
          value={`${fmt.x(ai?.geomean_energy_ratio)} · ${fmt.x(gc?.geomean_energy_ratio)}`}
          hint="original ÷ candidate energy (H3)"
        />
      </div>

      <div className="grid two" style={{ marginTop: 18 }}>
        <div className="card">
          <h3>Condition comparison</h3>
          {s && s.total_runs > 0 ? (
            <>
              <ConditionBars
                items={[
                  { label: "Correctness rate", ai_only: ai?.correctness_rate ?? null, greencode: gc?.correctness_rate ?? null },
                  { label: "Significantly faster", ai_only: ai && ai.benchmarked ? ai.faster_significant / ai.benchmarked : null, greencode: gc && gc.benchmarked ? gc.faster_significant / gc.benchmarked : null },
                  { label: "Unchanged candidates", ai_only: ai && ai.runs ? ai.unchanged / ai.runs : null, greencode: gc && gc.runs ? gc.unchanged / gc.runs : null },
                ]}
                format={(v) => `${(v * 100).toFixed(0)}%`}
                max={1}
              />
              <Legend items={[{ label: "AI-only", color: "ai_only" }, { label: "GreenCode (static-analysis guided)", color: "greencode" }]} />
            </>
          ) : (
            <Empty>No experiment data yet. Run the benchmark suite from the Experiments page.</Empty>
          )}
        </div>
        <div className="card">
          <h3>System</h3>
          {health.data ? (
            <div className="checks">
              <div>
                <Badge kind={health.data.database ? "ok" : "bad"}>database</Badge> evidence store
              </div>
              <div>
                <Badge kind={health.data.llm.ok ? "ok" : "bad"}>{health.data.llm.provider}</Badge> {health.data.llm.model ?? health.data.settings.model}
                {health.data.llm.ok && health.data.llm.model_available === false && <span className="muted"> (model not pulled)</span>}
                {health.data.llm.error && <span className="muted"> {health.data.llm.error}</span>}
              </div>
              <div>
                <Badge kind="info">energy</Badge> {health.data.energy.selected}
                <span className="muted"> · RAPL {health.data.energy.rapl ? "available" : "n/a"} · CodeCarbon {health.data.energy.codecarbon ? "installed" : "n/a"}</span>
              </div>
              <div>
                <Badge>benchmark</Badge> {health.data.settings.repetitions} reps · {health.data.settings.warmup} warm-up · region {health.data.settings.region}
              </div>
            </div>
          ) : (
            <Empty>API unreachable</Empty>
          )}
          <div className="row" style={{ marginTop: 16 }}>
            <button className="primary" onClick={() => navigate("/analyse")}>Analyse code</button>
            <button onClick={() => navigate("/experiments")}>Run experiments</button>
            <button onClick={() => navigate("/rules")}>Rule catalogue</button>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Hypotheses</h3>
        {s && s.total_runs > 0 ? (
          <HypothesisList summary={s} />
        ) : (
          <Empty>Hypothesis tests appear once at least one case has been run under both conditions.</Empty>
        )}
      </div>
    </div>
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
        return `${d.cases} cases · median |Δtime − Δenergy| ${fmt.num(d.median_divergence_pp as number, 1)} pp · ${d.cases_diverging_over_10pp ?? 0} diverge >10 pp · Spearman ρ ${fmt.num(d.spearman_rho as number)} (${fmt.p(d.spearman_p as number)})`;
    }
  };
  return (
    <div>
      {(["H1", "H2", "H3", "H4"] as const).map((id) => (
        <div className="hyp" key={id}>
          <div className="id">{id}</div>
          <div>
            <div>{HYP_TEXT[id]}</div>
            <div className="muted small">{detail(id)}</div>
          </div>
          <Badge kind={h[id].supported ? "ok" : "warn"}>{h[id].supported ? "supported so far" : "not supported yet"}</Badge>
        </div>
      ))}
      <div className="muted small" style={{ marginTop: 8 }}>
        Tests use α = 0.05. H2/H3 use a one-sided paired Wilcoxon on log ratios (requires ≥ 5 paired cases); H1 uses a one-sided Fisher exact test.
      </div>
    </div>
  );
}
