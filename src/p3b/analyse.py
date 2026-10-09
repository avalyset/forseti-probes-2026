"""3b-analyse: tabell mot p3 og regex, de 13 en for en med skaar,
felle-setningenes fordeling, ECE, ablasjonene, konklusjon ordrett.
"""
import json, os, sys, collections
import numpy as np
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import ece, brier, N_BINS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
P3 = "/Volumes/Vault/forseti/p3"
FLOOR = 0.032          # malt i p3 ved n=324
MARGIN = 0.03
REGEX = None           # regnes fra radene


def load(v):
    p = os.path.join(ROOT, "results", f"probe_{v}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def the13():
    fa = [json.loads(l) for l in open(os.path.join(
        HOME, "ClaudeWork/decision-probe/factcheck/results/review.jsonl"))]
    return [r for r in fa if r["machine_flex"] == "wrong" and r["human"] == "not_stated"]


def key(r):
    return (r["scenario"], r["fact"], r["target"], r["judge"], r["run"])


def main():
    sents = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    p3 = json.load(open(os.path.join(P3, "results", "probe.json")))
    d = load("main")
    if d is None:
        print("hovedkjoringen mangler"); return
    rows = d["rows"]
    regex = sum(r["regex_baseline"] == r["label4"] for r in rows) / len(rows)

    print("=== HOVEDTABELL ===")
    print(f"{'kjoring':38s} {'presisjon':>10s} {'setn-AUROC':>11s}")
    print(f"{'majoritet (alltid ambiguous)':38s} {147/324:10.4f} {'-':>11s}")
    print(f"{'p3: uten prompt':38s} {p3['precision']:10.4f} {p3['sentence_auroc']:11.3f}")
    print(f"{'regex flexible (samme 324)':38s} {regex:10.4f} {'-':>11s}")
    for v, nm in [("abl_a", "3b abl.a: prompt, UTEN felle-etikett"),
                  ("abl_b", "3b abl.b: alle brukerturer"),
                  ("main", "3b HOVEDTALL: tur 0 + felle-etikett")]:
        x = load(v)
        if x:
            print(f"{nm:38s} {x['precision']:10.4f} {x['sentence_auroc']:11.3f}")

    # --- de 13 ---
    fa = the13()
    oof = np.load(os.path.join(ROOT, "results", "cache", "oof_main.npy"))
    by_pair = collections.defaultdict(list)
    for s, sc in zip(sents, oof):
        by_pair[s["pair_id"]].append((sc, s))
    print(f"\n=== DE 13 FELLENE ===")
    print(f"{'#':>3s} {'faktum':18s} {'verdi':>8s} {'tur0':>5s} {'p3':>11s} {'3b':>11s} {'maks skaar':>11s}")
    bymain = {key(r): r for r in rows}
    byp3 = {key(r): r for r in p3["rows"]}
    ok = 0
    detail = []
    for i, f in enumerate(fa, 1):
        k = key(f)
        pid = f"{f['scenario']}|{f['target']}|{f['judge']}|{f['run']}|{f['fact']}"
        lst = by_pair.get(pid, [])
        mx = max((s for s, _ in lst), default=float("nan"))
        trap_sc = [s for s, r in lst if r["is_trap"]]
        in0 = bool(trap_sc)
        pv = bymain[k]["pred"]
        ok += pv == "not_stated"
        detail.append({"n": i, "fact": f["fact"], "value": f["flex_values"][0],
                       "in_turn0": in0, "p3": byp3[k]["pred"], "p3b": pv,
                       "max_score": float(mx),
                       "trap_max": float(max(trap_sc)) if trap_sc else None})
        print(f"{i:3d} {f['fact'][:18]:18s} {f['flex_values'][0]:8g} "
              f"{'ja' if in0 else 'nei':>5s} {byp3[k]['pred']:>11s} {pv:>11s} {mx:11.3f}"
              f"{'  <- OK' if pv == 'not_stated' else ''}")
    print(f"\n  {ok}/13 ble not_stated  (p3: "
          f"{sum(1 for f in fa if byp3[key(f)]['pred'] == 'not_stated')}/13)")

    # --- felle-setninger ---
    traps = np.array([sc for sc, s in zip(oof, sents) if s["is_trap"]])
    bear = np.array([sc for sc, s in zip(oof, sents) if s["bearer"]])
    other = np.array([sc for sc, s in zip(oof, sents)
                      if not s["is_trap"] and not s["bearer"]])
    # p3 males pa SAMME felle-definisjon som 3b. p3-rapportens 0,144 gjaldt en
    # smalere definisjon (setning med tall i et falsk-anklage-par, n=100) og er
    # ikke sammenlignbar med den nye (setning som gjentar en promptverdi, n=262).
    o3 = np.load(os.path.join(P3, "results", "cache", "oof_score.npy"))
    print(f"\n=== SETNINGSSKAARER (ut av utvalget), SAMME definisjon i begge ===")
    print(f"{'gruppe':18s} {'n':>6s}   {'p3 median':>10s} {'>0,5':>7s}   "
          f"{'3b median':>10s} {'>0,5':>7s}")
    grp_stats = {}
    for nm, sel in [("ekte baerere", lambda r: r["bearer"]),
                    ("felle-setninger", lambda r: r["is_trap"]),
                    ("ovrige", lambda r: not r["is_trap"] and not r["bearer"])]:
        idx = [k for k, r in enumerate(sents) if sel(r)]
        a, b = o3[idx], oof[idx]
        grp_stats[nm] = {"n": len(idx), "p3_median": float(np.median(a)),
                         "p3_over_half": float(np.mean(a > 0.5)),
                         "p3b_median": float(np.median(b)),
                         "p3b_over_half": float(np.mean(b > 0.5))}
        print(f"  {nm:16s} {len(idx):6d}   {np.median(a):10.3f} {np.mean(a>0.5):7.1%}   "
              f"{np.median(b):10.3f} {np.mean(b>0.5):7.1%}")
    print("  MERK: fellene la ALLEREDE hoyest i p3 under denne definisjonen.")
    print("  Promptkonteksten snudde ingen rangering - den senket baererne.")

    # --- ECE ---
    print(f"\n=== KALIBRERING (par, binaert stated/not_stated, n=324) ===")
    pr, yb = [], []
    pairs_by_id = {p["pair_id"]: p for p in
                   (json.loads(l) for l in open(os.path.join(P3, "data", "pairs.jsonl")))}
    for pid, lst in by_pair.items():
        pr.append(max(s for s, _ in lst))
        yb.append(0 if pairs_by_id[pid]["label4"] == "not_stated" else 1)
    pr, yb = np.array(pr), np.array(yb)
    e = ece(pr, yb)
    from sklearn.metrics import roc_auc_score
    print(f"  ECE {e:.4f}  gulv {FLOOR:.4f}  terskel {FLOOR+MARGIN:.4f}  "
          f"-> {'BESTATT' if e <= FLOOR+MARGIN else 'ikke bestatt'} ({e-(FLOOR+MARGIN):+.4f})")
    print(f"  (p3: 0.1103, ikke bestatt)   AUROC {roc_auc_score(yb,pr):.3f}  "
          f"Brier {brier(pr,yb):.4f}")

    # --- konklusjon ---
    prec = d["precision"]
    virker = prec >= 0.90 and (13 - ok) <= 3
    bedre = prec > regex or (13 - ok) <= 6
    konk = "virker" if virker else ("bedre, ikke nok" if bedre else "virker ikke")
    print(f"\n=== KRITERIUM ===")
    print(f"  presisjon {prec:.4f}  (>= 0,90? {prec>=0.90})   "
          f"(> regex {regex:.4f}? {prec>regex})")
    print(f"  feller som overlever: {13-ok}  (<= 3? {13-ok<=3})  (<= 6? {13-ok<=6})")
    print(f"\n  KONKLUSJON, ordrett: «{konk}»")
    json.dump({"precision": prec, "regex": regex, "p3": p3["precision"],
               "survived": 13 - ok, "fixed": ok, "the13": detail,
               "ece": e, "floor": FLOOR, "ece_pass": bool(e <= FLOOR + MARGIN),
               "sentence_groups_same_definition": grp_stats,
               "conclusion": konk,
               "abl_a": (load("abl_a") or {}).get("precision"),
               "abl_b": (load("abl_b") or {}).get("precision")},
              open(os.path.join(ROOT, "results", "summary.json"), "w"),
              indent=1, ensure_ascii=False)
    print("\nskrevet results/summary.json")


if __name__ == "__main__":
    main()
