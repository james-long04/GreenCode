export type Language = "python" | "sql";
export type Condition = "ai_only" | "greencode";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  analysis_count: number;
}

export interface Finding {
  id: string;
  rule_id: string;
  title: string;
  severity: "low" | "medium" | "high";
  category: string;
  line: number | null;
  column: number | null;
  end_line: number | null;
  snippet: string | null;
  explanation: string;
  suggestion: string;
  confidence: number;
  evidence: Record<string, unknown>;
}

export interface Analysis {
  id: string;
  project_id: string;
  name: string;
  language: Language;
  source: string;
  case_spec: Record<string, unknown>;
  case_id: string | null;
  status: string;
  analyser_version: string;
  duration_ms: number | null;
  created_at: string;
  findings: Finding[];
}

export interface AnalysisSummary {
  id: string;
  project_id: string;
  name: string;
  language: Language;
  case_id: string | null;
  status: string;
  created_at: string;
  finding_count: number;
  optimisation_count: number;
}

export interface TestResult {
  id: string;
  test_name: string;
  passed: boolean;
  failure_type: string | null;
  details: string | null;
  duration_ms: number | null;
}

export interface Measurement {
  id: string;
  metric: string;
  value: number;
  unit: string;
  method: string;
  source: string;
  details: Record<string, unknown>;
}

export interface BenchmarkRun {
  id: string;
  variant: "original" | "candidate";
  repetitions: number;
  warmup_runs: number;
  mean_ms: number | null;
  median_ms: number | null;
  stdev_ms: number | null;
  min_ms: number | null;
  max_ms: number | null;
  ci95_low_ms: number | null;
  ci95_high_ms: number | null;
  samples_ms: number[];
  environment: Record<string, unknown>;
  status: string;
  error: string | null;
  measurements: Measurement[];
}

export interface TimingSummary {
  original_median: number;
  candidate_median: number;
  speedup: number;
  percent_change: number;
  cliffs_delta: number;
  ci_overlap: boolean;
  mann_whitney_p: number | null;
  significant: boolean;
  verdict: "faster" | "slower" | "no_significant_change";
}

export interface EnergyEntry {
  method: string;
  original_joules: number;
  candidate_joules: number;
  percent_change: number | null;
  energy_ratio: number | null;
  original_co2e_g?: number;
  candidate_co2e_g?: number;
}

export interface OptimisationSummaryData {
  verification?: { passed: boolean; failure_type: string | null; error: string | null };
  unchanged?: boolean;
  timing?: TimingSummary;
  energy?: Record<string, EnergyEntry | { time_percent_change: number; energy_percent_change: number; divergence_pp: number }>;
  resources?: Record<string, number | null>;
  sql_plan?: { original: Record<string, number>; candidate: Record<string, number> };
  pipeline_seconds?: number;
}

export interface OptimisationSummary {
  id: string;
  analysis_id: string;
  condition: Condition;
  status: string;
  model_name: string;
  failure_reason: string | null;
  summary: OptimisationSummaryData;
  created_at: string;
}

export interface Optimisation extends OptimisationSummary {
  original_source: string;
  candidate_source: string | null;
  provider: string;
  prompt: string | null;
  raw_response: string | null;
  generation_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  updated_at: string;
  test_results: TestResult[];
  benchmark_runs: BenchmarkRun[];
}

export interface SuiteCase {
  id: string;
  title: string;
  language: Language;
  category: string;
  description: string;
  expected_rules: string[];
  entry_point: string | null;
  tests: number;
  source: string;
}

export interface SuiteJob {
  job_id: string;
  status: "running" | "completed" | "failed";
  done: number;
  total: number;
  results: SuiteRow[];
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface SuiteRow {
  case_id: string;
  language: Language;
  condition: Condition;
  analysis_id: string;
  optimisation_id: string;
  status: string;
  failure_reason: string | null;
  findings: number;
  speedup: number | null;
  energy: Record<string, number | null>;
}

export interface ResultRow {
  optimisation_id: string;
  analysis_id: string;
  case_id: string | null;
  name: string;
  language: Language;
  condition: Condition;
  status: string;
  failure_reason: string | null;
  model: string;
  findings: number;
  rules: string[];
  unchanged: boolean;
  generation_ms: number | null;
  speedup: number | null;
  time_percent_change: number | null;
  significant: boolean | null;
  verdict: string | null;
  p_value: number | null;
  energy_source: string | null;
  energy_method: string | null;
  energy_ratio: number | null;
  energy_percent_change: number | null;
  original_co2e_g: number | null;
  candidate_co2e_g: number | null;
  created_at: string | null;
}

export interface ConditionStats {
  runs: number;
  generated: number;
  correct: number;
  correctness_rate: number | null;
  unchanged: number;
  benchmarked: number;
  faster_significant: number;
  slower_significant: number;
  median_speedup: number | null;
  geomean_speedup: number | null;
  median_time_change_pct: number | null;
  geomean_energy_ratio: number | null;
  median_energy_change_pct: number | null;
  failures: Record<string, number>;
}

export interface Hypothesis {
  supported: boolean;
  [key: string]: number | boolean | null | undefined;
}

export interface ResultsSummary {
  total_runs: number;
  conditions: Record<Condition, ConditionStats>;
  hypotheses: Record<"H1" | "H2" | "H3" | "H4", Hypothesis>;
  by_language: Record<string, Record<Condition, ConditionStats>>;
}

export interface Health {
  status: string;
  database: boolean;
  llm: { provider: string; ok: boolean; model?: string; model_available?: boolean; models?: string[]; error?: string };
  energy: { selected: string; rapl: boolean; codecarbon: boolean };
  settings: { model: string; provider: string; repetitions: number; warmup: number; region: string };
}

export interface Rule {
  rule_id: string;
  name: string;
  language: Language;
  category: string;
  severity: string;
  description: string;
}

export interface CarbonFactor {
  id: string;
  region: string;
  year: number;
  grams_co2e_per_kwh: number;
  source: string;
  notes: string | null;
  is_default: boolean;
}
