import json
from statsmodels.stats.proportion import proportion_confint
from scipy.stats import boschloo_exact, fisher_exact
from statsmodels.stats.power import zt_ind_solve_power
import statsmodels.api as sm
import numpy as np

# Load data
with open('../output/evaluation_report.json', 'r', encoding='utf-8') as f:
    eval_a = json.load(f)['metrics']
with open('../output/evaluation_report_perturbed.json', 'r', encoding='utf-8') as f:
    eval_b = json.load(f)['metrics']

# Metrics for Group A
N_total_A = eval_a['total_records']
N_neutral_A = eval_a['neutral_count']
N_factual_A = eval_a['entailed_count']
# N_answered = N_factual + N_contradicted (since we exclude failed audits and neutrals)
# Total evaluated = N_factual + N_contradicted + N_neutral 
N_answered_A = eval_a['entailed_count'] + eval_a['contradicted_count']

# Metrics for Group B
N_total_B = eval_b['total_records']
N_neutral_B = eval_b['neutral_count']
N_factual_B = eval_b['entailed_count']
N_answered_B = eval_b['entailed_count'] + eval_b['contradicted_count']

print("=== RAW DATA ===")
print(f"Group A: Total={N_total_A}, Neutral={N_neutral_A}, Factual={N_factual_A}, Answered={N_answered_A}")
print(f"Group B: Total={N_total_B}, Neutral={N_neutral_B}, Factual={N_factual_B}, Answered={N_answered_B}")

# 1. Exact Binomial Confidence Intervals (Clopper-Pearson)
def clopper_pearson(k, n, alpha=0.05):
    ci = proportion_confint(count=k, nobs=n, alpha=alpha, method='beta')
    return (ci[0]*100, ci[1]*100)

print("\n=== CONFIDENCE INTERVALS (95% Clopper-Pearson) ===")
# Abstention Rate
ci_abst_A = clopper_pearson(N_neutral_A, N_total_A)
ci_abst_B = clopper_pearson(N_neutral_B, N_total_B)
print(f"Abstention Rate A: {N_neutral_A/N_total_A*100:.2f}% {ci_abst_A}")
print(f"Abstention Rate B: {N_neutral_B/N_total_B*100:.2f}% {ci_abst_B}")

# Quality-Adjusted Factual Yield
ci_qafy_A = clopper_pearson(N_factual_A, N_total_A)
ci_qafy_B = clopper_pearson(N_factual_B, N_total_B)
print(f"QAFY A: {N_factual_A/N_total_A*100:.2f}% {ci_qafy_A}")
print(f"QAFY B: {N_factual_B/N_total_B*100:.2f}% {ci_qafy_B}")

# Factuality Rate
ci_fact_A = clopper_pearson(N_factual_A, N_answered_A)
ci_fact_B = clopper_pearson(N_factual_B, N_answered_B)
print(f"Factuality Rate A: {N_factual_A/N_answered_A*100:.2f}% {ci_fact_A}")
print(f"Factuality Rate B: {N_factual_B/N_answered_B*100:.2f}% {ci_fact_B}")

# 2. Hypothesis Testing
print("\n=== HYPOTHESIS TESTING ===")
# Testing if Factuality Rate of B is lower than A
# H0: p_A <= p_B (or p_B >= p_A)
# H1: p_B < p_A (Factuality rate degraded in perturbed dataset)
# 2x2 contingency table for Factuality
#          Factual   Not Factual
# Group A    163         10
# Group B    180          8

table = [[N_factual_A, N_answered_A - N_factual_A],
         [N_factual_B, N_answered_B - N_factual_B]]

try:
    res = boschloo_exact(table, alternative='less')
    test_name = "Boschloo's Exact Test"
    p_val = res.pvalue
    stat = res.statistic
except AttributeError:
    res = fisher_exact(table, alternative='less')
    test_name = "Fisher's Exact Test"
    p_val = res[1]
    stat = res[0]

print(f"Test: {test_name}")
print(f"Statistic: {stat}")
print(f"P-value: {p_val}")


# 3. Statistical Power & Sample Size
print("\n=== STATISTICAL POWER & SAMPLE SIZE ===")
p1 = N_factual_A / N_answered_A
p2 = N_factual_B / N_answered_B
# Effect size for proportions (Cohen's h)
h = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))
delta = p1 - p2
print(f"Effect Size (Delta): {delta:.4f}")
print(f"Cohen's h: {h:.4f}")

nobs1 = N_answered_A
ratio = N_answered_B / N_answered_A

try:
    power = zt_ind_solve_power(effect_size=h, nobs1=nobs1, alpha=0.05, ratio=ratio, alternative='larger')
    print(f"Post-hoc Power (beta): {power:.4f}")
    
    # Calculate required sample size for 80% power
    req_n = zt_ind_solve_power(effect_size=h, nobs1=None, alpha=0.05, power=0.8, ratio=1.0, alternative='larger')
    print(f"Required sample size per group for 80% power: {np.ceil(req_n)}")
except Exception as e:
    print("Power calculation failed:", e)

