Viewed evaluation_report.json:1-800
Listed directory output
Listed directory data
Viewed evaluation_report_perturbed.json:1-20
Edited ci_calc.py
Ran command: `python ci_calc.py`
Used tool: manage_task
Ran command: `py ci_calc.py`
Used tool: manage_task

Here is the statistical report comparing the Standard Baseline with the Perturbed Baseline based on exact Clopper-Pearson 95% Confidence Intervals.

### LLM Evaluation: Phase 1 Statistical Report

**Dataset Sample Sizes**

- **Standard Baseline**: 100 total samples
- **Perturbed Baseline**: 40 total samples

---

#### 1. Abstention Rate

*(Successes = Abstentions, Trials = Total Samples)*

- **Standard Baseline**:
  - Rate: **13.00%** (13 / 100)
  - 95% CI: **[7.11%, 21.20%]**
- **Perturbed Baseline**:
  - Rate: **27.50%** (11 / 40)
  - 95% CI: **[14.60%, 43.89%]**

*Observation*: The perturbed dataset leads to a noticeably higher abstention rate, and their confidence intervals do overlap slightly, though the shift in the point estimate is substantial.

#### 2. Quality-Adjusted Factual Yield (QAFY)

*(Successes = Factual Answers, Trials = Total Samples)*

- **Standard Baseline**:
  - Rate: **84.00%** (84 / 100)
  - 95% CI: **[75.32%, 90.57%]**
- **Perturbed Baseline**:
  - Rate: **62.50%** (25 / 40)
  - 95% CI: **[45.80%, 77.27%]**

*Observation*: The QAFY has dropped by over 20 percentage points in the perturbed dataset. The 95% CIs overlap very slightly (between 75.32% and 77.27%), suggesting a strong likely degradation in overall yield.

#### 3. Factuality Rate

*(Successes = Factual Answers, Trials = Samples Answered)*

- **Standard Baseline**:
  - Rate: **96.55%** (84 / 87)
  - 95% CI: **[90.25%, 99.28%]**
- **Perturbed Baseline**:
  - Rate: **86.21%** (25 / 29)
  - 95% CI: **[68.34%, 96.11%]**

---

### Statistical Conclusion

**Do the Factuality Rate CIs overlap?**
Yes, the 95% Confidence Intervals overlap significantly. The Standard Baseline CI is **[90.25%, 99.28%]**, while the Perturbed Baseline CI is **[68.34%, 96.11%]**. The overlapping region is between **90.25%** and **96.11%**.

**Can we statistically conclude that the perturbation degraded the model's factuality?**
Based purely on the 95% Clopper-Pearson Confidence Intervals, we **cannot statistically conclude** with a high degree of confidence that the model's factuality was degraded. The wide confidence interval for the Perturbed Baseline (caused by the heavily constrained sample size of $N=29$ answered queries) completely envelops the lower bound of the Standard Baseline's interval.

While the point estimate dropped from ~96.5% to ~86.2%—hinting that the model might be struggling more with the perturbed entities—the small sample size does not provide enough statistical power to separate these distributions at a 95% confidence level.
