import { api } from "../api";
import { Badge, ErrorBox, LoadingBlock, PageHeader, Section, TableWrap, Term, fmt } from "../components/ui";
import { useAsync, useDocumentTitle } from "../hooks";
import type { CarbonFactor, Rule } from "../types";

const GROUPS = [
  { lang: "python" as const, title: "Python rules", hint: "AST analysis" },
  { lang: "sql" as const, title: "SQL rules", hint: "sqlglot and EXPLAIN" },
];

export function RulesPage() {
  useDocumentTitle("Rules & assumptions");
  const rules = useAsync<Rule[]>(() => api.rules(), []);
  const factors = useAsync<CarbonFactor[]>(() => api.carbonFactors(), []);
  return (
    <div className="stack">
      <PageHeader
        title="Rules & assumptions"
        lede="The fixed set of patterns that defines the scope of the experiment, and the coefficients behind every CO₂e figure."
      />
      <ErrorBox error={rules.error ?? factors.error} onRetry={() => { void rules.reload(); void factors.reload(); }} />

      {GROUPS.map((g) => (
        <Section key={g.lang} title={g.title} hint={g.hint} id={`rules-${g.lang}`}>
          {rules.data ? (
            <div className="panel flush">
              <TableWrap label={g.title}>
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
                      .filter((r) => r.language === g.lang)
                      .map((r) => (
                        <tr key={r.rule_id}>
                          <td>
                            <div>
                              <span className="mono">{r.rule_id}</span> <strong>{fmt.label(r.name)}</strong>
                            </div>
                            <div className="muted">{r.description}</div>
                          </td>
                          <td>{fmt.label(r.category)}</td>
                          <td>
                            <Badge kind={r.severity}>{r.severity}</Badge>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </TableWrap>
            </div>
          ) : (
            <LoadingBlock label="Loading rules" />
          )}
        </Section>
      ))}

      <Section title="Carbon factors" id="carbon" hint="Used to convert energy to CO₂e">
        {factors.data ? (
          <div className="stack-sm">
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
                    </tr>
                  </thead>
                  <tbody>
                    {factors.data.map((f) => (
                      <tr key={f.id}>
                        <td>
                          {f.region} {f.is_default && <Badge kind="ok">Default</Badge>}
                        </td>
                        <td>{f.year}</td>
                        <td className="num">{f.grams_co2e_per_kwh}</td>
                        <td>{f.source}</td>
                        <td className="muted">{f.notes}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </TableWrap>
            </div>
            <p className="muted" style={{ maxWidth: "75ch" }}>
              Energy is read from the processor's <Term id="rapl">RAPL</Term> counter through <Term id="lhm">LibreHardwareMonitor</Term> when it is running (machine-wide, with idle subtraction), otherwise from CodeCarbon, otherwise{" "}
              <Term id="estimated">estimated</Term> with a documented coefficient model (Green Algorithms). Every measurement records its method, so{" "}
              <Term id="measured">measured</Term> and estimated figures are never mixed silently.
            </p>
          </div>
        ) : (
          <LoadingBlock label="Loading carbon factors" />
        )}
      </Section>
    </div>
  );
}
