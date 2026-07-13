# Demo video script — Compliance Drift Sentinel (target 2:45, hard limit 3:00)

Record at 1280×800, local app (`make dev` + `make ui`, DataHub up) so write-back is **live**.
Speak to the on-screen action. Keep the DataHub UI (localhost:9002) open in a second tab.

---

### 0:00–0:18 · Hook (screen: the app, haircut_retype selected)
> "Every data team fears the silent break. Someone retypes a column upstream, and a regulatory
> report quietly starts shipping wrong numbers — no error, until an auditor finds it. DataHub
> knows the lineage. Drift Sentinel makes it *act* on it."

### 0:18–0:40 · The setup (screen: the lineage graph)
> "This is a broker's daily margin report, built from ledger, positions, and collateral. DataHub
> has the column-level lineage. I'm about to change one upstream column — before it ships."
- Point at `collateral` and its `haircut_pct` in the graph.

### 0:40–1:15 · Detect (screen: click through scenarios, land on retype)
- Click **"Retype collateral.haircut_pct (pct → fraction)"**.
> "The moment I simulate the change, the drift path lights up. The engine reads the fine-grained
> lineage and finds the exact three report columns that break — collateral_after_haircut,
> total_available_margin, margin_shortfall — because they still divide by 100."
- Let the red drift path + the flagged columns land on screen. Point at the "SILENT BREAK" chip.
> "And it's flagged a *silent* break — the dangerous kind. No error. Just wrong margin."

### 1:15–1:45 · Explain (screen: the Gemini panel)
> "Gemini narrates the impact and drafts a data contract — but it never decides *what* breaks;
> the deterministic engine did that. So the AI is grounded, never hallucinating the impact."
- Scroll the narrative → business impact → the proposed contract → remediation.

### 1:45–2:20 · Write back (screen: click the button, then switch to DataHub UI)
- Click **"Write findings back to DataHub"** → show "✓ wrote 3 columns · 6 tags".
> "One click writes it back — through the same MCP interface it reads from."
- Switch to the DataHub tab (localhost:9002) → open `margin_report` → Schema tab.
> "Here it is in DataHub: the affected columns now carry a drift-silent-break tag, a drift_status
> property, and the proposed contract in the description. The next engineer inherits the warning."

### 2:20–2:45 · The Skill + close (screen: the SKILL.md / repo)
> "And the whole workflow is packaged as a reusable DataHub Skill, in the official format — so any
> agent can run drift-to-contract analysis. That's Compliance Drift Sentinel: catch the silent
> break before it ships, and write the guardrail back."

---

**B-roll if short on time:** the "currency" scenario (shows a clean *no-impact* result — no false
positives) is a nice 5-second aside after 1:15.
