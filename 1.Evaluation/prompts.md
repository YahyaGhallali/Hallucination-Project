# Computes prompt stats

```md
Act as an expert Senior Biostatistician and Quantitative Evaluation Scientist specializing in machine learning metrics.

I need a scientifically rigorous, publication-grade statistical analysis comparing two evaluation runs of a Large Language Model. The goal is to determine if a specific data perturbation has introduced a statistically significant degradation in the model's factuality, or if the variance can be explained by random sampling noise.

Here is the exact raw data from the evaluation pipeline:

### 1. Group A: Standard Baseline Dataset

- Total Raw Samples Processed (N_total_A): 100
- Abstentions / Neutral / Unanswerable (N_neutral_A): 15
- Factual Answers / Entailed (N_factual_A): 79
- Total Valid Answered (N_answered_A = N_total_A - N_neutral_A): 85

### 2. Group B: Perturbed Baseline Dataset

- Total Raw Samples Processed (N_total_B): 40
- Abstentions / Neutral / Unanswerable (N_neutral_B): 10
- Factual Answers / Entailed (N_factual_B): 26
- Total Valid Answered (N_answered_B = N_total_B - N_neutral_B): 30

---

### Required Deliverables & Tasks

1. **Exact Binomial Confidence Intervals (95% CI):**
   Calculate the 95% Confidence Intervals for both groups for the following three specific rates using the Clopper-Pearson (Exact) method. Do NOT use the Wald (Normal approximation) method, as our sample sizes (especially Group B) are small and close to the boundary constraints.
   - Abstention Rate (Successes = Neutrals, Trials = Total Raw Samples)
   - Quality-Adjusted Factual Yield (Successes = Factual, Trials = Total Raw Samples)
   - Factuality Rate (Successes = Factual, Trials = Total Valid Answered)

2. **Hypothesis Testing (Significance Testing):**
   Perform a statistically sound hypothesis test to evaluate whether the Factuality Rate of Group B is lower than Group A. Because Group B's valid sample size is small (n=30), run Boschloo's Exact Test or Fisher's Exact Test instead of a standard large-sample Chi-Squared or Z-test for proportions. State the Null Hypothesis ($H_0$), Alternative Hypothesis ($H_1$), the calculated test statistic, and the exact p-value.

3. **Statistical Power & Sample Size Post-Mortem:**
   - Compute the post-hoc Statistical Power ($\beta$) of this current test given our observed effect size ($\Delta = \text{Factuality}_A - \text{Factuality}_B$).
   - If the results are found to be statistically insignificant due to the overlapping of CIs or a high p-value, calculate the exact minimum sample size ($n$) required per group to detect this exact effect size with a Significance Level ($\alpha = 0.05$) and a Statistical Power ($1-\beta = 0.80$).

4. **Rigorous Scientific Conclusion:**
   Provide a concise executive summary answering whether we can scientifically conclude that the perturbation degraded performance, explaining explicitly what the p-value and interval overlap mean for a production deployment decision.
```
