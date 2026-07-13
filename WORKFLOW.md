# Build Workflow — Compliance Drift Sentinel

> Everything here is AI-assisted ("vibecoded"). This doc is the discipline that keeps it correct and professional. Read before each session.

## The core rule (non-negotiable)
**Never trust the model's memory of a DataHub / MCP API.** Verify every integration call against the LIVE local instance (`localhost:8080` GMS / MCP server) before building on it. If a DataHub SDK/MCP call is written, run it and see a success response FIRST, then commit it.

## Build in vertical slices (demo-driven)
Each slice ends in something demoable end-to-end. If we run out of time, an earlier slice is still a complete product.
- **Slice 0** — SPIKE: prove DataHub MCP Server runs against local instance. (de-risk before architecture)
- **Slice 1** — Read column-level lineage via MCP → print it
- **Slice 2** — Schema diff → deterministic "which downstream column breaks"
- **Slice 3** — Write drift annotation + proposed data contract back to the graph  ← minimum viable winning product
- **Slice 4** — Agent narrates impact + drafts the contract in plain English
- **Slice 5** — React before/after UI (anti-slop)
- **Slice 6** — Package the impact engine as a reusable DataHub Skill (OSS bonus)

## Per-slice loop
1. **Spec** (1 paragraph): definition of done + how we demo it.
2. **Contract-check APIs** vs real docs (Context7) + live instance — before writing.
3. **TDD the deterministic core** (impact engine) with real fixtures.
4. **/verify** — drive against live DataHub, observe real behavior (green tests ≠ done).
5. **/code-review → /simplify** before commit.
6. **Small commit** (one concern) + screenshot for the demo.

## Guardrails vs vibecode-rot
- Pin all versions (DataHub v1.5.0.6, SDK, deps). No floating.
- `SNIPPETS.md` — every DataHub call that actually worked, saved for reuse (don't re-hallucinate).
- Human gate on any write-back to the graph.
- Reproducible from day 1: one-command bring-up (`make up`) so judges can run it.

## Submission artifacts are first-class from today
README · Apache-2.0 LICENSE · `examples/` folder · conventional commits · demo script — grow with the code, not bolted on in week 4.

## Judging criteria we're optimizing (keep visible)
Use of DataHub (esp. WRITE-BACK) · Technical Execution (it actually works) · Originality (beyond out-of-box) · Real-World Usefulness (a data team cares) · Submission Quality (video/README/setup) · OSS bonus (ship a Skill).

## Specialist agents
backend-architect (API) · test-writer-fixer (engine tests) · frontend-developer + ui-designer w/ anti-slop (UI) · code-reviewer (pre-commit).

## Env restart
`colima start` → `cd ~/hackathons/datahub-drift-sentinel && ./.venv/bin/datahub docker quickstart`. UI localhost:9002 (datahub/datahub), GMS localhost:8080.
