import { useState } from "react";

import { api } from "../api";
import { Badge, Empty, ErrorBox, fmt } from "../components/ui";
import { useAsync } from "../hooks";
import type { AnalysisSummary, Project } from "../types";

export function ProjectsPage({
  projectId,
  setProjectId,
  navigate,
}: {
  projectId: string | null;
  setProjectId: (id: string) => void;
  navigate: (p: string) => void;
}) {
  const projects = useAsync<Project[]>(() => api.projects(), []);
  const analyses = useAsync<AnalysisSummary[]>(() => (projectId ? api.analyses(projectId) : Promise.resolve([])), [projectId], 8000);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const create = async () => {
    if (!name.trim()) return;
    try {
      const p = await api.createProject(name.trim(), desc.trim() || undefined);
      setName("");
      setDesc("");
      setProjectId(p.id);
      await projects.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (id: string) => {
    if (!window.confirm("Delete this project and all of its analyses, optimisations and measurements?")) return;
    try {
      await api.deleteProject(id);
      await projects.reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div>
      <h1>Projects</h1>
      <div className="subtitle">A project groups analyses and experiment runs. Select one to scope the rest of the dashboard.</div>
      <ErrorBox error={err ?? projects.error} />
      <div className="grid two">
        <div className="card">
          <h3>Projects</h3>
          {projects.data?.length ? (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th className="num">Analyses</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {projects.data.map((p) => (
                  <tr key={p.id} className="clickable" onClick={() => setProjectId(p.id)}>
                    <td>
                      {p.name} {p.id === projectId && <Badge kind="ok">selected</Badge>}
                      <div className="muted small">{p.description}</div>
                    </td>
                    <td className="num">{p.analysis_count}</td>
                    <td className="muted small">{fmt.date(p.created_at)}</td>
                    <td>
                      <button
                        className="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          void remove(p.id);
                        }}
                      >
                        delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Empty>No projects yet.</Empty>
          )}
        </div>
        <div className="card">
          <h3>New project</h3>
          <div style={{ display: "grid", gap: 10 }}>
            <label className="field">
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Experiment 1 – qwen2.5-coder:7b" />
            </label>
            <label className="field">
              Description
              <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="model, machine, date…" />
            </label>
            <div>
              <button className="primary" onClick={() => void create()} disabled={!name.trim()}>
                Create project
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <h3>Analyses in selected project</h3>
        {!projectId ? (
          <Empty>Select a project.</Empty>
        ) : analyses.data?.length ? (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Language</th>
                <th>Case</th>
                <th className="num">Findings</th>
                <th className="num">Optimisations</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {analyses.data.map((a) => (
                <tr key={a.id} className="clickable" onClick={() => navigate(`/analyses/${a.id}`)}>
                  <td>{a.name}</td>
                  <td>
                    <Badge>{a.language}</Badge>
                  </td>
                  <td className="mono small">{a.case_id ?? "ad-hoc"}</td>
                  <td className="num">{a.finding_count}</td>
                  <td className="num">{a.optimisation_count}</td>
                  <td className="muted small">{fmt.date(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Empty>No analyses yet — submit code on the Analyse page or run the suite.</Empty>
        )}
      </div>
    </div>
  );
}
