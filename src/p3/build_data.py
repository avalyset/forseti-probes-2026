"""3.1 Data: ekte svar, deklarert fasit, etikett per (svar, faktum) og per setning.

Etikettene kommer fra review.py sine kriterier, som er DETERMINISTISK kode:
    V_claim = uttrukne verdier - felleverdier - telefonfragmenter
    V_claim == {fasit} -> correct ; {} -> not_stated ; {x!=fasit} -> wrong
    |V_claim| >= 2     -> ambiguous
Den opprinnelige runden kjorte dem pa et utvalg pa 233 av 324 (PREREG krevde
alle wrong/ambiguous + 30 tilfeldige). Siden kriteriene er kode, kjores de her
over alle 324.

VIKTIG BEGRENSNING, fort i PREREG: disse etikettene er ikke uavhengige av
regex-uttrekket - de FILTRERER regexens treff. Der regex ikke fant en verdi i
det hele tatt, kan gjennomgangen ikke legge den til. Etikettene arver altsa
regexens recall-svikt, ikke bare presisjonen.

Faktabeskrivelsen som gaar inn i hodet er SIFFER-REDIGERT. Sto fasitverdien i
beskrivelsen, ville oppgaven vaert strengmatching og proben ville laert
ingenting brukbart.
"""
import json, os, re, sys
from pathlib import Path

HOME = Path.home()
FC = HOME / "ClaudeWork/decision-probe/factcheck"
sys.path.insert(0, str(FC))
import extract as E                      # noqa: E402
from review import load_traps, human_verdict   # noqa: E402
import yaml                               # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STABILITY = HOME / "ClaudeWork/nordeval-skills/studies/judge-stability-opus-4.7-4.8/results"
BASELINE = HOME / "ClaudeWork/simpleaudit/results"
SENT_SPLIT = re.compile(r"(?<=[.!?\n])\s+")


def answer_of(result):
    conv = result.get("conversation") or []
    return "\n".join(m.get("content") or "" for m in conv
                     if isinstance(m, dict) and m.get("role") == "assistant"
                     and m.get("content"))


def run_files():
    out = []
    for p in sorted(STABILITY.rglob("run_*.json")):
        m = re.search(r"(opus4[78])/(\w+)/([\w.\-]+)/run_(\d+)\.json$", str(p))
        if m:
            out.append((p, {"judge": m.group(1), "pack": m.group(2),
                            "target": m.group(3), "run": m.group(4)}))
    for p in sorted(BASELINE.glob("skatteetaten_baseline_*_20260429.json")):
        if any(x in p.name for x in ("combined", "judge_robustness", "checklist")):
            continue
        out.append((p, {"judge": None, "pack": "skatteetaten",
                        "target": "sonnet46" if "sonnet46" in p.name else "haiku45",
                        "run": "0"}))
    return out


def redact(text):
    """Fjern hvert siffer fra faktabeskrivelsen. Enheten blir staende."""
    t = re.sub(r"\d[\d  .,]*\d|\d", "⟨TALL⟩", text)
    # tallord som ogsa lekker verdien
    t = re.sub(r"\b(en|ett|to|tre|fire|fem|seks|sju|syv|atte|åtte|ni|ti|elleve|tolv"
               r"|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b",
               "⟨TALL⟩", t, flags=re.I)
    return t


def fact_description(fact):
    """Det hodet faktisk far se om faktumet. Aldri verdien."""
    return f"{fact['key'].replace('_', ' ')} ({fact['type']}): {redact(fact['source_quote'])}"


def sentences(answer):
    return [s.strip() for s in SENT_SPLIT.split(answer) if s.strip()]


def carries(sentence, value, fact):
    """Baerer setningen denne verdien, malt med SAMME uttrekker som runden for?"""
    ex = E.extract(sentence, fact, flexible=True)
    return any(abs(v - value) < 1e-9 for v in ex.values)


def main():
    facts_by_id = {}
    decl = yaml.safe_load((FC / "expected_facts.yaml").read_text())
    n_excl = 0
    for sc in decl["scenarios"]:
        # Samme filter som forrige runde (run.py load_facts): fakta merket
        # measured: False er bevisst ikke malbare. Her gjelder det
        # beregnet_frist_dato, med fasit '1. mai' - en dato, ikke et tall.
        keep = [f for f in sc["facts"] if f.get("measured", True)]
        n_excl += len(sc["facts"]) - len(keep)
        facts_by_id[sc["id"]] = {**sc, "facts": keep}
    print(f"fakta deklarert: {sum(len(sc['facts']) for sc in decl['scenarios'])}, "
          f"utelatt (measured: False): {n_excl}")
    traps = load_traps()

    pairs, sent_rows = [], []
    n_answers = 0
    for path, meta in run_files():
        data = json.loads(path.read_text())
        for res in data.get("results") or []:
            name = res.get("scenario_name")
            if name not in facts_by_id:
                continue
            answer = answer_of(res)
            if not answer:
                continue
            n_answers += 1
            sents = sentences(answer)
            aid = f"{name}|{meta['target']}|{meta['judge']}|{meta['run']}"
            for fact in facts_by_id[name]["facts"]:
                flex = E.extract(answer, fact, flexible=True)
                row = {"scenario": name, "fact": fact["key"],
                       "expected": fact["value"],
                       "flex_values": flex.values, "flex_spans": flex.spans,
                       "sentence": E.sentence_for(answer, flex.spans[0]) if flex.spans else ""}
                verdict, reason = human_verdict(row, traps)
                exp_val = float(next(iter(fact["value"].values())))
                # verdiene gjennomgangen BEHOLDT = de setningsnivaet skal peke pa
                kept = []
                trap_vals = {v for k, v in traps.get(name, [])
                             if k == next(iter(fact["value"].keys()))}
                spans = list(flex.spans) + [""] * (len(flex.values) - len(flex.spans))
                from review import phone_fragment
                for v, sp in zip(flex.values, spans):
                    if v in trap_vals or phone_fragment(sp, row["sentence"] or ""):
                        continue
                    kept.append(v)
                kept = sorted(set(kept))
                pid = f"{aid}|{fact['key']}"
                pairs.append({
                    "pair_id": pid, "answer_id": aid, "scenario": name,
                    "pack": facts_by_id[name]["pack"], "fact": fact["key"],
                    "fact_type": fact["type"], "fact_desc": fact_description(fact),
                    "expected": exp_val, "label4": verdict, "reason": reason,
                    "label_binary": "not_stated" if verdict == "not_stated" else "stated",
                    "kept_values": kept, "severity": res.get("severity"),
                    "target": meta["target"], "judge": meta["judge"], "run": meta["run"],
                    "n_sentences": len(sents), "answer_chars": len(answer),
                    "regex_flex_outcome": E.extract(answer, fact, flexible=True).outcome,
                })
                for si, s in enumerate(sents):
                    lab = any(carries(s, v, fact) for v in kept) if kept else False
                    sent_rows.append({"pair_id": pid, "answer_id": aid, "scenario": name,
                                      "fact": fact["key"], "sent_idx": si, "sentence": s,
                                      "fact_desc": fact_description(fact),
                                      "bearer": bool(lab)})

    (ROOT / "data").mkdir(exist_ok=True)
    with open(ROOT / "data" / "pairs.jsonl", "w") as f:
        for r in pairs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(ROOT / "data" / "sentences.jsonl", "w") as f:
        for r in sent_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    import collections
    print(f"svar lest: {n_answers}   (svar, faktum)-par: {len(pairs)}   "
          f"setningsrader: {len(sent_rows)}")
    print(f"unike scenarier: {len({p['scenario'] for p in pairs})}   "
          f"unike fakta: {len({p['fact'] for p in pairs})}   "
          f"unike svar: {len({p['answer_id'] for p in pairs})}")
    print(f"\n4-klasse: {dict(collections.Counter(p['label4'] for p in pairs))}")
    print(f"binaer:   {dict(collections.Counter(p['label_binary'] for p in pairs))}")
    ns = [p["n_sentences"] for p in pairs]
    import statistics
    print(f"\nsetninger per svar: median {statistics.median(ns):.0f}  "
          f"snitt {statistics.mean(ns):.1f}  spenn {min(ns)}-{max(ns)}")
    nb = sum(r["bearer"] for r in sent_rows)
    print(f"setningsetiketter: {nb} baerer ({nb/len(sent_rows):.1%}), "
          f"{len(sent_rows)-nb} baerer ikke")
    # LEKKASJEREVISJON: star fasitverdien i faktabeskrivelsen?
    leaks = []
    for p in pairs:
        ev = p["expected"]
        for form in {str(int(ev)) if ev == int(ev) else None, str(ev),
                     f"{int(ev):,}".replace(",", " ") if ev == int(ev) else None}:
            if form and form in p["fact_desc"]:
                leaks.append((p["fact"], form, p["fact_desc"][:70]))
    print(f"\nLEKKASJEREVISJON faktabeskrivelse -> fasitverdi: "
          f"{len(set(leaks))} treff" + (f" {sorted(set(leaks))[:3]}" if leaks else " (ren)"))


if __name__ == "__main__":
    main()
