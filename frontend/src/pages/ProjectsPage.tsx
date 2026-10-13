import { useState, type FormEvent } from "react";

import { api } from "../api";
import { Icon } from "../components/icons";
import { Alert, Badge, Empty, ErrorBox, LoadingBlock, PageHeader, Section, TableWrap, fmt } from "../components/ui";
import { useAsync, useDocumentTitle } from "../hooks";
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
  useDocumentTitle("Projects");
  const projects = useAsync<Project[]>(() => api.projects(), []);
  const analyses = useAsync<AnalysisSummary[]>(() => (projectId ? api.analyses(projectId) : Promise.resolve([])), [projectId], 8000);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      const p = await api.createProject(name.trim(), desc.trim() || undefined);
      setName("");
      setDesc("");
      setErr(null);
      setProjectId(p.id);
      await projects.reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: string) => {
    try {
      await api.deleteProject(id);
      setConfirming(null);
      await projects.reload();
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    }
  };

  const selected = projects.data?.find((p) => p.id === projectId);

  return (
    <div className="stack">
      <PageHeader title="Projects" lede="A project groups analyses and experiment runs. The selected project scopes the rest of the dashboard." />
      <ErrorBox error={err ?? projects.error} onRetry={() => void projects.reload()} />

      <div className="grid wide-left">
        <Section title="All projects" id="projects">
          {!projects.data ? (
            <LoadingBlock label="Loading projects" />
          ) : projects.data.length ? (
            <div className="panel flush">
              <TableWrap label="Projects">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th className="num">Analyses</th>
                      <th>Created</th>
                      <th>
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {projects.data.map((p) => (
                      <tr key={p.id}>
                        <td>
                          <div className="row" style={{ gap: 8 }}>
                            <strong>{p.name}</strong>
                            {p.id === projectId && <Badge kind="ok">Selected</Badge>}
                          </div>
                          {p.description && <div className="muted">{p.description}</div>}
                          {confirming === p.id && (
                            <div className="row" style={{ marginTop: 8 }} role="group" aria-label={`Confirm deleting ${p.name}`}>
                              <span>Delete this project and all its analyses, optimisations and measurements?</span>
                              <button className="small danger" onClick={() => void remove(p.id)}>
                                Delete project
                              </button>
                              <button className="small quiet" onClick={() => setConfirming(null)}>
                                Keep
                              </button>
                            </div>
                          )}
                        </td>
                        <td className="num">{p.analysis_count}</td>
                        <td className="muted">{fmt.date(p.created_at)}</td>
                        <td>
                          <div className="row" style={{ justifyContent: "flex-end" }}>
                            {p.id !== projectId && (
                              <button className="small" onClick={() => setProjectId(p.id)}>
                                Use
                              </button>
                            )}
                            <button className="small quiet icon-only" onClick={() => setConfirming(p.id)} aria-label={`Delete ${p.name}`}>
                              <Icon name="trash" size={16} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </div>
          ) : (
            <Empty title="No projects yet">Create one with the form to start analysing code.</Empty>
          )}
        </Section>

        <Section title="New project" id="new">
          <form className="panel stack-sm" onSubmit={(e) => void create(e)}>
            <label className="field">
              Name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Experiment 1, qwen2.5-coder:7b" required />
            </label>
            <label className="field">
              Description
              <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Model, machine, date" />
            </label>
            <div>
              <button className="primary" type="submit" disabled={!name.trim() || creating}>
                <Icon name="plus" />
                Create project
              </button>
            </div>
          </form>
        </Section>
      </div>

      <Section title={selected ? `Analyses in ${selected.name}` : "Analyses"} id="analyses">
        {!projectId ? (
          <Alert kind="info">Select or create a project to see its analyses.</Alert>
        ) : analyses.data?.length ? (
          <div className="panel flush">
            <TableWrap label="Analyses in the selected project">
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
                    <tr key={a.id} className="linked">
                      <td className="link-cell">
                        <a
                          href={`#/analyses/${a.id}`}
                          onClick={(e) => {
                            e.preventDefault();
                            navigate(`/analyses/${a.id}`);
                          }}
                        >
                          {a.name}
                        </a>
                      </td>
                      <td>
                        <Badge>{a.language}</Badge>
                      </td>
                      <td className="mono">{a.case_id ?? "ad hoc"}</td>
                      <td className="num">{a.finding_count}</td>
                      <td className="num">{a.optimisation_count}</td>
                      <td className="muted">{fmt.date(a.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </TableWrap>
          </div>
        ) : (
          <Empty title="No analyses yet">Submit code on the Analyse page or run the suite on the Experiments page.</Empty>
        )}
      </Section>
    </div>
  );
}
