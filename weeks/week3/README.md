# Week 3 — Predictive Modelling and Forecasting

**Status:** not started. Due in the week beginning 14 November 2026.

## Task as set

Build and evaluate a predictive model that forecasts a key logistics parameter
— demand, delivery time or inventory level — on public or simulated data.
The Word report must document model development, the evaluation process, the
choice of algorithm and the reasoning behind it, the evaluation metrics
(including a confusion matrix where the problem is classification), forecasted
trends, and recommendations for logistics decision-making.

## Target

Transit time as a regression problem, and late delivery as its classification
counterpart. Both are already derivable from week 1's cleaned table, and both
have an honest baseline: the mode-level median.

## Planned approach

1. Features: mode, lane, carrier, category, weight, quantity, month.
2. Baselines first — median transit, then linear regression, then a
   gradient-boosted tree. No model ships without beating the baseline.
3. A time-based train/test split so the model never trains on the future.
4. A written leakage review: `delay_days` and `delivery_date` are consequences
   of the target and must not become features.
5. Metrics: MAE and RMSE for the regression; precision, recall and a confusion
   matrix for the classification; residuals broken down by mode.

## Definition of done

- The reported metric matches what the split actually measures.
- The chosen algorithm is justified against at least one rejected alternative.
- The report states where the model should not be used.
