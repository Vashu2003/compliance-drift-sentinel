# Known-Good Snippets (verified against live local DataHub)

> Every entry here has been RUN and confirmed working. Reuse these instead of re-generating from model memory.

## DataHub MCP Server — run against local OSS (VERIFIED 2026-07-13)
Package: `mcp-server-datahub` v0.6.0 (official acryldata). Run via `uvx mcp-server-datahub`.
Transports: `stdio | sse | http`. Detected our instance as `is_oss=True`.

Required env for local + write-back:
```
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_GMS_TOKEN=          # empty OK on local quickstart
TOOLS_IS_MUTATION_ENABLED=true   # REQUIRED for write-back tools; off by default
```

18 tools available with mutations on:
- read/lineage: `search`, `get_entities`, `list_schema_fields`, `get_lineage`, `get_lineage_paths_between`, `get_dataset_queries`
- write-back: `add_tags`, `remove_tags`, `add_terms`, `remove_terms`, `add_owners`, `remove_owners`,
  `set_domains`, `remove_domains`, `update_description`, `add_structured_properties`,
  `remove_structured_properties`, `save_document`

Smoke test: `./.venv/bin/python scripts/verify_mcp.py` → prints tools + a real `search` round-trip. Expect `SLICE 0 RESULT: PASS`.

## get_lineage tool — VERIFIED shapes (Slice 1)
Input: `{urn, upstream:bool=true, column:str|null=null, max_hops:int=1, max_results:int=30}`.
`column` enables column-level lineage. Output:
```
{"upstreams": {"total": N, "facets": [...], "searchResults": [
   {"entity": {"urn": "...", "type": "DATASET|DATA_JOB", ...}, "degree": 1}, ...
]}}
```
(`downstreams` key when upstream=false.) Sample graph: `fct_users_created` (hive) has 2 upstreams
— an Airflow DATA_JOB (`dag_abc/task_123`) + a hive DATASET. Parser: `r["entity"]["urn"]`,
`r["entity"]["type"]`, `r["degree"]`. See `engine/datahub_client.py`.

## Column-level lineage read for the IMPACT ENGINE — VERIFIED (Slice 2)
MCP `get_lineage(column=...)` aggregates to **dataset-level** — it does NOT return exact
downstream columns. For precise column→column edges, read the fine-grained aspect via the
DataHub graph SDK (stable, exact):
```python
from datahub.ingestion.graph.client import DataHubGraph, DatahubClientConfig
from datahub.metadata.schema_classes import UpstreamLineageClass
g = DataHubGraph(DatahubClientConfig(server="http://localhost:8080"))
asp = g.get_aspect(entity_urn=REPORT_URN, aspect_type=UpstreamLineageClass)
# asp.fineGrainedLineages: list; each has .upstreams (schemaField urns), .downstreams, .transformOperation
```
schemaField urn = `urn:li:schemaField:(<dataset_urn>,<column>)` via `make_schema_field_urn`.
Seeded pipeline: `data/seed_margin_pipeline.py` → collateral.haircut_pct feeds 3 report cols
(collateral_after_haircut, total_available_margin, margin_shortfall).

## MCP write-back (Slice 3) — VERIFIED signatures + gotchas
Needs `TOOLS_IS_MUTATION_ENABLED=true`. Tags/properties must be PROVISIONED first
(`data/seed_drift_vocab.py`) — add_tags fails if the tag urn doesn't exist ("Failed to validate label").
- `add_tags`: `{tag_urns:[...], entity_urns:[dataset_urn], column_paths:[col]}`  ← column-level.
- `update_description`: `{entity_urn:dataset_urn, column_path:col, operation:replace|append|remove, description}`.
- `add_structured_properties`: `{property_values:{prop_urn:[vals]}, entity_urns:[schemaField_urn]}`
  — does NOT accept `column_paths`; pass the schemaField urn as the entity. Property must be
  defined via `StructuredPropertyDefinitionClass` (valueType `urn:li:dataType:datahub.string`,
  entityTypes incl. `urn:li:entityType:datahub.schemaField`).
Read-back: `graph.get_aspect(dataset_urn, EditableSchemaMetadataClass)` →
`editableSchemaFieldInfo[].globalTags.tags` + `.description`.
(MCP server logs at DEBUG to stderr — run scripts with `2>/dev/null` for clean output.)

## Gemini narrator (Slice 4) — VERIFIED
`gemini-2.5-flash` is DEPRECATED for new users (404). Use `gemini-flash-latest` (alias, won't
deprecate mid-project) — set `GEMINI_MODEL` to override. REST generateContent with structured JSON:
```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=KEY
{ "systemInstruction": {...}, "contents":[{"parts":[{"text": FACTS}]}],
  "generationConfig": {"responseMimeType":"application/json","responseSchema":{...},"temperature":0.2} }
# text at candidates[0].content.parts[0].text -> json.loads
```
Key in `.env` (gitignored) → loaded by `engine/config._load_dotenv()`. Design: engine computes
impact (deterministic); Gemini only narrates + drafts contract, grounded strictly in given facts.

## GMS GraphQL direct (no MCP) — VERIFIED
```
curl -s http://localhost:8080/api/graphql -H 'Content-Type: application/json' \
  -X POST -d '{"query":"{ search(input:{type:DATASET, query:\"*\", start:0, count:5}){ total searchResults{ entity{ urn ... on Dataset{ name } } } } }"}'
```
Note: search `total` lags a few seconds after ingest (async OpenSearch indexing) — not a failure.
