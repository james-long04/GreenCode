import { useEffect, useState, type ReactElement } from "react";

import { api } from "./api";
import { Icon, type IconName } from "./components/icons";
import { useDocumentTitle, useHashRoute, useLocalStorage, useTheme } from "./hooks";
import { AnalysePage, AnalysisDetailPage } from "./pages/AnalysePage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { OptimisationPage } from "./pages/OptimisationPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { RulesPage } from "./pages/RulesPage";
import type { Health, Project } from "./types";

const NAV: { path: string; label: string; icon: IconName; matches: string[] }[] = [
  { path: "/overview", label: "Overview", icon: "squares-four", matches: ["overview", ""] },
  { path: "/projects", label: "Projects", icon: "folders", matches: ["projects"] },
  { path: "/analyse", label: "Analyse", icon: "magnifying-glass", matches: ["analyse", "analyses", "optimisations"] },
  { path: "/experiments", label: "Experiments", icon: "flask", matches: ["experiments"] },
  { path: "/rules", label: "Rules & assumptions", icon: "list-checks", matches: ["rules"] },
];

const TITLES: Record<string, string> = {
  overview: "Overview",
  projects: "Projects",
  analyse: "Analyse",
  analyses: "Analysis",
  optimisations: "Optimisation",
  experiments: "Experiments",
  rules: "Rules & assumptions",
};

export default function App() {
  const { parts, navigate } = useHashRoute();
  const [projectId, setProjectId] = useLocalStorage("greencode.project", "");
  const [projects, setProjects] = useState<Project[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const { effective, toggle } = useTheme();

  useEffect(() => {
    const load = () => {
      api.projects().then(setProjects).catch(() => setProjects([]));
      api.health().then(setHealth).catch(() => setHealth(null));
    };
    load();
    const id = window.setInterval(load, 20000);
    return () => window.clearInterval(id);
  }, [parts.join("/")]);

  useEffect(() => {
    if (projects.length && !projects.some((p) => p.id === projectId)) setProjectId(projects[0].id);
  }, [projects, projectId, setProjectId]);

  const section = parts[0] ?? "overview";
  const pid = projectId || null;
  useDocumentTitle(TITLES[section] ?? "Overview");

  let page: ReactElement;
  switch (section) {
    case "projects":
      page = <ProjectsPage projectId={pid} setProjectId={setProjectId} navigate={navigate} />;
      break;
    case "analyse":
      page = <AnalysePage projectId={pid} navigate={navigate} />;
      break;
    case "analyses":
      page = <AnalysisDetailPage id={parts[1]} navigate={navigate} />;
      break;
    case "optimisations":
      page = <OptimisationPage id={parts[1]} navigate={navigate} />;
      break;
    case "experiments":
      page = <ExperimentsPage projectId={pid} navigate={navigate} />;
      break;
    case "rules":
      page = <RulesPage />;
      break;
    default:
      page = <OverviewPage projectId={pid} navigate={navigate} health={health} />;
  }

  const dbOk = !!health?.database;
  const modelOk = !!health?.llm.ok && health.llm.model_available !== false;
  const energy = health?.energy.selected ?? null;

  return (
    <div className="app">
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand" href="#/overview" aria-label="GreenCode, go to overview">
          <span className="brand-mark">
            <Icon name="leaf" size={17} />
          </span>
          GreenCode
        </a>

        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <a key={n.path} href={`#${n.path}`} aria-current={n.matches.includes(section) ? "page" : undefined}>
              <Icon name={n.icon} />
              {n.label}
            </a>
          ))}
        </nav>

        <div className="sidebar-section">
          <label className="field">
            Project
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={projects.length === 0}>
              {projects.length === 0 && <option value="">No projects yet</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="sidebar-footer">
          <ul className="status-list" aria-label="System status">
            <li>
              <Icon name={dbOk ? "check-circle" : "x-circle"} size={15} className={`status-icon ${dbOk ? "ok" : "bad"}`} />
              <span>{health ? (dbOk ? "Database connected" : "Database unreachable") : "API offline"}</span>
            </li>
            <li>
              <Icon name={modelOk ? "check-circle" : "warning"} size={15} className={`status-icon ${modelOk ? "ok" : "warn"}`} />
              <span>{health ? (modelOk ? `${health.settings.model}` : health.llm.ok ? `${health.settings.model} not pulled` : `${health.llm.provider} not running`) : "Model unknown"}</span>
            </li>
            <li>
              <Icon name="info" size={15} className="status-icon" />
              <span>Energy: {energy ?? "unknown"}</span>
            </li>
          </ul>
          <button className="small quiet" onClick={toggle} aria-label={`Switch to ${effective === "dark" ? "light" : "dark"} theme`}>
            <Icon name={effective === "dark" ? "sun" : "moon"} size={16} />
            {effective === "dark" ? "Light theme" : "Dark theme"}
          </button>
        </div>
      </aside>
      <main className="main" id="main" tabIndex={-1} style={{ outline: "none" }}>
        {page}
      </main>
    </div>
  );
}
