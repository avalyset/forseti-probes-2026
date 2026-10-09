"""3b-data: som p3, men hver setning far brukerens prompt som kontekst, og
setninger som gjentar et tall fra prompten merkes «felle».

Gjenbruker p3 i sin helhet: samme svar, samme fakta, samme etikettkriterier
(review.py), samme setningsdeling. Den eneste endringen er inndata og den nye
negative setningsklassen.
"""
import json, os, re, sys
from pathlib import Path

HOME = Path.home()
FC = HOME / "ClaudeWork/decision-probe/factcheck"
P3 = Path("/Volumes/Vault/forseti/p3")
sys.path.insert(0, str(FC))
sys.path.insert(0, str(P3 / "src"))
import extract as E                                    # noqa: E402
from build_data import run_files, answer_of, sentences, fact_description  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAXTOK_PROMPT = 256


def norm(t):
    return re.sub(r"[   ]", "", t or "")


def prompt_values(prompt, fact):
    """Tallverdier brukeren selv innforte, malt med SAMME uttrekker."""
    return {round(v, 6) for v in E.extract(prompt, fact, flexible=True).values}


def main():
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("NbAiLab/nb-bert-base")

    import yaml
    decl = yaml.safe_load((FC / "expected_facts.yaml").read_text())
    facts_by_id = {}
    for sc in decl["scenarios"]:
        facts_by_id[sc["id"]] = {**sc, "facts": [f for f in sc["facts"]
                                                 if f.get("measured", True)]}

    # p3s par og setninger er fasit for hva som skal med - vi legger bare til
    p3_pairs = {r["pair_id"]: r for r in
                (json.loads(l) for l in open(P3 / "data" / "pairs.jsonl"))}
    p3_sents = [json.loads(l) for l in open(P3 / "data" / "sentences.jsonl")]
    by_pair = {}
    for r in p3_sents:
        by_pair.setdefault(r["pair_id"], []).append(r)

    prompts, n_trunc, tok_lens = {}, 0, []
    for path, meta in run_files():
        for res in json.loads(Path(path).read_text()).get("results") or []:
            name = res.get("scenario_name")
            if name not in facts_by_id or not answer_of(res):
                continue
            conv = res.get("conversation") or []
            users = [m.get("content") or "" for m in conv if m.get("role") == "user"]
            aid = f"{name}|{meta['target']}|{meta['judge']}|{meta['run']}"
            prompts[aid] = {"turn0": users[0] if users else "",
                            "all_turns": "\n".join(users)}

    # trunkering: 256 tokens, FRA SLUTTEN (slutten baerer sporsmalet)
    def trunc(text):
        nonlocal n_trunc
        ids = tok(text, add_special_tokens=False)["input_ids"]
        tok_lens.append(len(ids))
        if len(ids) <= MAXTOK_PROMPT:
            return text, False
        n_trunc += 1
        return tok.decode(ids[-MAXTOK_PROMPT:]), True

    out_sents, stats = [], {"felle": 0, "baerer": 0, "ovrig": 0,
                            "baerer_overstyrt_til_felle": 0}
    for pid, rows in by_pair.items():
        p = p3_pairs[pid]
        aid = p["answer_id"]
        fact = next(f for f in facts_by_id[p["scenario"]]["facts"]
                    if f["key"] == p["fact"])
        p0, was_t = trunc(prompts[aid]["turn0"])
        pall, _ = trunc(prompts[aid]["all_turns"])
        pv = prompt_values(prompts[aid]["turn0"], fact)
        pv_all = prompt_values(prompts[aid]["all_turns"], fact)
        for r in rows:
            sv = {round(v, 6) for v in E.extract(r["sentence"], fact, flexible=True).values}
            is_trap = bool(sv & pv)
            is_trap_all = bool(sv & pv_all)
            bearer = bool(r["bearer"])
            if is_trap and bearer:
                stats["baerer_overstyrt_til_felle"] += 1
            # En setning merket felle kan ikke vaere baerer.
            lab = "felle" if is_trap else ("baerer" if bearer else "ovrig")
            stats[lab] += 1
            out_sents.append({
                "pair_id": pid, "answer_id": aid, "scenario": p["scenario"],
                "fact": p["fact"], "sent_idx": r["sent_idx"],
                "sentence": r["sentence"], "fact_desc": r["fact_desc"],
                "prompt_turn0": p0, "prompt_all": pall,
                "prompt_truncated": was_t,
                "bearer_p3": bearer, "is_trap": is_trap, "is_trap_all": is_trap_all,
                "label": lab,
                "bearer": lab == "baerer",
            })

    with open(ROOT / "data" / "sentences.jsonl", "w") as f:
        for r in out_sents:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    import statistics
    n_pairs_trunc = sum(1 for r in out_sents if r["prompt_truncated"])
    uniq_ans = {r["answer_id"] for r in out_sents}
    uniq_trunc = {r["answer_id"] for r in out_sents if r["prompt_truncated"]}
    # tok_lens blander tur 0 og alle-turer; mal tur 0 for seg, det er inndata
    seen = {}
    for r in out_sents:
        seen.setdefault(r["answer_id"], r)
    l0 = [len(tok(r["prompt_turn0"], add_special_tokens=False)["input_ids"])
          for r in seen.values()]
    print(f"setningsrader: {len(out_sents)} (p3 hadde {len(p3_sents)})")
    print(f"\npromptlengde TUR 0 (inndata), tokens: median {statistics.median(l0):.0f}  "
          f"snitt {statistics.mean(l0):.0f}  maks {max(l0)}  over 256: {sum(x > 256 for x in l0)}")
    print(f"TRUNKERT: {len(uniq_trunc)} av {len(uniq_ans)} unike prompter "
          f"({len(uniq_trunc)/len(uniq_ans):.1%}), {n_pairs_trunc} setningsrader")
    print(f"\nsetningsetiketter:")
    tot = len(out_sents)
    for k in ("baerer", "felle", "ovrig"):
        print(f"  {k:8s} {stats[k]:6d}  ({stats[k]/tot:5.1%})")
    print(f"  av fellene var {stats['baerer_overstyrt_til_felle']} merket BAERER i p3 "
          f"- overstyrt, som preregistrert")
    json.dump({"n_sentences": len(out_sents), "stats": stats,
               "n_prompts": len(uniq_ans), "n_truncated": len(uniq_trunc),
               "trunc_share": len(uniq_trunc) / len(uniq_ans),
               "tok_median_turn0": statistics.median(l0), "tok_max_turn0": max(l0),
               "n_over_256_turn0": sum(x > 256 for x in l0)},
              open(ROOT / "results" / "data_stats.json", "w"), indent=1)


if __name__ == "__main__":
    main()
