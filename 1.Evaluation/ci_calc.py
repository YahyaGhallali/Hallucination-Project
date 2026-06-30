import scipy.stats as stats
import json

data = [
    {"name": "Standard Abstention Rate", "k": 13, "n": 100},
    {"name": "Perturbed Abstention Rate", "k": 11, "n": 40},
    {"name": "Standard QAFY", "k": 84, "n": 100},
    {"name": "Perturbed QAFY", "k": 25, "n": 40},
    {"name": "Standard Factuality Rate", "k": 84, "n": 87},
    {"name": "Perturbed Factuality Rate", "k": 25, "n": 29},
]

results = {}
for d in data:
    res = stats.binomtest(d["k"], d["n"]).proportion_ci(confidence_level=0.95)
    rate = d["k"] / d["n"]
    results[d["name"]] = {
        "rate": rate,
        "ci_low": res.low,
        "ci_high": res.high,
        "k": d["k"],
        "n": d["n"]
    }

print(json.dumps(results, indent=2))
