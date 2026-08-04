# Drift Sentinel — Write-Back Artifact (read back out of DataHub)

This is the state the agent left in the DataHub graph after analysing a **retype** of
`broker.raw.collateral.haircut_pct` (percent → fraction). It was read back out of a live
DataHub instance with the Python SDK, not composed by hand — it is what the next engineer
actually inherits when they open the dataset.

**Dataset:** `broker.marts.margin_report`  
**Annotated columns:** 3

---

## `collateral_after_haircut`

**Tags applied**

- `drift-at-risk`
- `drift-silent-break`

**Contract written into the column description**

```
⚠️ DRIFT SENTINEL CONTRACT: `broker.marts.margin_report.collateral_after_haircut` is derived via `market_value * (1 - haircut_pct/100)` and depends on `broker.raw.collateral.haircut_pct`. Contract: `broker.raw.collateral.haircut_pct` must exist and keep its type/semantics; a retyped upstream would cause a silent_break here.
```

---

## `total_available_margin`

**Tags applied**

- `drift-at-risk`
- `drift-silent-break`

**Contract written into the column description**

```
⚠️ DRIFT SENTINEL CONTRACT: `broker.marts.margin_report.total_available_margin` is derived via `cash_balance + market_value*(1 - haircut_pct/100)` and depends on `broker.raw.collateral.haircut_pct`. Contract: `broker.raw.collateral.haircut_pct` must exist and keep its type/semantics; a retyped upstream would cause a silent_break here.
```

---

## `margin_shortfall`

**Tags applied**

- `drift-at-risk`
- `drift-silent-break`

**Contract written into the column description**

```
⚠️ DRIFT SENTINEL CONTRACT: `broker.marts.margin_report.margin_shortfall` is derived via `(span+exposure) - total_available_margin` and depends on `broker.raw.collateral.haircut_pct`. Contract: `broker.raw.collateral.haircut_pct` must exist and keep its type/semantics; a retyped upstream would cause a silent_break here.
```

---

Reproduce locally with `make up && make seed && make provision`, then
`python scripts/demo_writeback.py`. On the hosted demo this runs in safe mode
(`SENTINEL_LIVE_WRITEBACK=false`) and reports what it *would* write.

