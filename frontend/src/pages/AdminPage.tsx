import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";

import { adminToken, api } from "../api";
import { Icon } from "../components/icons";
import {
  Alert,
  Badge,
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
import type { AdminModels, AdminOverview, AdminSettings, CarbonFactor, CarbonFactorInput, LogEntry, Project } from "../types";

const SECTIONS = [
  ["system", "System"],
  ["settings", "Settings"],
  ["models", "Models"],
  ["carbon", "Carbon factors"],
  ["maintenance", "Maintenance"],
  ["logs", "Server log"],
] as const;

const bytes = (v: number | null | undefined) => {
  if (v == null) return "–";
  if (v < 1e6) return `${(v / 1e3).toFixed(0)} kB`;
  if (v < 1e9) return `${(v / 1e6).toFixed(1)} MB`;
  return `${(v / 1e9).toFixed(2)} GB`;
};

const unauthorised = (e: string | null) => !!e && /^401/.test(e);

export function AdminPage({ projectId }: { projectId: string | null }) {
  useDocumentTitle("Admin");
  const [tokenVersion, setTokenVersion] = useState(0);
  const overview = useAsync<AdminOverview>(() => api.admin.overview(), [tokenVersion], 15000);

  if (unauthorised(overview.error)) {
    return (
      <div className="stack">
        <PageHeader title="Admin" lede="Operating the server needs the admin token." />
        <TokenForm onSaved={() => setTokenVersion((v) => v + 1)} wrong={!!adminToken.get()} />
      </div>
    );
  }

  return (
    <div className="stack">
      <PageHeader
        title="Admin"
        lede="Operate the evidence store and the pipeline. Nothing here changes the method: prompts, rules and statistics are fixed in code."
        actions={
          <>
            <a className="btn" href={api.admin.exportUrl(projectId ?? undefined)} download>
              <Icon name="download-simple" />
              Export results CSV
            </a>
            <button className="quiet" onClick={() => void overview.reload()} aria-label="Refresh admin data">
              <Icon name="arrow-clockwise" />
              Refresh
            </button>
            <button className="quiet" onClick={() => { adminToken.set(""); setTokenVersion((v) => v + 1); }}>
              Lock
            </button>
          </>
        }
      />
      <nav aria-label="On this page">
        <ul className="subnav">
          {SECTIONS.map(([id, label]) => (
            <li key={id}>
              <a href={`#/admin`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ block: "start" }); document.getElementById(`${id}-h`)?.focus(); }}>
                {label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <ErrorBox error={overview.error} onRetry={() => void overview.reload()} />

      <SystemSection data={overview.data} />
      <SettingsSection onChanged={() => void overview.reload()} />
      <ModelsSection />
      <CarbonSection />
      <MaintenanceSection overview={overview.data} projectId={projectId} onChanged={() => void overview.reload()} />
      <LogsSection />
    </div>
  );
}

// --- token ------------------------------------------------------------------

function TokenForm({ onSaved, wrong }: { onSaved: () => void; wrong: boolean }) {
  const [value, setValue] = useState("");
  return (
    <form
      className="panel stack-sm"
      style={{ maxWidth: 520 }}
      onSubmit={(e) => {
        e.preventDefault();
        adminToken.set(value.trim());
        onSaved();
      }}
    >
      {wrong && <Alert kind="error">That token was not accepted. If the server restarted without GREENCODE_ADMIN_TOKEN set, it printed a new one.</Alert>}
      <label className="field">
        Admin token
        <span className="help">
          The value of <code>GREENCODE_ADMIN_TOKEN</code> in the backend environment. If it is not set, the backend prints a random token in its terminal at startup. Stored in this browser only.
        </span>
        <input type="password" value={value} onChange={(e) => setValue(e.target.value)} autoComplete="off" required />
      </label>
      <div>
        <button className="primary" type="submit" disabled={!value.trim()}>
          <Icon name="shield-check" />
          Unlock admin
        </button>
      </div>
    </form>
  );
}

// --- system -----------------------------------------------------------------

function SystemSection({ data }: { data: AdminOverview | null }) {
  if (!data) {
    return (
      <Section title="System" id="system">
        <LoadingBlock label="Loading system status" rows={4} />
      </Section>
    );
  }
  const { store, llm, energy, host } = data;
  const statuses = Object.entries(store.optimisations_by_status)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${v} ${fmt.label(k)}`)
    .join(", ");
  const modelOk = llm.ok && llm.model_available !== false;
  return (
    <Section title="System" id="system">
      <div className="stack-sm">
        {data.admin_token_generated && (
          <Alert kind="info" title="Using a temporary admin token">
            The backend generated this token because <code>GREENCODE_ADMIN_TOKEN</code> is not set. It changes on every restart; set the variable in <code>backend/.env</code> to keep one.
          </Alert>
        )}
        {store.stuck_optimisations > 0 && (
          <Alert
            kind="warn"
            title={`${store.stuck_optimisations} optimisation${store.stuck_optimisations === 1 ? "" : "s"} stuck`}
            action={
              <a className="btn small" href="#/admin" onClick={(e) => { e.preventDefault(); document.getElementById("maintenance")?.scrollIntoView(); }}>
                Go to maintenance
              </a>
            }
          >
            Still marked as running after 30 minutes without progress. Usually the server restarted mid-pipeline.
          </Alert>
        )}
        <div className="metrics">
          <Metric label="Optimisations" value={store.counts.optimisations} note={statuses || "none yet"} />
          <Metric label="Benchmark runs" value={store.counts.benchmark_runs} note={`${store.counts.measurements} measurements`} />
          <Metric label="Analyses" value={store.counts.analyses} note={`${store.counts.findings} findings in ${store.counts.projects} project${store.counts.projects === 1 ? "" : "s"}`} />
          <Metric label="Evidence store" value={bytes(store.database_bytes)} note={store.postgres_version ? `PostgreSQL ${store.postgres_version}` : "size unknown"} />
        </div>
        <div className="grid two">
          <div className="panel">
            <h3>Pipeline</h3>
            <dl className="dl" style={{ marginTop: 10 }}>
              <dt>Provider</dt>
              <dd>
                {llm.provider} <Badge kind={llm.ok ? "ok" : "bad"}>{llm.ok ? "Reachable" : "Unreachable"}</Badge>
              </dd>
              <dt>Model</dt>
              <dd>
                {llm.model ?? "–"} {llm.ok && <Badge kind={modelOk ? "ok" : "warn"}>{modelOk ? "Installed" : "Not pulled"}</Badge>}
              </dd>
              {llm.error && (
                <>
                  <dt>Error</dt>
                  <dd className="muted">{llm.error}</dd>
                </>
              )}
              <dt>Energy method</dt>
              <dd>
                {energy.selected} <span className="muted">(configured: {energy.configured})</span>
              </dd>
              <dt>
                <Term id="rapl">RAPL</Term>
              </dt>
              <dd>{energy.rapl ? "Available" : "Not available"}</dd>
              <dt>CodeCarbon</dt>
              <dd>{energy.codecarbon ? "Available" : "Not installed"}</dd>
              <dt>Runs recorded</dt>
              <dd>{store.first_run ? `${fmt.date(store.first_run)} to ${fmt.date(store.last_run)}` : "none yet"}</dd>
            </dl>
          </div>
          <div className="panel">
            <h3>Host</h3>
            <dl className="dl" style={{ marginTop: 10 }}>
              <dt>Platform</dt>
              <dd>{host.platform}</dd>
              <dt>Python</dt>
              <dd>{host.python}</dd>
              <dt>CPU</dt>
              <dd>
                {host.physical_cores ?? "?"} cores ({host.logical_cores ?? "?"} logical), {host.cpu_percent.toFixed(0)}% busy
              </dd>
              <dt>Memory</dt>
              <dd>
                {host.memory_total_gb} GB, {host.memory_used_percent.toFixed(0)}% used
              </dd>
              <dt>Database</dt>
              <dd className="mono">{store.database_url}</dd>
              <dt>Process</dt>
              <dd>
                pid {host.pid} in <span className="mono">{host.cwd}</span>
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </Section>
  );
}

// --- settings ---------------------------------------------------------------

const SETTING_HELP: Record<string, string> = {
  llm_provider: "ollama runs a local model; mock returns canned output for tests.",
  ollama_model: "Model tag passed to Ollama. Must be pulled first (see Models).",
  ollama_base_url: "Where the Ollama server listens.",
  llm_temperature: "0 keeps generation deterministic, which the method relies on.",
  llm_seed: "Seed sent with every generation request.",
  benchmark_warmup_runs: "Runs discarded before timing starts.",
  benchmark_repetitions: "Timed runs per variant. More runs, tighter confidence intervals, longer suite.",
  benchmark_timeout_seconds: "Hard stop for one benchmark variant.",
  energy_method: "auto picks RAPL, then CodeCarbon, then the coefficient estimate.",
  carbon_factor_region: "Region code of the carbon factor used for CO₂e.",
  estimate_cpu_tdp_watts: "CPU TDP used by the coefficient estimate only.",
  estimate_pue: "Power usage effectiveness multiplier for the estimate (1.0 for a laptop).",
  sandbox_timeout_seconds: "Wall-clock limit for one verification run.",
  sandbox_memory_limit_mb: "Memory cap for the verification sandbox.",
};

const SETTING_OPTIONS: Record<string, string[]> = {
  llm_provider: ["ollama", "mock"],
  energy_method: ["auto", "rapl", "codecarbon", "estimate"],
};

function SettingsSection({ onChanged }: { onChanged: () => void }) {
  const q = useAsync<AdminSettings>(() => api.admin.settings(), []);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (q.data) setDraft(Object.fromEntries(q.data.adjustable.map((k) => [k, String(q.data!.values[k] ?? "")])));
  }, [q.data]);

  const changed = useMemo(() => {
    if (!q.data) return {};
    const out: Record<string, unknown> = {};
    for (const k of q.data.adjustable) {
      const current = String(q.data.values[k] ?? "");
      if (draft[k] !== undefined && draft[k] !== current) {
        const v = q.data.values[k];
        out[k] = typeof v === "number" ? Number(draft[k]) : draft[k];
      }
    }
    return out;
  }, [draft, q.data]);
  const dirty = Object.keys(changed).length > 0;

  const apply = async (e: FormEvent) => {
    e.preventDefault();
    if (!dirty) return;
    setBusy(true);
    setErr(null);
    try {
      await api.admin.updateSettings(changed);
      await q.reload();
      setSaved(`Applied ${Object.keys(changed).length} change${Object.keys(changed).length === 1 ? "" : "s"}. They last until the server restarts.`);
      onChanged();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    setBusy(true);
    setErr(null);
    try {
      await api.admin.resetSettings();
      await q.reload();
      setSaved("Overrides cleared. The environment values are in effect again.");
      onChanged();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const overrideCount = Object.keys(q.data?.overrides ?? {}).length;
  const fixed = q.data ? Object.entries(q.data.values).filter(([k]) => !q.data!.adjustable.includes(k)) : [];

  return (
    <Section
      title="Settings"
      hint={overrideCount ? `${overrideCount} overridden at runtime` : "Environment values in effect"}
      id="settings"
      actions={
        overrideCount > 0 && (
          <button className="small quiet" onClick={() => void reset()} disabled={busy}>
            Clear overrides
          </button>
        )
      }
    >
      {q.error && <ErrorBox error={q.error} onRetry={() => void q.reload()} />}
      {!q.data ? (
        <LoadingBlock label="Loading settings" rows={4} />
      ) : (
        <form className="stack-sm" onSubmit={(e) => void apply(e)}>
          <p className="muted" style={{ maxWidth: "75ch" }}>
            Changes apply to this server process only; a restart reverts to the environment. Every optimisation records the values it ran with, so earlier evidence is unaffected.
          </p>
          <div className="panel settings-grid">
            {q.data.adjustable.map((k) => {
              const current = q.data!.values[k];
              const isNumber = typeof current === "number";
              const overridden = k in q.data!.overrides;
              const options = SETTING_OPTIONS[k];
              return (
                <label className="field" key={k}>
                  <span className="field-head">
                    <span className="mono">{k}</span>
                    {overridden && <Badge kind="info">Overridden</Badge>}
                  </span>
                  {SETTING_HELP[k] && <span className="help">{SETTING_HELP[k]}</span>}
                  {options ? (
                    <select value={draft[k] ?? ""} onChange={(e) => setDraft((d) => ({ ...d, [k]: e.target.value }))}>
                      {options.map((o) => (
                        <option key={o} value={o}>
                          {o}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={isNumber ? "number" : "text"}
                      step={isNumber && !Number.isInteger(current) ? "any" : undefined}
                      value={draft[k] ?? ""}
                      onChange={(e) => setDraft((d) => ({ ...d, [k]: e.target.value }))}
                    />
                  )}
                </label>
              );
            })}
          </div>
          {err && <Alert kind="error">{err}</Alert>}
          {saved && !dirty && <Alert kind="ok">{saved}</Alert>}
          <div className="row">
            <button className="primary" type="submit" disabled={!dirty || busy}>
              {busy ? <Spinner /> : <Icon name="check" />}
              Apply {dirty ? `${Object.keys(changed).length} change${Object.keys(changed).length === 1 ? "" : "s"}` : "changes"}
            </button>
            {dirty && (
              <button type="button" className="quiet" onClick={() => setDraft(Object.fromEntries(q.data!.adjustable.map((k) => [k, String(q.data!.values[k] ?? "")])))}>
                Discard
              </button>
            )}
          </div>
          <details className="disclosure">
            <summary>Fixed settings ({fixed.length}), read from the environment only</summary>
            <div className="disclosure-body">
              <dl className="dl">
                {fixed.map(([k, v]) => (
                  <div key={k} style={{ display: "contents" }}>
                    <dt className="mono">{k}</dt>
                    <dd className="mono">{Array.isArray(v) ? v.join(", ") : String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </details>
        </form>
      )}
    </Section>
  );
}

// --- models -----------------------------------------------------------------

function ModelsSection() {
  const q = useAsync<AdminModels>(() => api.admin.models(), []);
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const pulling = q.data?.pulls.some((p) => p.status === "running") ?? false;

  useEffect(() => {
    if (!pulling) return undefined;
    const id = window.setInterval(() => void q.reload(), 2000);
    return () => window.clearInterval(id);
  }, [pulling, q]);

  const pull = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setErr(null);
    try {
      await api.admin.pullModel(name.trim());
      setName("");
      await q.reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    }
  };

  const use = async (model: string) => {
    setBusy(model);
    setErr(null);
    try {
      await api.admin.updateSettings({ ollama_model: model });
      await q.reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Section title="Models" hint={q.data ? `${q.data.health.provider}${q.data.health.ok ? "" : ", unreachable"}` : undefined} id="models">
      {q.error && <ErrorBox error={q.error} onRetry={() => void q.reload()} />}
      {!q.data ? (
        <LoadingBlock label="Loading models" />
      ) : (
        <div className="grid wide-left">
          <div className="stack-sm">
            {!q.data.health.ok && (
              <Alert kind="warn" title={`${q.data.health.provider} is not reachable`}>
                {q.data.health.error ?? "Start Ollama, then refresh."}
              </Alert>
            )}
            {q.data.installed.length ? (
              <div className="panel flush">
                <TableWrap label="Installed models">
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Parameters</th>
                        <th>Quantisation</th>
                        <th className="num">Size</th>
                        <th>Updated</th>
                        <th>
                          <span className="sr-only">Actions</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {q.data.installed.map((m) => {
                        const active = m.name === q.data!.configured;
                        return (
                          <tr key={m.name}>
                            <td>
                              <span className="mono">{m.name}</span> {active && <Badge kind="ok">In use</Badge>}
                            </td>
                            <td>{m.parameter_size ?? "–"}</td>
                            <td>{m.quantization ?? "–"}</td>
                            <td className="num">{bytes(m.size_bytes)}</td>
                            <td className="muted">{fmt.date(m.modified_at)}</td>
                            <td>
                              {!active && (
                                <button className="small" onClick={() => void use(m.name)} disabled={busy === m.name}>
                                  {busy === m.name ? <Spinner size={14} /> : null}
                                  Use
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </TableWrap>
              </div>
            ) : (
              q.data.health.ok && <Empty title="No models installed">Pull one with the form. The method used qwen2.5-coder:7b.</Empty>
            )}
            {q.data.pulls.map((p) => {
              const pct = p.total_bytes && p.completed_bytes != null ? (100 * p.completed_bytes) / p.total_bytes : null;
              return (
                <div key={p.name} className="panel stack-sm">
                  <div className="row spread">
                    <span>
                      <span className="mono">{p.name}</span>{" "}
                      <Badge kind={p.status === "completed" ? "ok" : p.status === "failed" ? "bad" : "warn"}>{p.status}</Badge>
                    </span>
                    <span className="muted">{p.detail}{pct != null ? `, ${pct.toFixed(0)}%` : ""}</span>
                  </div>
                  {p.status === "running" && (
                    <div className="progress" role="progressbar" aria-label={`Pulling ${p.name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct ?? undefined}>
                      <div style={{ width: `${pct ?? 2}%` }} />
                    </div>
                  )}
                  {p.error && <Alert kind="error">{p.error}</Alert>}
                </div>
              );
            })}
          </div>
          <form className="panel stack-sm" onSubmit={(e) => void pull(e)}>
            <h3>Pull a model</h3>
            <label className="field">
              Model tag
              <span className="help">As listed on ollama.com, for example qwen2.5-coder:7b.</span>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="qwen2.5-coder:7b" required />
            </label>
            {err && <Alert kind="error">{err}</Alert>}
            <div>
              <button className="primary" type="submit" disabled={!name.trim() || !q.data.health.ok || pulling}>
                {pulling ? <Spinner /> : <Icon name="download-simple" />}
                {pulling ? "Pull in progress" : "Pull"}
              </button>
            </div>
            <p className="muted">A 7B model is about 4.5 GB. The pull keeps going if you leave this page.</p>
          </form>
        </div>
      )}
    </Section>
  );
}

// --- carbon factors ---------------------------------------------------------

const EMPTY_FACTOR: CarbonFactorInput = { region: "", year: new Date().getFullYear(), grams_co2e_per_kwh: 0, source: "", notes: null, is_default: false };

function CarbonSection() {
  const q = useAsync<CarbonFactor[]>(() => api.carbonFactors(), []);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<CarbonFactorInput>(EMPTY_FACTOR);
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      await q.reload();
      setEditing(null);
      setAdding(false);
      setConfirming(null);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message.replace(/^\d+:\s*/, "") : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const startEdit = (f: CarbonFactor) => {
    setAdding(false);
    setEditing(f.id);
    setDraft({ region: f.region, year: f.year, grams_co2e_per_kwh: f.grams_co2e_per_kwh, source: f.source, notes: f.notes, is_default: f.is_default });
  };

  const makeDefault = (f: CarbonFactor) =>
    run(() => api.admin.updateCarbonFactor(f.id, { region: f.region, year: f.year, grams_co2e_per_kwh: f.grams_co2e_per_kwh, source: f.source, notes: f.notes, is_default: true }));

  const valid = draft.region.trim() && draft.source.trim() && draft.grams_co2e_per_kwh > 0 && draft.year >= 1990;

  const editor = (key: string, onSave: () => void, label: string) => (
    <tr key={key}>
      <td colSpan={6}>
        <form
          className="stack-sm"
          onSubmit={(e) => {
            e.preventDefault();
            onSave();
          }}
          aria-label={label}
        >
          <div className="settings-grid">
            <label className="field">
              Region code
              <input value={draft.region} onChange={(e) => setDraft({ ...draft, region: e.target.value.toUpperCase() })} maxLength={16} placeholder="IE" required />
            </label>
            <label className="field">
              Year
              <input type="number" min={1990} max={2100} value={draft.year} onChange={(e) => setDraft({ ...draft, year: Number(e.target.value) })} required />
            </label>
            <label className="field">
              Grams CO₂e per kWh
              <input type="number" min={0} step="any" value={draft.grams_co2e_per_kwh || ""} onChange={(e) => setDraft({ ...draft, grams_co2e_per_kwh: Number(e.target.value) })} required />
            </label>
            <label className="field">
              Source
              <span className="help">Where the figure comes from, so every CO₂e value is citable.</span>
              <input value={draft.source} onChange={(e) => setDraft({ ...draft, source: e.target.value })} maxLength={300} required />
            </label>
            <label className="field" style={{ gridColumn: "1 / -1" }}>
              Notes
              <input value={draft.notes ?? ""} onChange={(e) => setDraft({ ...draft, notes: e.target.value || null })} />
            </label>
          </div>
          <div className="row">
            <button className="primary small" type="submit" disabled={!valid || busy}>
              {busy ? <Spinner size={14} /> : <Icon name="check" size={14} />}
              Save
            </button>
            <button className="small quiet" type="button" onClick={() => { setEditing(null); setAdding(false); }}>
              Cancel
            </button>
          </div>
        </form>
      </td>
    </tr>
  );

  return (
    <Section
      title="Carbon factors"
      hint="Convert energy to CO₂e"
      id="carbon"
      actions={
        <button className="small" onClick={() => { setEditing(null); setAdding(true); setDraft(EMPTY_FACTOR); }} disabled={adding}>
          <Icon name="plus" size={14} />
          Add factor
        </button>
      }
    >
      {q.error && <ErrorBox error={q.error} onRetry={() => void q.reload()} />}
      <div className="stack-sm">
        {err && <Alert kind="error">{err}</Alert>}
        {!q.data ? (
          <LoadingBlock label="Loading carbon factors" />
        ) : (
          <div className="panel flush">
            <TableWrap label="Carbon factors">
              <table>
                <thead>
                  <tr>
                    <th>Region</th>
                    <th>Year</th>
                    <th className="num">gCO₂e per kWh</th>
                    <th>Source</th>
                    <th>Notes</th>
                    <th>
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {adding && editor("new", () => void run(() => api.admin.createCarbonFactor(draft)), "New carbon factor")}
                  {q.data.map((f) =>
                    editing === f.id ? (
                      editor(f.id, () => void run(() => api.admin.updateCarbonFactor(f.id, draft)), `Edit ${f.region} ${f.year}`)
                    ) : (
                      <tr key={f.id}>
                        <td>
                          {f.region} {f.is_default && <Badge kind="ok">Default</Badge>}
                        </td>
                        <td>{f.year}</td>
                        <td className="num">{f.grams_co2e_per_kwh}</td>
                        <td>{f.source}</td>
                        <td className="muted">
                          {f.notes}
                          {confirming === f.id && (
                            <div className="row" style={{ marginTop: 6 }} role="group" aria-label={`Confirm deleting ${f.region} ${f.year}`}>
                              <span>Delete this factor?</span>
                              <button className="small danger" onClick={() => void run(() => api.admin.deleteCarbonFactor(f.id))} disabled={busy}>
                                Delete
                              </button>
                              <button className="small quiet" onClick={() => setConfirming(null)}>
                                Keep
                              </button>
                            </div>
                          )}
                        </td>
                        <td>
                          <div className="row" style={{ justifyContent: "flex-end", gap: 4 }}>
                            {!f.is_default && (
                              <button className="small quiet" onClick={() => void makeDefault(f)} disabled={busy}>
                                Make default
                              </button>
                            )}
                            <button className="small quiet icon-only" onClick={() => startEdit(f)} aria-label={`Edit ${f.region} ${f.year}`}>
                              <Icon name="pencil-simple" size={15} />
                            </button>
                            {!f.is_default && (
                              <button className="small quiet icon-only" onClick={() => setConfirming(f.id)} aria-label={`Delete ${f.region} ${f.year}`}>
                                <Icon name="trash" size={15} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </TableWrap>
          </div>
        )}
        <p className="muted" style={{ maxWidth: "75ch" }}>
          A factor that measurements already reference cannot change its value or be deleted. Add a new row instead, so old CO₂e figures stay traceable.
        </p>
      </div>
    </Section>
  );
}

// --- maintenance ------------------------------------------------------------

function MaintenanceSection({ overview, projectId, onChanged }: { overview: AdminOverview | null; projectId: string | null; onChanged: () => void }) {
  const projects = useAsync<Project[]>(() => api.projects(), []);
  const [minutes, setMinutes] = useState(30);
  const [target, setTarget] = useState(projectId ?? "");
  const [status, setStatus] = useState<"failed" | "rejected">("failed");
  const [confirm, setConfirm] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!target && projects.data?.length) setTarget(projectId ?? projects.data[0].id);
  }, [projects.data, projectId, target]);

  const act = async (label: string, fn: () => Promise<{ updated?: number; deleted?: number }>) => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fn();
      const n = r.updated ?? r.deleted ?? 0;
      setResult(`${label}: ${n} row${n === 1 ? "" : "s"} affected.`);
      setConfirm(null);
      onChanged();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  };

  const stuck = overview?.store.stuck_optimisations ?? 0;
  const orphans = overview?.store.orphan_analyses ?? 0;
  const projectName = projects.data?.find((p) => p.id === target)?.name ?? "the selected project";

  const Confirm = ({ id, children, onYes }: { id: string; children: ReactNode; onYes: () => void }) =>
    confirm === id ? (
      <div className="row" role="group" aria-label="Confirm">
        <span>{children}</span>
        <button className="small danger" onClick={onYes} disabled={busy}>
          {busy ? <Spinner size={14} /> : null}
          Confirm
        </button>
        <button className="small quiet" onClick={() => setConfirm(null)}>
          Cancel
        </button>
      </div>
    ) : null;

  return (
    <Section title="Maintenance" hint="Benchmarked evidence is never deleted here" id="maintenance">
      <div className="stack-sm">
        {err && <Alert kind="error">{err}</Alert>}
        {result && !err && <Alert kind="ok">{result}</Alert>}
        <div className="grid two">
          <div className="panel stack-sm">
            <h3>Stuck optimisations</h3>
            <p className="muted">
              Rows still marked pending, generated or verified with no progress. {overview ? `${stuck} right now.` : ""} Marking them failed lets the suite run again and keeps the record.
            </p>
            <div className="row">
              <label className="field">
                No progress for (minutes)
                <input type="number" min={1} value={minutes} onChange={(e) => setMinutes(Math.max(1, Number(e.target.value)))} style={{ width: 120 }} />
              </label>
            </div>
            {confirm === "stuck" ? (
              <Confirm id="stuck" onYes={() => void act("Marked stuck optimisations failed", () => api.admin.markStuckFailed(minutes))}>
                Mark every optimisation with no progress for {minutes} minutes as failed?
              </Confirm>
            ) : (
              <div>
                <button className="small" onClick={() => setConfirm("stuck")} disabled={busy}>
                  Mark stuck as failed
                </button>
              </div>
            )}
          </div>

          <div className="panel stack-sm">
            <h3>Analyses without optimisations</h3>
            <p className="muted">
              Analyses that were never optimised, usually from an interrupted suite or a cancelled form. {overview ? `${orphans} right now.` : ""} Their findings go with them.
            </p>
            {confirm === "orphans" ? (
              <Confirm id="orphans" onYes={() => void act("Deleted analyses without optimisations", () => api.admin.deleteOrphanAnalyses())}>
                Delete {orphans} analys{orphans === 1 ? "is" : "es"}?
              </Confirm>
            ) : (
              <div>
                <button className="small" onClick={() => setConfirm("orphans")} disabled={busy || orphans === 0}>
                  <Icon name="broom" size={14} />
                  Delete {orphans || ""} orphan analyses
                </button>
              </div>
            )}
          </div>

          <div className="panel stack-sm">
            <h3>Failed or rejected runs in a project</h3>
            <p className="muted">
              Remove runs that produced no benchmark, for example after fixing a sandbox problem and before re-running the suite. Benchmarked runs are untouched.
            </p>
            <div className="row">
              <label className="field">
                Project
                <select value={target} onChange={(e) => setTarget(e.target.value)} disabled={!projects.data?.length}>
                  {(projects.data ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Status
                <select value={status} onChange={(e) => setStatus(e.target.value as "failed" | "rejected")}>
                  <option value="failed">failed</option>
                  <option value="rejected">rejected</option>
                </select>
              </label>
            </div>
            {confirm === "runs" ? (
              <Confirm id="runs" onYes={() => void act(`Deleted ${status} runs in ${projectName}`, () => api.admin.deleteProjectRuns(target, status))}>
                Delete all {status} runs in {projectName}?
              </Confirm>
            ) : (
              <div>
                <button className="small" onClick={() => setConfirm("runs")} disabled={busy || !target}>
                  <Icon name="trash" size={14} />
                  Delete {status} runs
                </button>
              </div>
            )}
          </div>

          <div className="panel stack-sm">
            <h3>Export evidence</h3>
            <p className="muted">One row per optimisation with speed-up, significance, energy method and CO₂e, the same data the Experiments page shows. Use it for the dissertation tables.</p>
            <div className="row">
              <a className="btn small" href={api.admin.exportUrl()} download>
                <Icon name="download-simple" size={14} />
                All projects (CSV)
              </a>
              {target && (
                <a className="btn small quiet" href={api.admin.exportUrl(target)} download>
                  {projectName} only
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </Section>
  );
}

// --- logs -------------------------------------------------------------------

function LogsSection() {
  const [level, setLevel] = useState("");
  const [live, setLive] = useState(false);
  const q = useAsync<LogEntry[]>(() => api.admin.logs(200, level || undefined), [level], live ? 3000 : undefined);
  const rows = useMemo(() => [...(q.data ?? [])].reverse(), [q.data]);
  return (
    <Section
      title="Server log"
      hint="Last 200 records kept in memory"
      id="logs"
      actions={
        <>
          <label className="sr-only" htmlFor="log-level">
            Minimum level
          </label>
          <select id="log-level" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">All levels</option>
            <option value="INFO">Info and above</option>
            <option value="WARNING">Warnings and errors</option>
            <option value="ERROR">Errors only</option>
          </select>
          <button className="small quiet" onClick={() => setLive((v) => !v)} aria-pressed={live}>
            {live ? <Spinner size={14} /> : <Icon name="arrow-clockwise" size={14} />}
            {live ? "Live" : "Auto-refresh"}
          </button>
        </>
      }
    >
      {q.error && <ErrorBox error={q.error} onRetry={() => void q.reload()} />}
      {!q.data ? (
        <LoadingBlock label="Loading log" />
      ) : rows.length ? (
        <div className="panel flush">
          <ol className="log" aria-label="Server log, newest first" aria-live={live ? "polite" : undefined}>
            {rows.map((r, i) => (
              <li key={`${r.time}-${i}`} data-level={r.level}>
                <span className="log-time">{new Date(r.time).toLocaleTimeString()}</span>
                <span className="log-level">{r.level}</span>
                <span className="log-msg">
                  <span className="muted">{r.logger}</span> {r.message}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : (
        <Empty title="Nothing logged yet">Records appear here as the server works. Start a pipeline run to see it.</Empty>
      )}
    </Section>
  );
}
