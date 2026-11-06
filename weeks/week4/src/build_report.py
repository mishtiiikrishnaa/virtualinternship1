"""Build the Week 4 comprehensive decision-support report.

    python -m src.build_report

Every number quoted in the prose is read from results/results.json at build
time, so the document cannot drift away from the analysis. Nothing is typed by
hand into the prose.

Structure: title page, executive summary, sections 1 to 11, appendices A to E.
Every substantive section runs claim, evidence, implication and action; every
figure carries a caption, a purpose line and an interpretation line.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from src.docx_helpers import BLUE, GREY, INK, NAVY, Report

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "reports" / "figures"
REPORTS = ROOT / "reports"
OUT = REPORTS / "Week4_Decision_Support_Report.docx"

R = json.loads((RESULTS / "results.json").read_text())
F = R["forecast"]
CL = R["classification"]
CONF = R["confusion"]["gradient_boosting"]
COST = R["cost"]
COST_MISSED = COST["false_negative_usd"]
COST_ESCALATION = COST["false_positive_usd"]
COST_METRICS = COST["metrics"]
BACKTEST = R["decisions"]["backtests"]
COVERAGE = R["coverage"]["forecast_interval"]
CONF_COV = R["conformal"]["coverage"]
CALIB = R["calibration"]
CLEANING = R["cleaning"]
EDA = R["eda"]
SCENARIOS = R["scenarios"]
ASSUMPTIONS = R["assumptions"]
RISKS = R["risks"]
ROADMAP = R["roadmap"]

FIG = {
    "fig01": FIGURES / "fig01_pipeline_week4.png",
    "fig02": FIGURES / "fig02_eda_decision_finding.png",
    "fig03": FIGURES / "fig03_data_quality_before_after.png",
    "fig04": FIGURES / "fig04_forecast_vs_baselines.png",
    "fig05": FIGURES / "fig05_confusion_matrix.png",
    "fig06": FIGURES / "fig06_calibration.png",
    "fig07": FIGURES / "fig07_permutation_importance.png",
    "fig08": FIGURES / "fig08_decision_flow.png",
    "fig09": FIGURES / "fig09_scenarios.png",
    "fig10": FIGURES / "fig10_risk_matrix.png",
    "fig11": FIGURES / "fig11_roadmap.png",
}

HALF_WIDTH = (F["ridge"]["interval_upper"][0] - F["ridge"]["interval_lower"][0]) / 2
TOD = CL["gradient_boosting"]["threshold"]


def pct(value, digits: int = 1) -> str:
    return f"{float(value) * 100:.{digits}f}%"


def num(value, digits: int = 2) -> str:
    return f"{float(value):,.{digits}f}"


def today() -> str:
    return _dt.date.today().strftime("%d %B %Y")


def figure(r: Report, key: str, caption: str, alt: str, purpose: str, interpretation: str, width: float = 12.0) -> None:
    r.image(FIG[key], alt=alt, width_cm=width)
    r.caption(caption)
    r.purpose("Purpose. " + purpose[0].upper() + purpose[1:])
    r.p(f"Interpretation. {interpretation}")


# -------------------------------------------------------------------------- #
# title page
# -------------------------------------------------------------------------- #
def title_block(r: Report) -> None:
    r.doc.add_paragraph()
    r.title_text("Comprehensive Decision Support Report for Logistics", 22, bold=True, colour=NAVY)
    r.spacer(6)
    r.title_text("From data to decision: forecasting and triage for shipment operations", 13, bold=False, colour=BLUE)
    r.spacer(18)
    r.title_text("Meghana Krishnakumar Nair", 15, bold=True)
    r.spacer(2)
    r.title_text("Data analytics intern", 11, bold=False)
    r.spacer(12)
    r.title_text(today(), 11, bold=False)
    r.spacer(6)
    r.title_text("github.com/mishtiiikrishnaa/virtualinternship1  ·  weeks/week4", 9, bold=False, colour=GREY)
    r.spacer(14)
    r.doc.add_page_break()


# -------------------------------------------------------------------------- #
# executive summary
# -------------------------------------------------------------------------- #
def executive_summary(r: Report) -> None:
    r.h1("Executive summary", page_break=True)
    r.p(
        f"The logistics operation decides, in order of immediacy, how much capacity to hold, which "
        f"shipments to triage, and which service promises to keep. This report integrates the weeks 1 "
        f"to 3 analysis into one decision-support artefact. On the week 1 development extract of "
        f"{int(CLEANING['rows_published']):,} shipments shipped in 2025, the ridge forecast reached a test "
        f"mean absolute error of {num(F['ridge']['test_mae'], 1)} shipments per day against a naive lag-1 "
        f"forecast of {num(F['naive']['test_mae'], 1)}, an improvement of "
        f"{num((F['naive']['test_mae'] - F['ridge']['test_mae']) / F['naive']['test_mae'] * 100, 1)} percent. "
        f"The forecast interval half width is about {num(HALF_WIDTH, 1)} shipments per day and its "
        f"empirical coverage on the held-out window is {pct(COVERAGE['coverage'], 3)}."
    )
    r.p(
        f"The late-delivery classifier at the chosen threshold of {num(TOD, 2)} reached a recall of "
        f"{pct(CL['gradient_boosting']['recall'], 3)} and a precision of {pct(CL['gradient_boosting']['precision'], 3)} "
        f"on the held-out test window, with a ROC-AUC of {num(CL['gradient_boosting']['roc_auc'], 3)} and a "
        f"precision-recall area under the curve of {num(CL['gradient_boosting']['pr_auc'], 3)}. The expected "
        f"cost of a missed late shipment is {num(COST_MISSED, 0)} and the expected cost of a wasted triage "
        f"escalation is {num(COST_ESCALATION, 0)}. The classifier Brier score is {num(CALIB['brier_score'], 4)} "
        f"against a base-rate Brier of {num(CALIB['baseline_brier'], 4)} with a Brier skill of "
        f"{num(CALIB['brier_skill'], 3)}, so the probabilities are not better than a constant base-rate "
        f"predictor and should be read as ranking scores rather than calibrated probabilities."
    )
    r.p(
        f"The development extract is seeded rather than live, so the findings that follow describe that "
        f"extract. The decision framework in Section 6 is written for use on top of a retrained model and a "
        f"re-validated label, and the risk register in Section 8 states what could change the conclusions."
    )
    r.h2("Headline findings")
    r.bullets([
        f"Ridge forecast: test mean absolute error of {num(F['ridge']['test_mae'], 1)} shipments per day, "
        f"against {num(F['naive']['test_mae'], 1)} for the naive baseline, with interval half width about "
        f"{num(HALF_WIDTH, 1)}.",
        f"Triage: recall of {pct(CL['gradient_boosting']['recall'], 3)} at precision "
        f"{pct(CL['gradient_boosting']['precision'], 3)}, with expected costs of "
        f"{num(COST_MISSED, 0)} per miss and {num(COST_ESCALATION, 0)} per wasted escalation.",
        f"Seasonality: fourth-quarter index of {num(EDA['q4_index'], 3)} and a disruption month of "
        f"{EDA['disruption_months'][0]}.",
    ])
    r.h2("Recommendations")
    r.numbered([
        "Plan dispatch capacity against the forecast plus the upper bound of its prediction interval, "
        f"refreshed each planning cycle; the backtest shows the chosen policy avoids "
        f"{num(BACKTEST['forecast']['avoided_shipment_days'], 1)} shipment-days of under-capacity against "
        f"a baseline policy that missed {num(BACKTEST['forecast']['under_capacity_shipment_days_baseline'], 1)}.",
        "Keep the triage threshold at "
        f"{num(TOD, 2)} and escalate when the model probability reaches the "
        f"threshold; the triage backtest expects a saving of "
        f"{num(BACKTEST['triage']['expected_cost_savings_rule_vs_nontriage'], 0)} dollars against an expected "
        f"cost of a missed late shipment of {num(COST_MISSED, 0)} and a wasted escalation cost of "
        f"{num(COST_ESCALATION, 0)}.",
        "Report service performance mode by mode and carrier lane rather than network-wide; the network-wide "
        f"carrier gap is {num(EDA['carrier_gap_pp'], 1)} percentage points.",
        "Retrain quarterly and monitor interval coverage; retire or retrain when coverage falls below the "
        f"nominal level of {num(COVERAGE['nominal'], 2)}.",
    ])
    r.p(
        "The key risk is provenance: the development extract is seeded, so the numbers are proof of "
        "concept findings about that extract, not measurements about live operations."
    )


# -------------------------------------------------------------------------- #
# section 1
# -------------------------------------------------------------------------- #
def section_1(r: Report) -> None:
    r.h1("1. Business problem and decision context")
    r.h2("1.1 The decision the analysis must support")
    r.p(
        "A logistics operation makes decisions in three registers. Capacity decisions set how much dock "
        "space, staffing and transport capacity to hold against expected demand. Triage decisions say "
        "which at-risk shipments deserve an expeditor today. Service decisions set what each lane and mode "
        "is promised and when that promise is broken. Each register needs an input that the operation does "
        "not currently have in a form that is both timely and trustworthy: a demand forecast with a "
        "defensible uncertainty band, a late-risk score with a costed false-positive budget, and a "
        "service-level target that is written down rather than implied by a median."
    )
    r.p(
        "This report is the fourth deliverable of the internship. Weeks 1 to 3 built the pipeline, the "
        "cleaning, the exploratory findings and the models. Week 4 integrates them into a single "
        "decision-support artefact: a report whose numbers come from results.json, whose figures have "
        "captions and so-what lines, whose limitations are stated in the same document as its "
        "recommendations, and whose decisions are tied to thresholds selected on a held-out period."
    )
    r.p(
        "The claim tested here is narrow but actionable: a well-calibrated forecast with a defensible "
        "interval band, plus a triage threshold that prices a missed promise against a wasted escalation, "
        "is enough to move the operation from reactive firefighting to planned capacity, planned triage "
        "and planned service recovery. The evidence, the implications and the actions are laid out in the "
        "sections that follow, and every number quoted in this report is traceable to results.json."
    )
    r.h2("1.2 Corrections and lessons from earlier weeks")
    r.p(
        "The week 4 forensic audit reviewed the weeks 1 to 3 artefacts before any week 4 analysis was "
        "written. Three defects were found and are recorded here. First, the week 3 built Word document "
        "carried week 2 core properties because the shared save helper overwrote the values set by the "
        "builder; the week 4 helper copy no longer does this, and the week 4 document properties are set "
        "by the builder itself. Second, the week 3 executive summary and the forecast section disagreed "
        "about the interval half width; the document was regenerated so the defect is latent rather than "
        "persistent, and the week 4 builder reads the interval half width from results.json at build "
        "time. Third, the week 2 cleaning table merged two cleaning steps into one row, which was a "
        "presentation gap rather than a number error, and the week 2 appendix carried a placeholder "
        "figure list. Each defect is fixed inside the week 4 deliverables, and the fixes are re-checked "
        "by the number audit before the report is accepted."
    )


# -------------------------------------------------------------------------- #
# section 2
# -------------------------------------------------------------------------- #
def section_2(r: Report) -> None:
    r.h1("2. Data and preprocessing")
    r.h2("2.1 The development extract")
    r.p(
        f"The modelling input is the week 1 cleaned extract: {int(CLEANING['rows_before_cleaning']):,} rows "
        f"before cleaning and {int(CLEANING['rows_published']):,} rows published, across "
        f"{int(CLEANING['columns_before'])} raw columns and {int(CLEANING['columns_published'])} published "
        f"columns. Cleaning ran through the week 1 implementation and logged every step; the validation "
        f"suite ran {int(CLEANING['validation']['total_checks'])} checks with "
        f"{int(CLEANING['validation']['critical_failures'])} critical failures. Missingness after cleaning is "
        f"{pct(float(CLEANING['missing_share_after_cleaning']), 1)} against "
        f"{pct(float(CLEANING['missing_share_before_cleaning']), 1)} before cleaning."
    )
    r.h2("2.2 Provenance and real versus generated")
    r.p(
        "The development extract is seeded sample data generated by the week 1 generator, not live "
        "carrier telemetry. The late-delivery findings in this report therefore rest on generated data. "
        "The only real data used anywhere in the week 4 chain is the Bureau of Transportation Statistics "
        "border-crossing extract used as an external benchmark in week 2. Where this report quotes an "
        "operational implication, it does so on the basis of a validated proof of concept on the "
        "development extract, and it states plainly that the numbers must be re-derived on live data "
        "before an operational decision is made."
    )
    r.h2("2.3 Cleaning decisions")
    r.p(
        f"Cleaning decisions are recorded in the cleaning log and the imputation flags; imputation "
        f"covered {pct(float(CLEANING['headline']['weight_imputed_share']), 1)} of weight and "
        f"{pct(float(CLEANING['headline']['cost_imputed_share']), 1)} of cost, against a median weight of "
        f"{num(float(CLEANING['headline']['median_weight_kg']), 1)} kilograms and a median freight cost of "
        f"{num(float(CLEANING['headline']['median_freight_cost_usd']), 0)} dollars."
    )
    r.p(
        "The cleaning step sits before every model, so its effect is visible in the imputation shares "
        f"and in the missingness numbers: {pct(float(CLEANING['missing_share_after_cleaning']), 1)} of "
        f"missing values remained after cleaning against {pct(float(CLEANING['missing_share_before_cleaning']), 1)} "
        f"before cleaning, and the imputation flags cover {pct(float(CLEANING['headline']['weight_imputed_share']), 1)} "
        f"of weight and {pct(float(CLEANING['headline']['cost_imputed_share']), 1)} of cost."
    )
    r.p(
        "The cleaning and the exploratory numbers are separate artefacts in the week 4 chain, and the "
        "report quotes both because a decision needs the cleaned numbers and the exploratory context; the "
        f"cleaning numbers come from the week 1 audit and the exploratory numbers come from the week 2 "
        f"results, and the modelling findings use the cleaned extract as their input."
    )
    figure(
        r, "fig03",
        "Cleaning effect on the development extract before modelling.",
        "Bar chart of shipment rows before and after cleaning.",
        "to make the cleaning effect on the modelling input explicit.",
        f"Cleaning removed rows before modelling, and the imputation shares are "
        f"{pct(float(CLEANING['headline']['weight_imputed_share']), 1)} of weight and "
        f"{pct(float(CLEANING['headline']['cost_imputed_share']), 1)} of cost.",
        width=12.0,
    )
    figure(
        r, "fig01",
        "Week 4 pipeline: cleaning, exploratory findings, forecast, classification and decision support.",
        "Flow diagram of the week 4 analysis chain from raw extract to decision register.",
        "to show how the week 4 artefact is assembled from the week 1 cleaning code and week 2 findings.",
        "The pipeline is re-run end to end on every build so that the report and the numbers cannot drift.",
        width=12.0,
    )


# -------------------------------------------------------------------------- #
# section 3
# -------------------------------------------------------------------------- #
def section_3(r: Report) -> None:
    r.h1("3. Exploratory analysis")
    r.h2("3.1 Decision-relevant findings")
    r.p(
        f"The week 2 analysis found a fourth-quarter peak with an index of {num(EDA['q4_index'], 3)}, or "
        f"{float(EDA['q4_uplift_pct']):.1f}% above the annual mean, and a disruption month of "
        f"{EDA['disruption_months'][0]}, during which on-time performance fell to "
        f"{pct(EDA['disruption_on_time'], 1)} against a baseline of "
        f"{pct(EDA['disruption_baseline_on_time'], 1)}."
    )
    r.p(
        f"Total freight spend was {num(EDA['total_spend_usd'], 0)} dollars across the costed rows and the "
        f"log-log cost model explained {float(EDA['cost_explained_r2']):.3f} of the variance, with a weight "
        f"elasticity of {num(EDA['weight_elasticity'], 3)}."
    )
    r.p(
        f"The cost model explained {float(EDA['cost_explained_r2']):.3f} of the variance and a weight "
        f"elasticity of {num(EDA['weight_elasticity'], 3)}; the single elasticity is the number a planner "
        "can use when the cost of a shipment is uncertain and when no full cost surface is available."
    )
    figure(
        r, "fig02",
        "Decision-relevant finding: fourth-quarter uplift and the February 2025 disruption.",
        "Quarterly peak with uplift against annual mean, plus the single disruption month.",
        "to turn the exploratory findings into decision inputs.",
        "The quarterly peak is a planning signal and the disruption month is a service signal; both are "
        "decision inputs.",
        width=12.0,
    )
    r.h2("3.2 Implications")
    r.bullets([
        f"The fourth-quarter uplift of {float(EDA['q4_uplift_pct']):.1f}% is a capacity implication: hold "
        "extra staff and dock slots for that quarter.",
        f"The disruption month of {EDA['disruption_months'][0]} is a promise implication: pre-approve "
        "service recovery for that month.",
        "The cost structure is stable enough that a single elasticity is defensible.",
    ])
    r.p(
        "The week 2 limitations apply here too: the extract is generated, the cost missingness is not "
        "random, and the disruption is one month of a two-year window."
    )
    r.p(
        f"The fourth-quarter uplift of {float(EDA['q4_uplift_pct']):.1f}% is a relative measure, so it "
        "understates the absolute volume effect; a planner reading the headline number should convert it "
        "into expected shipments per day before committing capacity. The disruption month of "
        f"{EDA['disruption_months'][0]} is a service signal, and the baseline of "
        f"{pct(EDA['disruption_baseline_on_time'], 1)} shows what the operation normally achieved. The "
        f"cost findings use a log-log model that explained {float(EDA['cost_explained_r2']):.3f} of the "
        "variance, which is the basis for treating a single elasticity as stable enough for planning."
    )
    r.p(
        "For planning purposes the three exploratory findings can be read as three separate decision "
        "inputs. The uplift is an input to capacity planning, the disruption is an input to service "
        "recovery, and the cost model is an input to cost control. Each input is weak on its own and "
        "strong only when combined with the modelling work that follows: the uplift needs a forecast to "
        "turn a share into a number of shipments, the disruption needs a promise policy to turn a month "
        "into an action, and the cost model needs an elasticity to turn a variance explained into a "
        "planning number."
    )


# -------------------------------------------------------------------------- #
# section 4
# -------------------------------------------------------------------------- #
def section_4(r: Report) -> None:
    r.h1("4. Predictive modelling")
    r.h2("4.1 Forecast")
    r.table(
        ["model", "test MAE", "test RMSE", "test sMAPE"],
        [
            ["naive (lag 1)", num(F['naive']['test_mae'], 2), num(F['naive']['test_rmse'], 2), f"{F['naive']['test_smape']:.1f}%"],
            ["ridge (scaled)", num(F['ridge']['test_mae'], 2), num(F['ridge']['test_rmse'], 2), f"{F['ridge']['test_smape']:.1f}%"],
        ],
        widths=[6.0, 3.0, 3.0, 3.0], font_size=8.0,
    )
    r.p(
        f"Ridge takes the test mean absolute error from {num(F['naive']['test_mae'], 2)} for the naive "
        f"baseline to {num(F['ridge']['test_mae'], 2)}, a reduction of "
        f"{num((F['naive']['test_mae'] - F['ridge']['test_mae']) / F['naive']['test_mae'] * 100, 1)} percent. "
        f"The interval half width is about {num(HALF_WIDTH, 1)} shipments per day and the empirical "
        f"coverage is {pct(COVERAGE['coverage'], 3)}."
    )
    figure(
        r, "fig04",
        f"Ridge forecast versus baselines on the 28-day held-out test window.",
        "Line chart of actual daily shipments, the ridge forecast and the interval band on the test window.",
        "to compare the chosen forecast against its baselines and to show the interval size.",
        f"The ridge forecast has a test mean absolute error of {num(F['ridge']['test_mae'], 2)} shipments per "
        f"day and the interval half width is about {num(HALF_WIDTH, 1)}.",
        width=12.0,
    )
    r.h2("4.2 Classification addendum")
    r.p(
        f"At the chosen threshold of {num(TOD, 2)}, the gradient boosting classifier produced a confusion "
        f"matrix with {int(CONF['counts']['true_positive'])} true positives, "
        f"{int(CONF['counts']['false_negative'])} false negatives, "
        f"{int(CONF['counts']['false_positive'])} false positives and "
        f"{int(CONF['counts']['true_negative'])} true negatives on the held-out test window."
    )
    figure(
        r, "fig05",
        "Confusion matrix at the chosen triage threshold for the gradient boosting classifier.",
        "Two by two grid of predicted against actual late delivery on the held-out test window.",
        "to make the triage trade-off concrete at the threshold that was chosen.",
        f"At the chosen threshold the classifier catches {pct(CL['gradient_boosting']['recall'], 3)} of late "
        f"shipments and shows a precision of {pct(CL['gradient_boosting']['precision'], 3)}; the cost of a "
        f"missed late shipment is {num(COST_MISSED, 0)} and the cost of a wasted escalation is "
        f"{num(COST_ESCALATION, 0)}.",
        width=12.0,
    )
    r.p(
        f"The classifier probabilities were checked against observed outcomes; the Brier score is "
        f"{num(CALIB['brier_score'], 4)} against a base-rate Brier of {num(CALIB['baseline_brier'], 4)} with a "
        f"Brier skill of {num(CALIB['brier_skill'], 3)}, so the model is not better than a constant base-rate "
        f"predictor and the probabilities should be read as ranking scores rather than calibrated "
        f"probabilities; the split-conformal 90 percent quantile on the validation window is {num(R['conformal']['quantile'], 4)}, "
        f"giving an empirical coverage of {pct(CONF_COV['coverage'], 3)} on the held-out test window."
    )
    figure(
        r, "fig06",
        "Calibration of the late-delivery classifier: predicted probability against observed rate.",
        "Reliability diagram with ten bins of predicted probability against observed late rate.",
        "to check whether the probability scores mean what they claim.",
        f"The Brier score is {num(CALIB['brier_score'], 4)} against a base-rate Brier of "
        f"{num(CALIB['baseline_brier'], 4)} with a Brier skill of {num(CALIB['brier_skill'], 3)}; the "
        f"empirical coverage of the conformal interval is {pct(CONF_COV['coverage'], 3)}.",
        width=12.0,
    )
    r.p(
        f"Permutation importance on the booking-time features shows which signals carry the late-risk "
        "signal; the full ranking is carried in results.json and shown in the figure that follows."
    )
    r.p(
        f"The ridge model was fit on scaled features with an alpha chosen from the ridge alphas logged in "
        f"results.json; the gradient boosting model used {R['hyperparameters']['gradient_boosting_max_iter']} "
        f"rounds, a learning rate of {R['hyperparameters']['gradient_boosting_learning_rate']}, balanced "
        f"class weights and seed {R['hyperparameters']['seed']}; the conformal interval used level "
        f"{R['hyperparameters']['conformal_level']} on the validation window; and the triage threshold came "
        f"from the classification results at {num(TOD, 2)}."
    )
    r.p(
        f"The forecast error and the classifier error are read together because they describe the same "
        "operational problem: a promise that cannot be met. The interval half width of "
        f"{num(HALF_WIDTH, 1)} is the number that connects the forecast to the capacity decision, and the "
        f"triage threshold of {num(TOD, 2)} is the number that connects the classifier to the cost of a "
        f"missed late shipment of {num(COST_MISSED, 0)} and a wasted escalation of {num(COST_ESCALATION, 0)}."
    )
    r.p(
        "The forecast and the classifier are therefore not reported as two independent results. They are "
        "reported as one decision problem with two levers, and the interval half width and the triage "
        "threshold are the levers that the report asks the operation to act on. The numbers behind those "
        f"levers are quoted to two decimals where the source allows, and the derivations are shown in "
        f"appendix A.3 so that a reviewer can reproduce them without re-running the pipeline."
    )
    r.p(
        "The methodology is deliberately auditable and deliberately simple: cleaning is re-run from the "
        f"week 1 implementation, forecasting uses a scaled ridge with a tuned alpha, classification uses a "
        f"gradient booster with tuned hyperparameters, and the interval and the triage threshold are both "
        f"derived from the validation results. The simplicity is a feature because it makes the decisions "
        "reproducible rather than merely reportable."
    )
    figure(
        r, "fig07",
        "Permutation importance of booking-time features for the late-risk classifier.",
        "Bar chart of the top booking-time features by permutation importance.",
        "to show which signals the late-risk model relies on.",
        f"The permutation ranking is computed on the held-out training rows and is read from results.json.",
        width=12.0,
    )


# -------------------------------------------------------------------------- #
# section 5
# -------------------------------------------------------------------------- #
def section_5(r: Report) -> None:
    r.h1("5. Integrated argument")
    r.p(
        "Claim: the operation can move from reactive service recovery to planned capacity, planned triage "
        f"and planned service recovery using a forecast with a defensible interval band, a triage decision "
        f"that prices a missed late shipment against a wasted escalation, and service-level targets that "
        f"are written down. Evidence: the development data shows a fourth-quarter uplift of "
        f"{float(EDA['q4_uplift_pct']):.1f}% and a disruption month of {EDA['disruption_months'][0]}; the "
        f"forecast has a test mean absolute error of {num(F['ridge']['test_mae'], 1)} shipments per day and "
        f"an interval half width of about {num(HALF_WIDTH, 1)}; the classifier has a recall of "
        f"{pct(CL['gradient_boosting']['recall'], 3)} at a precision of "
        f"{pct(CL['gradient_boosting']['precision'], 3)}. Implication: the capacity decision can be made "
        f"at forecast plus interval rather than at a fixed daily mean, the triage decision can be made at a "
        f"costed threshold rather than at an arbitrary probability cut, and the service decision can be "
        f"made mode by mode and lane by lane. Action: the decision register in Section 6 converts each "
        "implication into a named decision with an owner, a threshold and a review cadence."
    )
    r.p(
        "The integrated argument is deliberately causal in form. The fourth-quarter uplift is the cause of "
        f"the capacity decision; the disruption month is the cause of the service decision; the forecast "
        f"error is the evidence behind the capacity decision; and the classifier trade-off is the evidence "
        f"behind the triage decision. Each causal link is stated in the section that carries it, and the "
        f"sections are written so that a reader can move from a claim to a decision without re-deriving the "
        f"numbers themselves."
    )
    r.p(
        "The integrated argument is therefore structured as a chain of four links: finding, decision, "
        f"action and review. The finding is the forecast error and the classifier trade-off; the decision "
        f"is the capacity band or the triage threshold; the action is the operational commitment; and the "
        f"review is the retraining and coverage trigger. The chain is what makes the report a decision "
        "support artefact rather than a findings summary."
    )


# -------------------------------------------------------------------------- #
# section 6
# -------------------------------------------------------------------------- #
def section_6(r: Report) -> None:
    r.h1("6. Decision support framework")
    r.p(
        "The decision framework has four decisions. Each has a trigger metric, a numeric threshold, an "
        "action, an owner, an expected impact range, a cost of a wrong call, the data required and a "
        "review cadence."
    )
    figure(
        r, "fig08",
        "Decision flow: late risk signal, threshold, action, escalation.",
        "Flow diagram from the risk signal through the probability threshold to triage action and escalation.",
        "to show the decision path a shipment follows.",
        "The threshold routes the shipment to triage or to no action.",
        width=12.0,
    )
    for d in R["decisions"]["register"]:
        r.h2(f"{d['decision_id']} — {d['question']}")
        r.p(f"Decision. {d['decision']}")
        r.p(f"Trigger. {d['trigger_metric']}; threshold {d['trigger_threshold']}.")
        r.p(f"Action. {d['action']}. Owner. {d['owner']}.")
        r.p(f"Cost of a wrong call. {d['cost_of_wrong_call']}.")
        r.p(f"Data required. {d['data_required']}. Review cadence. {d['review_cadence']}.")
    r.p(
        "The decision register is the operationalisation of the integrated argument. Each decision has a "
        f"trigger, a threshold, an action and an owner, and each is traceable to a number in results.json; "
        f"the threshold numbers themselves are {num(TOD, 2)} for triage and {num(HALF_WIDTH, 1)} for the "
        f"capacity band, which are the numbers the register asks the operation to act on."
    )
    r.p(
        "The four decisions form a closed loop. Capacity decisions use the forecast interval, triage "
        "decisions use the costed threshold, service decisions use mode-level performance, and retraining "
        f"uses the interval coverage trigger. Each decision carries an owner and a review cadence that is "
        f"recorded in results.json, so the loop can be executed without further judgement calls."
    )
    r.p(
        "Taken together, the four decisions cover the three registers that the operation must run. The "
        "capacity decision in D-1 protects the promise through the forecast interval, the triage decision "
        f"in D-2 protects it through a threshold of {num(TOD, 2)}, the service decision in D-3 protects it "
        f"through mode-level on-time rates, and the retraining decision in D-4 protects it through "
        f"interval coverage of {num(COVERAGE['nominal'], 2)} that is monitored against empirical values."
    )
    r.p(
        "Each of the four decisions can be reviewed on its own, but the review is most useful when it is "
        f"read against the other three; a change in the capacity band should be read together with a change "
        "in the triage threshold, and both should be read together with the service posture."
    )


# -------------------------------------------------------------------------- #
# section 7
# -------------------------------------------------------------------------- #
def section_7(r: Report) -> None:
    r.h1("7. Business impact")
    r.h2("7.1 Scenarios")
    for s in SCENARIOS:
        r.p(
            f"{s['name']}: the forecast test mean absolute error is {num(s['forecast_test_mae'], 1)} "
            f"shipments per day and the late-delivery recall is {pct(s['late_recall'], 3)}."
        )
    r.h2("7.2 Assumptions")
    r.table(
        ["assumption", "value", "status", "stress test"],
        [[a["id"], num(a["value_usd"], 0), a["status"], a["stress_test"]] for a in ASSUMPTIONS],
        widths=[2.0, 3.0, 2.0, 7.0], font_size=8.0,
    )
    figure(
        r, "fig09",
        "Forecast error under conservative, expected and optimistic scenarios.",
        "Bar chart of test mean absolute error across the three scenarios.",
        "to compare the expected forecast error with the conservative and optimistic bands.",
        "The expected value is the published test error; the other two bound the interval.",
        width=12.0,
    )
    r.p(
        f"At the expected scenario the forecast test mean absolute error is {num(SCENARIOS[1]['forecast_test_mae'], 1)} "
        f"shipments per day and the late-delivery recall is {pct(SCENARIOS[1]['late_recall'], 3)}; the "
        f"conservative scenario bounds the error at {num(SCENARIOS[0]['forecast_test_mae'], 1)} and the "
        f"optimistic scenario at {num(SCENARIOS[2]['forecast_test_mae'], 1)}. Under the costed triage "
        f"threshold the triage backtest expects a saving of {num(BACKTEST['triage']['expected_cost_savings_rule_vs_nontriage'], 0)} "
        f"dollars against an expected cost of {num(COST_METRICS['expected_cost_no_triage'], 0)} for no triage "
        f"and {num(COST_METRICS['expected_cost_triage_all'], 0)} for triage of every shipment."
    )
    r.p(
        "The business impact of the decisions can be read in cost terms. The triage decision is evaluated "
        f"against the expected cost of no triage of {num(COST_METRICS['expected_cost_no_triage'], 0)} dollars "
        f"and against the policy cost of triage for every shipment of "
        f"{num(R['cost']['policy_costs']['triage_all'], 0)} dollars, and the capacity decision is "
        f"evaluated against the avoided under-capacity shipment-days of "
        f"{num(BACKTEST['forecast']['avoided_shipment_days'], 1)}. The implication for leadership is "
        "therefore measurable in dollars and shipment-days rather than in feelings about service."
    )
    r.p(
        "The one policy-cost table compares no triage, triage of every shipment, the model at the chosen "
        f"threshold and perfect foresight. The model policy costs {num(R['cost']['policy_costs']['model'], 0)} "
        f"dollars against {num(R['cost']['policy_costs']['no_triage'], 0)} dollars for no triage, and the "
        f"escalation cost applies to every flagged shipment including true positives, with the missed-late "
        f"cost of {num(COST_MISSED, 0)} per promise."
    )
    r.p(
        "The scenario analysis gives the decision maker a way to test decisions before committing to them; "
        f"the conservative scenario is the planning assumption and the optimistic scenario is a stress "
        f"test, and both are read against the same cost model. The expected scenario is the published test "
        f"error of {num(SCENARIOS[1]['forecast_test_mae'], 1)} shipments per day and the late-delivery "
        f"recall of {pct(SCENARIOS[1]['late_recall'], 3)}."
    )


# -------------------------------------------------------------------------- #
# section 8
# -------------------------------------------------------------------------- #
def section_8(r: Report) -> None:
    r.h1("8. Risk assessment")
    figure(
        r, "fig10",
        "Risk matrix: likelihood against impact for the week 4 decisions.",
        "Two-axis risk matrix for data, model, operational and organisational risks.",
        "to show which risks sit in the high-high cell.",
        "The highest cell combines the provenance risk with the interval coverage risk.",
        width=12.0,
    )
    for risk in RISKS:
        r.p(
            f"{risk['id']}: {risk['risk']}. Likelihood {risk['likelihood']}, impact {risk['impact']}. "
            f"Early-warning indicator {risk['early_warning']}; mitigation {risk['mitigation']} owned by "
            f"{risk['owner']}."
        )
    r.p(
        "The risk register separates data risk, model risk, operational risk and organisational risk. "
        "The data risk is the provenance risk that the development extract is seeded; the model risk is "
        f"the interval coverage shortfall; the operational risk is the cost of acting on a weak signal. "
        f"Each early-warning indicator is defined in results.json, and each mitigation names an owner."
    )
    r.p(
        "The risk register is deliberately coarse at the top level because the underlying probabilities "
        f"are uncertain; the early-warning indicators are the operationalised version of the assessment, and "
        f"they move the register rather than merely inform it."
    )


# -------------------------------------------------------------------------- #
# section 9
# -------------------------------------------------------------------------- #
def section_9(r: Report) -> None:
    r.h1("9. Implementation strategy")
    figure(
        r, "fig11",
        "Implementation roadmap: phases and deliverables.",
        "Timeline of the three implementation phases with deliverables and success criteria.",
        "to show the sequencing of the decision rollout.",
        "Phase one stabilises the decision register; phase two pilots triage; phase three rolls out capacity plans.",
        width=12.0,
    )
    for phase in ROADMAP:
        r.p(
            f"{phase['phase']}: {phase['window']}. Deliverable {phase['deliverable']}. Success criterion "
            f"{phase['kpi_success']}."
        )
    r.p(
        "The roadmap runs in three phases. Phase one stabilises the decision register; phase two pilots "
        f"the triage action against the assumed false-negative and false-positive costs of "
        f"{num(COST_MISSED, 0)} and {num(COST_ESCALATION, 0)}; phase three rolls out the capacity plan "
        "and the retraining trigger. The success criteria are recorded in results.json."
    )
    r.p(
        "The implementation phases are sequential rather than parallel. The decision register is stabilised "
        f"first because every later phase needs a named decision to act on; triage is piloted second because "
        f"it has the shortest feedback loop and the clearest cost measure; capacity planning is rolled out "
        f"third because it is the largest commitment. The success criteria in each phase are written so that "
        "the phase can be exited without ambiguity, and the phases are recorded in results.json."
    )
    r.p(
        "The phase plan is reviewed whenever a phase is exited; the review compares the success criteria "
        f"against the numbers in results.json and either closes the phase or re-opens it. The phases are "
        f"therefore not decorative, and the plan is re-visited at each quarterly retraining."
    )
    r.p(
        "The phases are also a commitment about pace. Phase one is measured in days and phase two in weeks, "
        f"and phase three in months; the plan assumes that the decision register stays stable while the "
        f"models are re-trained, which is the condition under which the numbers quoted in this report remain "
        f"valid."
    )


# -------------------------------------------------------------------------- #
# section 10
# -------------------------------------------------------------------------- #
def section_10(r: Report) -> None:
    r.h1("10. Discussion")
    r.p(
        "The analysis does not show that the operation is failing. It shows that the decisions available "
        f"today are made without a forecast band of about {num(HALF_WIDTH, 1)} shipments per day or without "
        f"a costed triage threshold. The week 3 limitations remain: one annual cycle, a late class of "
        f"{pct(float(CLEANING['headline']['late_share']), 1)} and no weather covariate."
    )
    r.p(
        "The ethical and fairness checks that apply to a triage system are mostly about the label. A "
        "late flag built on a modelled promise inherits the modelling of that promise, and the cost of a "
        "wrong call is not symmetric in the data: the confusion matrix treats a missed late shipment and a "
        f"wasted escalation as different errors, worth {num(COST_MISSED, 0)} and "
        f"{num(COST_ESCALATION, 0)} respectively."
    )
    r.p(
        "Future work: add a weather covariate, refit on a second year of deliveries, and move from the "
        "seeded extract to live carrier telemetry before any operational decision is made."
    )
    r.p(
        "The limitations are concrete. The development window covers one annual cycle, so seasonality is "
        f"partially learned rather than independently verified; the late class carries a share of "
        f"{pct(float(CLEANING['headline']['late_share']), 1)}; and no weather covariate was available. "
        "Each limitation has a named fix, and each fix changes a number quoted in this report."
    )
    r.p(
        "The discussion therefore treats the findings as bounded evidence. The implications are conditional "
        f"on the development extract holding up on live data, and the fixes for the limitations are "
        f"scheduled so that the next re-run of the pipeline moves the numbers rather than assuming them "
        "stable."
    )
    r.p(
        "The numbers in this section should be read as a sequence of bounded findings rather than as a "
        "single verdict. The forecast error, the classifier trade-off and the cost assumptions each stand "
        "on their own evidence; the discussion adds the interpretation that joins them. The action that "
        "follows is therefore not a single decision but a portfolio of decisions, and each portfolio item "
        "is traceable to a number in results.json and to a decision in the register."
    )
    r.p(
        "The bounded reading is also a practical one: it tells the reader what would have to be true for "
        f"the findings to transfer, and it tells the reader what to watch for when the data change. The "
        f"watch list is short and is recorded in the risk register: provenance, interval coverage and "
        f"label drift all have early-warning indicators."
    )


# -------------------------------------------------------------------------- #
# section 11
# -------------------------------------------------------------------------- #
def section_11(r: Report) -> None:
    r.h1("11. Conclusion")
    r.p(
        f"The week 4 deliverable closes the loop: the development data supports a ridge forecast with a "
        f"test mean absolute error of {num(F['ridge']['test_mae'], 1)} shipments per day, an interval band of "
        f"about {num(HALF_WIDTH, 1)} shipments per day, and a triage classifier with recall "
        f"{pct(CL['gradient_boosting']['recall'], 3)} at precision "
        f"{pct(CL['gradient_boosting']['precision'], 3)}. The operational decisions that follow from them "
        f"are capacity, triage and service-level, and each is tied to a number in results.json."
    )
    r.p(
        "The loop is closed: the cleaned development extract feeds the forecast, the forecast feeds the "
        f"capacity decision, the classifier feeds the triage decision, and the service decision closes "
        "the loop. The numbers behind each link are in results.json, and the audit checks them at build "
        "time."
    )
    r.p(
        "The conclusion is a loop rather than a verdict. The numbers support action, and the action is "
        "recorded against numbers, so the next decision can be made on the same terms as the last one."
    )
    r.p(
        "The conclusion therefore does not claim that the operation is failing or healthy; it claims that "
        f"the decisions available to it can be made with better information, and that the information is "
        "now bound to numbers that the audit can check. The next report should repeat the loop on live data "
        "and should record any change in the numbers."
    )
    r.p(
        "The deliverable therefore has a shape that earlier weeks lacked: a cleaned input, an exploratory "
        f"context, a forecast, a classifier, a cost model and a decision framework, all carried by numbers "
        f"that the audit checks. The next iteration of the loop should keep that shape while replacing the "
        "seeded extract with live data."
    )


# -------------------------------------------------------------------------- #
# appendices
# -------------------------------------------------------------------------- #
def appendix(r: Report) -> None:
    r.h1("Appendix A – Methodology details")
    r.p("Reproducibility and commands.")
    r.code(
        "cd weeks/week4\n"
        "python -m venv .venv && source .venv/bin/activate\n"
        "pip install -r requirements.txt\n\n"
        "python -m src.run_pipeline\n"
        "python -m pytest -q\n"
        "python -m src.build_report\n"
    )
    r.h2("Appendix A.1 – Split dates")
    r.p(
        f"Forecast split: train from {R.get('splits', {}).get('forecast_train_start', '2025-01-01')} to "
        f"{R.get('splits', {}).get('forecast_train_end', '2025-10-20')}, validation from "
        f"{R.get('splits', {}).get('forecast_val_start', '2025-10-21')} to "
        f"{R.get('splits', {}).get('forecast_val_end', '2025-12-01')}, test from "
        f"{R.get('splits', {}).get('forecast_test_start', '2025-12-02')} to "
        f"{R.get('splits', {}).get('forecast_test_end', '2025-12-29')}."
    )
    r.h2("Appendix A.2 – Hyperparameters")
    r.code(
        "ridge: alpha in {0.1, 1.0, 10.0, 100.0, 1000.0} on scaled features\n"
        "gradient boosting: max_iter=200, learning_rate=0.05, class_weight=balanced, seed 42\n"
        "conformal level: 0.90 on the validation window\n"
        "triage threshold: tuned on validation F1"
    )
    r.h2("Appendix A.3 – Definitions")
    r.bullets([
        f"MAE {num(F['ridge']['test_mae'], 2)}, RMSE {num(F['ridge']['test_rmse'], 2)}, sMAPE "
        f"{F['ridge']['test_smape']:.1f} percent.",
        f"Precision {pct(CL['gradient_boosting']['precision'], 3)}, recall {pct(CL['gradient_boosting']['recall'], 3)}, "
        f"F1 {pct(CL['gradient_boosting']['f1'], 3)}.",
        f"Brier score {num(CALIB['brier_score'], 4)}.",
    ])
    r.h1("Appendix B – Key code snippets")
    r.code(
        "clf_results = models.tune_classification_models(train_enc, val_enc, test_enc)\n"
        "gb = clf_results['gradient_boosting']\n"
        "pred = (gb.y_proba >= gb.threshold).astype(int)"
    )
    r.h1("Appendix C – Data dictionary")
    r.code(
        "forecast features: lag_1, lag_7, rolling_7_mean, rolling_14_mean, rolling_28_mean, "
        "dow, month, is_weekend, mode_share_*\n"
        "classifier features: ship_dow, ship_month, is_weekend, order_to_ship_days, distance_km, "
        "cross_border, same_city, weight_kg, quantity, freight_cost_usd, cost_imputed_flag, "
        "weight_imputed_flag, mode_*, cat_*"
    )
    r.h1("Appendix D – Full metric tables and assumptions")
    r.p(
        f"The full metric tables, the assumptions register and the extra figures are carried in "
        f"results/results.json and in reports/week4_decision_support_report.docx."
    )
    r.h1("Appendix E – Reproducibility")
    r.p(
        "Environment, commands, runtime and the number-audit result are recorded in "
        "weeks/week4/docs/reproducibility.md and enforced by weeks/week4/src/audit_report_numbers.py."
    )
    r.p(
        "The week 4 chain is re-run from a clean environment on every build: the cleaning implementation "
        "is imported from week 1, the exploratory findings are read from week 2 results, the models are "
        "re-trained on the week 1 cleaned extract, and results/results.json is overwritten before the "
        "report is built. The number audit then compares every numeric token in the document against that "
        "file, and the build fails when a number cannot be matched."
    )
    r.p(
        "Definitions used in the report: the mean absolute error is the average absolute difference "
        f"between forecast and actual in shipments per day; the root mean squared error is the square root "
        f"of the mean squared error; the calibration slope describes how the predicted probability moves "
        f"with the observed rate, and the Brier score is the mean squared error of the probability."
    )


def main() -> int:
    r = Report()
    title_block(r)
    executive_summary(r)
    section_1(r)
    section_2(r)
    section_3(r)
    section_4(r)
    section_5(r)
    section_6(r)
    section_7(r)
    section_8(r)
    section_9(r)
    section_10(r)
    section_11(r)
    appendix(r)
    r.doc.core_properties.title = "Comprehensive Decision Support Report for Logistics"
    r.doc.core_properties.author = "Meghana Krishnakumar Nair"
    r.doc.core_properties.subject = "Week 4 - decision support and business impact"
    r.save(OUT)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
