import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_NORMAL = os.path.join(SCRIPT_DIR, "output", "evaluation_report.json")
REPORT_PERTURBED = os.path.join(SCRIPT_DIR, "output", "evaluation_report_perturbed.json")

def print_record(record, report_type):
    print("=" * 80)
    status_label = record.get("status", "success")
    confidence_str = " [LOW CONFIDENCE]" if status_label == "low_confidence_contradiction" else ""
    print(f"ID: {record.get('id')} | Category: {record.get('category')}{confidence_str} | Source: {report_type}")
    print("-" * 80)
    print(f"Question: {record.get('question')}")
    print(f"Context: {record.get('context')}")
    print(f"Ground Truth: {record.get('ground_truth')}")
    print(f"Model Answer: {record.get('model_generated_answer')}")
    print(f"Judge Reasoning:\n{record.get('reasoning')}")
    if "raw_verdicts" in record:
        print("\nRaw Self-Consistency Verdicts:")
        for idx, val in enumerate(record["raw_verdicts"]):
            print(f"  Run {idx+1}: Category: {val.get('category')} | Reasoning: {val.get('reasoning')}")
    print("=" * 80)
    print("\n")

def run_spot_review():
    for name, path in [("Standard Evaluation", REPORT_NORMAL), ("Perturbed Evaluation", REPORT_PERTURBED)]:
        if not os.path.exists(path):
            print(f"Report file not found: {path}. Skipping...\n")
            continue
            
        print(f"=== Filtering {name} ===")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get("results", [])
            count = 0
            for record in results:
                category = record.get("category")
                status = record.get("status")
                
                if category in ("CONTRADICTION", "NEUTRALITY") or status == "low_confidence_contradiction":
                    print_record(record, name)
                    count += 1
            print(f"Found {count} records matching filters in {name}.\n")
        except Exception as e:
            print(f"Error reading {name}: {e}\n")

if __name__ == "__main__":
    run_spot_review()
