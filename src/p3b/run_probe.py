"""3b: leave-one-scenario-out, 12 folder. Identisk med p3 bortsett fra
inndata (prompt med) og felle-etiketten.

Varianter:
  main   turn0-representasjon  + felle-etikett   (hovedtall)
  abl_a  turn0-representasjon  + p3s etikett     (prompt, UTEN felle-etikett)
  abl_b  allturns-representasjon + felle-etikett fra alle turer
"""
import json, os, sys, time, collections
import numpy as np
from sklearn.metrics import roc_auc_score

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "ClaudeWork/decision-probe/factcheck"))
import extract as E                                      # noqa: E402
sys.path.insert(0, "/Volumes/Vault/forseti/p3/src")
from run_probe import (fit_head, pscore, verdict_from, pair_verdicts,   # noqa: E402
                       C_GRID, TAU_GRID, INNER_K, SEED)
from sklearn.model_selection import GroupKFold           # noqa: E402
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import brier                                   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P3 = "/Volumes/Vault/forseti/p3"

VARIANTS = {
    "main":  {"repr": "sent_turn0",    "label": "bearer"},
    "abl_a": {"repr": "sent_turn0",    "label": "bearer_p3"},
    "abl_b": {"repr": "sent_allturns", "label": "bearer_allturns"},
    # Lagt til ETTER hovedkjoringen, som diagnose - ikke et kriterium.
    # Uten denne cellen kan ikke fallet tilskrives: 2x2 er {prompt, ingen
    # prompt} x {felle-etikett, p3-etikett}. p3 = ingen prompt + p3-etikett,
    # main = prompt + felle, abl_a = prompt + p3. Denne er ingen prompt + felle.
    "abl_c": {"repr": "p3_noprompt", "label": "bearer"},
}


def main(variant="main"):
    t0 = time.time()
    cfg = VARIANTS[variant]
    pairs = [json.loads(l) for l in open(os.path.join(P3, "data", "pairs.jsonl"))]
    sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    if cfg["repr"] == "p3_noprompt":
        X = np.load(os.path.join(P3, "results", "cache", "sent_repr.npz"))["mean"]
    else:
        X = np.load(os.path.join(ROOT, "results", "cache", cfg["repr"] + ".npz"))["mean"]
    assert len(X) == len(sents)
    if cfg["label"] == "bearer_allturns":
        y = np.array([int(r["bearer_p3"] and not r["is_trap_all"]) for r in sents])
    else:
        y = np.array([int(r[cfg["label"]]) for r in sents])
    groups = np.array([r["scenario"] for r in sents])
    pairs_by_id = {p["pair_id"]: p for p in pairs}

    import yaml
    decl = yaml.safe_load(open(os.path.join(
        HOME, "ClaudeWork/decision-probe/factcheck/expected_facts.yaml")))
    fact_objs = {(sc["id"], f["key"]): f for sc in decl["scenarios"] for f in sc["facts"]}

    scen = sorted(set(groups.tolist()))
    print(f"[{variant}] {len(sents)} setninger, {len(pairs)} par, "
          f"{y.sum()} baerere ({y.mean():.1%})", flush=True)

    all_pred, folds = {}, []
    oof = np.zeros(len(sents))
    for fi, s_out in enumerate(scen, 1):
        te = groups == s_out
        tr = ~te
        ytr, gtr = y[tr], groups[tr]
        inner = list(GroupKFold(n_splits=INNER_K).split(np.zeros(tr.sum()), ytr, gtr))
        best = None
        for li in range(X.shape[1]):
            Xl = X[tr, li, :].astype(np.float32)
            for C in C_GRID:
                o = np.zeros(tr.sum())
                for a, b in inner:
                    sc_, clf_ = fit_head(Xl[a], ytr[a], C)
                    o[b] = pscore(sc_, clf_, Xl[b])
                bs = brier(o, ytr)
                if best is None or bs < best[0]:
                    best = (bs, li, C, o.copy())
        _, li, C, o = best
        tr_idx = np.flatnonzero(tr)
        inner_sents = [sents[i] for i in tr_idx]
        best_tau, best_acc = TAU_GRID[0], -1.0
        for tau in TAU_GRID:
            pv = pair_verdicts(o, inner_sents, pairs_by_id, tau, fact_objs)
            acc = np.mean([pv[p]["verdict"] == pairs_by_id[p]["label4"] for p in pv])
            if acc > best_acc:
                best_acc, best_tau = acc, tau
        sc_, clf_ = fit_head(X[tr, li, :].astype(np.float32), ytr, C)
        s_te = pscore(sc_, clf_, X[te, li, :].astype(np.float32))
        oof[te] = s_te
        pv = pair_verdicts(s_te, [sents[i] for i in np.flatnonzero(te)],
                           pairs_by_id, best_tau, fact_objs)
        all_pred.update(pv)
        folds.append({"scenario": s_out, "layer": f"L{li}", "C": C, "tau": best_tau,
                      "inner_acc": float(best_acc)})
        print(f"  [{fi:2d}/12] {s_out[:38]:38s} L{li:<2d} C={C:<6g} tau={best_tau:.2f} "
              f"indre {best_acc:.3f}  ({time.time()-t0:.0f}s)", flush=True)

    labs = ["correct", "wrong", "not_stated", "ambiguous"]
    rows = []
    for p in pairs:
        pr = all_pred[p["pair_id"]]
        rows.append({**{k: p[k] for k in ("pair_id", "scenario", "fact", "expected",
                                          "label4", "severity", "target", "judge", "run")},
                     "pred": pr["verdict"], "pred_values": pr["values"],
                     "n_chosen": pr["n_chosen"], "max_score": pr["max_score"],
                     "best_sentence": pr["best_sentence"],
                     "regex_baseline": p["regex_flex_outcome"]})
    prec = float(np.mean([r["pred"] == r["label4"] for r in rows]))
    sauroc = float(roc_auc_score(y, oof))
    print(f"\n[{variant}] PRESISJON {prec:.4f} "
          f"({sum(r['pred']==r['label4'] for r in rows)}/{len(rows)})   "
          f"setnings-AUROC {sauroc:.3f}")
    print(f"{'maskin\\fasit':16s}" + "".join(f"{l:>12s}" for l in labs))
    for m in labs:
        print(f"{m:16s}" + "".join(
            f"{sum(1 for r in rows if r['pred']==m and r['label4']==h):>12d}" for h in labs))
    for l in labs:
        tp = sum(1 for r in rows if r["pred"] == l and r["label4"] == l)
        fp = sum(1 for r in rows if r["pred"] == l and r["label4"] != l)
        fn = sum(1 for r in rows if r["pred"] != l and r["label4"] == l)
        print(f"  {l:12s} n={tp+fn:3d}  presisjon "
              f"{tp/(tp+fp) if tp+fp else float('nan'):.3f}  "
              f"recall {tp/(tp+fn) if tp+fn else float('nan'):.3f}")
    json.dump({"variant": variant, "precision": prec, "sentence_auroc": sauroc,
               "rows": rows, "folds": folds},
              open(os.path.join(ROOT, "results", f"probe_{variant}.json"), "w"),
              indent=1, ensure_ascii=False)
    np.save(os.path.join(ROOT, "results", "cache", f"oof_{variant}.npy"), oof)
    print(f"skrevet results/probe_{variant}.json  ({time.time()-t0:.0f}s)\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "main")
