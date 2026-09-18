import json
import sys

start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
end_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 10

with open("eval/eval_report.json", "r", encoding="utf-8") as f:
    report = json.load(f)

cases = report["per_question_results"][start_idx:end_idx]

for tc in cases:
    qid = tc["id"]
    cat = tc["category"]
    q = tc["question"]
    exp_d = tc["expected_diagnosis"]
    exp_p = tc.get("expected_parts_or_specs", "")
    ans = tc.get("full_generated_answer", "")
    cur_acc = tc.get("diagnostic_accuracy")
    cur_tag = tc.get("eval_tag")
    
    print(f"{'='*80}")
    print(f"ID: {qid} | Cat: {cat} | Current Script: {cur_tag} ({cur_acc})")
    print(f"Question: {q}")
    print(f"Expected Diagnosis: {exp_d}")
    print(f"Expected Parts/Specs: {exp_p}")
    print(f"Generated Answer:\n{ans}")
    print(f"{'='*80}\n")
