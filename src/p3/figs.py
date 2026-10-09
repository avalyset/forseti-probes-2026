import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R, F = os.path.join(ROOT, "results"), os.path.join(ROOT, "figs")
os.makedirs(F, exist_ok=True)
d = json.load(open(os.path.join(R, "probe.json")))
d0 = json.load(open(os.path.join(R, "probe_taufloor.json")))
dg = json.load(open(os.path.join(R, "diag.json")))
sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
sc = np.load(os.path.join(R, "cache", "oof_score.npy"))
LABS = ["correct", "wrong", "not_stated", "ambiguous"]

fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))

# --- 1: presisjon mot baselines ---
names = ["majoritet\n(alltid ambiguous)", "probe\nτ-gulv 0,30", "probe\nτ-grid utvidet",
         "regex flexible\n(samme 324)"]
vals = [147 / 324, d0["precision"], d["precision"],
        sum(r["regex_baseline"] == r["label4"] for r in d["rows"]) / 324]
cols = ["#bbb", "#9ab", "#1f4e79", "#c9a227"]
b = ax[0].bar(range(4), vals, color=cols)
for i, v in enumerate(vals):
    ax[0].annotate(f"{v:.3f}", (i, v + 0.012), ha="center", fontsize=9)
ax[0].axhline(0.90, ls="--", c="#b00", lw=1.4)
ax[0].annotate("kriteriet «virker» ≥ 0,90", (-0.4, 0.915), fontsize=7.5, color="#b00")
ax[0].axhline(0.85, ls=":", c="#777", lw=1.2)
ax[0].annotate("«delvis» 0,85", (-0.4, 0.858), fontsize=7, color="#777")
ax[0].set_xticks(range(4)); ax[0].set_xticklabels(names, fontsize=7)
ax[0].set_ylim(0.4, 1.0); ax[0].set_ylabel("presisjon (4-klasse, eksakt treff)")
ax[0].set_title("Presisjon på (svar, faktum)-nivå\nleave-one-scenario-out, 12 folder", fontsize=9)
ax[0].grid(alpha=0.25, axis="y")

# --- 2: setningsskaarer, tre grupper ---
import re
fa = [json.loads(l) for l in open(os.path.expanduser(
    "~/ClaudeWork/decision-probe/factcheck/results/review.jsonl"))]
fa = [r for r in fa if r["machine_flex"] == "wrong" and r["human"] == "not_stated"]
fap = {f"{f['scenario']}|{f['target']}|{f['judge']}|{f['run']}|{f['fact']}" for f in fa}
tr, be, ot = [], [], []
for i, s in enumerate(sents):
    if s["pair_id"] in fap and re.search(r"\d", s["sentence"]):
        tr.append(sc[i])
    elif s["bearer"]:
        be.append(sc[i])
    else:
        ot.append(sc[i])
bins = np.linspace(0, 1, 26)
for a, c, lab in [(ot, "#ccc", f"øvrige (n={len(ot)})"),
                  (be, "#1f4e79", f"ekte bærere (n={len(be)})"),
                  (tr, "#c0504d", f"felle-setninger m/tall (n={len(tr)})")]:
    ax[1].hist(a, bins=bins, density=True, alpha=0.6, color=c, label=lab)
ax[1].axvline(0.02, ls="--", c="#333", lw=1.2)
ax[1].annotate("τ = 0,02 (valgt i 9/12 folder)", (0.05, ax[1].get_ylim()[1] * 0.82),
               fontsize=7, color="#333")
ax[1].set_xlabel("probe-skår per setning (ut av utvalget)"); ax[1].set_ylabel("tetthet")
ax[1].set_title("Hodet skiller bærere fra øvrige —\nmen ikke bærere fra feller", fontsize=9)
ax[1].legend(fontsize=7); ax[1].set_yscale("log"); ax[1].grid(alpha=0.25)

# --- 3: de 13 ---
byk = {(r["scenario"], r["fact"], r["target"], r["judge"], r["run"]): r for r in d["rows"]}
byk0 = {(r["scenario"], r["fact"], r["target"], r["judge"], r["run"]): r for r in d0["rows"]}
labels, v_new, v_old = [], [], []
for i, f in enumerate(fa, 1):
    k = (f["scenario"], f["fact"], f["target"], f["judge"], f["run"])
    labels.append(f"{i}. {f['fact'][:15]} {f['flex_values'][0]:g}")
    v_new.append(1 if byk[k]["pred"] == "not_stated" else 0)
    v_old.append(1 if byk0[k]["pred"] == "not_stated" else 0)
yy = np.arange(len(labels))
ax[2].barh(yy + 0.2, v_old, 0.38, color="#9ab", label=f"τ-gulv 0,30: {sum(v_old)}/13 OK")
ax[2].barh(yy - 0.2, v_new, 0.38, color="#1f4e79", label=f"τ-grid utvidet: {sum(v_new)}/13 OK")
ax[2].set_yticks(yy); ax[2].set_yticklabels(labels, fontsize=6.5)
ax[2].set_xlim(0, 1.15); ax[2].set_xticks([0, 1]); ax[2].set_xticklabels(["anklager\nfortsatt", "not_stated\n(riktig)"], fontsize=7)
ax[2].set_title("De 13 kjente falske anklagene\nkriteriet tillater maks 3 feil", fontsize=9)
ax[2].legend(fontsize=7, loc="lower right"); ax[2].grid(alpha=0.25, axis="x")
ax[2].invert_yaxis()

fig.tight_layout(); fig.savefig(os.path.join(F, "p3_resultat.png"), dpi=150); plt.close(fig)
print("figur: figs/p3_resultat.png")
