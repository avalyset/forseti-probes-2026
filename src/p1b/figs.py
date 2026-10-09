"""Figurer for fase 1b."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R, F = os.path.join(ROOT, "results"), os.path.join(ROOT, "figs")
os.makedirs(F, exist_ok=True)
COLS = {"nb-bert-base/mean": "#1f4e79", "nb-bert-base/cls": "#c0504d",
        "nb-llama-3.1-8b/ollama-embed": "#4f8a3d"}
FASE1 = {"nb-bert-base/mean": 0.870, "nb-bert-base/cls": 0.866,
         "nb-llama-3.1-8b/ollama-embed": 0.852}

oc = json.load(open(os.path.join(R, "oneclass.json")))
cal = json.load(open(os.path.join(R, "calib.json")))
tags = [t for t in oc["B_prime"]]

# ---------- Figur 1: B-prime ----------
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
for t in tags:
    pl = oc["B_prime"][t]["per_layer"]
    names = [l for l in pl if l.startswith("L")]
    if names:
        xs = sorted(int(l[1:]) for l in names)
        ys = [pl[f"L{i}"]["mahalanobis"]["auroc"] for i in xs]
        ax[0].plot(xs, ys, "o-", lw=1.6, ms=4, color=COLS[t], label=t)
        hl = int(oc["B_prime"][t]["headline_layer"][1:])
        ax[0].scatter([hl], [pl[f"L{hl}"]["mahalanobis"]["auroc"]], s=120,
                      facecolors="none", edgecolors=COLS[t], lw=2, zorder=5)
    else:
        v = pl["last_pooled"]["mahalanobis"]["auroc"]
        ax[0].axhline(v, ls="-.", lw=1.4, color=COLS[t], label=t + " (ett lag)")
ax[0].axhline(0.5, ls="--", c="#777", lw=1)
ax[0].annotate("tilfeldig 0,50", (0.2, 0.513), fontsize=7, color="#777")
ax[0].set_xlabel("NB-BERT-lag"); ax[0].set_ylabel("AUROC på de 47")
ax[0].set_title("B′: énklasse-manifold på pakkene → de 47\n"
                "ring = lag forhåndsvalgt fra fase 1", fontsize=9)
ax[0].legend(fontsize=6.5, loc="upper left"); ax[0].grid(alpha=0.25)
ax[0].set_ylim(0.2, 1.0)

labs, b, f1, errs = [], [], [], [[], []]
for t in tags:
    hl = oc["B_prime"][t]["headline_layer"]
    m = oc["B_prime"][t]["per_layer"][hl]["mahalanobis"]
    labs.append(t.split("/")[0] + "\n" + t.split("/")[1])
    b.append(m["auroc"]); f1.append(FASE1[t])
    errs[0].append(m["auroc"] - m["ci"][0]); errs[1].append(m["ci"][1] - m["auroc"])
x = np.arange(len(labs))
ax[1].bar(x - 0.2, f1, 0.4, color="#999", label="fase 1: trent på de 47 (LOO)")
ax[1].bar(x + 0.2, b, 0.4, yerr=errs, capsize=4, color=[COLS[t] for t in tags],
          label="B′: trent på pakkene, 0 refuse-eksempler")
ax[1].axhline(0.5, ls="--", c="#777", lw=1)
ax[1].set_xticks(x); ax[1].set_xticklabels(labs, fontsize=7)
ax[1].set_ylabel("AUROC på de 47"); ax[1].set_ylim(0.2, 1.0)
ax[1].set_title("Samme testsett. Med og uten refuse-eksempler i treningen.", fontsize=9)
ax[1].legend(fontsize=6.5, loc="upper right"); ax[1].grid(alpha=0.25, axis="y")
fig.tight_layout(); fig.savefig(os.path.join(F, "b_prime.png"), dpi=150); plt.close(fig)
print("figur: figs/b_prime.png")

# ---------- Figur 2: spørsmål C ----------
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
ns = sorted(int(k) for k in cal["C1_gulv_mot_n"])
med = [cal["C1_gulv_mot_n"][str(n)]["gulv_median"] for n in ns]
thr = [cal["C1_gulv_mot_n"][str(n)]["terskel"] for n in ns]
fa = [cal["C1_gulv_mot_n"][str(n)]["falsk_alarm_rate"] for n in ns]
ax[0].plot(ns, med, "o-", color="#1f4e79", lw=1.8, label="ECE-støygulv (median)")
ax[0].plot(ns, thr, "s--", color="#c9a227", lw=1.6, label="terskel = gulv + 0,03")
ax[0].axhline(0.10, ls=":", c="#b00", lw=1.4)
ax[0].annotate("fase 1s absolutte krav ≤ 0,10", (60, 0.104), fontsize=7, color="#b00")
ax[0].set_xscale("log"); ax[0].set_xticks(ns); ax[0].set_xticklabels(ns)
ax[0].set_xlabel("n"); ax[0].set_ylabel("ECE")
ax[0].set_title("C1: ECE-gulvet faller med n.\nUnder gulvet er kravet ingen test.", fontsize=9)
ax[0].legend(fontsize=7); ax[0].grid(alpha=0.25)

ax[1].plot(ns, [v * 100 for v in fa], "o-", color="#7030a0", lw=1.8)
ax[1].axhline(5, ls="--", c="#777", lw=1)
ax[1].annotate("5 %", (520, 6), fontsize=7, color="#777")
for n, v in zip(ns, fa):
    ax[1].annotate(f"{v:.0%}", (n, v * 100 + 1.1), fontsize=7, ha="center")
ax[1].set_xscale("log"); ax[1].set_xticks(ns); ax[1].set_xticklabels(ns)
ax[1].set_xlabel("n"); ax[1].set_ylabel("falsk alarm (%)")
ax[1].set_title("Hvor ofte en PERFEKT kalibrert modell stryker\npå «gulv + 0,03»", fontsize=9)
ax[1].grid(alpha=0.25)
fig.tight_layout(); fig.savefig(os.path.join(F, "sporsmal_c.png"), dpi=150); plt.close(fig)
print("figur: figs/sporsmal_c.png")

# ---------- Figur 3: A-prime, for og etter rettelsen ----------
dfp = os.path.join(R, "domain_fixed.json")
fixed = json.load(open(dfp)) if os.path.exists(dfp) else {}
avail = [t for t in tags if t in fixed]
if avail:
    fig, axes = plt.subplots(1, len(avail), figsize=(5.4 * len(avail), 4.6), squeeze=False)
    for ai, t in enumerate(avail):
        a = axes[0][ai]
        dom = fixed[t]["per_domain"]
        names = sorted(dom, key=lambda p: -dom[p]["ratio"])
        pre = oc["A_prime"][t]["per_domain"]
        xr = np.arange(len(names))
        a.barh(xr + 0.2, [pre[p]["ratio_median"] for p in names], 0.4,
               color="#ccc", label="PREREG (ugyldig): mot avstand i utvalget")
        a.barh(xr - 0.2, [dom[p]["ratio"] for p in names], 0.4, color=COLS[t],
               hatch=["xx" if dom[p]["skiller_seg_ut"] else "" for p in names],
               edgecolor="white", linewidth=0.8,
               label="rettet: mot ut-av-utvalget-referanse")
        a.set_yticks(xr); a.set_yticklabels(names, fontsize=7)
        a.set_xscale("log"); a.axvline(1, ls="--", c="#777", lw=1)
        a.set_xlabel("utholdt median / referansemedian (log)")
        n_pre = sum(pre[p]["skiller_seg_ut"] for p in names)
        n_post = sum(dom[p]["skiller_seg_ut"] for p in names)
        a.set_title(f"A′ {t}\nflagget: {n_pre}/8 før rettelse → {n_post}/8 etter", fontsize=8.5)
        from matplotlib.patches import Patch
        hs = [Patch(facecolor="#ccc", label="PREREG (ugyldig): mot avstand i utvalget"),
              Patch(facecolor=COLS[t], label="rettet: mot ut-av-utvalget-referanse"),
              Patch(facecolor=COLS[t], hatch="xx", edgecolor="white",
                    label="flagget: over p95 av referansen")]
        a.legend(handles=hs, fontsize=6, loc="lower right"); a.grid(alpha=0.25, axis="x")
    fig.tight_layout(); fig.savefig(os.path.join(F, "a_prime_domener.png"), dpi=150)
    plt.close(fig)
    print("figur: figs/a_prime_domener.png")
else:
    print("(domain_fixed.json mangler - A′-figur hoppet over)")
