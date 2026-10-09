"""Hovedtabell, figurer og kriterievurdering. Ingen prompttekst beroeres."""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import N_BINS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")
F = os.path.join(ROOT, "figs")
PRIOR = {"auroc": 0.47126436781609193, "ci": [0.289272030651341, 0.657088122605364],
         "ece_cal": 0.13761550936776892, "brier_cal": 0.25678224669713956}


def reliability(ax, p, y, title, n_bins=N_BINS):
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    xs, ys, ns = [], [], []
    for b in range(n_bins):
        m = idx == b
        if m.any():
            xs.append(p[m].mean()); ys.append(y[m].mean()); ns.append(int(m.sum()))
    ax.plot([0, 1], [0, 1], "--", color="#999", lw=1, label="perfekt")
    ax.plot(xs, ys, "o-", color="#1f4e79", lw=1.6, ms=5, label="observert")
    for x, yy, n in zip(xs, ys, ns):
        ax.annotate(str(n), (x, yy), textcoords="offset points", xytext=(4, 5), fontsize=7, color="#555")
    ax.set_xlim(-0.02, 1.02); ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("predikert p(refuse)"); ax.set_ylabel("observert andel refuse")
    ax.set_title(title, fontsize=9)
    ax.legend(fontsize=7, loc="upper left"); ax.grid(alpha=0.25)


def main():
    ms = json.load(open(os.path.join(R, "main_summary.json")))
    mp = json.load(open(os.path.join(R, "main_preds.json")))
    cv = json.load(open(os.path.join(R, "curve.json")))
    cl = json.load(open(os.path.join(R, "curve_loo_30_vs_47.json")))
    tr = json.load(open(os.path.join(R, "transfer.json")))
    os.makedirs(F, exist_ok=True)

    backbones = [k for k in ms if k != "baseline/majoritet"]

    # --- reliability-diagram per backbone (for og etter kalibrering) ---
    for tag in backbones:
        fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.9))
        reliability(axes[0], mp[tag]["raw_p"], mp[tag]["y"],
                    f"{tag}\nfor kalibrering - ECE {ms[tag]['ece_raw']:.3f}")
        reliability(axes[1], mp[tag]["cal_p"], mp[tag]["y"],
                    f"{tag}\netter kalibrering - ECE {ms[tag]['ece_cal']:.3f} "
                    f"(stoygulv {ms[tag]['ece_noise_floor_median']:.3f})")
        fig.suptitle(f"Reliability, LOO paa n=47 - {tag}", fontsize=10)
        fig.tight_layout()
        p = os.path.join(F, "reliability_" + tag.replace("/", "_") + ".png")
        fig.savefig(p, dpi=150); plt.close(fig)
        print("figur:", os.path.relpath(p, ROOT))

    # --- laeringskurve ---
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    cols = {"nb-bert-base/mean": "#1f4e79", "nb-bert-base/cls": "#c0504d",
            "nb-llama-3.1-8b/ollama-embed": "#4f8a3d"}
    for tag in backbones:
        pts = cv[tag]
        ho = [q for q in pts if q.get("n_splits_used")]
        x = [q["n_train"] for q in ho]; ymean = [q["auroc_mean"] for q in ho]
        sd = [q["auroc_sd"] for q in ho]
        axes[0].errorbar(x, ymean, yerr=sd, marker="o", capsize=3, lw=1.6,
                         color=cols.get(tag), label=tag)
        axes[0].scatter([47], [ms[tag]["auroc"]], marker="s", s=55,
                        facecolors="none", edgecolors=cols.get(tag), zorder=5)
    axes[0].axhline(0.8, ls=":", c="#777", lw=1)
    axes[0].axhline(PRIOR["auroc"], ls="--", c="#b00", lw=1)
    axes[0].annotate("bokstavavlesning 0,471", (10.5, PRIOR["auroc"] + 0.012), fontsize=7, color="#b00")
    axes[0].annotate("0,80", (46.2, 0.812), fontsize=7, color="#777")
    axes[0].set_xlabel("treningseksempler"); axes[0].set_ylabel("AUROC")
    axes[0].set_title("Laeringskurve (PREREG): 10/20/30 = hold-out,\n47 = LOO (apen firkant) - ULIKE protokoller", fontsize=9)
    axes[0].legend(fontsize=7, loc="lower right"); axes[0].grid(alpha=0.25); axes[0].set_ylim(0.4, 1.02)

    w = 0.26
    for i, tag in enumerate(backbones):
        r = cl[tag]
        axes[1].bar(i - w/2, r["n_30_loo_mean"], w, yerr=r["n_30_loo_sd"], capsize=3,
                    color=cols.get(tag), alpha=0.45, hatch="//", edgecolor="white")
        axes[1].bar(i + w/2, r["n_47_loo"], w, color=cols.get(tag))
        axes[1].annotate(f"{r['delta_30_to_47']:+.3f}", (i, max(r['n_30_loo_mean'], r['n_47_loo']) + 0.045),
                         ha="center", fontsize=8)
    axes[1].axhline(0.8, ls=":", c="#777", lw=1)
    axes[1].set_xticks(range(len(backbones)))
    axes[1].set_xticklabels([t.split("/")[0] + "\n" + t.split("/")[1] for t in backbones], fontsize=7)
    axes[1].set_ylabel("AUROC"); axes[1].set_ylim(0.4, 1.02)
    axes[1].set_title("POST-PREREG: 30 og 47 maalt med SAMME protokoll (LOO)", fontsize=9)
    from matplotlib.patches import Patch
    axes[1].legend(handles=[Patch(facecolor="#888", alpha=0.45, hatch="//", edgecolor="white", label="n=30 (LOO, snitt av 5)"),
                            Patch(facecolor="#888", label="n=47 (LOO)")],
                   fontsize=7, loc="lower right")
    axes[1].grid(alpha=0.25, axis="y")
    fig.tight_layout()
    p = os.path.join(F, "laeringskurve.png"); fig.savefig(p, dpi=150); plt.close(fig)
    print("figur:", os.path.relpath(p, ROOT))

    # --- transfer ---
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for tag in backbones:
        if tag not in tr:
            continue
        pts = tr[tag]["curve"]
        x = [q["n_train_generated"] for q in pts] + [tr[tag]["n_train_generated"]]
        ym = [q["auroc_mean"] for q in pts] + [tr[tag]["auroc"]]
        sd = [q["auroc_sd"] for q in pts] + [0]
        axes[0].errorbar(x, ym, yerr=sd, marker="o", capsize=3, lw=1.6,
                         color=cols.get(tag), label=tag)
    axes[0].axhline(0.5, ls="--", c="#777", lw=1)
    axes[0].annotate("tilfeldig 0,50", (55, 0.513), fontsize=7, color="#777")
    axes[0].set_xlabel("genererte treningseksempler"); axes[0].set_ylabel("AUROC paa de 47")
    axes[0].set_title("Transfer: tren paa generert, test paa de 47\n(eget eksperiment, ikke blandet inn)", fontsize=9)
    axes[0].legend(fontsize=7, loc="lower left"); axes[0].grid(alpha=0.25); axes[0].set_ylim(0.35, 1.0)

    labs, inn, out = [], [], []
    for tag in backbones:
        if tag not in tr:
            continue
        labs.append(tag.split("/")[0] + "\n" + tag.split("/")[1])
        inn.append(ms[tag]["auroc"]); out.append(tr[tag]["auroc"])
    xi = np.arange(len(labs))
    axes[1].bar(xi - 0.2, inn, 0.4, color="#1f4e79", label="trent paa de 47 (LOO)")
    axes[1].bar(xi + 0.2, out, 0.4, color="#c9a227", label="trent paa generert")
    axes[1].axhline(0.5, ls="--", c="#777", lw=1)
    axes[1].axhline(PRIOR["auroc"], ls="--", c="#b00", lw=1)
    axes[1].set_xticks(xi); axes[1].set_xticklabels(labs, fontsize=7)
    axes[1].set_ylabel("AUROC paa de 47"); axes[1].set_ylim(0.35, 1.0)
    axes[1].set_title("Samme testsett, to treningskilder", fontsize=9)
    axes[1].legend(fontsize=7, loc="lower right"); axes[1].grid(alpha=0.25, axis="y")
    fig.tight_layout()
    p = os.path.join(F, "transfer.png"); fig.savefig(p, dpi=150); plt.close(fig)
    print("figur:", os.path.relpath(p, ROOT))

    # --- kriterievurdering ---
    best = max(backbones, key=lambda t: ms[t]["auroc"])
    b = ms[best]
    lo, hi = b["auroc_ci"]
    c_virker = {
        "auroc_ge_080": b["auroc"] >= 0.80,
        "lower_bound_gt_070": lo > 0.70,
        "ece_le_010": b["ece_cal"] <= 0.10,
    }
    stiger = cl[best]["delta_30_to_47"] > 0
    c_trenger = {"ci_krysser_080": lo <= 0.80 <= hi, "kurven_stiger_30_til_47": bool(stiger)}
    c_blindvei = {"ci_inneholder_060": lo <= 0.60 <= hi,
                  "kurven_flat": not stiger}
    verdicts = {
        "metoden virker": all(c_virker.values()),
        "trenger data": all(c_trenger.values()),
        "blindvei": all(c_blindvei.values()),
    }
    hit = [k for k, v in verdicts.items() if v]
    konklusjon = hit[0] if len(hit) == 1 else ("uavklart" if not hit else "+".join(hit))

    crit = {
        "beste_backbone": best, "auroc": b["auroc"], "auroc_ci": [lo, hi],
        "ece_cal": b["ece_cal"], "ece_noise_floor_median": b["ece_noise_floor_median"],
        "kriterium_metoden_virker": c_virker,
        "kriterium_trenger_data": c_trenger,
        "kriterium_blindvei": c_blindvei,
        "oppfylte": verdicts, "konklusjon": konklusjon,
        "merknad_ece_kriteriet": (
            "ECE-kravet <= 0,10 ligger UNDER stoygulvet ved n=47 for alle tre "
            f"backbones (gulv {min(ms[t]['ece_noise_floor_median'] for t in backbones):.3f}-"
            f"{max(ms[t]['ece_noise_floor_median'] for t in backbones):.3f}). En perfekt "
            "kalibrert modell ville i forventning ikke klart kravet ved denne n. "
            "Kriteriet var dermed ikke oppnaaelig av konstruksjonsgrunner - fort som "
            "designfeil i PREREG, ikke brukt til aa omdefinere konklusjonen."),
        "delta_30_til_47_sammenlignbart": {t: cl[t]["delta_30_to_47"] for t in backbones},
    }
    json.dump(crit, open(os.path.join(R, "criteria.json"), "w"), indent=1, ensure_ascii=False)

    print("\n=== HOVEDTABELL ===")
    hdr = f"{'backbone/pooling':34s} {'AUROC':>6s} {'95 % KI':>16s} {'ECE for':>8s} {'ECE etter':>10s} {'gulv':>6s} {'Brier':>6s} {'beste lag':>12s}"
    print(hdr); print("-" * len(hdr))
    for tag in backbones:
        v = ms[tag]
        print(f"{tag:34s} {v['auroc']:6.3f} [{v['auroc_ci'][0]:.3f}; {v['auroc_ci'][1]:.3f}] "
              f"{v['ece_raw']:8.3f} {v['ece_cal']:10.3f} {v['ece_noise_floor_median']:6.3f} "
              f"{v['brier_cal']:6.3f} {v.get('layer_modal','-'):>12s}")
    mv = ms["baseline/majoritet"]
    print(f"{'baseline/majoritet':34s} {mv['auroc']:6.3f} {'[0.500; 0.500]':>16s} "
          f"{mv['ece_raw']:8.3f} {mv['ece_cal']:10.3f} {'-':>6s} {mv['brier_cal']:6.3f} {'-':>12s}")
    print(f"{'bokstavavlesning (forrige probe)':34s} {PRIOR['auroc']:6.3f} "
          f"[{PRIOR['ci'][0]:.3f}; {PRIOR['ci'][1]:.3f}] {'-':>8s} {PRIOR['ece_cal']:10.3f} "
          f"{'0.105':>6s} {PRIOR['brier_cal']:6.3f} {'-':>12s}")
    print(f"\nKONKLUSJON (per PREREG): {konklusjon.upper()}   [beste backbone: {best}]")
    for k, v in verdicts.items():
        print(f"  {k:16s} {'OPPFYLT' if v else 'ikke oppfylt'}")
    print("skrevet results/criteria.json")


if __name__ == "__main__":
    main()
