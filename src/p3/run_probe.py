"""3.3 Kjor: leave-one-scenario-out, 12 folder. Lag, C og tau velges ved indre
gruppert CV i hver treningsfold. Utfall via gjennomgangens egen regel.
"""
import json, os, sys, time, collections
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "ClaudeWork/decision-probe/factcheck"))
import extract as E                                    # noqa: E402
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import ece, brier, sigmoid, N_BINS          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C_GRID = [1e-3, 1e-2, 1e-1, 1.0]
TAU_GRID = [0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60,
            0.70, 0.80, 0.90]
# Utvidet nedover etter at forste kjoring valgte grid-gulvet 0,30 i 11 av 12
# folder - et randartefakt i sokerommet. tau velges fortsatt UTELUKKENDE ved
# indre gruppert CV og ser aldri utholdt scenario, sa utvidelsen er ikke
# tilpasning mot testen. Begge kjoringer rapporteres.
INNER_K = 4
SEED = 20261009


def fit_head(X, y, C):
    sc = StandardScaler().fit(X)
    clf = LogisticRegression(C=C, max_iter=3000, solver="lbfgs", class_weight="balanced")
    clf.fit(sc.transform(X), y)
    return sc, clf


def pscore(sc, clf, X):
    return clf.predict_proba(sc.transform(X))[:, 1]


def verdict_from(values, expected):
    """Gjennomgangens egen regel, uendret."""
    V = sorted({round(v, 6) for v in values})
    if not V:
        return "not_stated"
    if len(V) > 1:
        return "ambiguous"
    return "correct" if abs(V[0] - expected) < 1e-9 else "wrong"


def pair_verdicts(scores, sent_rows, pairs_by_id, tau, fact_objs):
    """Fra setningsskarer -> utfall per par. Regex leser BARE valgte setninger."""
    by_pair = collections.defaultdict(list)
    for s, r in zip(scores, sent_rows):
        by_pair[r["pair_id"]].append((s, r))
    out = {}
    for pid, lst in by_pair.items():
        p = pairs_by_id[pid]
        fact = fact_objs[(p["scenario"], p["fact"])]
        chosen = [r for s, r in lst if s >= tau]
        vals, spans = [], []
        for r in chosen:
            ex = E.extract(r["sentence"], fact, flexible=True)
            vals += list(ex.values); spans += list(ex.spans)
        best = max(lst, key=lambda t: t[0])
        out[pid] = {"verdict": verdict_from(vals, p["expected"]), "values": sorted(set(vals)),
                    "n_chosen": len(chosen), "max_score": float(best[0]),
                    "best_sentence": best[1]["sentence"][:200], "spans": spans}
    return out


def main():
    t0 = time.time()
    pairs = [json.loads(l) for l in open(os.path.join(ROOT, "data", "pairs.jsonl"))]
    sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    X = np.load(os.path.join(ROOT, "results", "cache", "sent_repr.npz"))["mean"]
    assert len(X) == len(sents), f"{len(X)} vs {len(sents)}"
    y = np.array([int(r["bearer"]) for r in sents])
    groups = np.array([r["scenario"] for r in sents])
    pairs_by_id = {p["pair_id"]: p for p in pairs}

    import yaml
    decl = yaml.safe_load(open(os.path.join(
        HOME, "ClaudeWork/decision-probe/factcheck/expected_facts.yaml")))
    fact_objs = {(sc["id"], f["key"]): f for sc in decl["scenarios"] for f in sc["facts"]}

    scen = sorted(set(groups.tolist()))
    print(f"{len(sents)} setninger, {len(pairs)} par, {len(scen)} scenarier "
          f"({y.sum()} baerere)", flush=True)

    all_pred, chosen_cfg = {}, []
    oof_score = np.zeros(len(sents))
    for fi, s_out in enumerate(scen, 1):
        te = groups == s_out
        tr = ~te
        ytr, gtr = y[tr], groups[tr]
        # --- indre gruppert CV: lag x C ved Brier ---
        inner = list(GroupKFold(n_splits=INNER_K).split(np.zeros(tr.sum()), ytr, gtr))
        best = None
        for li in range(X.shape[1]):
            Xl = X[tr, li, :].astype(np.float32)
            for C in C_GRID:
                oof = np.zeros(tr.sum())
                for a, b in inner:
                    sc_, clf_ = fit_head(Xl[a], ytr[a], C)
                    oof[b] = pscore(sc_, clf_, Xl[b])
                bs = brier(oof, ytr)
                if best is None or bs < best[0]:
                    best = (bs, li, C, oof.copy())
        _, li, C, oof = best
        # --- tau ved indre CV, pa 4-klasses treffrate ---
        tr_idx = np.flatnonzero(tr)
        inner_sents = [sents[i] for i in tr_idx]
        best_tau, best_acc = TAU_GRID[0], -1.0
        for tau in TAU_GRID:
            pv = pair_verdicts(oof, inner_sents, pairs_by_id, tau, fact_objs)
            acc = np.mean([pv[pid]["verdict"] == pairs_by_id[pid]["label4"] for pid in pv])
            if acc > best_acc:
                best_acc, best_tau = acc, tau
        # --- tren pa hele treningsfolden, prediker utholdt scenario ---
        sc_, clf_ = fit_head(X[tr, li, :].astype(np.float32), ytr, C)
        s_te = pscore(sc_, clf_, X[te, li, :].astype(np.float32))
        oof_score[te] = s_te
        te_sents = [sents[i] for i in np.flatnonzero(te)]
        pv = pair_verdicts(s_te, te_sents, pairs_by_id, best_tau, fact_objs)
        all_pred.update(pv)
        chosen_cfg.append({"scenario": s_out, "layer": f"L{li}", "C": C, "tau": best_tau,
                           "inner_acc": float(best_acc), "n_pairs": len(pv)})
        print(f"  [{fi:2d}/12] {s_out[:40]:40s} L{li:<2d} C={C:<6g} tau={best_tau:.2f} "
              f"indre {best_acc:.3f}  ({time.time()-t0:.0f}s)", flush=True)

    # --- evaluering ---
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
    sent_auroc = float(roc_auc_score(y, oof_score))
    print(f"\n=== PRESISJON (4-klasse, eksakt treff): {prec:.4f} "
          f"({sum(r['pred']==r['label4'] for r in rows)}/{len(rows)}) ===")
    print(f"setningsnivaets AUROC (ut av utvalget): {sent_auroc:.3f}")

    print(f"\n{'maskin\\fasit':16s}" + "".join(f"{l:>12s}" for l in labs))
    for m in labs:
        print(f"{m:16s}" + "".join(
            f"{sum(1 for r in rows if r['pred']==m and r['label4']==h):>12d}" for h in labs))
    print("\nper klasse:")
    for l in labs:
        tp = sum(1 for r in rows if r["pred"] == l and r["label4"] == l)
        fp = sum(1 for r in rows if r["pred"] == l and r["label4"] != l)
        fn = sum(1 for r in rows if r["pred"] != l and r["label4"] == l)
        pr_ = tp / (tp + fp) if tp + fp else float("nan")
        rc = tp / (tp + fn) if tp + fn else float("nan")
        print(f"  {l:12s} n={tp+fn:3d}  presisjon {pr_:.3f}  recall {rc:.3f}")

    json.dump({"precision": prec, "sentence_auroc": sent_auroc, "rows": rows,
               "folds": chosen_cfg},
              open(os.path.join(ROOT, "results", "probe.json"), "w"),
              indent=1, ensure_ascii=False)
    np.save(os.path.join(ROOT, "results", "cache", "oof_score.npy"), oof_score)
    print(f"\nskrevet results/probe.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
