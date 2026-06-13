"""
Project Veracity: Automated Hallucination Evaluation (Phase 1)
Script: meta_eval.py

This script implements the validation layer (Meta-Evaluation) of the evaluation pipeline.
To certify that the LLM-as-a-Judge system is reliable and aligns with human assessment,
it calculates the Spearman Rank Correlation Coefficient (rho) and the direct accuracy alignment
between the automated judge's verdicts and human ground truth annotations across a validation subset.

Mathematical Context:
- Direct Accuracy Alignment: Measures the exact percentage match of classifications.
- Spearman Rank Correlation Coefficient (rho): Assesses the monotonic relationship between two variables.
  It ranks each dataset, handles ties by averaging ranks, and computes the Pearson correlation 
  coefficient on these ranks.
  
Formula:
  rho = Cov(Rank(X), Rank(Y)) / (StdDev(Rank(X)) * StdDev(Rank(Y)))
  
A threshold of rho >= 0.75 is required to certify the automated judge for production deployment.
"""

import os
import sys

# Resolve execution path to keep script locations robust
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg, level="INFO"):
    """
    Standard log printing wrapper.
    
    Args:
        msg (str): Message body.
        level (str): Category prefix (e.g. INFO, WARNING, ERROR, SUCCESS).
    """
    print(f"[{level}] {msg}")

def mean(lst):
    """
    Calculates arithmetic mean.
    
    Args:
        lst (list of float/int): Numerical values.
        
    Returns:
        float: Arithmetic average.
    """
    return sum(lst) / len(lst)

def pearson_correlation(x, y):
    """
    Computes Pearson Correlation Coefficient between two lists.
    
    Args:
        x (list of float): First dataset.
        y (list of float): Second dataset.
        
    Returns:
        float: Pearson correlation coefficient.
    """
    mx = mean(x)
    my = mean(y)
    xm = [val - mx for val in x]
    ym = [val - my for val in y]
    num = sum(val_x * val_y for val_x, val_y in zip(xm, ym))
    den_x = sum(val**2 for val in xm)
    den_y = sum(val**2 for val in ym)
    if den_x == 0 or den_y == 0:
        return 0.0
    return num / ((den_x * den_y) ** 0.5)

def rank_data(x):
    """
    Assigns ranks to numerical data list, using average ranks for tied values.
    
    This implements fractional ranking (or "1 2.5 2.5 4" ranking).
    If multiple elements are identical, their rank is the average of the positions
    they would have taken in the sorted array.
    
    Args:
        x (list of float/int): Data to rank.
        
    Returns:
        list of float: Fractional ranks corresponding to input elements.
    """
    n = len(x)
    indices = sorted(range(n), key=lambda i: x[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        # Find index boundaries of tied values
        while j < n - 1 and x[indices[j]] == x[indices[j+1]]:
            j += 1
        # Calculate arithmetic average rank of current rank cluster
        avg_rank = (i + j + 2) / 2.0
        for k in range(i, j + 1):
            ranks[indices[k]] = avg_rank
        i = j + 1
    return ranks

def compute_native_spearman(x, y):
    """
    Computes Spearman Rank Correlation natively by calculating Pearson correlation on fractional ranks.
    
    Args:
        x (list of float): First dataset.
        y (list of float): Second dataset.
        
    Returns:
        float: Monotonic correlation coefficient (rho).
    """
    rx = rank_data(x)
    ry = rank_data(y)
    return pearson_correlation(rx, ry)

def run_meta_evaluation():
    """
    Executes meta-evaluation over a hardcoded 30-sample validation subset:
    1. Defines arrays for human ground truth and judge predictions.
    2. Computes and logs direct percentage accuracy match.
    3. Calculates Spearman Rank Correlation Coefficient (using SciPy if available, otherwise native fallback).
    4. Evaluates correlation against the production threshold (rho >= 0.75).
    """
    # Define validation subset vectors representing ground truth consensus and judge predictions
    human_ground_truth = [1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1]
    judge_predictions  = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1] 
    
    n_samples = len(human_ground_truth)
    log(f"Starting meta-evaluation on {n_samples} validation samples...")

    # Calculate exact accuracy alignment
    matches = sum(1 for h, j in zip(human_ground_truth, judge_predictions) if h == j)
    accuracy = (matches / n_samples) * 100
    log(f"Direct Accuracy Alignment: {accuracy:.2f}% ({matches}/{n_samples} matches)")

    # Compute Spearman Rank Correlation Coefficient (rho)
    rho = 0.0
    use_scipy = False
    
    try:
        from scipy.stats import spearmanr
        # Compute correlation using SciPy package
        rho, _ = spearmanr(human_ground_truth, judge_predictions)
        use_scipy = True
        log(f"Computed Spearman Correlation using scipy.stats.spearmanr.")
    except ImportError:
        # Fallback to pure Python custom rank calculation
        rho = compute_native_spearman(human_ground_truth, judge_predictions)
        log(f"scipy not found. Computed Spearman Correlation natively.")

    log(f"Spearman Rank Correlation Coefficient (rho): {rho:.4f}")

    # Validate alignment against reliability threshold
    print("="*60)
    if rho >= 0.75:
        log("SUCCESS: Automated evaluation pipeline is validated and ready for production!", "SUCCESS")
        log(f"Validation Spearman Correlation Coefficient (rho) = {rho:.4f} satisfies the reliability threshold (>= 0.75).", "SUCCESS")
    else:
        log(f"WARNING: Automated prompt configuration is unstable.", "WARNING")
        log(f"Validation Spearman Correlation Coefficient (rho) = {rho:.4f} is below the reliability threshold (0.75).", "WARNING")
    print("="*60)

if __name__ == "__main__":
    run_meta_evaluation()
