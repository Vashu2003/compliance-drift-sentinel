# Drift Sentinel — Agent Explanation (Gemini)

**Detected (deterministic engine):** RETYPED of broker.raw.collateral.haircut_pct [silent_break] breaks 3 report column(s): broker.marts.margin_report.collateral_after_haircut, broker.marts.margin_report.margin_shortfall, broker.marts.margin_report.total_available_margin

## Narrative
The upstream column `broker.raw.collateral.haircut_pct` was modified from a percentage scale (0-100) to a fractional scale (0-1). This change silently breaks downstream calculations for `collateral_after_haircut`, `total_available_margin`, and `margin_shortfall` which still divide the value by 100. As a result, the daily regulatory margin report will severely overestimate available collateral.

## Business impact
Silently misreporting margin requirements constitutes a severe regulatory compliance breach. This exposes the broker to undetected credit risk and potential financial penalties from regulatory authorities.

## Proposed data contract
```
dataset: broker.raw.collateral, columns: [{name: haircut_pct, type: float, tests: [{type: range, min: 0, max: 100}]}]
```

## Remediation
Update the downstream SQL formulas for `collateral_after_haircut` and `total_available_margin` to remove the `/100` division, aligning them with the new fractional scale.
