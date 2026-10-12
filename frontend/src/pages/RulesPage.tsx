import { api } from "../api";
import { Badge, Empty, ErrorBox } from "../components/ui";
import { useAsync } from "../hooks";
import type { CarbonFactor, Rule } from "../types";

export function RulesPage() {
  const rules = useAsync<Rule[]>(() => api.rules(), []);
  const factors = useAsync<CarbonFactor[]>(() => api.carbonFactors(), []);
  return (
    <div>
      <h1>Rules & assumptions</h1>
      <div className="subtitle">The fixed, deterministic pattern set that defines the scope of the experiment, and the environmental coefficients behind every CO₂e figure.</div>
      <ErrorBox error={rules.error ?? factors.error} />
      <div className="grid two">
        {(["python", "sql"] as const).map((lang) => (
          <div className="card" key={lang}>
            <h3>{lang === "python" ? "Python (AST)" : "SQL (sqlglot + EXPLAIN)"}</h3>
            {rules.data ? (
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Category</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.data
                    .filter((r) => r.language === lang)
                    .map((r) => (
                      <tr key={r.rule_id}>
                        <td>
                          <div>
                            <span className="mono">{r.rule_id}</span> {r.name.replace(/_/g, " ")}
                          </div>
                          <div className="muted small">{r.description}</div>
                        </td>
                        <td className="small">{r.category.replace(/_/g, " ")}</td>
                        <td>
                          <Badge kind={r.severity}>{r.severity}</Badge>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            ) : (
              <Empty>Loading…</Empty>
            )}
          </div>
        ))}
      </div>
      <div className="card">
        <h3>Carbon factors</h3>
        {factors.data ? (
          <table>
            <thead>
              <tr>
                <th>Region</th>
                <th>Year</th>
                <th className="num">gCO₂e / kWh</th>
                <th>Source</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {factors.data.map((f) => (
                <tr key={f.id}>
                  <td>
                    {f.region} {f.is_default && <Badge kind="ok">default</Badge>}
                  </td>
                  <td>{f.year}</td>
                  <td className="num">{f.grams_co2e_per_kwh}</td>
                  <td className="small">{f.source}</td>
                  <td className="muted small">{f.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <Empty>Loading…</Empty>
        )}
        <div className="muted small" style={{ marginTop: 10 }}>
          Energy is measured with RAPL when available (direct hardware counters, machine-wide with idle subtraction), otherwise CodeCarbon, otherwise a
          documented coefficient model (Green Algorithms). Every measurement row records its method so measured and estimated figures are never mixed silently.
        </div>
      </div>
    </div>
  );
}
