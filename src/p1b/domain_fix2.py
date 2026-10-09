"""A-prime rettet, versjon som fullfores innenfor budsjett.

NB-BERT (d=768): LOO-referanse, som i domain_fix.py - 74 fit per pakke.
nb-llama (d=4096): LOO ville kostet 592 fit x 21,2 s = 210 min, malt. Erstattet
med en GROVERE referanse: 10-folds ut-av-utvalget-avstander regnet EN gang paa
alle 85, brukt som felles referanse for alle atte pakker. Merkes som grovere -
den er ikke pakke-spesifikk slik LOO-referansen er.
"""
import json, os, sys, time
import numpy as np
from sklearn.model_selection import KFold
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oneclass import mahalanobis_scorer, layers_of, HEADLINE_LAYER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "results", "cache")
SEED = 20261009


def loo_reference(X):
    n = len(X); out = np.zeros(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        sc, _ = mahalanobis_scorer(X[m]); out[i] = sc(X[i:i + 1])[0]
    return out


def kfold_reference(X, k=10):
    out = np.zeros(len(X))
    for tr, va in KFold(n_splits=k, shuffle=True, random_state=SEED).split(X):
        sc, _ = mahalanobis_scorer(X[tr]); out[va] = sc(X[va])
    return out


def main():
    t0 = time.time()
    pb = np.load(os.path.join(CACHE, "packs_bert.npz"), allow_pickle=True)
    pn = np.load(os.path.join(CACHE, "packs_nbllama.npz"), allow_pickle=True)
    packs = pb["pack"]
    res = {}
    for tag, d, kind, mode in [("nb-bert-base/mean", pb, "mean", "loo"),
                               ("nb-bert-base/cls", pb, "cls", "loo"),
                               ("nb-llama-3.1-8b/ollama-embed", pn, "nbllama", "kfold10")]:
        head = f"L{HEADLINE_LAYER[kind]}" if kind in HEADLINE_LAYER else "last_pooled"
        X = layers_of(d, kind)[head]
        print(f"--- {tag} ({head}, referanse: {mode}) ---", flush=True)
        shared_ref = kfold_reference(X) if mode == "kfold10" else None
        dom, medians = {}, {}
        for p in sorted(set(packs.tolist())):
            m = packs == p
            scf, _ = mahalanobis_scorer(X[~m])
            out_s = scf(X[m])
            ref = shared_ref if shared_ref is not None else loo_reference(X[~m])
            p95 = float(np.percentile(ref, 95))
            dom[p] = {"n": int(m.sum()), "median_holdout": float(np.median(out_s)),
                      "median_referanse": float(np.median(ref)),
                      "p95_referanse": p95, "referansetype": mode,
                      "skiller_seg_ut": bool(np.median(out_s) > p95),
                      "ratio": float(np.median(out_s) / np.median(ref))}
            medians[p] = dom[p]["median_holdout"]
        vals = np.array([medians[p] for p in sorted(medians)])
        med, mad = float(np.median(vals)), float(np.median(np.abs(vals - np.median(vals))))
        for p in dom:
            dom[p]["robust_z"] = float((medians[p] - med) / (1.4826 * mad)) if mad > 0 else 0.0
        flagged = sorted([p for p, v in dom.items() if v["skiller_seg_ut"]])
        for p in sorted(dom, key=lambda q: -dom[q]["ratio"]):
            v = dom[p]
            print(f"    {p:28s} n={v['n']:2d}  utholdt {v['median_holdout']:8.1f}  "
                  f"ref {v['median_referanse']:8.1f}  p95 {v['p95_referanse']:8.1f}  "
                  f"x{v['ratio']:5.2f}  z={v['robust_z']:+.2f}"
                  f"{'  <== over p95' if v['skiller_seg_ut'] else ''}")
        print(f"    -> flagget: {flagged if flagged else 'ingen'}   ({time.time()-t0:.0f}s)\n",
              flush=True)
        res[tag] = {"headline_layer": head, "referansetype": mode,
                    "per_domain": dom, "flagged": flagged}
    json.dump(res, open(os.path.join(ROOT, "results", "domain_fixed.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"skrevet results/domain_fixed.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
