import { useEffect, useState } from "react";
import { api, type Analysis, type Lineage, type Narration, type Scenario, type WriteResult } from "./api";
import LineageGraph from "./LineageGraph";

const SEV_LABEL: Record<string, string> = { hard_break: "hard break", silent_break: "silent break" };

export default function App() {
  const [lineage, setLineage] = useState<Lineage | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [active, setActive] = useState<Scenario | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [narration, setNarration] = useState<Narration | null>(null);
  const [narrating, setNarrating] = useState(false);
  const [writing, setWriting] = useState(false);
  const [written, setWritten] = useState<WriteResult | null>(null);

  useEffect(() => {
    Promise.all([api.lineage(), api.scenarios()]).then(([lin, scn]) => {
      setLineage(lin);
      setScenarios(scn);
      setActive(scn[0] ?? null);
    });
  }, []);

  useEffect(() => {
    if (!active) return;
    const body = { dataset: active.dataset, column: active.column, change_type: active.change_type, detail: active.detail };
    setNarration(null);
    setWritten(null);
    api.analyze(body).then(setAnalysis);
    setNarrating(true);
    api.narrate(body).then(setNarration).finally(() => setNarrating(false));
  }, [active]);

  const runWriteback = () => {
    if (!active) return;
    setWriting(true);
    api
      .writeback({ dataset: active.dataset, column: active.column, change_type: active.change_type, detail: active.detail })
      .then(setWritten)
      .finally(() => setWriting(false));
  };

  const affected = analysis?.affected.map((a) => a.column) ?? [];

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand"><span className="mk">◈</span> Drift Sentinel</span>
        <span className="crumb">broker.marts.margin_report</span>
        <span className="live"><span className="dot" /> watching lineage</span>
      </header>

      <div className="shell">
        <aside className="rail">
          <div className="rail-h">Simulate upstream change</div>
          {scenarios.map((s) => (
            <button key={s.id} className={`scn${active?.id === s.id ? " on" : ""}`} onClick={() => setActive(s)}>
              <span className="scn-col">{s.column}</span>
              <span className="scn-lab">{s.label}</span>
            </button>
          ))}
          <div className="rail-note">Nothing is changed in your warehouse — the Sentinel reads DataHub lineage and predicts the blast radius before the change ships.</div>
        </aside>

        <main className="main">
          {analysis && (
            <div className={`alert ${analysis.breaks ? analysis.severity : "safe"}`}>
              <span className="ico">{analysis.breaks ? "⚠" : "✓"}</span>
              <span className="msg">
                {analysis.breaks ? (
                  <>Change on <code>{analysis.dataset}.{analysis.column}</code> — {analysis.detail} <b>{analysis.affected.length}</b> report columns break.</>
                ) : (
                  <>Change on <code>{analysis.dataset}.{analysis.column}</code> has no downstream impact on the margin report.</>
                )}
              </span>
              {analysis.breaks && <span className="sev">{SEV_LABEL[analysis.severity]}</span>}
            </div>
          )}

          {lineage && (
            <section className="graph-card">
              <LineageGraph lineage={lineage} changedDataset={active?.dataset ?? null} changedColumn={active?.column ?? null} affected={affected} />
            </section>
          )}

          <div className="lower">
            <section className="panel">
              <h3>Impacted report columns</h3>
              {analysis && analysis.affected.length > 0 ? (
                <div className="hits">
                  {analysis.affected.map((a) => (
                    <div className="hit" key={a.column}>
                      <span className="hit-name">{a.column}</span>
                      <span className="hit-drv">⟵ {a.transform}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No columns affected by this change.</p>
              )}
            </section>

            <section className="panel">
              <h3>Impact &amp; contract <span className="by">Gemini</span></h3>
              {narrating && <p className="muted pulse">Analyzing impact…</p>}
              {narration && narration.available && (
                <>
                  <p className="narr">{narration.narrative}</p>
                  <p className="biz">{narration.business_impact}</p>
                  <div className="lab">Proposed data contract</div>
                  <pre className="contract">{narration.contract}</pre>
                  <div className="lab">Remediation</div>
                  <p className="fix">{narration.remediation}</p>
                </>
              )}
              {narration && !narration.available && (
                <p className="muted">{narration.reason ?? "Narration unavailable."}</p>
              )}
            </section>
          </div>

          {analysis?.breaks && (
            <div className="actionbar">
              <button className="btn" onClick={runWriteback} disabled={writing}>
                {writing ? "Writing…" : "Write findings back to DataHub"}
              </button>
              {written && (
                <span className="wrote">
                  {written.live ? "✓ wrote" : "✓ (demo) would write"} {written.columns_annotated} columns · {written.tags_written} tags
                </span>
              )}
              {written && (
                <span className="chips">
                  <span className="chip">tag drift-{analysis.severity.replace("_", "-")}</span>
                  <span className="chip">drift_status</span>
                  <span className="chip">contract note</span>
                </span>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
