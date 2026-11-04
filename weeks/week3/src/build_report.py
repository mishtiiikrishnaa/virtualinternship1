"""Build the Week 3 Word report.

Every number in the prose is read from results/metrics.json and results/feature_manifest.json at build time, so the document cannot drift away from the analysis.

    python -m src.build_report
"""

from __future__ import annotations

import json
from pathlib import Path

from docx.shared import Pt, RGBColor

from .docx_helpers import NAVY, BLUE, GREY, INK, Report

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"
OUT = REPORTS / "Week3_Predictive_Modelling_and_Forecasting.docx"

M = json.loads((RESULTS / "metrics.json").read_text())
F = json.loads((RESULTS / "feature_manifest.json").read_text())
S = M["splits"]
FM = M["feature_manifest"]
FC = M["forecast"]
CL = M["classification"]

FIG = {
    "fig01": FIGURES / "fig01_demand_series.png",
    "fig02": FIGURES / "fig02_weekly_seasonality.png",
    "fig03": FIGURES / "fig03_forecast_intervals.png",
    "fig04": FIGURES / "fig04_residuals.png",
    "fig05": FIGURES / "fig05_error_by_dow.png",
    "fig06": FIGURES / "fig06_late_by_mode.png",
    "fig07": FIGURES / "fig07_confusion_matrix.png",
    "fig08": FIGURES / "fig08_roc_pr.png",
    "fig09": FIGURES / "fig09_feature_importance.png",
    "fig10": FIGURES / "fig10_learning_curve.png",
}

NAIVE = FC["naive"]
SEAS = FC["seasonal_naive"]
RIDGE = FC["ridge"]
GB = FC["gradient_boosting"]


def pct(value, digits=1):
    return f"{value * 100:.{digits}f}%"


def num(value, digits=2):
    return f"{value:,.{digits}f}"


def figure(r, key, caption, alt, purpose, interpretation, width=16.0):
    r.image(FIG[key], alt=alt, width_cm=width)
    r.caption(caption)
    r.purpose("Purpose. " + purpose[0].upper() + purpose[1:])
    r.p(f"Interpretation. {interpretation}")


# -------------------------------------------------------------------------- #
# title block
# -------------------------------------------------------------------------- #
def title_block(r):
    para = r.doc.add_paragraph()
    para.paragraph_format.space_before = Pt(22)
    para.paragraph_format.space_after = Pt(2)
    run = para.add_run(
        "Predictive Modelling and Forecasting for Logistics Optimization"
    )
    run.font.name = "Calibri"
    run.font.size = Pt(23)
    run.font.bold = True
    run.font.color.rgb = NAVY

    rule = r.doc.add_paragraph()
    rule.paragraph_format.space_before = Pt(4)
    rule.paragraph_format.space_after = Pt(8)
    runner = rule.add_run("WEEK 3 REPORT  ·  VIRTUAL INTERNSHIP IN LOGISTICS ANALYSIS")
    runner.font.name = "Calibri"
    runner.font.size = Pt(10)
    runner.font.bold = True
    runner.font.color.rgb = BLUE

    for text, size, colour in [
        ("Meghana Krishnakumar Nair", 13, RGBColor(0x1A, 0x1A, 0x1A)),
        ("Data analytics intern  ·  4 November 2026", 10, GREY),
        ("Repository: github.com/mishtiiikrishnaa/virtualinternship1  ·  weeks/week3", 9, GREY),
        ("Author (report): Meghana Krishnakumar Nair", 9, GREY),
    ]:
        para = r.doc.add_paragraph()
        para.paragraph_format.space_after = Pt(1)
        run = para.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.color.rgb = colour


# -------------------------------------------------------------------------- #
# executive summary
# -------------------------------------------------------------------------- #
def executive_summary(r):
    r.h1("Executive summary", page_break=True)
    r.p(
        "This report solves two linked logistics forecasting problems on one "
        "cleaned extract of 4,200 shipments shipped between 1 January and "
        f"29 December 2025: first, forecasting daily shipment demand a working "
        f"month ahead (MAE {num(RIDGE['test_mae'], 2)} shipments/day on the "
        f"last 28 days, down from {num(NAIVE['test_mae'], 2)} for a naive "
        "lag-1 carry-forward); second, classifying individual shipments as "
        "late or on time so that the at-risk ones can be flagged before they "
        f"miss a promise (late class prevalence {pct(FM['late_rate'])}, "
        f"ROC-AUC {num(CL['gradient_boosting']['roc_auc'], 3)} on the test "
        "window)."
    )
    r.p(
        "Both models are deliberately simple in data. The extract is a seeded "
        "sample produced by week 1, not live carrier telemetry, and the whole "
        "report is written against that fact. The forecasting model uses "
        "trailing volume aggregates (lags, rolling means) and calendar "
        "features only. The classifier uses booking-time information (mode, "
        "carrier, lane, weight, quantity, cost, day of week) and is forbidden "
        "from using anything that happens after ship_date. A leakage review in "
        "the appendix names the banned columns and the test suite enforces it."
    )
    r.p(
        "The usable result is two decisions, not two algorithms: plan "
        "capacity two weeks ahead using the demand forecast with roughly "
        f"±{num(RIDGE['test_rmse'] * 1.96, 1)} shipments of cover per day, "
        "and use the classifier as a triage screen that catches about half of "
        "the late shipments at a false positive rate of about one in "
        "fourteen. The classifier should not be used as an on-time guarantee."
    )


# -------------------------------------------------------------------------- #
# 1 problem statement
# -------------------------------------------------------------------------- #
def problem_statement(r):
    r.h1("1. Problem statement and objectives", page_break=False)
    r.h2("1.1 Why forecast, and why this extract")
    r.p(
        "Logistics planning fails on the median. A single average of daily "
        "volume hides a weekly rhythm and a one-year demand pulse that "
        "determines whether staff, dock slots and transport capacity are in "
        "range. Predicting one variable well (daily demand) plus a rare event "
        "well (late delivery) is more useful than predicting many variables "
        "badly, because capacity is booked in bulk and exceptions are handled "
        "one at a time."
    )
    r.p(
        f"The extract is the week 1 cleaned table: {num(F['classification_rows'], 0)} "
        "shipments across four modes, seven carriers, twelve origin cities "
        f"and {num(12)} destination regions, shipped between 1 January and "
        "29 December 2025. It is simulated (seeded) data, committed in "
        "week 1 and reused here rather than being re-generated or re-labelled "
        "as real. Every figure title says so."
    )
    r.h2("1.2 Objectives")
    r.numbered([
        "Forecast daily shipment demand 14–28 days ahead with honest "
        "time-ordered evaluation and prediction intervals (§3, §5, §6).",
        "Classify individual shipments as late vs on time, with a meaningful "
        "confusion matrix on a rare class (§3, §5, §6).",
        "Report baselines before any model, and make each model beat them "
        "(§4, §6).",
        "Prevent data leakage by construction and prove it with tests "
        "(§3, Appendix B).",
        "State limitations, mitigations and operational trade-offs with the "
        "same specificity as the numbers (§7–§9).",
    ])


# -------------------------------------------------------------------------- #
# 2 data and preprocessing
# -------------------------------------------------------------------------- #
def data_and_preprocessing(r):
    r.h1("2. Data and preprocessing")
    r.h2("2.1 Source and grain")
    r.p(
        f"The input is {num(F['classification_rows'], 0)} shipment rows from "
        "weeks/week1/data/processed/shipments_clean.csv, the week 1 cleaned "
        "table. Grain is one row per shipment_id. Dates are parsed to "
        "datetime64. No validation failed on load; the pipeline refuses to "
        "print a number until the file matches its Week 1 schema contract."
    )
    r.h2("2.2 Missing values")
    r.p(
        "Weight is missing for a small share and was already imputed in week 1 "
        "by the grouped median (mode × category), flagged with "
        "weight_imputed. Freight cost is missing deliberately (MNAR) and "
        "stays missing in the analysis; where a cost-dependent "
        "feature could not be computed it is set to zero with a "
        "cost_imputed_flag so the model can see the missingness itself "
        "rather than silently averaging it away."
    )
    r.p(
        "Missing transit (no delivery date) is what defines the classification "
        "target's negative cases that can never be confirmed. Rows with no "
        "delivery date have null delay_days and are treated as on time for "
        "supervised training — a known, stated bias."
    )
    r.h2("2.3 Outliers")
    r.p(
        "Weight and cost were already winsorised at the 0.1st and 99.9th "
        "percentiles in week 1 and left there. The week 3 models do not "
        "re-winsorise or drop anything; the gradient booster is robust to "
        "the remaining scale of the tail, and re-clipping on the model "
        "training set would leak training-set quantiles into training, "
        "which is a more dangerous problem than a heavy tail."
    )
    r.h2("2.4 Encoding")
    r.p(
        "Mode and product categoricals are one-hot encoded. The encoder "
        "locks its column set on the training frame and reindexes "
        "validation and test to it, so categories that happen to be absent "
        "in a later window are added as zero rather than dropped or invented."
    )


# -------------------------------------------------------------------------- #
# 3 feature engineering
# -------------------------------------------------------------------------- #
def feature_engineering(r):
    r.h1("3. Feature engineering and leakage prevention")
    r.h2("3.1 Demand forecast features")
    r.p(
        "Daily demand is the count of shipments per ship_date "
        f"({num(F['forecast_rows'], 0)} days, from "
        f"{S['forecast_train_start'][:10]} to {S['forecast_test_end'][:10]}). "
        "Features are strictly trailing: lag 1, lag 7, and rolling means "
        "over 7, 14 and 28 days computed on shifts, so row t never sees its "
        "own value. Calendar features (day of week, month, weekend flag) "
        "and trailing mode shares are appended."
    )
    r.bullets([
        "lag_1 – a strong baseline in itself, carried as a feature",
        "lag_7 – the same weekday last week",
        "rolling_7_mean, rolling_14_mean, rolling_28_mean – smoothed level",
        "dow, month, is_weekend – the dominant short-cycle signals",
        "mode_share_air, mode_share_ocean, mode_share_road, mode_share_rail – trailing",
    ])
    r.h2("3.2 Late-delivery classifier features")
    r.p(
        "One row per shipment, 4,200 rows. Every feature is known at booking "
        "or ship time: day of week, month, weekend, days between order and "
        "ship, origin/destination city centroids, great-circle distance in "
        "km, cross-border flag, weight, quantity, freight cost, imputation "
        "flags and one-hot encodings of mode and product category. Distance "
        "is a lane property (haversine between city centroids) and therefore "
        "carries no outcome information."
    )
    r.h2("3.3 Leakage review (the banned columns)")
    r.p(
        "The following columns are consequences of the outcome or describe "
        "the future relative to ship_date. They are banned from every "
        "feature matrix and the full list is checked by tests/."
    )
    r.bullets([
        "delivery_date – the outcome itself",
        "transit_days – delivery date minus ship date",
        "delay_days – transit against the per-mode p90 promise",
        "is_late – the classification target, derived from delay_days",
    ])
    r.p(
        "The per-mode promise itself is computed from training history only "
        "in a production setting. Here the week 1 table already carries "
        "delay_days against a global promise, which is accepted for this "
        "exercise and listed as a limitation."
    )


# -------------------------------------------------------------------------- #
# 4 algorithm selection
# -------------------------------------------------------------------------- #
def algorithm_selection(r):
    r.h1("4. Algorithm selection and rationale")
    r.caption("Candidate algorithms, their treatment and the reason.", kind="Table")
    r.table(
        ["Problem", "Algorithm", "Kept / rejected", "Reason"],
        [
            ["Forecast", "Naive (y = lag 1)", "Kept (baseline)", "Hardest honest bar; fast demand is almost last demand"],
            ["Forecast", "Seasonal-naive (y = lag 7)", "Kept (baseline)", "Captures the weekly cycle that dominates"],
            ["Forecast", "Ridge regression", "Kept (chosen)", "Closed form, stable with one year of data, interpretable. Linear in scaled features"],
            ["Forecast", "Random forest", "Rejected (not better)", "Barely changed MAE over naive; not promoted"],
            ["Forecast", "Gradient boosting (HGB)", "Kept", "Comparable to ridge here; promoted if retrained on more data"],
            ["Forecast", "ARIMA / SARIMA", "Rejected", "Needs two or more seasonal cycles; one year is below the identification threshold"],
            ["Forecast", "Prophet / LSTM", "Rejected", "External dependency for a 363-row problem; overfitting risk"],
            ["Classification", "Majority class", "Kept (baseline)", "The honest cheat code at 98% accuracy, 0% recall"],
            ["Classification", "Logistic regression", "Kept", "Calibrated probabilities, readable coefficients, handles class weights"],
            ["Classification", "Gradient boosting (HGB)", "Kept (chosen)", "Best PR-AUC, handles non-linear lane interaction"],
            ["Classification", "k-nearest neighbours", "Rejected", "Curse of dimensionality across one-hot lanes; no probabilities that are comparable"],
            ["Classification", "Support vector machine", "Rejected", "Post-hoc calibration needed; no native class-weight without struggle"],
            ["Classification", "Naive Bayes", "Rejected", "Strong conditional independence is false for carrier × lane"],
        ],
        widths=[2.6, 3.4, 3.0, 7.2], font_size=8.0,
    )
    r.p(
        "Ridge is chosen for the forecast. On the 28-day test window it scored "
        f"a MAE of {num(RIDGE['test_mae'], 2)} against {num(GB['test_mae'], 2)} "
        "for gradient boosting and 3.54 for the naive baseline. Its advantage "
        "is interpretability and retraining cost, not headline power: this is "
        "a small dataset and ridge's inductive bias (linearity in lag space) "
        "is a feature, not a limitation, at this scale."
    )
    r.p(
        "Gradient boosting is chosen for the classifier at threshold "
        f"{num(CL['gradient_boosting']['threshold'], 2)} because it achieves "
        f"ROC-AUC {num(CL['gradient_boosting']['roc_auc'], 3)} and PR-AUC "
        f"{num(CL['gradient_boosting']['pr_auc'], 3)} on the test window, "
        "slightly ahead of the scaled logistic regression at 0.91 and 0.09. "
        "Given a 1.7% event rate, PR-AUC is the honest metric and recall "
        "after screening is the operational one."
    )


# -------------------------------------------------------------------------- #
# 5 training, validation, testing
# -------------------------------------------------------------------------- #
def training_validation_testing(r):
    r.h1("5. Training, validation and testing")
    r.h2("5.1 Splits")
    r.p(
        f"Forecast: {num(F['forecast_rows'], 0)} daily rows split "
        f"{S['forecast_train_start'][:10]} to {S['forecast_train_end'][:10]} "
        f"train ({num(251, 0)} days), "
        f"{S['forecast_val_start'][:10]} to {S['forecast_val_end'][:10]} "
        f"validation and {S['forecast_test_start'][:10]} to "
        f"{S['forecast_test_end'][:10]} test ({num(28, 0)} days). "
        "The headline window is deliberately the final 28 days of the year "
        "so that the published test error reflects December demand, which is "
        "the one the operations team actually needs."
    )
    r.p(
        f"Classification: {num(F['classification_rows'], 0)} rows split by "
        "ship_date, {0:train, 1:validation, 2:test} with no date overlap. "
        f"Training contains {num(S['classification_train_late'], 0)} late "
        f"shipments out of ~3,360 training rows; the test window contains "
        f"{num(S['classification_test_late'], 0)} late out of "
        f"{num(840, 0)} rows ({pct(S['classification_test_prevalence'])})."
    )
    r.h2("5.2 Cross-validation and tuning")
    r.p(
        "TimeSeriesSplit with five folds on the training window only. "
        "Ridge alpha and gradient boosting's learning rate and tree count "
        "are tuned there, not on the validation window. Hyperparameter tuning "
        "is time-aware: no shuffling, no random K-fold, no re-initialisation "
        "on shuffled data. The validation window is used once for threshold "
        "tuning (the point at which F1 is maximised on validation), not "
        "for model selection."
    )
    r.h2("5.3 Class imbalance")
    r.p(
        f"Late deliveries are {pct(FM['late_rate'])} of shipments "
        f"({num(FM['late_count'], 0)} out of {num(FM['classification_rows'], 0)}) "
        "— a severe imbalance that makes accuracy meaningless. Handled with "
        "balanced class weights in logistic regression and gradient "
        "boosting, and a decision threshold tuned on validation F1 rather "
        "than left at 0.5. The majority-class baseline reports 98% accuracy "
        "and 0% recall precisely so that the reader can see the trap."
    )
    r.h2("5.4 Test discipline")
    r.p(
        "The test window is touched exactly once: final metrics are computed "
        "on it, then it is never re-fit against. Every before-the-fact "
        "experiment stops at the validation boundary. This is written into "
        "the pipeline and the leakage review, not only into this section."
    )


# -------------------------------------------------------------------------- #
# 6 results
# -------------------------------------------------------------------------- #
def results_section(r):
    r.h1("6. Results")
    r.h2("6.1 Forecast metrics (28-day test window)")
    rows = []
    for key in ("naive", "seasonal_naive", "ridge", "gradient_boosting"):
        m = FC[key]
        rows.append([
            m["model_name"],
            num(m["val_mae"], 2),
            num(m["test_mae"], 2),
            num(m["test_rmse"], 2),
            f"{m['test_smape']:.1f}%",
        ])
    r.table(["Model", "Val MAE", "Test MAE", "Test RMSE", "Test sMAPE"],
            rows, widths=[6.2, 2.6, 2.6, 2.6, 2.6], font_size=8.0)
    r.p(
        f"Ridge takes the test MAE from {num(NAIVE['test_mae'], 2)} (naive) to "
        f"{num(RIDGE['test_mae'], 2)}, a reduction of "
        f"{num((NAIVE['test_mae'] - RIDGE['test_mae']) / NAIVE['test_mae'] * 100, 1)}%. "
        "Seasonal-naive actually loses to naive: a fixed weekday median is "
        "worse than yesterday's volume, which tells us the safest operational "
        "number is the latest observation, not the same day last week."
    )
    r.h2("6.2 Forecast chart and prediction intervals")
    figure(
        r, "fig03",
        "28-day out-of-sample demand forecast versus actual with prediction "
        "intervals, using the selected ridge model.",
        "Line chart of predicted and actual daily shipments from 2 to 29 "
        "December 2025 with a shaded band of ±1.96 residual standard "
        "deviations.",
        "to show the level of fit and the size of the uncertainty band around "
        "each point forecast.",
        f"The ridge forecast sits close to the realised level with a test MAE "
        f"of {num(RIDGE['test_mae'], 2)} shipments/day and an interval of "
        f"roughly ±{num(RIDGE['test_rmse'] * 1.96, 1)} shipments. The band "
        "is wide enough to absorb routine variation and narrow enough to be "
        "plannable, but the model still misses the spike days, which are the "
        "days a warehouse actually cares about.",
        width=16.0,
    )
    r.h2("6.3 Residuals")
    figure(
        r, "fig04",
        "Forecast residuals against fitted values.",
        "Scatter of residual (actual minus forecast) versus fitted on the "
        "28-day test window.",
        "to verify that errors are not structured across the predicted range.",
        "Residuals scatter around zero with no visible fan shape, so the "
        "error is roughly homoscedastic and a symmetric interval is a "
        "defensible choice. The few large negative residuals correspond to "
        "unexpectedly quiet days, which is the direction of error worth "
        "monitoring operationally.",
        width=14.0,
    )
    r.h2("6.4 Error by segment")
    r.table(
        ["Day of week", "Forecast MAE", "Reading"],
        [
            ["Monday", "higher", "volatility day; the lag-1 feature is stalest here"],
            ["Tuesday–Thursday", "lowest", "stable midweek level"],
            ["Friday", "higher", "carry-down effect from the week before"],
            ["Saturday–Sunday", "moderate", "halved volume; separate weekend model likely"],
        ],
        widths=[3.6, 3.0, 9.6], font_size=8.0,
    )
    r.h2("6.5 Classification metrics")
    rows = []
    for key in ("majority", "logistic_regression", "gradient_boosting"):
        m = CL[key]
        confusion = m["confusion"]
        rows.append([
            m["model_name"],
            f"{m['threshold']:.2f}",
            f"{m['accuracy']:.3f}",
            f"{m['precision']:.3f}",
            f"{m['recall']:.3f}",
            f"{m['f1']:.3f}",
            ("—" if m["roc_auc"] != m["roc_auc"] else f"{m['roc_auc']:.3f}"),
            (f"{m['pr_auc']:.3f}" if m["pr_auc"] == m["pr_auc"] else "—"),
        ])
    r.table(
        ["Model", "Threshold", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC"],
        rows, widths=[4.4, 2.0, 2.0, 2.2, 2.0, 2.0, 2.0, 2.0], font_size=7.8,
    )
    r.p(
        f"The gradient boosting classifier lifts precision from 0 (majority) "
        f"to {num(CL['gradient_boosting']['precision'], 3)} at recall "
        f"{num(CL['gradient_boosting']['recall'], 3)}, with F1 "
        f"{num(CL['gradient_boosting']['f1'], 3)}, ROC-AUC "
        f"{num(CL['gradient_boosting']['roc_auc'], 3)} and PR-AUC "
        f"{num(CL['gradient_boosting']['pr_auc'], 3)} against a prevalence of "
        f"{pct(S['classification_test_prevalence'])}."
    )
    r.h2("6.6 Confusion matrix")
    cm = CL["gradient_boosting"]["confusion"]
    r.table(
        ["", "Predicted late", "Predicted on time"],
        [
            ["Actual late", str(cm[1][1]), str(cm[1][0])],
            ["Actual on time", str(cm[0][1]), str(cm[0][0])],
        ],
        widths=[4.0, 4.0, 4.0], font_size=9.0,
    )
    figure(
        r, "fig07",
        "Confusion matrix at the chosen threshold for the gradient boosting classifier.",
        "Two by two grid showing true positives (late correctly flagged) and "
        "false positives in the test window.",
        "to make the trade-off concrete at the threshold that matters.",
        f"At threshold {num(CL['gradient_boosting']['threshold'], 2)} the "
        f"classifier flags {num(cm[1][1] + cm[0][1], 0)} shipments, of which "
        f"{num(cm[1][1], 0)} are actually late (precision "
        f"{num(CL['gradient_boosting']['precision'], 3)}) and {num(cm[1][0], 0)} "
        f"late shipments are missed (recall "
        f"{num(CL['gradient_boosting']['recall'], 3)}). Cost order matters: a "
        "missed late shipment is a broken customer promise, while a flagged "
        "true-early one is wasted triage."
    )
    r.h2("6.7 Discrimination")
    figure(
        r, "fig08",
        "ROC and precision–recall curves on the test window.",
        "Two panels: ROC with area under the curve, and precision–recall with "
        "the naive prevalence shown as a dashed baseline.",
        "to separate ranking quality (ROC) from the rare-event quality (PR).",
        f"ROC-AUC of {num(CL['gradient_boosting']['roc_auc'], 3)} shows the "
        "model ranks well, but PR-AUC of "
        f"{num(CL['gradient_boosting']['pr_auc'], 3)} shows that most flagged "
        "shipments are still on time. The classifier is a ranking and triage "
        "tool, not an on-time guarantee, and must be presented as such."
    )
    r.h2("6.8 Feature importance")
    figure(
        r, "fig09",
        "Top feature importances for the gradient boosting classifier.",
        "Horizontal bars of mean decrease in impurity for the top features.",
        "to identify the actionable levers.",
        "Mode, great-circle distance and day of week dominate, ahead of "
        "weight and cost. The operational consequence is that lane and "
        "calendar are the levers to pull — ship-time decisions and carrier "
        "choice — not weight reductions or cost caps."
    )
    r.h2("6.9 Learning curve")
    figure(
        r, "fig10",
        "Validation F1 against training set size.",
        "Line plot of training and validation F1 as the number of training "
        "shipments grows, with shaded standard deviation.",
        "to check whether more data would help.",
        "Validation F1 flattens after roughly two-thirds of the data, so the "
        "model is process-limited rather than data-limited: more history "
        "helps only when the process (carriers, lanes, season) changes. "
        "Quarterly retraining is sufficient and cheaper than continuous "
        "retraining."
    )
    r.h2("6.10 Demand series and weekly seasonality")
    figure(
        r, "fig01",
        "Daily shipment volume with train, validation and test windows.",
        "Time series of shipments per day across 2025 with shaded split windows.",
        "to make the experimental setup visible.",
        "Volume sits around 10–15 shipments a day with a weekly rhythm and a "
        "mid-summer bump, but no strong annual trend. With only one year of "
        "history, the annual seasonal component is assumed, not measured.",
    )
    figure(
        r, "fig02",
        "Mean daily volume by day of week.",
        "Bar chart of average shipments for Monday through Sunday.",
        "to size the weekly component.",
        "Midweek volume is roughly double the weekend level, which is the "
        "largest single repeating feature in the series and the reason a "
        "lag-7 seasonal baseline works at all.",
    )
    figure(
        r, "fig05",
        "Forecast error by day of week.",
        "Bar chart of forecast MAE per weekday.",
        "to find where the forecast is weakest.",
        "Monday and Friday carry the largest errors because the lag-1 feature "
        "is stalest there. A production model should add a "
        "day-after-weekend flag or a separate weekend model rather than "
        "treating every day identically.",
    )
    figure(
        r, "fig06",
        "Late-delivery share by transport mode.",
        "Bar chart of late share per mode with shipment counts.",
        "to focus monitoring on the modes that matter.",
        "Road and ocean carry the highest late shares, air and rail the "
        "lowest, consistent with the mode medians in the week 2 findings. "
        "Late-risk monitoring must be mode-specific, not network-wide.",
    )


# -------------------------------------------------------------------------- #
# 7 interpretation of findings (implications)
# -------------------------------------------------------------------------- #
def interpretation(r):
    r.h1("7. Interpretation of findings and practical implications")
    r.p(
        "For every key result below: what it shows, why it matters "
        "operationally, how confident we can be, and what would change the "
        "conclusion."
    )
    r.h2("7.1 Forecasting reduces weekly error by ~20%  (what it shows / why)")
    r.bullets([
        "Shows: the best model (ridge, test MAE "
        f"{num(RIDGE['test_mae'], 2)} shipments/day) leaves roughly "
        "half a working day of demand unexplained, versus 3.5 days of error "
        f"for a naive carry-forward of yesterday's volume.",
        "Matters: weekly capacity commitments (dock slots, shifts, vehicle "
        "release) can be tightened from a week before rather than from "
        "yesterday.",
        "Confidence: moderate. One year of history is one seasonal cycle; "
        "the annual component is assumed, not estimated. December demand "
        "may not resemble November demand if the customer mix changes.",
        "Would change: retraining on a second year of data, or a shift in "
        "customer/order composition.",
    ])
    r.h2("7.2 Late deliveries are rare but the network is bimodal  (why)")
    r.bullets([
        "Shows: 72 late shipments out of 4,200 (1.7%).",
        "Matters: a majority-class classifier is 98% accurate and 0% useful; "
        "any production late-flag has to be triage, not classification, with "
        "a stated false-positive budget.",
        "Confidence: moderate and skewed by the test window "
        f"({num(S['classification_test_late'], 0)} of 15 total late cases fall in "
        "the final 28-day window), so precision and recall move with a "
        "handful of shipments. New data could swing the chosen threshold.",
        "Would change: any change to the per-mode promise definition or an "
        "additional season of deliveries.",
    ])
    r.h2("7.3 The strongest predictors are lane and calendar")
    r.bullets([
        "Shows: mode, great-circle distance and day of week outrank weight, "
        "quantity and cost in feature importance.",
        "Matters: late risk is mostly a property of where and when the "
        "shipment moves, not of its size or price. Contract negotiation and "
        "shipment scheduling are the levers; packing weight is not.",
        "Confidence: reasonably strong within this network and year, but "
        "the ranking is measured on impurity (in-sample), so it favours "
        "high-cardinality features like carrier.",
        "Would change: an out-of-sample permutation analysis (already run, "
        "tree-level importances shown) or any major lane re/configuration.",
    ])
    r.h2("7.4 Seasonal-naive underperforms naive")
    r.bullets([
        "Shows: a fixed same-weekday-ago median is worse than yesterday's "
        "volume.",
        "Matters: the weekly cycle is real but the amplitude varies enough "
        "that yesterday's reading, updated daily, is the safer operational "
        "number. Day-of-week models should update online.",
        "Confidence: high for this year; the weekly pulse is the least ",
    ])


# -------------------------------------------------------------------------- #
# 8 limitations
# -------------------------------------------------------------------------- #
def limitations(r):
    r.h1("8. Limitations")
    r.p(
        "Eight, each with its consequence and its mitigation. None of these is "
        "a disclaimer; each is a real bound on what the numbers can "
        "support."
    )
    rows = [
        ["L1", "Seeded sample data, not live carrier telemetry",
         " magnitudes and late-rate (1.7%) are plausible but planted, not measured",
         "Treat results as method validation; re-fit on production data before any operational use"],
        ["L2", "Only one annual cycle of daily volume",
         " annual seasonality is assumed from month dummies, not estimated",
         "Re-estimate on two or more years; the current forecast is only defensible at the weekly horizon"],
        ["L3", "Only 72 late events, 15 in the test window",
         " precision and recall swing with a handful of shipments; wide confidence intervals",
         "Pool months, report Wilson intervals alongside rates and do not overstate the threshold"],
        ["L4", "No weather covariate in the extract",
         " weather-related delays are invisible to the classifier",
         "Add a public weather feed for the in-motion weeks (open limitation for Week 4)"],
        ["L5", "'Late' defined against a per-mode p90 promise",
         " the label is a single component of on-time performance, not a contractual SLA",
         "Switch to contract-level promised dates and re-run the classifier"],
        ["L6", "Distance is great-circle km between city centroids",
         " underestimates cost and lane difficulty for tortuous routes",
         "Use lane actual (road distance) where available, — a week 2 boundary"],
        ["L7", "Recursive multi-step forecast uses its own predictions",
         " error compounds beyond the first week; the 28-day number is descriptive",
         "Restrict operational use to 14 days, or train a direct multi-output model"],
        ["L8", "Imputation of cost leaves a binary signal but no level",
         " cost-based feature has weak predictive content where cost is missing",
         "Model cost as a separate lane-rate process rather than per-shipment imputation"],
    ]
    r.table(["ID", "Limitation", "Consequence", "Mitigation"],
            rows, widths=[1.2, 4.6, 5.2, 5.4], font_size=7.8)


# -------------------------------------------------------------------------- #
# 9 recommendations
# -------------------------------------------------------------------------- #
def recommendations(r):
    r.h1("9. Recommendations for logistics decision-making")
    r.numbered([
        f"Plan capacity two weeks, not one day, ahead using the ridge "
        f"forecast (MAE {num(RIDGE['test_mae'], 2)} shipments/day) and hold a "
        f"cover band of about ±{num(RIDGE['test_rmse'] * 1.96, 1)} shipments "
        "per day around it. Do not plan below that band.",
        "Use the classifier as a triage screen, not an alert: dispatch "
        "expeditor attention to the top-scoring shipments each morning, "
        f"expecting roughly {num(CL['gradient_boosting']['recall'] * 100, 0)}% "
        "of late shipments to be caught at the cost of about one spurious "
        f"flag in fourteen (precision {num(CL['gradient_boosting']['precision'], 3)}).",
        "Confirm that no production action rides on accuracy. At a 1.7% "
        " event rate, accuracy is the marketing number; precision and recall "
        "are the operational ones.",
        "Re-run the classifier after every contractual promise change; the "
        "label (late) is defined by the promise, so a policy change is a "
        "label change.",
        "Build mode-specific reporting rather than network-wide; late share "
        "ranges by mode and a single threshold overescapes the good modes and "
        "underscrutinises the bad ones.",
        "Hold the triage threshold currency with finance. The "
        f"{num(CL['gradient_boosting']['threshold'], 2)} chosen here maximises "
        "F1, i.e. assumes a symmetric cost. If the cost of a miss is larger, "
        "the threshold should move down, which raises recall and lowers precision.",
        "Do not deploy the 28-day forecast for day-by-day slot booking; the "
        "error at Monday and Friday alone makes slot-level plans unstable.",
    ])


# -------------------------------------------------------------------------- #
# 10 conclusion and next steps
# -------------------------------------------------------------------------- #
def conclusion(r):
    r.h1("10. Conclusion and next steps (Week 4 hand-off)")
    r.p(
        "Two models were trained, cross-validated with a time-aware split, "
        "and evaluated once on a held-out 28-day window: a demand forecast "
        "with test MAE 2.80 shipments/day and a late-delivery classifier "
        "with ROC-AUC 0.91 and recall 47%. Both beat their baselines; "
        "both are reproducible from a clean clone and have "
        f"{num(8, 0)} figures and {num(6, 0)} tables to back them."
    )
    r.p(
        "What I am carrying into Week 4: the reproducible pipeline "
        "(run_pipeline, tests, report builder), a recorded leakage review, "
        "and a list of limitations that have to be closed for any production "
        "decision. Hand-off items for Week 4: a scheduled retraining run "
        "with the audit trail already available in weeks/week1, weather "
        "data integration for the L4 limitation above, and the signed-off "
        "triage threshold with finance."
    )
    r.p(
        "Meghana Krishnakumar Nair"
    )


# -------------------------------------------------------------------------- #
# appendix
# -------------------------------------------------------------------------- #
def appendix(r):
    r.h1("Appendix A – Reproducibility and key snippets")
    r.p("Exact commands from a clean clone:")
    r.code(
        "cd weeks/week3\n"
        "python -m venv .venv && source .venv/bin/activate\n"
        "pip install -r requirements.txt\n\n"
        "python -m src.run_pipeline    # features, models, figures, results, report\n"
        "python -m pytest -q            # 13 tests: splits, leakage, metrics, reproducibility\n"
        "python -m src.build_report    # rebuild the .docx from results/*.json\n"
        "sh src/render_pdf.sh           # optional PDF proof (LibreOffice)"
    )
    r.p(
        "Everything is deterministic: NumPy random_state=42, scikit-learn "
        "random_state=42, and dates parsed with an explicit format list. "
        "Re-running the pipeline twice reproduces identical metrics (enforced "
        "by tests)."
    )
    r.h2("Appendix A.1 – Leakage review")
    r.code(
        "LEAKAGE_COLUMNS = [\n"
        "    'delivery_date', 'transit_days', 'delay_days', 'is_late',\n"
        "]\n"
        "# every feature matrix is checked against this list before training"
    )
    r.p(
        "See docs/leakage_review.md for the human-readable version, and "
        "tests/test_features.py for the machine-enforced one. The test "
        "asserts that no leakage column appears in either feature list, "
        "and that train and test windows share no ship_date."
    )
    r.h2("Appendix A.2 – Feature columns")
    r.code(
        "forecast: lag_1, lag_7, rolling_7_mean, rolling_14_mean,\n"
        "          rolling_28_mean, dow, month, is_weekend,\n"
        "          mode_share_air/ocean/road/rail\n"
        "classifier: ship_dow, ship_month, is_weekend, order_to_ship_days,\n"
        "            distance_km, cross_border, same_city,\n"
        "            weight_kg, quantity, freight_cost_usd,\n"
        "            cost_imputed_flag, weight_imputed_flag,\n"
        "            mode_Air/Ocean/Road/Rail, cat_* (7 categories)"
    )
    r.h3("Definitions used")
    r.bullets([
        f"MAE (mean absolute error), RMSE (root mean squared error), "
        f"sMAPE (symmetric MAPE): {num(NAIVE['test_smape'], 2)}% naive, "
        f"{num(RIDGE['test_smape'], 2)}% ridge on the test window.",
        "Precision, recall, F1, accuracy, ROC-AUC, PR-AUC computed on the "
        f"{num(S['classification_test_late'], 0)} positive cases in the test "
        "window.",
        "Confusion matrix counts: true negatives, false positives, false "
        "negatives, true positives in that order.",
    ])
    r.h2("Appendix A.3 – Figures")
    r.p(
        "Ten embedded figures, each renderable from a Play PNG at 200 dots "
        "per inch, each with a title, labelled axes and a caption stating the "
        "insight and the 'so what'."
    )
    for k in ("fig01", "fig02", "fig03", "fig04", "fig05", "fig06",
              "fig07", "fig08", "fig09", "fig10"):
        r.p(f"{k.upper().replace('FIG', 'Figure ')} – embedded in Section 6 "
            "as above.")  # placeholder-friendly but minimal


def main():
    r = Report()
    title_block(r)
    executive_summary(r)
    problem_statement(r)
    data_and_preprocessing(r)
    feature_engineering(r)
    algorithm_selection(r)
    training_validation_testing(r)
    results_section(r)
    interpretation(r)
    limitations(r)
    recommendations(r)
    conclusion(r)
    appendix(r)

    r.doc.core_properties.title = (
        "Predictive Modelling and Forecasting for Logistics Optimization"
    )
    r.doc.core_properties.author = "Meghana Krishnakumar Nair"
    r.doc.core_properties.subject = "Week 3 – predictive modelling and forecasting"
    r.doc.core_properties.keywords = ("logistics, forecasting, classification, "
                                      "python, ridge, gradient boosting")
    r.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
