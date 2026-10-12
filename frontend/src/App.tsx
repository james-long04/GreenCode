import { useEffect, useState, type ReactElement } from "react";

import { api } from "./api";
import { useHashRoute, useLocalStorage } from "./hooks";
import { AnalysePage, AnalysisDetailPage } from "./pages/AnalysePage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { OptimisationPage } from "./pages/OptimisationPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { RulesPage } from "./pages/RulesPage";
import type { Health, Project } from "./types";

const NAV: { path: string; label: string }[] = [
  { path: "/overview", label: "Overview" },
  { path: "/projects", label: "Projects" },
  { path: "/analyse", label: "Analyse" },
  { path: "/experiments", label: "Experiments" },
  { path: "/rules", label: "Rules & assumptions" },
];

export default function App() {
  const { parts, navigate } = useHashRoute();
  const [projectId, setProjectId] = useLocalStorage("greencode.project", "");
  const [projects, setProjects] = useState<Project[]>([]);
  const [health, setHealth] = useState<Health | null>(null);

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
      page = <OverviewPage projectId={pid} navigate={navigate} />;
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="leaf" /> GreenCode
        </div>
        <div className="tagline">Static-analysis-guided AI optimisation for sustainable Python & SQL</div>
        <nav className="nav">
          {NAV.map((n) => (
            <button key={n.path} className={`#/${section}`.startsWith(`#${n.path}`) ? "active" : ""} onClick={() => navigate(n.path)}>
              {n.label}
            </button>
          ))}
        </nav>
        <div style={{ marginTop: 14 }}>
          <label className="field" style={{ color: "#8ea392" }}>
            Project
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} style={{ width: "100%" }}>
              {projects.length === 0 && <option value="">(none)</option>}
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="status">
          <div>
            <span className={`dot ${health?.database ? "ok" : "bad"}`} />
            API {health ? (health.database ? "connected" : "degraded") : "offline"}
          </div>
          <div>
            <span className={`dot ${health?.llm.ok ? "ok" : "bad"}`} />
            {health ? `${health.llm.provider} · ${health.settings.model}` : "model unknown"}
          </div>
          <div>
            <span className="dot ok" />
            energy: {health?.energy.selected ?? "–"}
          </div>
        </div>
      </aside>
      <main className="main">{page}</main>
    </div>
  );
}
