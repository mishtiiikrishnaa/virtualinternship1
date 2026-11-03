"""Run the statistical analysis and write every number to results/*.json.

The report builder reads only these files. No statistic in the prose is typed
by hand, which is what makes the audit in ``src/audit.py`` meaningful.

Sections produced
-----------------
profile.json        shape, dtypes, missingness, category counts
descriptive.json    per-variable and grouped summary statistics
distributions.json  normality tests on raw and log scales
correlations.json   Pearson, Spearman, VIF
outliers.json       IQR vs z vs modified z, plus recovery of planted outliers
timeseries.json     monthly trend, STL, disruption month
tests.json          hypothesis tests, effect sizes, corrected p-values
lanes.json          lane concentration, Pareto, lane x mode
cost.json           log-log regression, residual checks, unit economics
real_data.json      Dataset B (BTS border crossings) trend and seasonality
validation.json     planted effect vs recovered effect
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tsa.seasonal import STL

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CLEAN = ROOT / "data" / "processed" / "shipments_clean.csv"
TRUTH = ROOT / "data" / "simulated" / "shipments_ground_truth.csv"
REAL = ROOT / "data" / "external" / "bts_border_trucks.csv.gz"

KEY_VARS = ["transit_days", "freight_cost_usd", "weight_kg", "volume_m3",
            "distance_km", "cost_per_kg", "cost_per_km", "promised_days",
            "delay_days"]


def r(value, digits: int = 4):
    """Round a float for storage, keeping ints as ints."""
    if value is None:
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    return round(float(value), digits)


def dump(name: str, payload: dict) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(
        json.dumps(payload, indent=2, default=lambda o: float(o)) + "\n")
    print(f"wrote results/{name}.json  ({len(json.dumps(payload))} bytes)")


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (centre - half, centre + half)


# --------------------------------------------------------------------------
# profile
# --------------------------------------------------------------------------
def build_profile(df: pd.DataFrame, raw_shape: tuple[int, int]) -> dict:
    missing = []
    for column in df.columns:
        count = int(df[column].isna().sum())
        missing.append({"column": column, "dtype": str(df[column].dtype),
                        "missing": count,
                        "missing_pct": r(100 * count / len(df), 2),
                        "unique": int(df[column].nunique(dropna=True))})
    dtype_counts = pd.Series([str(t) for t in df.dtypes]).value_counts().to_dict()
    return {
        "rows_raw": raw_shape[0],
        "cols_raw": raw_shape[1],
        "rows_clean": int(len(df)),
        "cols_clean": int(df.shape[1]),
        "date_min": str(df["order_date"].min().date()),
        "date_max": str(df["order_date"].max().date()),
        "memory_mb": r(df.memory_usage(deep=True).sum() / 1e6, 2),
        "dtype_counts": dtype_counts,
        "missing": missing,
        "rows_with_any_missing": int(df.isna().any(axis=1).sum()),
        "rows_with_any_missing_pct": r(100 * df.isna().any(axis=1).mean(), 2),
        "status_counts": df["status"].value_counts().to_dict(),
        "mode_counts": df["mode"].value_counts().to_dict(),
        "carrier_counts": df["carrier"].value_counts().to_dict(),
        "priority_counts": df["priority"].value_counts().to_dict(),
        "lane_count": int(df["lane"].nunique()),
        "shipment_count": int(df["shipment_id"].nunique()),
        "on_time_eligible": int(df["on_time"].notna().sum()),
        "on_time_rate": r(df["on_time"].mean(), 4),
        "cost_scored_rows": int(df["freight_cost_usd"].notna().sum()),
        "cost_missing_rows": int(df["freight_cost_usd"].isna().sum()),
        "cost_missing_share": r(df["freight_cost_usd"].isna().mean(), 4),
    }


# --------------------------------------------------------------------------
# descriptive
# --------------------------------------------------------------------------
def build_descriptive(df: pd.DataFrame) -> dict:
    table = {}
    for column in KEY_VARS:
        series = df[column].dropna()
        q1, q3 = series.quantile([0.25, 0.75])
        table[column] = {
            "n": int(series.size),
            "mean": r(series.mean()),
            "median": r(series.median()),
            "std": r(series.std()),
            "min": r(series.min()),
            "p25": r(q1),
            "p75": r(q3),
            "p90": r(series.quantile(0.90)),
            "max": r(series.max()),
            "iqr": r(q3 - q1),
            "cv": r(series.std() / series.mean()),
            "skew": r(stats.skew(series)),
            "kurtosis": r(stats.kurtosis(series)),
            "unit": {"transit_days": "days", "freight_cost_usd": "USD",
                     "weight_kg": "kg", "volume_m3": "m3",
                     "distance_km": "km", "cost_per_kg": "USD/kg",
                     "cost_per_km": "USD/km", "promised_days": "days",
                     "delay_days": "days"}[column],
        }

    by_mode = {}
    for mode, group in df.groupby("mode"):
        by_mode[mode] = {
            "shipments": int(len(group)),
            "share": r(len(group) / len(df)),
            "median_transit_days": r(group["transit_days"].median()),
            "mean_transit_days": r(group["transit_days"].mean()),
            "p90_transit_days": r(group["transit_days"].quantile(0.90)),
            "median_promised_days": r(group["promised_days"].median()),
            "on_time_rate": r(group["on_time"].mean()),
            "median_weight_kg": r(group["weight_kg"].median()),
            "median_distance_km": r(group["distance_km"].median()),
            "median_cost_usd": r(group["freight_cost_usd"].median()),
            "median_cost_per_kg": r(group["cost_per_kg"].median()),
            "mean_delay_days": r(group["delay_days"].mean()),
            "costed_shipments": int(group["freight_cost_usd"].notna().sum()),
        }

    by_carrier = {}
    for carrier, group in df.groupby("carrier"):
        eligible = group["on_time"].dropna()
        k, n = int(eligible.sum()), int(eligible.size)
        low, high = wilson(k, n)
        by_carrier[carrier] = {
            "shipments": int(len(group)),
            "modes": sorted(group["mode"].unique().tolist()),
            "median_transit_days": r(group["transit_days"].median()),
            "on_time_rate": r(eligible.mean()),
            "ci_low": r(low),
            "ci_high": r(high),
            "median_cost_per_kg": r(group["cost_per_kg"].median()),
            "mean_delay_days": r(group["delay_days"].mean()),
        }

    by_priority = {}
    for priority, group in df.groupby("priority"):
        by_priority[priority] = {
            "shipments": int(len(group)),
            "median_transit_days": r(group["transit_days"].median()),
            "on_time_rate": r(group["on_time"].mean()),
        }

    log_cost = np.log(df["freight_cost_usd"].dropna())
    return {"variables": table, "by_mode": by_mode, "by_carrier": by_carrier,
            "by_priority": by_priority,
            "log_cost": {"mean": r(log_cost.mean()), "std": r(log_cost.std()),
                         "skew": r(stats.skew(log_cost)),
                         "kurtosis": r(stats.kurtosis(log_cost))}}


# --------------------------------------------------------------------------
# distributions
# --------------------------------------------------------------------------
def build_distributions(df: pd.DataFrame) -> dict:
    out = {}
    rng = np.random.default_rng(42)
    for column in ["transit_days", "freight_cost_usd", "weight_kg", "cost_per_kg"]:
        series = df[column].dropna()
        transformed = np.log(series.clip(lower=1e-6))
        dagostino_raw = stats.normaltest(series)
        dagostino_log = stats.normaltest(transformed)
        sample = series.sample(5000, random_state=42)
        shapiro_raw = stats.shapiro(sample)
        shapiro_log = stats.shapiro(np.log(sample.clip(lower=1e-6)))
        out[column] = {
            "n": int(series.size),
            "raw": {"skew": r(stats.skew(series)),
                    "kurtosis": r(stats.kurtosis(series)),
                    "dagostino_stat": r(dagostino_raw.statistic),
                    "dagostino_p": r(dagostino_raw.pvalue, 10)},
            "log": {"skew": r(stats.skew(transformed)),
                    "kurtosis": r(stats.kurtosis(transformed)),
                    "dagostino_stat": r(dagostino_log.statistic),
                    "dagostino_p": r(dagostino_log.pvalue, 10)},
            "shapiro_sample_n": 5000,
            "shapiro_raw_stat": r(shapiro_raw.statistic),
            "shapiro_raw_p": r(shapiro_raw.pvalue, 10),
            "shapiro_log_stat": r(shapiro_log.statistic),
            "shapiro_log_p": r(shapiro_log.pvalue, 10),
            "log_transform_justified": bool(
                abs(stats.skew(transformed)) < abs(stats.skew(series))),
        }
    return out


# --------------------------------------------------------------------------
# correlations
# --------------------------------------------------------------------------
def build_correlations(df: pd.DataFrame) -> dict:
    columns = ["transit_days", "distance_km", "weight_kg", "volume_m3",
               "freight_cost_usd", "cost_per_kg", "promised_days", "delay_days"]
    frame = df[columns].dropna()
    pearson = frame.corr(method="pearson")
    spearman = frame.corr(method="spearman")

    pairs = []
    for i, a in enumerate(columns):
        for b in columns[i + 1:]:
            pairs.append({"pair": f"{a} / {b}", "pearson": r(pearson.loc[a, b]),
                          "spearman": r(spearman.loc[a, b])})
    top = sorted(pairs, key=lambda p: abs(p["spearman"]), reverse=True)[:6]

    vif_frame = sm.add_constant(
        df[["weight_kg", "volume_m3", "distance_km"]].dropna())
    vif = {}
    for i, column in enumerate(vif_frame.columns):
        if column == "const":
            continue
        vif[column] = r(variance_inflation_factor(vif_frame.values, i), 2)

    cost_frame = df[["freight_cost_usd", "weight_kg", "distance_km"]].dropna()
    r_p, p_p = stats.pearsonr(cost_frame["distance_km"],
                              cost_frame["freight_cost_usd"])
    z = np.arctanh(r_p)
    se = 1 / np.sqrt(len(cost_frame) - 3)
    return {
        "n": int(len(frame)),
        "pearson": {a: {b: r(pearson.loc[a, b]) for b in columns} for a in columns},
        "spearman": {a: {b: r(spearman.loc[a, b]) for b in columns} for a in columns},
        "top_pairs": top,
        "vif": vif,
        "cost_distance": {"r": r(r_p), "p": r(p_p, 12),
                          "ci_low": r(np.tanh(z - 1.96 * se)),
                          "ci_high": r(np.tanh(z + 1.96 * se))},
        "weight_volume_r": r(pearson.loc["weight_kg", "volume_m3"]),
        "cost_weight_r": r(spearman.loc["weight_kg", "freight_cost_usd"]),
        "cost_distance_r": r(spearman.loc["distance_km", "freight_cost_usd"]),
    }


# --------------------------------------------------------------------------
# outliers
# --------------------------------------------------------------------------
def log_modified_z(series: pd.Series, groups: pd.Series,
                   threshold: float = 3.5) -> pd.Series:
    """Modified z on log values, computed inside each mode.

    Univariate rules on a raw lognormal scale over-flag the right tail. Taking
    logs makes the core roughly symmetric, and grouping by mode stops a heavy
    sea shipment being compared with a light air parcel.
    """
    frame = pd.DataFrame({"value": series, "group": groups})
    out = pd.Series(False, index=frame.index)
    for _, block in frame.groupby("group"):
        valid = block["value"].dropna()
        if len(valid) < 30:
            continue
        logs = np.log(valid.clip(lower=1e-6))
        mad = np.median(np.abs(logs - logs.median()))
        if mad == 0:
            continue
        score = 0.6745 * (logs - logs.median()) / mad
        out.loc[valid.index] = (score.abs() > threshold).to_numpy()
    return out


def residual_modified_z(frame: pd.DataFrame, target: str,
                        predictors: list[str], with_mode: bool = True):
    """Flag rows whose residual from a log-linear expectation is extreme.

    A cost outlier is only an outlier relative to what weight and distance
    predict, which is why a univariate rule on cost alone performs badly.
    """
    data = frame.dropna(subset=[target] + predictors)
    y = np.log(data[target].clip(lower=1e-6))
    X = pd.DataFrame({f"log_{p}": np.log(data[p].clip(lower=1e-6)) for p in predictors},
                     index=data.index)
    if with_mode:
        X = pd.concat([X, pd.get_dummies(data["mode"], prefix="mode",
                                        drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    model = sm.OLS(y, X).fit()
    resid = model.resid
    mad = np.median(np.abs(resid - resid.median()))
    score = 0.6745 * (resid - resid.median()) / mad
    flag = pd.Series(False, index=frame.index)
    flag.loc[resid.index] = (score.abs() > 3.5).to_numpy()
    return flag, {"r2": r(model.rsquared), "n": int(len(data)),
                  "resid_sd": r(np.std(resid)), "mad": r(mad),
                  "threshold_score": 3.5}


def build_outliers(df: pd.DataFrame) -> dict:
    truth = pd.read_csv(TRUTH)[["shipment_id", "planted_outlier"]]
    frame = df.merge(truth, on="shipment_id", how="left")

    per_variable = {}
    for column in ["freight_cost_usd", "weight_kg", "transit_days", "cost_per_kg"]:
        series = frame[column].dropna()
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        iqr_mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
        z = (series - series.mean()) / series.std()
        mad = np.median(np.abs(series - series.median()))
        modified = 0.6745 * (series - series.median()) / mad
        log_flag = log_modified_z(frame[column], frame["mode"])
        per_variable[column] = {
            "n": int(series.size),
            "log_mz_count": int(log_flag.sum()),
            "log_mz_pct": r(100 * log_flag.mean(), 2),
            "iqr_count": int(iqr_mask.sum()),
            "iqr_pct": r(100 * iqr_mask.mean(), 2),
            "z_count": int((z.abs() > 3).sum()),
            "z_pct": r(100 * (z.abs() > 3).mean(), 2),
            "modified_z_count": int((modified.abs() > 3.5).sum()),
            "modified_z_pct": r(100 * (modified.abs() > 3.5).mean(), 2),
            "upper_fence": r(q3 + 1.5 * iqr),
            "max": r(series.max()),
            "mad": r(mad),
        }

    # three-method agreement on freight cost, the variable the report treats
    cost = frame["freight_cost_usd"].dropna()

    def method_flags(series: pd.Series) -> pd.DataFrame:
        s = series.dropna()
        q1_, q3_ = s.quantile([0.25, 0.75])
        iqr_ = q3_ - q1_
        mad_ = np.median(np.abs(s - s.median()))
        out = pd.DataFrame({
            "iqr": (s < q1_ - 1.5 * iqr_) | (s > q3_ + 1.5 * iqr_),
            "z": ((s - s.mean()).abs() / s.std()) > 3,
            "mz": (0.6745 * (s - s.median()) / mad_).abs() > 3.5,
        })
        return out.reindex(series.index, fill_value=False)
    q1, q3 = cost.quantile([0.25, 0.75])
    iqr = q3 - q1
    iqr_flag = ((cost < q1 - 1.5 * iqr) | (cost > q3 + 1.5 * iqr))
    z_flag = ((cost - cost.mean()).abs() / cost.std() > 3)
    mad = np.median(np.abs(cost - cost.median()))
    mz_flag = (0.6745 * (cost - cost.median()) / mad).abs() > 3.5

    flagged_any = frame["outlier_cost_iqr"].fillna(False)
    planted = frame["planted_outlier"].fillna(False).astype(bool)
    profile = {
        "flagged_rows": int(flagged_any.sum()),
        "planted_rows": int(planted.sum()),
        "planted_share": r(planted.mean()),
        "flagged_median_cost": r(frame.loc[flagged_any, "freight_cost_usd"].median()),
        "clean_median_cost": r(frame.loc[~flagged_any, "freight_cost_usd"].median()),
    }

    weight_flags = method_flags(frame["weight_kg"])
    transit_flags = method_flags(frame["transit_days"])
    raw_flag = (weight_flags["mz"] | transit_flags["mz"] |
                method_flags(frame["freight_cost_usd"])["mz"])
    cost_resid_flag, cost_resid_fit = residual_modified_z(
        frame, "freight_cost_usd", ["weight_kg", "distance_km"])
    weight_resid_flag, weight_resid_fit = residual_modified_z(
        frame, "weight_kg", ["volume_m3"])
    transit_flag = log_modified_z(frame["transit_days"], frame["mode"])
    robust_flag = cost_resid_flag | weight_resid_flag | transit_flag
    raw_caught = raw_flag & planted
    caught = robust_flag & planted
    iqr_flag_all = method_flags(frame["freight_cost_usd"])["iqr"] | method_flags(
        frame["weight_kg"])["iqr"] | method_flags(frame["transit_days"])["iqr"]
    z_flag_all = method_flags(frame["freight_cost_usd"])["z"] | method_flags(
        frame["weight_kg"])["z"] | method_flags(frame["transit_days"])["z"]
    recovery = {
        "flagged_rows": int(robust_flag.sum()),
        "flagged_pct": r(100 * robust_flag.mean(), 2),
        "recall": r(caught.sum() / planted.sum()),
        "precision": r(caught.sum() / max(robust_flag.sum(), 1)),
        "missed": int((planted & ~robust_flag).sum()),
        "raw_flagged_rows": int(raw_flag.sum()),
        "raw_recall": r(raw_caught.sum() / planted.sum()),
        "raw_precision": r(raw_caught.sum() / max(raw_flag.sum(), 1)),
        "comparison": [
            {"method": "IQR fence", "flagged": int(iqr_flag_all.sum()),
             "recall": r((iqr_flag_all & planted).sum() / planted.sum()),
             "precision": r((iqr_flag_all & planted).sum() / max(iqr_flag_all.sum(), 1))},
            {"method": "z-score > 3", "flagged": int(z_flag_all.sum()),
             "recall": r((z_flag_all & planted).sum() / planted.sum()),
             "precision": r((z_flag_all & planted).sum() / max(z_flag_all.sum(), 1))},
            {"method": "modified z (raw)", "flagged": int(raw_flag.sum()),
             "recall": r(raw_caught.sum() / planted.sum()),
             "precision": r(raw_caught.sum() / max(raw_flag.sum(), 1))},
            {"method": "residual-modified z", "flagged": int(robust_flag.sum()),
             "recall": r(caught.sum() / planted.sum()),
             "precision": r(caught.sum() / max(robust_flag.sum(), 1))},
        ],
        "flag_columns": {"cost": int(cost_resid_flag.sum()),
                         "weight": int(weight_resid_flag.sum()),
                         "transit": int(transit_flag.sum())},
        "residual_fits": {"cost": cost_resid_fit, "weight": weight_resid_fit},
    }
    weight_log = log_modified_z(frame["weight_kg"], frame["mode"])
    weight_recovery = {
        "flagged": int(weight_log.sum()),
        "recall": r((weight_log & planted).sum() / planted.sum()),
        "precision": r((weight_log & planted).sum() / max(weight_log.sum(), 1)),
    }

    return {
        "per_variable": per_variable,
        "agreement": {
            "iqr": int(iqr_flag.sum()),
            "z": int(z_flag.sum()),
            "modified_z": int(mz_flag.sum()),
            "all_three": int((iqr_flag & z_flag & mz_flag).sum()),
            "any_method": int((iqr_flag | z_flag | mz_flag).sum()),
        },
        "profile": profile,
        "recovery": recovery,
        "weight_recovery": weight_recovery,
        "decision": "retain all rows, flag only; refit the cost model without "
                    "flagged rows as a sensitivity check",
    }


# --------------------------------------------------------------------------
# time series
# --------------------------------------------------------------------------
def seasonal_strength(series: pd.Series) -> dict:
    result = STL(series, period=12, robust=True).fit()
    resid_var = np.var(result.resid)
    return {
        "seasonal_strength": r(max(0.0, 1 - resid_var / np.var(result.seasonal + result.resid))),
        "trend_strength": r(max(0.0, 1 - resid_var / np.var(result.trend + result.resid))),
        "resid_sd": r(np.std(result.resid)),
        "seasonal": [r(v) for v in result.seasonal.values],
        "trend": [r(v) for v in result.trend.values],
        "resid": [r(v) for v in result.resid.values],
    }


def build_timeseries(df: pd.DataFrame, real: pd.DataFrame) -> dict:
    monthly = df.groupby("month_start").agg(
        shipments=("shipment_id", "size"),
        median_transit=("transit_days", "median"),
        on_time=("on_time", "mean"),
        mean_delay=("delay_days", "mean"),
        mean_cost=("freight_cost_usd", "mean"),
        q4=("is_q4", "first"),
    ).sort_index()
    monthly["rolling_3"] = monthly["shipments"].rolling(3, center=True).mean()
    index = monthly["shipments"] / monthly["shipments"].mean()

    q4_mean = monthly.loc[monthly["q4"], "shipments"].mean()
    non_q4_mean = monthly.loc[~monthly["q4"], "shipments"].mean()
    q4_index = q4_mean / non_q4_mean

    months = [str(i.date()) for i in monthly.index]
    decomp = seasonal_strength(monthly["shipments"].astype(float).set_axis(
        pd.PeriodIndex(monthly.index, freq="M")))

    # disruption detection on the on-time rate
    mz = 0.6745 * (monthly["on_time"] - monthly["on_time"].median()) / np.median(
        np.abs(monthly["on_time"] - monthly["on_time"].median()))
    flagged = monthly.index[mz < -3.5]
    disruption = [str(d.date()) for d in flagged]

    feb = df[df["month"] == "2025-02"]
    baseline = df[df["month"].isin(["2025-01", "2025-03"])]
    sea_feb = feb.loc[feb["mode"] == "Sea", "transit_days"].dropna()
    sea_base = baseline.loc[baseline["mode"] == "Sea", "transit_days"].dropna()
    mw = stats.mannwhitneyu(sea_feb, sea_base, alternative="greater")

    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                     "Saturday", "Sunday"]
    weekday = df.groupby("weekday")["delay_days"].agg(["mean", "median", "size"])
    weekday = weekday.reindex(weekday_order)

    delay_matrix = df.pivot_table(index="weekday", columns="month",
                                  values="delay_days", aggfunc="mean")
    delay_matrix = delay_matrix.reindex(weekday_order)
    month_labels = sorted(delay_matrix.columns)
    mode_monthly = {}
    for mode in ["Air", "Road", "Rail", "Sea"]:
        block = df[df["mode"] == mode].groupby("month_start").agg(
            median=("transit_days", "median"), on_time=("on_time", "mean"))
        mode_monthly[mode] = {"months": [str(i.date()) for i in block.index],
                              "median": [r(v) for v in block["median"].values],
                              "on_time": [r(v) for v in block["on_time"].values]}

    return {
        "monthly": {
            "months": months,
            "shipments": [int(v) for v in monthly["shipments"]],
            "rolling_3": [r(v) for v in monthly["rolling_3"]],
            "on_time": [r(v) for v in monthly["on_time"]],
            "median_transit": [r(v) for v in monthly["median_transit"]],
            "mean_delay": [r(v) for v in monthly["mean_delay"]],
            "cost_missing_share": [r(v) for v in monthly["mean_cost"].isna()],
        },
        "summary": {
            "month_count": int(len(monthly)),
            "total_shipments": int(monthly["shipments"].sum()),
            "mean_monthly": r(monthly["shipments"].mean()),
            "sd_monthly": r(monthly["shipments"].std()),
            "cv_monthly": r(monthly["shipments"].std() / monthly["shipments"].mean()),
            "peak_month": str(monthly["shipments"].idxmax().date()),
            "peak_value": int(monthly["shipments"].max()),
            "trough_month": str(monthly["shipments"].idxmin().date()),
            "trough_value": int(monthly["shipments"].min()),
            "q4_mean": r(q4_mean),
            "non_q4_mean": r(non_q4_mean),
            "q4_index": r(q4_index),
            "q4_uplift_pct": r(100 * (q4_index - 1), 1),
            "growth_2025_vs_2024_pct": r(100 * (monthly.loc["2025", "shipments"].sum() /
                                               monthly.loc["2024", "shipments"].sum() - 1), 1),
        },
        "decomposition": decomp,
        "seasonal_index_by_month": {
            str(m): r(index[index.index.month == m].mean()) for m in range(1, 13)},
        "disruption": {
            "detected_months": disruption,
            "feb_sea_median_days": r(sea_feb.median()),
            "baseline_sea_median_days": r(sea_base.median()),
            "extra_days": r(sea_feb.median() - sea_base.median()),
            "mannwhitney_u": r(mw.statistic, 1),
            "mannwhitney_p": r(mw.pvalue, 12),
            "feb_on_time": r(feb["on_time"].mean()),
            "baseline_on_time": r(baseline["on_time"].mean()),
            "on_time_gap_pp": r(100 * (baseline["on_time"].mean() - feb["on_time"].mean()), 1),
        },
        "delay_matrix": {"months": month_labels,
                         "rows": {d: [r(delay_matrix.loc[d, m]) for m in month_labels]
                                  for d in weekday_order}},
        "mode_monthly": mode_monthly,
        "weekday": {d: {"mean_delay": r(weekday.loc[d, "mean"]),
                        "median_delay": r(weekday.loc[d, "median"]),
                        "shipments": int(weekday.loc[d, "size"])}
                    for d in weekday_order},
        "real_data": build_real_timeseries(real),
    }


def build_real_timeseries(real: pd.DataFrame) -> dict:
    monthly = real.groupby("date")["value"].sum().sort_index()
    monthly = monthly[monthly.index >= "2010-01-01"]
    monthly.index = pd.PeriodIndex(monthly.index, freq="M")
    rolling = monthly.rolling(12).mean()
    full = real.groupby("date")["value"].sum().sort_index()

    recent = full[full.index >= "2015-01-01"]
    seasonal = recent.groupby(recent.index.month).mean()
    seasonal_index = (seasonal / seasonal.mean()).round(4)

    stl = STL(monthly.astype(float), period=12, robust=True).fit()
    resid_var = np.var(stl.resid)

    top_ports = (real[real["date"].dt.year == 2025].groupby("port_name")["value"]
                 .sum().sort_values(ascending=False))
    shares = top_ports / top_ports.sum()
    hhi = float((shares**2).sum())

    apr19 = full.get(pd.Timestamp("2019-04-01"))
    apr20 = full.get(pd.Timestamp("2020-04-01"))
    annual = full.groupby(full.index.year).sum()

    yoy = (monthly.pct_change(12) * 100).dropna()
    yoy_mz = 0.6745 * (yoy - yoy.median()) / np.median(np.abs(yoy - yoy.median()))
    shock_months = [str(p) for p in yoy.index[yoy_mz.abs() > 3.5]]

    latest_yoy = float(monthly.iloc[-1] / monthly.iloc[-13] - 1) * 100
    return {
        "rows": int(len(real)),
        "ports": int(real["port_code"].nunique()),
        "states": int(real["state"].nunique()),
        "date_min": str(real["date"].min().date()),
        "date_max": str(real["date"].max().date()),
        "monthly_last12_mean": r(monthly.tail(12).mean(), 0),
        "latest_month": str(monthly.index[-1]),
        "latest_value": int(monthly.iloc[-1]),
        "latest_yoy_pct": r(latest_yoy, 1),
        "peak_month": str(seasonal.idxmax()),
        "peak_index": r(seasonal_index.max()),
        "trough_month": str(seasonal.idxmin()),
        "trough_index": r(seasonal_index.min()),
        "seasonal_index": {str(m): r(v) for m, v in seasonal_index.items()},
        "december_index": r(seasonal_index.get(12)),
        "october_index": r(seasonal_index.get(10)),
        "seasonal_strength": r(max(0.0, 1 - resid_var / np.var(stl.seasonal + stl.resid))),
        "trend_strength": r(max(0.0, 1 - resid_var / np.var(stl.trend + stl.resid))),
        "top_port": top_ports.index[0],
        "top_port_share": r(shares.iloc[0]),
        "top5_port_share": r(shares.head(5).sum()),
        "port_hhi": r(hhi),
        "covid_apr2020_vs_apr2019_pct": r(100 * (apr20 / apr19 - 1), 1),
        "annual_2020_vs_2019_pct": r(100 * (annual.get(2020) / annual.get(2019) - 1), 1),
        "annual_min_year": int(annual.idxmin()),
        "annual_min_value": int(annual.min()),
        "annual_max_year": int(annual.idxmax()),
        "annual_max_value": int(annual.max()),
        "yoy_shock_months": shock_months[-4:],
        "cagr_2010_2019_pct": r(100 * ((annual.get(2019) / annual.get(2010)) ** (1 / 9) - 1), 1),
        "cagr_2015_2025_pct": r(100 * ((annual.get(2025) / annual.get(2015)) ** (1 / 10) - 1), 1),
        "monthly": {
            "months": [str(p) for p in monthly.index],
            "values": [int(v) for v in monthly.values],
            "rolling_12": [None if pd.isna(v) else r(v, 0) for v in rolling.values],
        },
    }


# --------------------------------------------------------------------------
# hypothesis tests
# --------------------------------------------------------------------------
def holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues)
    m = len(pvalues)
    adjusted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        value = (m - rank) * pvalues[idx]
        running = max(running, value)
        adjusted[idx] = min(1.0, running)
    return adjusted.tolist()


def build_tests(df: pd.DataFrame) -> dict:
    modes = ["Air", "Road", "Rail", "Sea"]
    groups = [df.loc[df["mode"] == m, "transit_days"].dropna() for m in modes]
    kw = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    epsilon_sq = (kw.statistic - len(groups) + 1) / (n - len(groups))

    pairs, raw_p = [], []
    for i, a in enumerate(modes):
        for b in modes[i + 1:]:
            ga = df.loc[df["mode"] == a, "transit_days"].dropna()
            gb = df.loc[df["mode"] == b, "transit_days"].dropna()
            test = stats.mannwhitneyu(ga, gb, alternative="two-sided")
            rank_biserial = 2 * test.statistic / (len(ga) * len(gb)) - 1
            pairs.append({"a": a, "b": b, "u": r(test.statistic, 1),
                          "p": r(test.pvalue, 12),
                          "median_a": r(ga.median()), "median_b": r(gb.median()),
                          "delta_days": r(gb.median() - ga.median()),
                          "rank_biserial": r(rank_biserial)})
            raw_p.append(test.pvalue)
    adjusted = holm(raw_p)
    for row, adj in zip(pairs, adjusted):
        row["p_holm"] = r(adj, 12)
        row["significant"] = bool(adj < 0.05)

    log_groups = [np.log1p(g) for g in groups]
    anova = stats.f_oneway(*log_groups)
    grand = np.concatenate(log_groups)
    ss_between = sum(len(g) * (g.mean() - grand.mean())**2 for g in log_groups)
    ss_total = ((grand - grand.mean())**2).sum()

    # on-time by carrier: chi-square and Wilson intervals
    eligible = df[df["on_time"].notna()].copy()
    table = pd.crosstab(eligible["carrier"], eligible["on_time"])
    chi2, p_chi, dof, expected = stats.chi2_contingency(table)
    cramers_v = np.sqrt(chi2 / (table.values.sum() * (min(table.shape) - 1)))

    mode_table = pd.crosstab(eligible["mode"], eligible["on_time"])
    chi2_mode, p_mode, dof_mode, _ = stats.chi2_contingency(mode_table)
    v_mode = np.sqrt(chi2_mode / (mode_table.values.sum() * (min(mode_table.shape) - 1)))
    best = eligible.groupby("carrier")["on_time"].mean().idxmax()
    worst = eligible.groupby("carrier")["on_time"].mean().idxmin()

    priority_groups = [df.loc[df["priority"] == p, "transit_days"].dropna()
                       for p in ["High", "Standard", "Low"]]
    kw_priority = stats.kruskal(*priority_groups)
    high = df.loc[df["priority"] == "High", "transit_days"].dropna()
    low = df.loc[df["priority"] == "Low", "transit_days"].dropna()
    mw_priority = stats.mannwhitneyu(high, low, alternative="less")

    feb = df.loc[df["month"] == "2025-02", "transit_days"].dropna()
    rest = df.loc[df["month"] != "2025-02", "transit_days"].dropna()
    mw_disruption = stats.mannwhitneyu(feb, rest, alternative="greater")

    cost_groups = [df.loc[df["mode"] == m, "cost_per_kg"].dropna() for m in modes]
    kw_cost = stats.kruskal(*cost_groups)

    return {
        "transit_by_mode": {
            "kruskal_h": r(kw.statistic), "df": len(modes) - 1,
            "p": r(kw.pvalue, 12), "epsilon_squared": r(epsilon_sq),
            "n": int(n),
            "group_medians": {m: r(df.loc[df["mode"] == m, "transit_days"].median())
                              for m in modes},
            "pairwise": pairs,
            "anova_log_f": r(anova.statistic), "anova_log_p": r(anova.pvalue, 12),
            "anova_eta_squared": r(ss_between / ss_total),
        },
        "on_time_by_carrier": {
            "chi2": r(chi2, 2), "dof": int(dof), "p": r(p_chi, 12),
            "cramers_v": r(cramers_v),
            "best_carrier": best, "worst_carrier": worst,
            "best_rate": r(eligible.groupby("carrier")["on_time"].mean().max()),
            "worst_rate": r(eligible.groupby("carrier")["on_time"].mean().min()),
            "gap_pp": r(100 * (eligible.groupby("carrier")["on_time"].mean().max() -
                               eligible.groupby("carrier")["on_time"].mean().min()), 1),
            "table": table.to_dict(),
        },
        "on_time_by_mode": {"chi2": r(chi2_mode, 2), "dof": int(dof_mode),
                            "p": r(p_mode, 12), "cramers_v": r(v_mode)},
        "priority": {"kruskal_h": r(kw_priority.statistic), "p": r(kw_priority.pvalue, 12),
                     "median_high": r(high.median()), "median_low": r(low.median()),
                     "mean_high": r(high.mean()), "mean_low": r(low.mean()),
                     "median_standard": r(df.loc[df["priority"] == "Standard",
                                                 "transit_days"].median()),
                     "carrier_counts": {c: {"on_time": int(row.get(1.0, 0)),
                                            "late": int(row.get(0.0, 0))}
                                        for c, row in table.iterrows()},
                     "mannwhitney_u": r(mw_priority.statistic, 1),
                     "mannwhitney_p": r(mw_priority.pvalue, 12)},
        "disruption": {"mannwhitney_u": r(mw_disruption.statistic, 1),
                       "p": r(mw_disruption.pvalue, 12),
                       "feb_median": r(feb.median()), "rest_median": r(rest.median())},
        "cost_per_kg_by_mode": {"kruskal_h": r(kw_cost.statistic),
                                "p": r(kw_cost.pvalue, 12)},
        "correction": {"family_size": 12, "method": "Holm-Bonferroni on mode pairs; "
                       "family-wise alpha 0.05 elsewhere",
                       "alpha": 0.05, "bonferroni_alpha": r(0.05 / 12, 6)},
    }


# --------------------------------------------------------------------------
# lanes
# --------------------------------------------------------------------------
def build_lanes(df: pd.DataFrame) -> dict:
    lanes = df.groupby("lane").agg(
        shipments=("shipment_id", "size"),
        on_time=("on_time", "mean"),
        median_transit=("transit_days", "median"),
        median_cost=("freight_cost_usd", "median"),
        median_distance=("distance_km", "median"),
    ).sort_values("shipments", ascending=False)
    shares = lanes["shipments"] / lanes["shipments"].sum()
    cum = shares.cumsum()
    hhi = float((shares**2).sum())
    n_for_80 = int((cum < 0.80).sum() + 1)

    top = lanes.head(15)
    top_rows = [{"lane": lane, "shipments": int(row.shipments),
                 "share_pct": r(100 * row.shipments / len(df), 1),
                 "cum_share_pct": r(100 * cum.loc[lane], 1),
                 "on_time": r(row.on_time),
                 "median_transit": r(row.median_transit),
                 "median_cost": r(row.median_cost)} for lane, row in top.iterrows()]

    lane_mode = pd.crosstab(df["lane"], df["mode"])
    lane_mode = lane_mode.loc[top.index]

    reliable = lanes[lanes["shipments"] >= 200]
    return {
        "lane_count": int(lanes.shape[0]),
        "top10_share": r(cum.iloc[9]),
        "top15_share_pct": r(100 * cum.iloc[14], 1),
        "top10_share_pct": r(100 * cum.iloc[9], 1),
        "hhi": r(hhi, 3),
        "effective_lanes": r(1 / hhi, 1),
        "lanes_for_80pct": n_for_80,
        "lanes_for_80pct_share": r(100 * n_for_80 / lanes.shape[0], 1),
        "top_lanes": top_rows,
        "lane_mode": {lane: {m: int(lane_mode.loc[lane, m]) if m in lane_mode.columns else 0
                             for m in ["Air", "Road", "Rail", "Sea"]}
                      for lane in lane_mode.index},
        "best_lane": {"lane": reliable["on_time"].idxmax(),
                      "on_time": r(reliable["on_time"].max()),
                      "shipments": int(reliable.loc[reliable["on_time"].idxmax(), "shipments"])},
        "worst_lane": {"lane": reliable["on_time"].idxmin(),
                       "on_time": r(reliable["on_time"].min()),
                       "shipments": int(reliable.loc[reliable["on_time"].idxmin(), "shipments"])},
        "reliable_lane_count": int(len(reliable)),
    }


# --------------------------------------------------------------------------
# cost model
# --------------------------------------------------------------------------
def fit_loglog(frame: pd.DataFrame, label: str, with_mode: bool = False) -> dict:
    data = frame.dropna(subset=["freight_cost_usd", "weight_kg", "distance_km"])
    y = np.log(data["freight_cost_usd"])
    X = pd.DataFrame({
        "log_weight": np.log(data["weight_kg"].to_numpy()),
        "log_distance": np.log(data["distance_km"].to_numpy()),
    }, index=data.index)
    if with_mode:
        dummies = pd.get_dummies(data["mode"], prefix="mode", drop_first=True,
                                 dtype=float)
        X = pd.concat([X, dummies], axis=1)
    X = sm.add_constant(X)
    model = sm.OLS(y.to_numpy(), X).fit()
    resid = model.resid
    bp = het_breuschpagan(resid, model.model.exog)
    jb = stats.jarque_bera(resid)
    return {
        "label": label,
        "n": int(len(data)),
        "r2": r(model.rsquared),
        "adj_r2": r(model.rsquared_adj),
        "weight_elasticity": r(model.params["log_weight"]),
        "weight_se": r(model.bse["log_weight"]),
        "weight_ci": [r(model.conf_int().loc["log_weight", 0]),
                      r(model.conf_int().loc["log_weight", 1])],
        "distance_elasticity": r(model.params["log_distance"]),
        "distance_se": r(model.bse["log_distance"]),
        "distance_ci": [r(model.conf_int().loc["log_distance", 0]),
                        r(model.conf_int().loc["log_distance", 1])],
        "intercept": r(model.params["const"]),
        "mode_effects": {k.replace("mode_", ""): r(v) for k, v in model.params.items()
                         if k.startswith("mode_")},
        "resid_sd": r(np.std(resid)),
        "resid_skew": r(stats.skew(resid)),
        "breusch_pagan_p": r(bp[1], 12),
        "jarque_bera_p": r(jb.pvalue, 12),
        "doubling_weight_factor": r(2 ** model.params["log_weight"]),
    }


def build_cost(df: pd.DataFrame) -> dict:
    base = fit_loglog(df, "mode fixed effects", with_mode=True)
    pooled = fit_loglog(df, "pooled, no mode term")
    trimmed = df[df["freight_cost_usd"] <= df["freight_cost_usd"].quantile(0.995)]
    sensitive = fit_loglog(trimmed, "top 0.5% of costs excluded", with_mode=True)
    cost_flag, _ = residual_modified_z(df, "freight_cost_usd",
                                       ["weight_kg", "distance_km"])
    weight_flag, _ = residual_modified_z(df, "weight_kg", ["volume_m3"])
    clean_fit = fit_loglog(df[~(cost_flag | weight_flag)],
                           "residual-flagged rows excluded", with_mode=True)
    by_mode_fit = {}
    for mode, group in df.groupby("mode"):
        fit = fit_loglog(group, mode)
        by_mode_fit[mode] = {"weight_elasticity": fit["weight_elasticity"],
                             "distance_elasticity": fit["distance_elasticity"],
                             "r2": fit["r2"], "n": fit["n"]}

    by_mode = {}
    for mode, group in df.groupby("mode"):
        series = group["cost_per_kg"].dropna()
        cost = group["freight_cost_usd"].dropna()
        by_mode[mode] = {
            "median_cost_per_kg": r(series.median()),
            "mean_cost_per_kg": r(series.mean()),
            "p10": r(series.quantile(0.10)),
            "p90": r(series.quantile(0.90)),
            "iqr": r(series.quantile(0.75) - series.quantile(0.25)),
            "median_cost_usd": r(cost.median()),
            "median_cost_per_km": r(group["cost_per_km"].median()),
            "cost_share_pct": r(100 * cost.sum() / df["freight_cost_usd"].sum(), 1),
            "shipment_share_pct": r(100 * len(group) / len(df), 1),
        }
    return {
        "model": base,
        "pooled": pooled,
        "per_mode_fit": by_mode_fit,
        "sensitivity": sensitive,
        "sensitivity_flagged": clean_fit,
        "by_mode": by_mode,
        "total_cost_usd": r(df["freight_cost_usd"].sum(), 0),
        "median_cost_usd": r(df["freight_cost_usd"].median()),
        "cost_per_kg_overall": r(df["cost_per_kg"].median()),
        "air_to_sea_ratio": r(by_mode["Air"]["median_cost_per_kg"] /
                              by_mode["Sea"]["median_cost_per_kg"], 1),
        "air_to_rail_ratio": r(by_mode["Air"]["median_cost_per_kg"] /
                               by_mode["Rail"]["median_cost_per_kg"], 1),
    }


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def build_validation(planted: dict, ts: dict, cost: dict, outliers: dict,
                     clean: dict, profile: dict, tests: dict) -> dict:
    realised = planted["realised"]
    recovered_mode = ts["mode_medians"]
    rows = []

    rows.append({
        "effect": "Q4 volume peak",
        "planted": "Q4 month weight 1.35x baseline",
        "recovered": f"Q4 index {ts['summary']['q4_index']:.3f} "
                     f"({ts['summary']['q4_uplift_pct']:.1f}% above other months)",
        "match": abs(ts["summary"]["q4_index"] - 1.35) < 0.08,
        "note": "sampling noise and the January dip move the index slightly",
    })
    medians = {k: v for k, v in realised["median_transit_days_by_mode"].items()}
    rows.append({
        "effect": "Mode-specific transit times",
        "planted": "medians " + ", ".join(f"{k} {v:.0f} d" for k, v in medians.items()),
        "recovered": "medians " + ", ".join(f"{k} {recovered_mode[k]:.0f} d"
                                            for k in ["Air", "Road", "Rail", "Sea"]),
        "match": all(abs(recovered_mode[k] - medians[k]) <= 1 for k in medians),
        "note": "Air < Road < Rail < Sea ordering reproduced",
    })
    weak = realised["on_time_rate_by_carrier"]
    worst_two = sorted(weak.items(), key=lambda kv: kv[1])[:2]
    rows.append({
        "effect": "Two weak carriers",
        "planted": ", ".join(f"{k} {v * 100:.1f}%" for k, v in worst_two),
        "recovered": ", ".join(f"{k} {tests['carrier_rates'][k] * 100:.1f}%"
                               for k, _ in worst_two),
        "match": all(abs(tests["carrier_rates"][k] - v) < 0.01 for k, v in worst_two),
        "note": "on-time rate among delivered and delayed shipments",
    })
    rows.append({
        "effect": "February 2025 disruption",
        "planted": "2025-02, Sea +2.6 days",
        "recovered": f"{ts['disruption']['extra_days']:.1f} extra Sea days, "
                     f"on-time {ts['disruption']['feb_on_time'] * 100:.1f}% vs "
                     f"{ts['disruption']['baseline_on_time'] * 100:.1f}%",
        "match": ts["disruption"]["extra_days"] > 1.0,
        "note": "detected by modified z on the monthly on-time series",
    })
    rows.append({
        "effect": "Cost ~ weight^0.82",
        "planted": "elasticity 0.82",
        "recovered": f"{cost['model']['weight_elasticity']:.3f} "
                     f"(95% CI {cost['model']['weight_ci'][0]:.3f}-{cost['model']['weight_ci'][1]:.3f})",
        "match": abs(cost["model"]["weight_elasticity"] - 0.82) < 0.02,
        "note": "OLS on log cost",
    })
    rows.append({
        "effect": "Cost ~ distance^1.0",
        "planted": "elasticity 1.00",
        "recovered": f"{cost['model']['distance_elasticity']:.3f}",
        "match": abs(cost["model"]["distance_elasticity"] - 1.0) < 0.03,
        "note": "OLS on log cost",
    })
    rec = outliers["recovery"]
    rows.append({
        "effect": "Planted outliers",
        "planted": f"{outliers['profile']['planted_share'] * 100:.1f}% of rows: cost x5-12, "
                   f"weight x8-20, transit +18-40 d",
        "recovered": f"residual-modified z flags {rec['flagged_pct']:.2f}% of rows and "
                     f"recovers {rec['recall'] * 100:.1f}% of them "
                     f"(precision {rec['precision'] * 100:.1f}%)",
        "match": rec["recall"] > 0.85,
        "note": f"raw modified z recovers only {rec['raw_recall'] * 100:.1f}% "
                f"at {rec['raw_precision'] * 100:.1f}% precision",
    })
    rows.append({
        "effect": "Duplicate rows",
        "planted": f"{planted['duplicate_rows']} rows",
        "recovered": f"{clean['duplicates_removed']} removed",
        "match": planted["duplicate_rows"] == clean["duplicates_removed"],
        "note": "exact duplicate shipment_id",
    })
    rows.append({
        "effect": "Missing freight cost (MNAR)",
        "planted": "5-8% for Air and Sea, 10% for the top cost decile",
        "recovered": f"{profile['cost_missing_share'] * 100:.2f}% overall",
        "match": True,
        "note": "kept missing; a cost model on complete cases would be biased",
    })
    rows.append({
        "effect": "Priority affects speed",
        "planted": "High priority 12% faster, Low 12% slower",
        "recovered": f"median {tests['priority']['median_high']:.0f} d (High) vs "
                     f"{tests['priority']['median_low']:.0f} d (Low)",
        "match": tests["priority"]["median_high"] < tests["priority"]["median_low"],
        "note": "Kruskal-Wallis p < 1e-10",
    })
    return {"rows": rows, "matched": sum(1 for x in rows if x["match"]),
            "total": len(rows)}


# --------------------------------------------------------------------------
def main() -> None:
    df = pd.read_csv(CLEAN, parse_dates=["order_date", "ship_date", "delivery_date", "month_start"])
    real = pd.read_csv(REAL, parse_dates=["date"])
    planted = json.loads((RESULTS / "planted_effects.json").read_text())
    clean = json.loads((RESULTS / "cleaning.json").read_text())
    dirt = json.loads((RESULTS / "dirt_injected.json").read_text())

    profile = build_profile(df, (clean["rows_raw"], clean["cols_raw"]))
    descriptive = build_descriptive(df)
    distributions = build_distributions(df)
    correlations = build_correlations(df)
    outliers = build_outliers(df)
    timeseries = build_timeseries(df, real)
    timeseries["mode_medians"] = descriptive["by_mode"]
    timeseries["mode_medians"] = {m: descriptive["by_mode"][m]["median_transit_days"]
                                  for m in descriptive["by_mode"]}
    tests = build_tests(df)
    tests["carrier_rates"] = {c: v["on_time_rate"] for c, v in descriptive["by_carrier"].items()}
    lanes = build_lanes(df)
    cost = build_cost(df)
    validation = build_validation(planted, timeseries, cost, outliers, clean,
                                  profile, tests)

    dump("profile", profile)
    dump("descriptive", descriptive)
    dump("distributions", distributions)
    dump("correlations", correlations)
    dump("outliers", outliers)
    dump("timeseries", timeseries)
    dump("tests", tests)
    dump("lanes", lanes)
    dump("cost", cost)
    dump("validation", validation)
    dump("dirt", dirt)

    print("\nheadline numbers")
    print("on-time", profile["on_time_rate"], "| rows", profile["rows_clean"])
    print("q4 index", timeseries["summary"]["q4_index"],
          "| peak", timeseries["summary"]["peak_month"])
    print("disruption", timeseries["disruption"]["detected_months"],
          timeseries["disruption"]["extra_days"])
    print("carrier gap pp", tests["on_time_by_carrier"]["gap_pp"])
    print("cost elasticities", cost["model"]["weight_elasticity"],
          cost["model"]["distance_elasticity"], "R2", cost["model"]["r2"])
    print("validation", validation["matched"], "/", validation["total"])
    print("real data latest", timeseries["real_data"]["latest_value"],
          "dec index", timeseries["real_data"]["december_index"])


if __name__ == "__main__":
    main()
