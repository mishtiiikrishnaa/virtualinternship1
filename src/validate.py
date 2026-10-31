"""Post-clean validation.

Checks are declarative where possible (allowed value lists come from
`config/schema.yml`) and each returns a severity. A critical failure stops the
publish step; a warning is recorded and the report carries on. The split
matters: a run that dies on every soft anomaly never gets finished, and a run
that publishes through every hard one never gets trusted.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "config" / "schema.yml"

# tolerated share of rows carrying an imputed value before the run is queried
MAX_IMPUTED_SHARE = 0.15


@dataclass
class Check:
    name: str
    passed: bool
    severity: str  # "critical" | "warning"
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {
            "check": self.name,
            "severity": self.severity,
            "result": "pass" if self.passed else "fail",
            "detail": self.detail,
        }


def load_schema(path: Path = SCHEMA_PATH) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def run_checks(frame: pd.DataFrame, schema: dict | None = None) -> list[Check]:
    schema = schema or load_schema()
    columns = schema["columns"]
    checks: list[Check] = []

    dupes = int(frame["shipment_id"].duplicated().sum())
    checks.append(Check("unique shipment_id", dupes == 0, "critical", f"{dupes} duplicate keys"))

    keys = [
        "shipment_id", "order_id", "order_date", "ship_date",
        "origin_city", "origin_country", "dest_city", "dest_country", "mode",
    ]
    nulls = {k: int(frame[k].isna().sum()) for k in keys}
    checks.append(Check("key columns populated", all(v == 0 for v in nulls.values()), "critical", str(nulls)))

    for column in ("origin_country", "dest_country", "mode", "product_category"):
        allowed = set(columns[column]["allowed"])
        extra = set(frame[column].dropna().astype(str).unique()) - allowed
        checks.append(
            Check(
                f"{column} within vocabulary",
                len(extra) == 0,
                "critical",
                f"unexpected values: {sorted(extra) if extra else 'none'}",
            )
        )

    bad_weight = int((frame["weight_kg"] <= 0).sum())
    checks.append(Check("weight positive", bad_weight == 0, "critical", f"{bad_weight} non-positive weights"))

    bad_cost = int((frame["freight_cost_usd"] < 0).sum())
    checks.append(Check("cost non-negative", bad_cost == 0, "critical", f"{bad_cost} negative costs"))

    backwards = int((frame["ship_date"] < frame["order_date"]).sum())
    checks.append(Check("ship not before order", backwards == 0, "critical", f"{backwards} violations"))

    impossible = int((frame["transit_days"] < 0).sum())
    checks.append(Check("transit non-negative", impossible == 0, "warning", f"{impossible} negative transits"))

    imputed = round(float(frame["weight_imputed"].mean()), 4)
    checks.append(
        Check(
            "imputation share",
            imputed <= MAX_IMPUTED_SHARE,
            "warning",
            f"{imputed:.2%} of weights imputed (limit {MAX_IMPUTED_SHARE:.0%})",
        )
    )

    # cost per kg is the domain-plausible way to spot a unit or currency slip:
    # a mixed mode book should sit between a few cents and a few dollars
    per_kg = (frame["freight_cost_usd"] / frame["weight_kg"].replace(0, pd.NA)).median()
    checks.append(
        Check(
            "cost per kg plausible",
            0.02 <= float(per_kg) <= 15.0,
            "warning",
            f"median ${float(per_kg):,.2f} per kg",
        )
    )

    checks.append(
        Check("row count in expected band", 2_000 <= len(frame) <= 50_000, "warning", f"{len(frame):,} rows")
    )
    return checks


def summarise(checks: list[Check]) -> dict[str, int]:
    failed = [c for c in checks if not c.passed]
    return {
        "total": len(checks),
        "failed": len(failed),
        "critical_failures": sum(1 for c in failed if c.severity == "critical"),
        "warnings": sum(1 for c in failed if c.severity == "warning"),
    }
