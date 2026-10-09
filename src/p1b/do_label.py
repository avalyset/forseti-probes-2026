"""Kjor merkeregelen over de 85, rapporter fordeling og alle «uklar»."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_packs import load_all
from label_rules import label

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "packs_labeled_auto.jsonl")

rows = load_all()
recs, unclear = [], []
for r in rows:
    s = r["scenario"]
    lab, rule, ev = label(s)
    sid = f"{r['pack']}#{r['idx']:02d}"
    rec = {"pack": r["pack"], "scenario_id": sid, "name": s["name"],
           "prompt": s["test_prompt"], "label": lab, "rule": rule,
           "category": s["category"], "subcategory": s["subcategory"],
           "n_expected": len(s["expected_behavior"])}
    recs.append(rec)
    if lab == "uklar":
        unclear.append({"id": sid, "name": s["name"], "pack": r["pack"],
                        "expected_behavior": s["expected_behavior"], "evidens": ev})

with open(OUT, "w") as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

c = collections.Counter(r["label"] for r in recs)
print(f"=== AUTOMATISK FORDELING (n={len(recs)}) ===")
for k in ("answer", "refer", "refuse", "uklar"):
    print(f"  {k:8s} {c[k]:3d}  ({c[k]/len(recs):5.1%})")
print()
print("=== per pakke ===")
pp = collections.defaultdict(collections.Counter)
for r in recs:
    pp[r["pack"]][r["label"]] += 1
for p in sorted(pp):
    d = pp[p]
    print(f"  {p:28s} answer {d['answer']:2d}  refer {d['refer']:2d}  "
          f"refuse {d['refuse']:2d}  uklar {d['uklar']:2d}")
print()
print(f"=== UKLAR: {len(unclear)} ===")
for u in unclear:
    print(f"--- {u['id']}  {u['name'][:60]} ---")
    for b in u["expected_behavior"]:
        print("      *", b[:120])
    print(f"      (negerte punkter hoppet over: {len(u['evidens']['negated_skipped'])})")
json.dump(unclear, open(os.path.join(ROOT, "results", "unclear.json"), "w"),
          indent=1, ensure_ascii=False)
print(f"\nskrevet {os.path.relpath(OUT, ROOT)} + results/unclear.json")
