"""A-prime og B-prime: enklasse-manifold pa de 85 pakkescenariene.

A-prime: indre sammenheng + per-domene-holdout (hold ut en pakke, tilpass pa sju).
B-prime: tilpass pa alle 85, skaar de 47 hei_refusal, AUROC mot deres ekte etiketter.

Avviksskaar: Mahalanobis med Ledoit-Wolf-krymping (hovedtall) + kNN-cosinus k=5
(robusthet). Lag: fase 1s modale lag er hovedtallet (L10 mean, L8 cls); alle lag
rapporteres som diagnosekurve.

Ingen prompttekst fra hei_refusal beroeres.
"""
import json, os, sys, time
import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import boot_auroc, SEED   # samme bootstrap som fase 1

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "results", "cache")
HEADLINE_LAYER = {"mean": 10, "cls": 8}   # fase 1s modale lag, fastsatt i PREREG


def mahalanobis_scorer(Xtr):
    sc = StandardScaler().fit(Xtr)
    Z = sc.transform(Xtr)
    lw = LedoitWolf(assume_centered=False).fit(Z)
    def score(X):
        return lw.mahalanobis(sc.transform(X))
    return score, {"shrinkage": float(lw.shrinkage_)}


def knn_scorer(Xtr, k=5):
    A = Xtr / (np.linalg.norm(Xtr, axis=1, keepdims=True) + 1e-12)
    def score(X):
        B = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-12)
        sim = B @ A.T                      # (n_test, n_train) cosinus
        part = np.sort(sim, axis=1)[:, ::-1][:, :k]
        return 1.0 - part.mean(axis=1)     # hoy = langt unna
    return score


def layers_of(d, kind):
    if kind == "nbllama":
        return {"last_pooled": d["emb"]}
    return {f"L{i}": d[kind][:, i, :] for i in range(d[kind].shape[1])}


def main():
    t0 = time.time()
    pb = np.load(os.path.join(CACHE, "packs_bert.npz"), allow_pickle=True)
    pn = np.load(os.path.join(CACHE, "packs_nbllama.npz"), allow_pickle=True)
    tb = np.load("/Volumes/Vault/forseti/p1/results/cache/bert_repr.npz", allow_pickle=True)
    tn = np.load("/Volumes/Vault/forseti/p1/results/cache/nbllama_repr.npz", allow_pickle=True)
    t47 = np.load(os.path.join(CACHE, "tok47.npz"))
    y47 = tb["labels"]
    assert np.array_equal(y47, tn["labels"]) and np.array_equal(y47, t47["labels"])
    packs = pb["pack"]
    out = {"A_prime": {}, "B_prime": {}, "meta": {}}

    # --- lengdekonfundering ---
    ltr, lte = pb["ntok"], t47["ntok"]
    len_auroc, len_lo, len_hi = boot_auroc(lte.astype(float), y47)
    out["meta"]["lengde"] = {
        "pakker_median_tokens": float(np.median(ltr)), "pakker_spenn": [int(ltr.min()), int(ltr.max())],
        "de47_median_tokens": float(np.median(lte)), "de47_spenn": [int(lte.min()), int(lte.max())],
        "lengde_baseline_auroc_pa_de47": len_auroc, "lengde_baseline_ci": [len_lo, len_hi],
    }
    print(f"=== lengde === pakker median {np.median(ltr):.0f} tok "
          f"[{ltr.min()}-{ltr.max()}] | de 47 median {np.median(lte):.0f} tok "
          f"[{lte.min()}-{lte.max()}]")
    print(f"    lengdebaseline AUROC pa de 47: {len_auroc:.3f} [{len_lo:.3f}; {len_hi:.3f}]\n")

    specs = [("nb-bert-base/mean", pb, tb, "mean"),
             ("nb-bert-base/cls", pb, tb, "cls"),
             ("nb-llama-3.1-8b/ollama-embed", pn, tn, "nbllama")]

    for tag, dtr, dte, kind in specs:
        Ltr, Lte = layers_of(dtr, kind), layers_of(dte, kind)
        head = f"L{HEADLINE_LAYER[kind]}" if kind in HEADLINE_LAYER else "last_pooled"
        print(f"--- {tag}  (hovedlag {head}) ---", flush=True)

        # ---------- B-prime: alle lag, hovedtall pa forhandsvalgt lag ----------
        per_layer = {}
        for lname in Ltr:
            sc_m, info = mahalanobis_scorer(Ltr[lname])
            s_m = sc_m(Lte[lname])
            a_m, lo_m, hi_m = boot_auroc(s_m, y47)
            sc_k = knn_scorer(Ltr[lname])
            s_k = sc_k(Lte[lname])
            a_k, lo_k, hi_k = boot_auroc(s_k, y47)
            per_layer[lname] = {
                "mahalanobis": {"auroc": a_m, "ci": [lo_m, hi_m], "shrinkage": info["shrinkage"]},
                "knn5": {"auroc": a_k, "ci": [lo_k, hi_k]},
            }
            if lname == head:
                per_layer[lname]["scores_mahalanobis"] = s_m.tolist()
        hl = per_layer[head]
        print(f"    B': mahalanobis {hl['mahalanobis']['auroc']:.3f} "
              f"[{hl['mahalanobis']['ci'][0]:.3f}; {hl['mahalanobis']['ci'][1]:.3f}]   "
              f"knn5 {hl['knn5']['auroc']:.3f} "
              f"[{hl['knn5']['ci'][0]:.3f}; {hl['knn5']['ci'][1]:.3f}]", flush=True)
        best_l = max(per_layer, key=lambda l: per_layer[l]["mahalanobis"]["auroc"])
        print(f"    (alle lag, maha: beste {best_l} = "
              f"{per_layer[best_l]['mahalanobis']['auroc']:.3f}, "
              f"spenn {min(per_layer[l]['mahalanobis']['auroc'] for l in per_layer):.3f}-"
              f"{max(per_layer[l]['mahalanobis']['auroc'] for l in per_layer):.3f})", flush=True)
        out["B_prime"][tag] = {"headline_layer": head, "per_layer": per_layer,
                               "best_layer_posthoc": best_l, "y": y47.tolist()}

        # ---------- A-prime: per-domene-holdout pa hovedlaget ----------
        X = Ltr[head]
        dom = {}
        for p in sorted(set(packs.tolist())):
            m = packs == p
            if m.sum() < 2 or (~m).sum() < 10:
                continue
            scf, _ = mahalanobis_scorer(X[~m])
            in_s = scf(X[~m]); out_s = scf(X[m])
            p95 = float(np.percentile(in_s, 95))
            dom[p] = {"n": int(m.sum()), "median_holdout": float(np.median(out_s)),
                      "median_insample": float(np.median(in_s)),
                      "p95_insample": p95,
                      "skiller_seg_ut": bool(np.median(out_s) > p95),
                      "ratio_median": float(np.median(out_s) / np.median(in_s))}
        out["A_prime"][tag] = {"headline_layer": head, "per_domain": dom}
        flagged = [p for p, v in dom.items() if v["skiller_seg_ut"]]
        for p in sorted(dom, key=lambda q: -dom[q]["ratio_median"]):
            v = dom[p]
            mark = "  <== over p95" if v["skiller_seg_ut"] else ""
            print(f"      {p:28s} n={v['n']:2d}  median utholdt {v['median_holdout']:8.1f}  "
                  f"innenfor {v['median_insample']:8.1f}  p95 {v['p95_insample']:8.1f}"
                  f"  x{v['ratio_median']:.2f}{mark}")
        print(f"      -> flagget: {flagged if flagged else 'ingen'}\n", flush=True)

    json.dump(out, open(os.path.join(ROOT, "results", "oneclass.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"skrevet results/oneclass.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
