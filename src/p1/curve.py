"""Laeringskurve: treningsstorrelser 10/20/30/47, 20 tilfeldige stratifiserte
delinger per punkt. Lag og C velges ved indre CV INNENFOR hvert treningsutvalg.
Punktet 47 har ingen hold-out igjen og rapporteres som LOO-tallet fra probe.py.
"""
import json, os, sys, time
import numpy as np
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import fit_head, predict_logit, sigmoid, brier, C_GRID, SEED

SIZES = [10, 20, 30]
N_SPLITS = 20


def inner_select_small(Xl, y, seed):
    """Som probe.inner_select, men k tilpasset sma treningsutvalg."""
    k = int(min(5, np.bincount(y).min()))
    if k < 2:
        return list(Xl.keys())[0], 1.0
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    folds = list(skf.split(np.zeros(len(y)), y))
    best = None
    for lname, X in Xl.items():
        for C in C_GRID:
            oof = np.zeros(len(y)); ok = True
            for tr, va in folds:
                if len(np.unique(y[tr])) < 2:
                    ok = False; break
                sc, clf = fit_head(X[tr], y[tr], C)
                oof[va] = predict_logit(sc, clf, X[va])
            if not ok:
                continue
            b = brier(sigmoid(oof), y)
            if best is None or b < best[0]:
                best = (b, lname, C)
    if best is None:
        return list(Xl.keys())[0], 1.0
    return best[1], best[2]


def curve_for(layers, y, tag, seed=SEED):
    out = []
    for n_tr in SIZES:
        sss = StratifiedShuffleSplit(n_splits=N_SPLITS, train_size=n_tr, random_state=seed + n_tr)
        aurocs = []
        for si, (tr, te) in enumerate(sss.split(np.zeros(len(y)), y)):
            ytr, yte = y[tr], y[te]
            if len(np.unique(ytr)) < 2 or len(np.unique(yte)) < 2:
                continue
            Xl_tr = {k: v[tr] for k, v in layers.items()}
            lname, C = inner_select_small(Xl_tr, ytr, seed + si)
            X = layers[lname]
            sc, clf = fit_head(X[tr], ytr, C)
            p = sigmoid(predict_logit(sc, clf, X[te]))
            aurocs.append(roc_auc_score(yte, p))
        a = np.array(aurocs)
        out.append({"n_train": n_tr, "n_splits_used": len(a),
                    "auroc_mean": float(a.mean()), "auroc_sd": float(a.std(ddof=1)),
                    "auroc_median": float(np.median(a))})
        print(f"    n_tr={n_tr:2d}  AUROC {a.mean():.3f} +/- {a.std(ddof=1):.3f}  (k={len(a)})", flush=True)
    return out


def main():
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    t0 = time.time()
    main_sum = json.load(open(os.path.join(ROOT, "results", "main_summary.json")))
    res = {}

    d = np.load(os.path.join(ROOT, "results", "cache", "bert_repr.npz"), allow_pickle=True)
    y = d["labels"]
    for pool in ["mean", "cls"]:
        arr = d[pool]
        layers = {f"L{li}": arr[:, li, :] for li in range(arr.shape[1])}
        tag = f"nb-bert-base/{pool}"
        print(f"--- laeringskurve {tag} ---", flush=True)
        pts = curve_for(layers, y, tag)
        pts.append({"n_train": 47, "n_splits_used": None,
                    "auroc_mean": main_sum[tag]["auroc"], "auroc_sd": None,
                    "auroc_median": main_sum[tag]["auroc"], "note": "LOO, ingen hold-out"})
        print(f"    n_tr=47  AUROC {main_sum[tag]['auroc']:.3f}  (LOO)", flush=True)
        res[tag] = pts

    pth = os.path.join(ROOT, "results", "cache", "nbllama_repr.npz")
    if os.path.exists(pth):
        d2 = np.load(pth, allow_pickle=True)
        tag = "nb-llama-3.1-8b/ollama-embed"
        print(f"--- laeringskurve {tag} ---", flush=True)
        pts = curve_for({"last_pooled": d2["emb"]}, d2["labels"], tag)
        pts.append({"n_train": 47, "n_splits_used": None,
                    "auroc_mean": main_sum[tag]["auroc"], "auroc_sd": None,
                    "auroc_median": main_sum[tag]["auroc"], "note": "LOO, ingen hold-out"})
        print(f"    n_tr=47  AUROC {main_sum[tag]['auroc']:.3f}  (LOO)", flush=True)
        res[tag] = pts

    with open(os.path.join(ROOT, "results", "curve.json"), "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(f"skrevet results/curve.json  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
