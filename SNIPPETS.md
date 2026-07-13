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

## GMS GraphQL direct (no MCP) — VERIFIED
```
curl -s http://localhost:8080/api/graphql -H 'Content-Type: application/json' \
  -X POST -d '{"query":"{ search(input:{type:DATASET, query:\"*\", start:0, count:5}){ total searchResults{ entity{ urn ... on Dataset{ name } } } } }"}'
```
Note: search `total` lags a few seconds after ingest (async OpenSearch indexing) — not a failure.
