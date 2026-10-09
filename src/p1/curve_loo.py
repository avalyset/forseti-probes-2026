"""POST-PREREG tillegg, tydelig merket.

PREREG definerte laeringskurvens 10/20/30-punkter som hold-out og 47-punktet som
LOO. De to tallene ligger dermed ikke paa samme skala, og kriteriet «kurven
stiger fra 30 til 47» er ikke lesbart slik. Her males 30 og 47 med SAMME
protokoll: LOO innenfor en stratifisert delmengde paa 30, gjentatt R ganger, mot
LOO paa alle 47.

Dette endrer ikke hovedtallet og ikke kriteriene. Det gjor bare
30-vs-47-sammenligningen lesbar.
"""
import json, os, sys, time
import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import run_loo, SEED

R = 5
N_SUB = 30


def main():
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_sum = json.load(open(os.path.join(ROOT, "results", "main_summary.json")))
    out = {}
    t0 = time.time()

    def do(layers, y, tag):
        sss = StratifiedShuffleSplit(n_splits=R, train_size=N_SUB, random_state=SEED)
        vals = []
        for ri, (sub, _) in enumerate(sss.split(np.zeros(len(y)), y)):
            sl = {k: v[sub] for k, v in layers.items()}
            res = run_loo(sl, y[sub], f"{tag}@30#{ri}", seed=SEED + 1000 * ri)
            a = roc_auc_score(res["y"], res["cal_p"])
            vals.append(float(a))
            print(f"      rep {ri+1}/{R}: LOO-AUROC paa 30 = {a:.3f}  ({time.time()-t0:.0f}s)", flush=True)
        v = np.array(vals)
        r = {"n_30_loo_mean": float(v.mean()), "n_30_loo_sd": float(v.std(ddof=1)),
             "n_30_loo_values": vals, "n_47_loo": main_sum[tag]["auroc"],
             "delta_30_to_47": main_sum[tag]["auroc"] - float(v.mean()),
             "reps": R, "protocol": "LOO i baade 30 og 47 - sammenlignbart"}
        print(f"    {tag}: 30 -> {v.mean():.3f} +/- {v.std(ddof=1):.3f} | "
              f"47 -> {main_sum[tag]['auroc']:.3f} | delta {r['delta_30_to_47']:+.3f}", flush=True)
        return r

    d = np.load(os.path.join(ROOT, "results", "cache", "bert_repr.npz"), allow_pickle=True)
    y = d["labels"]
    for pool in ["mean", "cls"]:
        arr = d[pool]
        tag = f"nb-bert-base/{pool}"
        print(f"--- {tag} (LOO@30 x{R} vs LOO@47) ---", flush=True)
        out[tag] = do({f"L{i}": arr[:, i, :] for i in range(arr.shape[1])}, y, tag)

    pth = os.path.join(ROOT, "results", "cache", "nbllama_repr.npz")
    if os.path.exists(pth):
        d2 = np.load(pth, allow_pickle=True)
        tag = "nb-llama-3.1-8b/ollama-embed"
        print(f"--- {tag} (LOO@30 x{R} vs LOO@47) ---", flush=True)
        out[tag] = do({"last_pooled": d2["emb"]}, d2["labels"], tag)

    json.dump(out, open(os.path.join(ROOT, "results", "curve_loo_30_vs_47.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"skrevet results/curve_loo_30_vs_47.json  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
