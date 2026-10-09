"""POST-PREREG RETTELSE av A-primes domenekriterium.

PREREG sa: «den utholdte pakkens median ligger over 95-persentilen av avstandene
innenfor treningspakkene». Den sammenligningen er ugyldig: avstandene «innenfor»
males pa de samme punktene som kovariansen er tilpasset pa, med d=768 >> n=74.
De er dermed drastisk underestimerte, og ETHVERT utholdt punkt ser ekstremt ut.
Kjoringen bekreftet det - alle atte pakker ble flagget, 15-120x over.

Rettelsen maler begge sider UTENFOR utvalget:
  (1) LOO-referanse: for hver av de 74 treningspunktene, tilpass pa de ovrige 73
      og skaar punktet. Da er bade referansen og den utholdte pakken
      ut-av-utvalget-avstander.
  (2) Pa tvers av pakker: er en pakkes ut-av-utvalget-median en uteligger blant
      de atte pakkenes medianer? (robust z mot median og MAD)

Kriteriet «skiller seg sterkt ut» leses na av (1): median over 95-persentilen av
LOO-referansen. (2) rapporteres ved siden av.
"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oneclass import mahalanobis_scorer, layers_of, HEADLINE_LAYER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "results", "cache")


def loo_reference(X):
    """Ut-av-utvalget Mahalanobis for hvert punkt i X (tilpass pa de ovrige)."""
    n = len(X)
    out = np.zeros(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        sc, _ = mahalanobis_scorer(X[m])
        out[i] = sc(X[i:i + 1])[0]
    return out


def main():
    t0 = time.time()
    pb = np.load(os.path.join(CACHE, "packs_bert.npz"), allow_pickle=True)
    pn = np.load(os.path.join(CACHE, "packs_nbllama.npz"), allow_pickle=True)
    packs = pb["pack"]
    res = {}
    for tag, d, kind in [("nb-bert-base/mean", pb, "mean"),
                         ("nb-bert-base/cls", pb, "cls"),
                         ("nb-llama-3.1-8b/ollama-embed", pn, "nbllama")]:
        head = f"L{HEADLINE_LAYER[kind]}" if kind in HEADLINE_LAYER else "last_pooled"
        X = layers_of(d, kind)[head]
        print(f"--- {tag} ({head}) ---", flush=True)
        dom, medians = {}, {}
        for p in sorted(set(packs.tolist())):
            m = packs == p
            Xtr, Xte = X[~m], X[m]
            scf, _ = mahalanobis_scorer(Xtr)
            out_s = scf(Xte)                       # utholdt pakke, ut-av-utvalget
            ref = loo_reference(Xtr)               # treningspakker, OGSA ut-av-utvalget
            p95 = float(np.percentile(ref, 95))
            dom[p] = {"n": int(m.sum()),
                      "median_holdout": float(np.median(out_s)),
                      "median_loo_referanse": float(np.median(ref)),
                      "p95_loo_referanse": p95,
                      "skiller_seg_ut": bool(np.median(out_s) > p95),
                      "ratio_mot_loo_median": float(np.median(out_s) / np.median(ref))}
            medians[p] = dom[p]["median_holdout"]
        # (2) uteligger blant de atte medianene, robust z
        vals = np.array([medians[p] for p in sorted(medians)])
        med, mad = float(np.median(vals)), float(np.median(np.abs(vals - np.median(vals))))
        for p in dom:
            z = (medians[p] - med) / (1.4826 * mad) if mad > 0 else 0.0
            dom[p]["robust_z_blant_pakker"] = float(z)
        flagged = sorted([p for p, v in dom.items() if v["skiller_seg_ut"]])
        for p in sorted(dom, key=lambda q: -dom[q]["ratio_mot_loo_median"]):
            v = dom[p]
            mark = "  <== over p95" if v["skiller_seg_ut"] else ""
            print(f"    {p:28s} n={v['n']:2d}  utholdt {v['median_holdout']:7.1f}  "
                  f"LOO-ref median {v['median_loo_referanse']:7.1f}  p95 {v['p95_loo_referanse']:7.1f}  "
                  f"x{v['ratio_mot_loo_median']:.2f}  z={v['robust_z_blant_pakker']:+.2f}{mark}")
        print(f"    -> flagget: {flagged if flagged else 'ingen'}   ({time.time()-t0:.0f}s)\n", flush=True)
        res[tag] = {"headline_layer": head, "per_domain": dom, "flagged": flagged}
    json.dump(res, open(os.path.join(ROOT, "results", "domain_fixed.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"skrevet results/domain_fixed.json  ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
