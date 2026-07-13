# Compliance Drift Sentinel

> An AI agent that reads **DataHub column-level lineage** to predict which downstream report field breaks when an upstream schema changes — then **writes a proposed data contract back** to the graph.

Built for **[Build with DataHub: The Agent Hackathon](https://datahub.devpost.com/)** · Track: Open / Wildcard.

## The problem

Data teams live in fear of the *silent break*: someone renames or retypes a column three hops upstream, and a regulatory report quietly ships wrong numbers — no error, until an auditor finds it. DataHub knows the lineage; it doesn't reason about the **blast radius of a change before it lands**.

## What it does

1. Reads column-level lineage from DataHub via the **MCP Server**.
2. Takes a proposed upstream schema change and **predicts which downstream fields break**, tracing the exact lineage path.
3. **Writes back** a drift annotation + a proposed **data contract** that would fail-fast next time.
4. Demonstrated on a synthetic **fintech regulatory-report pipeline** (source ledgers → transforms → daily margin report).

A deterministic engine does the reliable impact analysis; the agent explains the risk in plain English and drafts the contract.

## Architecture

```
Schema diff ──▶ FastAPI ──▶ Impact Engine (deterministic) ──▶ Agent (narrate + draft contract)
                   │                                                    │
                   └────────── DataHub MCP Server (read lineage / write-back) ──────────┘
                                            │
                                   DataHub OSS (localhost)
```

## Quickstart

Prereqs: Docker (Colima or Desktop), Python 3.12, `uv`.

```bash
make up        # start local DataHub + load sample data
make verify    # Slice 0: prove the MCP server talks to DataHub
make test      # run the impact-engine test suite
make dev       # run the FastAPI backend
```

DataHub UI: http://localhost:9002 (`datahub` / `datahub`). GMS API: http://localhost:8080.

## Status

Active build (hackathon). See `WORKFLOW.md` for the slice plan and `SNIPPETS.md` for verified DataHub calls.

## License

[Apache-2.0](./LICENSE).
