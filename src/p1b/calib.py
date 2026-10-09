"""Spormal C: kan kalibrering males na?

C1: ECE-stoygulv som funksjon av n. Ved hvilken n blir «ECE <= gulv + 0,03» i det
    hele tatt en test som skiller en kalibrert modell fra en ukalibrert?
C2: Fase 1s LOO-prediksjoner skaret om mot 1b-kriteriet ECE_etter <= gulv + 0,03.

Ingen ny kalibrert klassifikator finnes i 1b - ingen toklasse-treningskilde er
tillatt. Det er en grense, ikke et resultat.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import ece, N_BINS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P1R = "/Volumes/Vault/forseti/p1/results"
NS = [47, 85, 132, 200, 500, 1000]
N_SIM = 2000
MARGIN = 0.03
SEED = 20261009


def floor_for(p_profile, n, seed, n_sim=N_SIM):
    """Gulv ved storrelse n: trekk n sannsynligheter fra profilen, anta dem
    perfekt kalibrerte, trekk y ~ Bernoulli(p), mal ECE. Median + p95."""
    rng = np.random.default_rng(seed)
    vals = np.empty(n_sim)
    for i in range(n_sim):
        p = rng.choice(p_profile, size=n, replace=True)
        y = (rng.random(n) < p).astype(float)
        vals[i] = ece(p, y, N_BINS)
    return float(np.median(vals)), float(np.percentile(vals, 95))


def main():
    ms = json.load(open(os.path.join(P1R, "main_summary.json")))
    mp = json.load(open(os.path.join(P1R, "main_preds.json")))
    backbones = [k for k in ms if k != "baseline/majoritet"]
    out = {"C1_gulv_mot_n": {}, "C2_fase1_omskaret": {}, "margin": MARGIN}

    # --- C1: gulvet mot n. Profil = fase 1s beste backbones kalibrerte p-er. ---
    best = max(backbones, key=lambda t: ms[t]["auroc"])
    prof = np.array(mp[best]["cal_p"], dtype=float)
    print(f"=== C1: ECE-stoygulv mot n (profil fra {best}) ===")
    print(f"{'n':>6s} {'gulv (median)':>14s} {'gulv p95':>10s} {'terskel gulv+0,03':>18s}")
    for n in NS:
        med, p95 = floor_for(prof, n, SEED + n)
        out["C1_gulv_mot_n"][str(n)] = {"gulv_median": med, "gulv_p95": p95,
                                        "terskel": med + MARGIN}
        print(f"{n:6d} {med:14.4f} {p95:10.4f} {med+MARGIN:18.4f}")

    # Hvor mye «rom» gir marginen? Andelen av simuleringene som faller over
    # terskelen NAR modellen ER perfekt kalibrert = falsk-alarm-raten til testen.
    print(f"\n=== C1b: falsk alarm ved perfekt kalibrering (andel simuleringer > gulv+{MARGIN}) ===")
    rng = np.random.default_rng(SEED + 7)
    for n in NS:
        med = out["C1_gulv_mot_n"][str(n)]["gulv_median"]
        thr = med + MARGIN
        vals = []
        for _ in range(N_SIM):
            p = rng.choice(prof, size=n, replace=True)
            y = (rng.random(n) < p).astype(float)
            vals.append(ece(p, y, N_BINS))
        fa = float(np.mean(np.array(vals) > thr))
        out["C1_gulv_mot_n"][str(n)]["falsk_alarm_rate"] = fa
        print(f"  n={n:5d}  falsk alarm {fa:6.1%}")

    # --- C2: fase 1 omskaret mot gulv + 0,03 ---
    print(f"\n=== C2: fase 1 (commit 746add9) mot 1b-kriteriet ECE_etter <= gulv + {MARGIN} ===")
    print(f"{'backbone':34s} {'ECE etter':>10s} {'gulv':>8s} {'terskel':>9s} {'margin':>8s}  utfall")
    for tag in backbones:
        v = ms[tag]
        fl = v["ece_noise_floor_median"]
        thr = fl + MARGIN
        ok = v["ece_cal"] <= thr
        out["C2_fase1_omskaret"][tag] = {
            "ece_cal": v["ece_cal"], "gulv": fl, "terskel": thr,
            "over_terskel": v["ece_cal"] - thr, "bestatt": bool(ok),
            "ece_raw": v["ece_raw"],
        }
        print(f"{tag:34s} {v['ece_cal']:10.3f} {fl:8.3f} {thr:9.3f} "
              f"{v['ece_cal']-thr:+8.3f}  {'BESTATT' if ok else 'ikke bestatt'}")
    # til sammenligning: fase 1s eget absolutte krav
    print(f"\n  (fase 1s eget krav var ECE <= 0,10 absolutt - under gulvet "
          f"{min(ms[t]['ece_noise_floor_median'] for t in backbones):.3f}-"
          f"{max(ms[t]['ece_noise_floor_median'] for t in backbones):.3f}, altsa ingen test)")
    json.dump(out, open(os.path.join(ROOT, "results", "calib.json"), "w"), indent=1)
    print("\nskrevet results/calib.json")


if __name__ == "__main__":
    main()
