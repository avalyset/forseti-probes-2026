import json, os, collections
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R, F = os.path.join(ROOT, "results"), os.path.join(ROOT, "figs")
os.makedirs(F, exist_ok=True)
HOME = os.path.expanduser("~")
P3 = "/Volumes/Vault/forseti/p3"
p3 = json.load(open(os.path.join(P3, "results", "probe.json")))
sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]


def L(v):
    p = os.path.join(R, f"probe_{v}.json")
    return json.load(open(p)) if os.path.exists(p) else None


main = L("main")
regex = sum(r["regex_baseline"] == r["label4"] for r in main["rows"]) / len(main["rows"])
fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.5))

# --- 1: presisjon ---
bars = [("majoritet", 147 / 324, "#ccc"),
        ("p3\nhverken", p3["precision"], "#888"),
        ("abl.c\nkun felle-\netikett", (L("abl_c") or {}).get("precision"), "#9ab"),
        ("abl.a\nkun prompt", (L("abl_a") or {}).get("precision"), "#6a8caf"),
        ("abl.b\nalle turer\n+ etikett", (L("abl_b") or {}).get("precision"), "#4f8a3d"),
        ("HOVEDTALL\nbegge", main["precision"], "#c0504d"),
        ("regex", regex, "#c9a227")]
bars = [b for b in bars if b[1] is not None]
x = np.arange(len(bars))
ax[0].bar(x, [b[1] for b in bars], color=[b[2] for b in bars])
for i, b in enumerate(bars):
    ax[0].annotate(f"{b[1]:.3f}", (i, b[1] + 0.008), ha="center", fontsize=8.5)
ax[0].axhline(0.90, ls="--", c="#b00", lw=1.4)
ax[0].annotate("«virker» ≥ 0,90", (-0.45, 0.908), fontsize=7.5, color="#b00")
ax[0].axhline(regex, ls=":", c="#c9a227", lw=1.4)
ax[0].set_xticks(x); ax[0].set_xticklabels([b[0] for b in bars], fontsize=7)
ax[0].set_ylim(0.4, 1.0); ax[0].set_ylabel("presisjon (4-klasse)")
ax[0].set_title("Prompt-kontekst gjør det verre, ikke bedre", fontsize=9.5)
ax[0].grid(alpha=0.25, axis="y")

# --- 2: setningsskårer, p3 vs 3b ---
oof = np.load(os.path.join(R, "cache", "oof_main.npy"))
o3 = np.load(os.path.join(P3, "results", "cache", "oof_score.npy"))
p3s = [json.loads(l) for l in open(os.path.join(P3, "data", "sentences.jsonl"))]
tr3b = [s for s, r in zip(oof, sents) if r["is_trap"]]
be3b = [s for s, r in zip(oof, sents) if r["bearer"]]
# SAMME definisjon i begge: setningen gjentar en promptverdi.
tr3 = [s for s, q in zip(o3, sents) if q["is_trap"]]
be3 = [s for s, q in zip(o3, sents) if q["bearer"]]
pos = [1, 2, 4, 5]
bp = ax[1].boxplot([be3, tr3, be3b, tr3b], positions=pos, widths=0.62,
                   patch_artist=True, showfliers=False, medianprops=dict(color="k", lw=1.6))
for b, c in zip(bp["boxes"], ["#1f4e79", "#c0504d", "#1f4e79", "#c0504d"]):
    b.set_facecolor(c); b.set_alpha(0.65)
ax[1].set_xticks(pos)
ax[1].set_xticklabels(["bærere", "feller", "bærere", "feller"], fontsize=8)
ax[1].annotate("p3 (uten prompt)", (1.5, 1.06), ha="center", fontsize=8.5)
ax[1].annotate("3b (med prompt)", (4.5, 1.06), ha="center", fontsize=8.5)
ax[1].axhline(0.5, ls=":", c="#777", lw=1)
ax[1].set_ylim(-0.03, 1.13); ax[1].set_ylabel("probe-skår per setning")
ax[1].set_title("Fellene lå allerede høyest i p3.\n3b senket bærerne, snudde ingenting.", fontsize=9.5)
ax[1].grid(alpha=0.25, axis="y")

# --- 3: variansdekomponering ---
A = np.load(os.path.join(R, "cache", "sent_turn0.npz"))["mean"][:, 0, :].astype(np.float32)
B = np.load(os.path.join(P3, "results", "cache", "sent_repr.npz"))["mean"][:, 0, :].astype(np.float32)
grp = collections.defaultdict(list)
for i, s in enumerate(sents):
    grp[s["pair_id"]].append(i)


def dec(X):
    gm = X.mean(0); w = b = 0.0
    for ids in grp.values():
        if len(ids) < 2: continue
        sub = X[ids]; m = sub.mean(0)
        w += ((sub - m) ** 2).sum(); b += len(ids) * ((m - gm) ** 2).sum()
    return w / (w + b)


wp3, w3b = dec(B), dec(A)
ax[2].bar([0, 1], [wp3, w3b], color=["#888", "#c0504d"], width=0.55)
ax[2].bar([0, 1], [1 - wp3, 1 - w3b], bottom=[wp3, w3b], color="#ddd", width=0.55)
for i, v in enumerate([wp3, w3b]):
    ax[2].annotate(f"{v:.1%}", (i, v / 2), ha="center", fontsize=11, color="white", weight="bold")
    ax[2].annotate(f"{1-v:.1%}", (i, v + (1 - v) / 2), ha="center", fontsize=10, color="#555")
ax[2].set_xticks([0, 1]); ax[2].set_xticklabels(["p3\nfaktum + setning",
                                                 "3b\nprompt + faktum + setning"], fontsize=8)
ax[2].set_ylim(0, 1.0); ax[2].set_ylabel("andel av total varians")
ax[2].set_title("Mekanismen: den delte prompten fortrenger\nsetningssignalet "
                "(mørkt = innenfor par)", fontsize=9.5)
ax[2].grid(alpha=0.25, axis="y")

fig.tight_layout(); fig.savefig(os.path.join(F, "p3b_resultat.png"), dpi=150)
print("figur: figs/p3b_resultat.png")
