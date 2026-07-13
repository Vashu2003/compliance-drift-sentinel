PY := ./.venv/bin/python
DATAHUB := ./.venv/bin/datahub

.PHONY: up down verify test dev fmt

up:  ## Start local DataHub + load sample data
	colima start || true
	$(DATAHUB) docker quickstart
	$(DATAHUB) docker ingest-sample-data || true
	@echo "DataHub UI: http://localhost:9002 (datahub/datahub)"

down:  ## Stop DataHub containers
	$(DATAHUB) docker nuke || true

verify:  ## Slice 0: prove the MCP server talks to DataHub
	$(PY) scripts/verify_mcp.py

seed:  ## Author the synthetic broker margin pipeline (with column lineage) into DataHub
	$(PY) data/seed_margin_pipeline.py

provision:  ## Provision drift tags + structured property (once, before write-back)
	$(PY) data/seed_drift_vocab.py

demo:  ## Run the impact engine over live lineage -> examples/margin_haircut_impact.md
	$(PY) scripts/demo_impact.py

narrate:  ## Run engine + Gemini narrator -> examples/margin_haircut_explanation.md (needs GEMINI_API_KEY)
	$(PY) scripts/demo_agent.py

writeback:  ## Detect drift and write findings back to DataHub
	$(PY) scripts/demo_writeback.py

test:  ## Run the test suite
	$(PY) -m pytest -q

dev:  ## Run the FastAPI backend
	$(PY) -m uvicorn app.main:app --reload --port 8099

ui:  ## Run the React UI (proxies /api to the backend on :8099)
	cd frontend && npm run dev

ui-install:  ## Install frontend dependencies
	cd frontend && npm install

ui-build:  ## Production build of the frontend
	cd frontend && npm run build

fmt:  ## Format
	$(PY) -m ruff format . || true
