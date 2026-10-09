import json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "results", "eval.json")))
R = d["results"]
F = os.path.join(ROOT, "figs"); os.makedirs(F, exist_ok=True)

order = ["p3 (probe, ingen filtre)", "probe + F1", "probe + F1F2", "probe + F1F2F3",
         "regex (ingen filtre)", "regex + F1", "regex + F1F2", "regex + F1F2F3"]
short = ["p3\nprobe", "probe\n+F1", "probe\n+F1F2", "probe\n+F1F2F3",
         "regex", "regex\n+F1", "regex\n+F1F2", "regex\n+F1F2F3"]
cols = ["#888", "#6a8caf", "#1f4e79", "#9ab", "#d9c08a", "#c9a227", "#8a6d1f", "#ddd0a0"]

fig, ax = plt.subplots(1, 2, figsize=(13.5, 4.6))

# --- presisjon ---
x = np.arange(len(order))
vals = [R[k]["precision"] for k in order]
ax[0].bar(x, vals, color=cols)
for i, v in enumerate(vals):
    ax[0].annotate(f"{v:.3f}", (i, v + 0.004), ha="center", fontsize=8)
ax[0].axhline(0.90, ls="--", c="#b00", lw=1.4)
ax[0].annotate("«virker» ≥ 0,90", (-0.45, 0.906), fontsize=7.5, color="#b00")
ax[0].axhline(0.8673, ls=":", c="#c9a227", lw=1.5)
ax[0].annotate("regex uten filtre 0,867", (-0.45, 0.8705), fontsize=7.5, color="#8a6d1f")
ax[0].set_xticks(x); ax[0].set_xticklabels(short, fontsize=7)
ax[0].set_ylim(0.80, 0.93); ax[0].set_ylabel("par-presisjon (4-klasse)")
ax[0].set_title("Presisjon: ingen forskjell er skillbar fra støy\n"
                "(McNemar p = 0,22–1,00) — unntatt at F3 skader (p = 0,002)",
                fontsize=9.5)
ax[0].grid(alpha=0.25, axis="y")

# --- fellene ---
t = [R[k]["traps_fixed"] for k in order]
ax[1].bar(x, t, color=cols)
for i, v in enumerate(t):
    ax[1].annotate(f"{v}/13", (i, v + 0.25), ha="center", fontsize=8.5,
                   weight="bold" if v == 13 else "normal")
ax[1].axhline(10, ls="--", c="#b00", lw=1.4)
ax[1].annotate("kriteriet: ≤ 3 overlever, dvs. ≥ 10 fikset", (-0.45, 10.25),
               fontsize=7.5, color="#b00")
ax[1].set_xticks(x); ax[1].set_xticklabels(short, fontsize=7)
ax[1].set_ylim(0, 14.6); ax[1].set_ylabel("falske anklager fikset (av 13)")
ax[1].set_title("Fellene: 0–1 → 13 av 13.\nF1 tar 11, F2 tar de to telefonfragmentene.",
                fontsize=9.5)
ax[1].grid(alpha=0.25, axis="y")

fig.tight_layout(); fig.savefig(os.path.join(F, "p3c_resultat.png"), dpi=150)
print("figur: figs/p3c_resultat.png")
