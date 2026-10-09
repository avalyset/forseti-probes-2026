"""3c-evaluering. Ingen trening: p3s oof-skaarer og tau per fold gjenbrukes.
Filtrene legges pa etter proben; regex-kontrollen far de samme filtrene.
"""
import json, os, sys, collections
import numpy as np

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.join(HOME, "ClaudeWork/decision-probe/factcheck"))
import extract as E                                       # noqa: E402
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import filters as F                                        # noqa: E402
sys.path.insert(0, "/Volumes/Vault/forseti/p1/src")
from probe import ece, brier                               # noqa: E402

P3 = "/Volumes/Vault/forseti/p3"
FLOOR, MARGIN = 0.032, 0.03

CONFIGS = [
    ("p3 (probe, ingen filtre)",      "probe", dict()),
    ("probe + F1",                    "probe", dict(f1=True)),
    ("probe + F1F2",                  "probe", dict(f1=True, f2=True)),
    ("probe + F1F2F3",                "probe", dict(f1=True, f2=True, f3=True)),
    ("probe + F2F3 (F1 av)",          "probe", dict(f2=True, f3=True)),
    ("probe + F1F3 (F2 av)",          "probe", dict(f1=True, f3=True)),
    ("regex (ingen filtre)",          "regex", dict()),
    ("regex + F1",                    "regex", dict(f1=True)),
    ("regex + F1F2",                  "regex", dict(f1=True, f2=True)),
    ("regex + F1F2F3",                "regex", dict(f1=True, f2=True, f3=True)),
]


def load():
    import yaml
    d = json.load(open(os.path.join(P3, "results", "probe.json")))
    sents = [json.loads(l) for l in open(os.path.join(P3, "data", "sentences.jsonl"))]
    pairs = {p["pair_id"]: p for p in
             (json.loads(l) for l in open(os.path.join(P3, "data", "pairs.jsonl")))}
    oof = np.load(os.path.join(P3, "results", "cache", "oof_score.npy"))
    turns = json.load(open(os.path.join(ROOT, "data", "user_turns.json")))
    decl = yaml.safe_load(open(os.path.join(
        HOME, "ClaudeWork/decision-probe/factcheck/expected_facts.yaml")))
    fo = {(sc["id"], f["key"]): f for sc in decl["scenarios"] for f in sc["facts"]}
    tau = {f["scenario"]: f["tau"] for f in d["folds"]}
    by_pair = collections.defaultdict(list)
    for i, s in enumerate(sents):
        by_pair[s["pair_id"]].append(i)
    return d, sents, pairs, oof, turns, fo, tau, by_pair


def run(mode, flags, sents, pairs, oof, turns, fo, tau, by_pair, want_trace=None):
    """Returnerer {pair_id: {verdict, values, flagged, trace}}."""
    out = {}
    for pid, idx in by_pair.items():
        p = pairs[pid]
        fact = fo[(p["scenario"], p["fact"])]
        uv = F.user_values(turns[p["answer_id"]], fact) if flags.get("f1") else None
        exp = float(p["expected"])
        trace = [] if (want_trace and pid in want_trace) else None
        if mode == "probe":
            t = tau[p["scenario"]]
            chosen = [sents[i]["sentence"] for i in idx if oof[i] >= t]
        else:
            # regex over HELE svaret = alle setninger, uten utvalg
            chosen = [sents[i]["sentence"] for i in idx]
        vals = []
        for s in chosen:
            vals += F.values_of_sentence(s, fact, uvals=uv, trace=trace, **flags)
        flagged = bool(flags.get("f1") and uv and round(exp, 6) in uv)
        out[pid] = {"verdict": F.verdict_from(vals, exp),
                    "values": sorted({round(v, 6) for v in vals}),
                    "user_cited_fasit": flagged, "trace": trace}
    return out


def main():
    d, sents, pairs, oof, turns, fo, tau, by_pair = load()
    fa = [json.loads(l) for l in open(os.path.join(
        HOME, "ClaudeWork/decision-probe/factcheck/results/review.jsonl"))]
    fa = [r for r in fa if r["machine_flex"] == "wrong" and r["human"] == "not_stated"]
    fa_pids = [f"{r['scenario']}|{r['target']}|{r['judge']}|{r['run']}|{r['fact']}"
               for r in fa]

    results, the13 = {}, {}
    print(f"{'kjoring':30s} {'presisjon':>10s} {'feller OK':>10s} {'ECE':>8s}")
    print("-" * 62)
    for name, mode, flags in CONFIGS:
        pred = run(mode, flags, sents, pairs, oof, turns, fo, tau, by_pair)
        acc = float(np.mean([pred[p]["verdict"] == pairs[p]["label4"] for p in pred]))
        ok13 = sum(1 for pid in fa_pids if pred[pid]["verdict"] == "not_stated")
        # ECE: proben gir sannsynlighet, regex gjor ikke -> bare for probe
        e = float("nan")
        if mode == "probe":
            pr = np.array([max(oof[i] for i in by_pair[p]) for p in pred])
            yb = np.array([0 if pairs[p]["label4"] == "not_stated" else 1 for p in pred])
            e = ece(pr, yb)
        results[name] = {"precision": acc, "traps_fixed": ok13, "ece": e,
                         "mode": mode, "flags": flags,
                         "n_user_cited": sum(1 for p in pred if pred[p]["user_cited_fasit"])}
        the13[name] = {pid: pred[pid]["verdict"] for pid in fa_pids}
        print(f"{name:30s} {acc:10.4f} {ok13:>7d}/13 "
              f"{(f'{e:.4f}' if e == e else '-'):>8s}")

    json.dump({"results": results, "the13": the13,
               "fa_meta": [{"fact": r["fact"], "value": r["flex_values"][0],
                            "pid": p} for r, p in zip(fa, fa_pids)]},
              open(os.path.join(ROOT, "results", "eval.json"), "w"),
              indent=1, ensure_ascii=False)
    print("\nskrevet results/eval.json")


if __name__ == "__main__":
    main()
