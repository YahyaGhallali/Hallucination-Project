import json
with open('c:/Users/yahya/Desktop/Hallucination/1.Evaluation/output/evaluation_report.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

fails = [r for r in d['results'] if r.get('known_hallucination_baseline_check') and r['known_hallucination_baseline_check'].get('correct') is False]
print('Total fails:', len(fails))
for r in fails[:5]:
    print(f"ID: {r['id']}")
    print(f"Question: {r['question']}")
    check = r['known_hallucination_baseline_check']
    print(f"Category: {check['category']}")
    print(f"Reasoning: {check['reasoning']}")
    print("---")
