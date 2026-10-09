"""Eksporter faktahodet som artefakt for SimpleAudit-dommeren.

Trent pa ALLE 324 par / 12 440 setninger. Lag, C og tau settes til de modale
valgene fra leave-one-scenario-out-kjoringen - ikke tilpasset pa nytt.

MERK: hodet BESTO IKKE kriteriet i p3 (12 av 13 falske anklager overlever).
Artefaktet eksporteres for at dommeren skal kunne bygges og testes, ikke fordi
det er klart til bruk. Dommeren er registrert med default_enabled = False.
"""
import collections, json, os, pickle, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
X = np.load(os.path.join(ROOT, "results", "cache", "sent_repr.npz"))["mean"]
y = np.array([int(r["bearer"]) for r in sents])
d = json.load(open(os.path.join(ROOT, "results", "probe.json")))

layer = collections.Counter(f["layer"] for f in d["folds"]).most_common(1)[0][0]
C = collections.Counter(f["C"] for f in d["folds"]).most_common(1)[0][0]
tau = collections.Counter(f["tau"] for f in d["folds"]).most_common(1)[0][0]
li = int(layer[1:])
print(f"modale valg fra LOSO: lag {layer}, C {C}, tau {tau}")

Xl = X[:, li, :].astype(np.float32)
sc = StandardScaler().fit(Xl)
clf = LogisticRegression(C=C, max_iter=3000, solver="lbfgs", class_weight="balanced")
clf.fit(sc.transform(Xl), y)
print(f"trent pa {len(y)} setninger ({y.sum()} baerere)")

art = {
    "format_version": 1,
    "backbone": "NbAiLab/nb-bert-base",
    "pooling": "mean",
    "layer": li,
    "tau": float(tau),
    "C": float(C),
    "scaler_mean": sc.mean_.astype(np.float32),
    "scaler_scale": sc.scale_.astype(np.float32),
    "coef": clf.coef_.astype(np.float32),
    "intercept": clf.intercept_.astype(np.float32),
    "max_length": 192,
    "trained_on": {"n_sentences": int(len(y)), "n_bearers": int(y.sum()),
                   "n_pairs": 324, "n_scenarios": 12},
    "provenance": {
        "prereg": "208343b2814bd55e3dddd323fe684bf4e7017656",
        "loso_precision": d["precision"],
        "loso_sentence_auroc": d["sentence_auroc"],
        "criterion": "IKKE BESTATT - 12 av 13 falske anklager overlever; "
                     "presisjon 0,852 under regex-baselinens 0,867",
    },
}
p = os.path.join(ROOT, "artifacts")
os.makedirs(p, exist_ok=True)
fp = os.path.join(p, "fact_head_v1.pkl")
with open(fp, "wb") as f:
    pickle.dump(art, f, protocol=4)
import hashlib
sha = hashlib.sha256(open(fp, "rb").read()).hexdigest()
print(f"skrevet {fp}  ({os.path.getsize(fp)/1024:.0f} KB)")
print(f"sha256 {sha}")
json.dump({"path": "artifacts/fact_head_v1.pkl", "sha256": sha,
           "layer": li, "tau": float(tau), "C": float(C)},
          open(os.path.join(ROOT, "artifacts", "fact_head_v1.json"), "w"), indent=1)
