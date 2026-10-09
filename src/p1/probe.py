"""Lineær probe på frosne representasjoner: LOO, indre CV over lag og C,
temperaturskalering tilpasset på out-of-fold-prediksjoner, AUROC-bootstrap,
ECE med 10 botter, Brier, ECE-stoygulv ved n=47.

Indre seleksjonskriterium: Brier pa indre valideringsfolder. sklearn trener med
log-loss (Brier-tap stottes ikke), sa seleksjon og kalibrering barer vekten for
kalibreringsmalet. Valgt for kjoring, fort i rapporten.

Ingen prompttekst leses eller skrives her.
"""
import json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
from scipy.optimize import minimize_scalar

C_GRID = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
N_BOOT = 2000
N_BINS = 10
INNER_K = 5
SEED = 20261009


def fit_head(X, y, C):
    sc = StandardScaler().fit(X)
    clf = LogisticRegression(penalty="l2", C=C, max_iter=5000, solver="lbfgs")
    clf.fit(sc.transform(X), y)
    return sc, clf


def predict_logit(sc, clf, X):
    return clf.decision_function(sc.transform(X))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


def ece(p, y, n_bins=N_BINS):
    """Likebreddede botter over [0,1]. Tomme botter bidrar ikke."""
    p = np.asarray(p, dtype=float); y = np.asarray(y, dtype=float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
    tot = 0.0
    for b in range(n_bins):
        m = idx == b
        if not m.any():
            continue
        tot += (m.sum() / len(p)) * abs(y[m].mean() - p[m].mean())
    return float(tot)


def fit_temperature(logits, y):
    """Finn T>0 som minimerer log-loss pa (logits, y). Returner T."""
    logits = np.asarray(logits, dtype=float); y = np.asarray(y, dtype=float)

    def nll(log_t):
        t = np.exp(log_t)
        z = np.clip(logits / t, -500, 500)
        # stabil log-loss
        ll = np.where(z >= 0,
                      y * (-np.log1p(np.exp(-z))) + (1 - y) * (-z - np.log1p(np.exp(-z))),
                      y * (z - np.log1p(np.exp(z))) + (1 - y) * (-np.log1p(np.exp(z))))
        return -float(np.mean(ll))

    r = minimize_scalar(nll, bounds=(np.log(0.05), np.log(100.0)), method="bounded")
    return float(np.exp(r.x))


def sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -500, 500)
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


def inner_select(Xl, y, rng_seed):
    """Xl: dict lagnavn -> (n,d). Velg (lag, C) ved Brier pa indre stratifisert CV.
    Returner (beste_lag, beste_C, oof_logits_for_beste, oof_y)."""
    skf = StratifiedKFold(n_splits=INNER_K, shuffle=True, random_state=rng_seed)
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
                best = (b, lname, C, oof.copy())
    _, lname, C, oof = best
    return lname, C, oof


def run_loo(layers, y, tag, seed=SEED):
    """layers: dict lagnavn -> (n,d) matrise. Returnerer dict med LOO-resultat."""
    n = len(y)
    raw_logit = np.zeros(n); cal_p = np.zeros(n); raw_p = np.zeros(n)
    chosen_layers = []; chosen_Cs = []; temps = []
    for i in range(n):
        tr = np.array([j for j in range(n) if j != i])
        ytr = y[tr]
        Xl_tr = {k: v[tr] for k, v in layers.items()}
        lname, C, oof = inner_select(Xl_tr, ytr, seed + i)
        chosen_layers.append(lname); chosen_Cs.append(C)
        # temperatur pa out-of-fold-logits fra treningsfolden (ikke pa testpunktet)
        T = fit_temperature(oof, ytr)
        temps.append(T)
        X = layers[lname]
        sc, clf = fit_head(X[tr], ytr, C)
        z = float(predict_logit(sc, clf, X[i:i + 1])[0])
        raw_logit[i] = z
        raw_p[i] = float(sigmoid(z))
        cal_p[i] = float(sigmoid(z / T))
    return {
        "tag": tag,
        "raw_p": raw_p, "cal_p": cal_p, "y": y,
        "chosen_layers": chosen_layers, "chosen_Cs": chosen_Cs, "temps": temps,
    }


def boot_auroc(p, y, n_boot=N_BOOT, seed=SEED):
    """Stratifisert bootstrap: resample innenfor hver klasse, bevar 18/29."""
    rng = np.random.default_rng(seed)
    pos = np.flatnonzero(y == 1); neg = np.flatnonzero(y == 0)
    vals = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(pos, len(pos), replace=True),
                              rng.choice(neg, len(neg), replace=True)])
        vals.append(roc_auc_score(y[idx], p[idx]))
    vals = np.array(vals)
    return float(roc_auc_score(y, p)), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def ece_noise_floor(p, n_boot=N_BOOT, seed=SEED, n_bins=N_BINS):
    """Nullfordeling: anta prediksjonene p er PERFEKT kalibrerte, trekk
    y ~ Bernoulli(p), mal ECE. Median = gulvet. Et ECE under dette er ikke
    bevis for kalibrering."""
    rng = np.random.default_rng(seed + 1)
    p = np.asarray(p, dtype=float)
    vals = [ece(p, (rng.random(len(p)) < p).astype(float), n_bins) for _ in range(n_boot)]
    v = np.array(vals)
    return float(np.median(v)), float(np.percentile(v, 95))


def summarize(res):
    y = res["y"]; raw = res["raw_p"]; cal = res["cal_p"]
    auroc, lo, hi = boot_auroc(cal, y)
    auroc_raw = float(roc_auc_score(y, raw))
    floor_med, floor_p95 = ece_noise_floor(cal)
    from collections import Counter
    lc = Counter(res["chosen_layers"]); cc = Counter(res["chosen_Cs"])
    return {
        "tag": res["tag"],
        "n": int(len(y)),
        "auroc": auroc, "auroc_ci": [lo, hi],
        "auroc_raw_same_ranking": auroc_raw,
        "ece_raw": ece(raw, y), "ece_cal": ece(cal, y),
        "ece_noise_floor_median": floor_med, "ece_noise_floor_p95": floor_p95,
        "brier_raw": brier(raw, y), "brier_cal": brier(cal, y),
        "layer_modal": lc.most_common(1)[0][0],
        "layer_modal_frac": lc.most_common(1)[0][1] / len(y),
        "layer_counts": dict(lc),
        "C_modal": cc.most_common(1)[0][0],
        "C_counts": {str(k): v for k, v in cc.items()},
        "temp_median": float(np.median(res["temps"])),
    }


def main():
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = {}
    preds = {}

    # (a) NB-BERT: mean-pool og [CLS], alle lag
    d = np.load(os.path.join(ROOT, "results", "cache", "bert_repr.npz"), allow_pickle=True)
    y = d["labels"]
    for pool in ["mean", "cls"]:
        arr = d[pool]  # (n, L, H)
        layers = {f"L{li}": arr[:, li, :] for li in range(arr.shape[1])}
        tag = f"nb-bert-base/{pool}"
        print(f"--- {tag}: {arr.shape[1]} lag x {arr.shape[2]} dim ---", flush=True)
        res = run_loo(layers, y, tag)
        s = summarize(res)
        out[tag] = s
        preds[tag] = {"cal_p": res["cal_p"].tolist(), "raw_p": res["raw_p"].tolist(), "y": y.tolist()}
        print(f"    AUROC {s['auroc']:.3f} [{s['auroc_ci'][0]:.3f}; {s['auroc_ci'][1]:.3f}]  "
              f"ECE {s['ece_raw']:.3f}->{s['ece_cal']:.3f} (gulv {s['ece_noise_floor_median']:.3f})  "
              f"Brier {s['brier_cal']:.3f}  lag {s['layer_modal']} ({s['layer_modal_frac']:.0%})", flush=True)

    # (b) nb-llama via ollama: ETT lag (siste, pooled) - lagvalg ikke mulig
    pth = os.path.join(ROOT, "results", "cache", "nbllama_repr.npz")
    if os.path.exists(pth):
        d2 = np.load(pth, allow_pickle=True)
        y2 = d2["labels"]
        assert np.array_equal(y2, y), "etikettene avviker mellom backbones"
        layers = {"last_pooled": d2["emb"]}
        tag = "nb-llama-3.1-8b/ollama-embed"
        print(f"--- {tag}: 1 lag x {d2['emb'].shape[1]} dim (per-lag ikke tilgjengelig) ---", flush=True)
        res = run_loo(layers, y2, tag)
        s = summarize(res)
        out[tag] = s
        preds[tag] = {"cal_p": res["cal_p"].tolist(), "raw_p": res["raw_p"].tolist(), "y": y2.tolist()}
        print(f"    AUROC {s['auroc']:.3f} [{s['auroc_ci'][0]:.3f}; {s['auroc_ci'][1]:.3f}]  "
              f"ECE {s['ece_raw']:.3f}->{s['ece_cal']:.3f} (gulv {s['ece_noise_floor_median']:.3f})  "
              f"Brier {s['brier_cal']:.3f}", flush=True)

    # Baseline 1: majoritetsklasse (alltid answer -> p(refuse) = prevalens)
    prev = float(y.mean())
    out["baseline/majoritet"] = {
        "tag": "baseline/majoritet", "n": int(len(y)),
        "auroc": 0.5, "auroc_ci": [0.5, 0.5],
        "ece_cal": ece(np.full(len(y), prev), y), "ece_raw": ece(np.full(len(y), prev), y),
        "brier_cal": brier(np.full(len(y), prev), y), "brier_raw": brier(np.full(len(y), prev), y),
        "note": f"konstant p(refuse)={prev:.3f}; AUROC 0,5 ved konstruksjon (ingen rangering)",
    }

    with open(os.path.join(ROOT, "results", "main_summary.json"), "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    with open(os.path.join(ROOT, "results", "main_preds.json"), "w") as f:
        json.dump(preds, f, indent=1)
    print("skrevet results/main_summary.json + main_preds.json", flush=True)


if __name__ == "__main__":
    main()
