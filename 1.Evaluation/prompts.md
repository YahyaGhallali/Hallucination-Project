# Computes prompt stats

I need to calculate exact statistical confidence intervals for Phase 1 of my LLM evaluation project.

Step 1: Data Extraction

Please read the following two files in the workspace:

1.Evaluation/data/evaluation_report.json (Standard Baseline)

1.Evaluation/data/perturbed_evaluation_report.json (Perturbed Baseline)

For each file, extract the adequate counts

Step 2: Statistical Calculation

Because the sample sizes are constrained, you MUST use the Clopper-Pearson (Exact) method to calculate the 95% Confidence Intervals. Do not use the Wald approximation. You should write and execute a short Python script using scipy.stats.binomtest(...).proportion_ci(confidence_level=0.95) to get the exact bounds.

Step 3: Reporting

Output a clean Markdown report comparing both datasets. Include:

Abstention Rate with 95% CI (Successes = Abstentions, Trials = Total Samples)

Quality-Adjusted Factual Yield (QAFY) with 95% CI (Successes = Factual Answers, Trials = Total Samples)

Factuality Rate with 95% CI (Successes = Factual Answers, Trials = Samples Answered)

Statistical Conclusion: Analyze the Factuality Rate CIs. Do they overlap? Can we statistically conclude that the perturbation degraded the model's factuality?"
