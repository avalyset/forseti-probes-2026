"""Sla sammen automatiske og manuelle etiketter til data/packs_labeled.jsonl."""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
auto = [json.loads(l) for l in open(os.path.join(ROOT, "data", "packs_labeled_auto.jsonl"))]
man = {m["scenario_id"]: m for m in
       (json.loads(l) for l in open(os.path.join(ROOT, "data", "labels_manual.jsonl")))}
out = []
for r in auto:
    sid = r["scenario_id"]
    if sid in man:
        assert r["label"] == "uklar", f"{sid}: manuell overstyring av ikke-uklar etikett"
        r = dict(r, label=man[sid]["manual_label"], rule="MANUELL: " + man[sid]["regelhull"],
                 manual=True)
    else:
        r["manual"] = False
    out.append(r)
assert not any(r["label"] == "uklar" for r in out), "uklar igjen etter manuell runde"
p = os.path.join(ROOT, "data", "packs_labeled.jsonl")
with open(p, "w") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
c = collections.Counter(r["label"] for r in out)
nman = sum(r["manual"] for r in out)
print(f"=== ENDELIG FORDELING (n={len(out)}) ===")
for k in ("answer", "refer", "refuse"):
    print(f"  {k:8s} {c[k]:3d}  ({c[k]/len(out):5.1%})")
print(f"\nmanuelt avgjort: {nman}/{len(out)} = {nman/len(out):.1%}  (grense 30 %: "
      f"{'under' if nman/len(out) <= 0.30 else 'OVER - svakhet'})")
print(f"\nrefuse-klassen er TOM: {c['refuse']} av {len(out)}")
print(f"refer-klassen er TOM:  {c['refer']} av {len(out)}")
print(f"skrevet data/packs_labeled.jsonl")
