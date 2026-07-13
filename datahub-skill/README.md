# datahub-drift-contract — a DataHub Skill

A reusable [DataHub Skill](https://docs.datahub.com/docs/dev-guides/agent-context/skills) that
teaches an AI agent to do **drift-to-contract** analysis: given a proposed upstream schema
change, predict exactly which downstream report columns break, classify severity, draft an
enforceable data contract, and write the findings back to DataHub.

It follows the same layout and conventions as the official
[`datahub-project/datahub-skills`](https://github.com/datahub-project/datahub-skills) registry, so
it is ready to open as a PR there.

```
skills/datahub-drift-contract/
  SKILL.md                              # the skill (frontmatter + workflow)
  references/drift-impact-reference.md  # column-level lineage + write-back call shapes
  templates/drift-report.template.md    # the finding report layout
```

## Why it's a gap worth filling

The official registry ships `datahub-lineage` (trace dependencies), `datahub-search`,
`datahub-enrich`, and `datahub-quality`. None of them answer the question a data engineer actually
asks before shipping a change: **"what silently breaks if I change this, and what contract would
have caught it?"** This skill does, and it *writes the answer back* so the knowledge compounds.

## Reference implementation

This skill was extracted from the **Compliance Drift Sentinel** project (this repo). The
deterministic engine that implements the skill's workflow end-to-end — column-level impact,
severity, write-back, plus a Gemini narrator and a UI — is in `../engine/` and `../app/`.

## Install (Claude Code)

Copy `skills/datahub-drift-contract/` into your project's `.claude/skills/`, or add this repo as
a plugin. Requires the DataHub MCP server (`mcp-server-datahub`) connected, with
`TOOLS_IS_MUTATION_ENABLED=true` for the write-back step.
