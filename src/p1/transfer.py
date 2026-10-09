"""Transfer-eksperiment, rapportert for seg: tren paa generert mengde, test paa
de 47. Lag og C velges ved GRUPPERT CV innenfor den genererte mengden (grupper =
kilde-rad-ID), slik at naer-identiske sporsmal fra samme rad ikke havner i bade
trening og validering.

Kurve: treningsstorrelser i generert mengde, 20 tilfeldige delinger per punkt.
Blandes IKKE inn i hovedtallet.
"""
import json, os, sys, time
import numpy as np
from sklearn.model_selection import GroupKFold, StratifiedShuffleSplit
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import (fit_head, predict_logit, sigmoid, brier, ece, fit_temperature,
                   boot_auroc, ece_noise_floor, C_GRID, SEED)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN_SIZES = [50, 100, 200]
N_SPLITS = 20


def select_grouped(layers, y, groups, seed):
    """Velg (lag, C) ved gruppert CV. Returner lag, C, oof-logits."""
    ug = np.unique(groups)
    k = int(min(5, len(ug)))
    if k < 2:
        return list(layers.keys())[0], 1.0, np.zeros(len(y))
    gkf = GroupKFold(n_splits=k)
    folds = list(gkf.split(np.zeros(len(y)), y, groups))
    best = None
    for lname, X in layers.items():
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
                best = (b, lname, C, oof.copy())
    if best is None:
        return list(layers.keys())[0], 1.0, np.zeros(len(y))
    return best[1], best[2], best[3]


def run_transfer(gen_layers, y_gen, groups, test_layers, y_test, tag):
    lname, C, oof = select_grouped(gen_layers, y_gen, groups, SEED)
    T = fit_temperature(oof, y_gen)          # kalibrering fra generert, ikke fra de 47
    sc, clf = fit_head(gen_layers[lname], y_gen, C)
    z = predict_logit(sc, clf, test_layers[lname])
    raw_p, cal_p = sigmoid(z), sigmoid(z / T)
    auroc, lo, hi = boot_auroc(cal_p, y_test)
    fl_med, fl_p95 = ece_noise_floor(cal_p)
    return {
        "tag": tag, "chosen_layer": lname, "chosen_C": C, "temperature": T,
        "n_train_generated": int(len(y_gen)), "n_test": int(len(y_test)),
        "auroc": auroc, "auroc_ci": [lo, hi],
        "ece_raw": ece(raw_p, y_test), "ece_cal": ece(cal_p, y_test),
        "ece_noise_floor_median": fl_med,
        "brier_raw": brier(raw_p, y_test), "brier_cal": brier(cal_p, y_test),
        "cal_p": cal_p.tolist(), "y": y_test.tolist(),
    }


def transfer_curve(gen_layers, y_gen, groups, test_layers, y_test, seed=SEED):
    pts = []
    for n_tr in GEN_SIZES:
        sss = StratifiedShuffleSplit(n_splits=N_SPLITS, train_size=n_tr, random_state=seed + n_tr)
        vals = []
        for si, (tr, _) in enumerate(sss.split(np.zeros(len(y_gen)), y_gen)):
            ytr = y_gen[tr]
            if len(np.unique(ytr)) < 2:
                continue
            sub = {k: v[tr] for k, v in gen_layers.items()}
            lname, C, _ = select_grouped(sub, ytr, groups[tr], seed + si)
            sc, clf = fit_head(sub[lname], ytr, C)
            p = sigmoid(predict_logit(sc, clf, test_layers[lname]))
            vals.append(roc_auc_score(y_test, p))
        a = np.array(vals)
        pts.append({"n_train_generated": n_tr, "n_splits_used": len(a),
                    "auroc_mean": float(a.mean()), "auroc_sd": float(a.std(ddof=1))})
        print(f"      n_gen={n_tr:3d}  AUROC paa de 47: {a.mean():.3f} +/- {a.std(ddof=1):.3f}", flush=True)
    return pts


def main():
    t0 = time.time()
    out = {}
    gb = np.load(os.path.join(ROOT, "results", "cache", "gen_bert_repr.npz"), allow_pickle=True)
    tb = np.load(os.path.join(ROOT, "results", "cache", "bert_repr.npz"), allow_pickle=True)
    y_gen, groups, y_test = gb["labels"], gb["src"], tb["labels"]

    for pool in ["mean", "cls"]:
        ga, ta = gb[pool], tb[pool]
        gl = {f"L{i}": ga[:, i, :] for i in range(ga.shape[1])}
        tl = {f"L{i}": ta[:, i, :] for i in range(ta.shape[1])}
        tag = f"nb-bert-base/{pool}"
        print(f"--- transfer {tag} ---", flush=True)
        r = run_transfer(gl, y_gen, groups, tl, y_test, tag)
        print(f"    alle 270: AUROC {r['auroc']:.3f} [{r['auroc_ci'][0]:.3f}; {r['auroc_ci'][1]:.3f}]  "
              f"ECE {r['ece_raw']:.3f}->{r['ece_cal']:.3f}  Brier {r['brier_cal']:.3f}  "
              f"lag {r['chosen_layer']}  C {r['chosen_C']}  T {r['temperature']:.2f}", flush=True)
        r["curve"] = transfer_curve(gl, y_gen, groups, tl, y_test)
        out[tag] = r

    gn = os.path.join(ROOT, "results", "cache", "gen_nbllama_repr.npz")
    tn = os.path.join(ROOT, "results", "cache", "nbllama_repr.npz")
    if os.path.exists(gn) and os.path.exists(tn):
        g2, t2 = np.load(gn, allow_pickle=True), np.load(tn, allow_pickle=True)
        tag = "nb-llama-3.1-8b/ollama-embed"
        print(f"--- transfer {tag} ---", flush=True)
        r = run_transfer({"last_pooled": g2["emb"]}, g2["labels"], g2["src"],
                         {"last_pooled": t2["emb"]}, t2["labels"], tag)
        print(f"    alle 270: AUROC {r['auroc']:.3f} [{r['auroc_ci'][0]:.3f}; {r['auroc_ci'][1]:.3f}]  "
              f"ECE {r['ece_raw']:.3f}->{r['ece_cal']:.3f}  Brier {r['brier_cal']:.3f}  "
              f"C {r['chosen_C']}  T {r['temperature']:.2f}", flush=True)
        r["curve"] = transfer_curve({"last_pooled": g2["emb"]}, g2["labels"], g2["src"],
                                    {"last_pooled": t2["emb"]}, t2["labels"])
        out[tag] = r

    json.dump(out, open(os.path.join(ROOT, "results", "transfer.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"skrevet results/transfer.json  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
