import type {
  AdminModels,
  AdminOverview,
  AdminSettings,
  CarbonFactorInput,
  LogEntry,
  ModelPull,
  Analysis,
  AnalysisSummary,
  CarbonFactor,
  Condition,
  Health,
  Language,
  Optimisation,
  OptimisationSummary,
  Project,
  ResultRow,
  ResultsSummary,
  Rule,
  SuiteCase,
  SuiteJob,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api";

const ADMIN_TOKEN_KEY = "greencode.adminToken";

export const adminToken = {
  get: (): string => {
    try {
      return localStorage.getItem(ADMIN_TOKEN_KEY) ?? "";
    } catch {
      return "";
    }
  },
  set: (value: string) => {
    try {
      if (value) localStorage.setItem(ADMIN_TOKEN_KEY, value);
      else localStorage.removeItem(ADMIN_TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = adminToken.get();
  if (path.startsWith("/admin") && token) headers["X-Admin-Token"] = token;
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const qs = (params: Record<string, string | number | undefined | null>) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  health: () => request<Health>("/health"),
  rules: () => request<Rule[]>("/rules"),
  carbonFactors: () => request<CarbonFactor[]>("/carbon-factors"),

  projects: () => request<Project[]>("/projects"),
  createProject: (name: string, description?: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name, description }) }),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),

  analyses: (projectId?: string, language?: Language) =>
    request<AnalysisSummary[]>(`/analyses${qs({ project_id: projectId, language })}`),
  analysis: (id: string) => request<Analysis>(`/analyses/${id}`),
  createAnalysis: (body: {
    project_id: string;
    name: string;
    language: Language;
    source: string;
    case_spec?: Record<string, unknown>;
  }) => request<Analysis>("/analyses", { method: "POST", body: JSON.stringify(body) }),
  analysisOptimisations: (id: string) => request<OptimisationSummary[]>(`/analyses/${id}/optimisations`),

  optimisations: (projectId?: string) => request<OptimisationSummary[]>(`/optimisations${qs({ project_id: projectId })}`),
  optimisation: (id: string) => request<Optimisation>(`/optimisations/${id}`),
  createOptimisation: (analysis_id: string, condition: Condition) =>
    request<OptimisationSummary>("/optimisations", {
      method: "POST",
      body: JSON.stringify({ analysis_id, condition, run_pipeline: true }),
    }),
  rerunOptimisation: (id: string) => request<OptimisationSummary>(`/optimisations/${id}/rerun`, { method: "POST" }),

  suiteCases: () => request<SuiteCase[]>("/suite/cases"),
  runSuite: (body: { project_id: string; case_ids?: string[]; conditions: Condition[] }) =>
    request<SuiteJob>("/suite/run", { method: "POST", body: JSON.stringify(body) }),
  suiteJobs: () => request<SuiteJob[]>("/suite/jobs"),
  suiteJob: (id: string) => request<SuiteJob>(`/suite/jobs/${id}`),

  results: (projectId?: string, language?: Language) =>
    request<ResultRow[]>(`/results${qs({ project_id: projectId, language })}`),
  resultsSummary: (projectId?: string, language?: Language) =>
    request<ResultsSummary>(`/results/summary${qs({ project_id: projectId, language })}`),

  admin: {
    overview: () => request<AdminOverview>("/admin/overview"),
    settings: () => request<AdminSettings>("/admin/settings"),
    updateSettings: (values: Record<string, unknown>) =>
      request<AdminSettings>("/admin/settings", { method: "PUT", body: JSON.stringify({ values }) }),
    resetSettings: () => request<AdminSettings>("/admin/settings", { method: "DELETE" }),
    models: () => request<AdminModels>("/admin/models"),
    pullModel: (name: string) => request<ModelPull>("/admin/models/pull", { method: "POST", body: JSON.stringify({ name }) }),
    createCarbonFactor: (body: CarbonFactorInput) =>
      request<CarbonFactor>("/admin/carbon-factors", { method: "POST", body: JSON.stringify(body) }),
    updateCarbonFactor: (id: string, body: CarbonFactorInput) =>
      request<CarbonFactor>(`/admin/carbon-factors/${id}`, { method: "PUT", body: JSON.stringify(body) }),
    deleteCarbonFactor: (id: string) => request<void>(`/admin/carbon-factors/${id}`, { method: "DELETE" }),
    markStuckFailed: (olderThanMinutes: number) =>
      request<{ updated: number }>(`/admin/maintenance/mark-stuck-failed${qs({ older_than_minutes: olderThanMinutes })}`, { method: "POST" }),
    deleteOrphanAnalyses: () => request<{ deleted: number }>("/admin/maintenance/orphan-analyses", { method: "DELETE" }),
    deleteProjectRuns: (projectId: string, status: "failed" | "rejected") =>
      request<{ deleted: number }>(`/admin/maintenance/project-runs/${projectId}${qs({ status })}`, { method: "DELETE" }),
    logs: (limit = 200, level?: string) => request<LogEntry[]>(`/admin/logs${qs({ limit, level })}`),
    exportUrl: (projectId?: string) => `${BASE}/admin/export/results.csv${qs({ project_id: projectId })}`,
  },
};
