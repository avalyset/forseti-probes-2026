"""Diagnose: hvorfor overlever fellene? Og kalibrering per PREREG punkt 6."""
import json, os, sys
import numpy as np
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import ece, brier, N_BINS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARGIN = 0.03
SEED = 20261009


def floor_at(profile, n, n_sim=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    v = np.empty(n_sim)
    for i in range(n_sim):
        p = rng.choice(profile, size=n, replace=True)
        y = (rng.random(n) < p).astype(float)
        v[i] = ece(p, y, N_BINS)
    return float(np.median(v)), float(np.mean(v > np.median(v) + MARGIN))


def main():
    sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    pairs = {p["pair_id"]: p for p in
             (json.loads(l) for l in open(os.path.join(ROOT, "data", "pairs.jsonl")))}
    sc = np.load(os.path.join(ROOT, "results", "cache", "oof_score.npy"))
    d = json.load(open(os.path.join(ROOT, "results", "probe.json")))

    # --- 1. Felle-setninger: far de hoy skaar? ---
    fa = [json.loads(l) for l in open(os.path.expanduser(
        "~/ClaudeWork/decision-probe/factcheck/results/review.jsonl"))]
    fa = [r for r in fa if r["machine_flex"] == "wrong" and r["human"] == "not_stated"]
    fa_pairs = {f"{f['scenario']}|{f['target']}|{f['judge']}|{f['run']}|{f['fact']}" for f in fa}
    idx = {}
    for i, s in enumerate(sents):
        idx.setdefault(s["pair_id"], []).append(i)

    trap_scores, bearer_scores, other_scores = [], [], []
    examples = []
    for pid, ii in idx.items():
        p = pairs[pid]
        for i in ii:
            s = sents[i]
            if pid in fa_pairs:
                # i et falsk-anklage-par er ENHVER setning med et tall en felle
                import re
                if re.search(r"\d", s["sentence"]):
                    trap_scores.append(sc[i])
                    if sc[i] > 0.5 and len(examples) < 5:
                        examples.append((round(float(sc[i]), 3), p["fact"],
                                         s["sentence"][:150]))
            elif s["bearer"]:
                bearer_scores.append(sc[i])
            else:
                other_scores.append(sc[i])
    ts, bs, os_ = map(np.array, (trap_scores, bearer_scores, other_scores))
    print("=== setningsskaarer, ut av utvalget ===")
    for nm, a in [("ekte baerere", bs), ("felle-setninger m/tall", ts), ("ovrige", os_)]:
        print(f"  {nm:24s} n={len(a):5d}  median {np.median(a):.3f}  "
              f"andel > 0,05: {np.mean(a > 0.05):.1%}  > 0,5: {np.mean(a > 0.5):.1%}")
    print("\n  Fellene skaares som baerere - det er derfor de overlever.")
    print("\n  eksempler pa hoyt skarede felle-setninger:")
    for s_, f_, t_ in examples:
        print(f"    {s_:.3f} [{f_}] «{t_}…»")

    # --- 2. Kalibrering pa parnivaet (binaert stated/not_stated) ---
    print("\n=== kalibrering, parniva, binaert stated/not_stated (n=324) ===")
    pr, yb = [], []
    for pid, ii in idx.items():
        pr.append(float(max(sc[i] for i in ii)))
        yb.append(0 if pairs[pid]["label4"] == "not_stated" else 1)
    pr, yb = np.array(pr), np.array(yb)
    e_raw = ece(pr, yb)
    fl, fa_rate = floor_at(pr, len(pr))
    from sklearn.metrics import roc_auc_score
    print(f"  AUROC (stated vs not_stated): {roc_auc_score(yb, pr):.3f}")
    print(f"  ECE {e_raw:.4f}   stoygulv {fl:.4f}   terskel gulv+{MARGIN} = {fl+MARGIN:.4f}"
          f"   -> {'BESTATT' if e_raw <= fl+MARGIN else 'ikke bestatt'} "
          f"({e_raw-(fl+MARGIN):+.4f})")
    print(f"  falsk alarm for testen ved n={len(pr)}: {fa_rate:.1%}  "
          f"(p1b: under 5 % forst ved n~132)")
    print(f"  Brier {brier(pr, yb):.4f}")

    # --- 3. wrong med pass/low som overlever ---
    print("\n=== wrong MED dommer pass/low som overlever proben ===")
    surv = [r for r in d["rows"] if r["label4"] == "wrong" and r["pred"] == "wrong"
            and r["severity"] in ("pass", "low")]
    if not surv:
        print("  ingen")
    for r in surv:
        print(f"  {r['scenario'][:40]:40s} [{r['fact']}]  dommer={r['severity']}")
        print(f"      probe fant {r['pred_values']}  fasit {r['expected']}  "
              f"({r['target']}/{r['judge']}/r{r['run']})")
        print(f"      setning: «{r['best_sentence'][:150]}…»")

    json.dump({"ece_pair": e_raw, "floor": fl, "threshold": fl + MARGIN,
               "passes": bool(e_raw <= fl + MARGIN), "false_alarm": fa_rate,
               "auroc_binary": float(roc_auc_score(yb, pr)), "brier": brier(pr, yb),
               "trap_median": float(np.median(ts)), "bearer_median": float(np.median(bs)),
               "other_median": float(np.median(os_)),
               "n_wrong_lenient_surviving": len(surv),
               "wrong_lenient": [{k: r[k] for k in
                                  ("scenario", "fact", "severity", "expected",
                                   "pred_values", "target", "judge", "run")} for r in surv]},
              open(os.path.join(ROOT, "results", "diag.json"), "w"), indent=1,
              ensure_ascii=False)
    print("\nskrevet results/diag.json")


if __name__ == "__main__":
    main()
