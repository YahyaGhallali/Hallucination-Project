# LLM Evaluation Phase 1: Statistical Analysis Report

This report compares the performance of the model on the Standard Baseline dataset against the Perturbed Baseline dataset. Exact 95% Confidence Intervals (CIs) were calculated using the Clopper-Pearson method to account for constrained sample sizes.

## 1. Data Summary

| Metric | Standard Baseline | Perturbed Baseline |
| :--- | :--- | :--- |
| **Total Samples evaluated** | 100 | 40 |
| **Abstentions (Neutral)** | 15 | 10 |
| **Factual Answers (Entailed)** | 79 | 26 |
| **Total Answered (Total - Abstentions)** | 85 | 30 |

---

## 2. Confidence Interval Estimates (95% CI)

### Abstention Rate

*(Successes = Abstentions, Trials = Total Samples)*

- **Standard Baseline**: 15.00% &nbsp; `[95% CI: 8.65%, 23.53%]`
- **Perturbed Baseline**: 25.00% &nbsp; `[95% CI: 12.69%, 41.20%]`

### Quality-Adjusted Factual Yield (QAFY)

*(Successes = Factual Answers, Trials = Total Samples)*

- **Standard Baseline**: 79.00% &nbsp; `[95% CI: 69.71%, 86.51%]`
- **Perturbed Baseline**: 65.00% &nbsp; `[95% CI: 48.32%, 79.37%]`

### Factuality Rate

*(Successes = Factual Answers, Trials = Samples Answered)*

- **Standard Baseline**: 92.94% &nbsp; `[95% CI: 85.27%, 97.37%]`
- **Perturbed Baseline**: 86.67% &nbsp; `[95% CI: 69.28%, 96.24%]`

---

## 3. Statistical Conclusion

**Analyze the Factuality Rate CIs. Do they overlap?**
Yes, the 95% Confidence Intervals for the Factuality Rate **overlap significantly**.

- Standard CI ranges from **85.27%** to **97.37%**
- Perturbed CI ranges from **69.28%** to **96.24%**

The overlapping region is between `85.27%` and `96.24%`.

**Explain what overlapping means and implies:**
When 95% confidence intervals overlap, it means that the ranges of plausible values for the true underlying metric in both groups share common values. In hypothesis testing, overlapping intervals typically imply that the difference between the two sample proportions might simply be due to random sampling variability rather than a true underlying difference.

**Can we statistically conclude that the perturbation degraded the model's factuality?**
**No.** Because the confidence intervals for the Factuality Rate overlap, we do not have enough statistical evidence at the 95% confidence level to conclude that the perturbation caused a definitive degradation in factuality. While the point estimate dropped from 92.94% to 86.67%, the small sample size (especially the 30 answered questions in the perturbed set) results in a very wide confidence interval. We cannot rule out the possibility that the true factuality rate remains the same across both scenarios.
