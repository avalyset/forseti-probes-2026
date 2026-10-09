"""Frosne NB-BERT-representasjoner for «[prompt] [SEP] [faktum] [SEP] [setning]».

«[SEP]»-strengen mapper til tokenizerens ekte separator (id 102), sa oppsettet
blir [CLS] prompt [SEP] faktum [SEP] setning [SEP] - tre segmenter, ikke en
tilnaerming.

Varianter:
  turn0   - hovedtall: brukerens tur 0
  allturns- ablasjon (b): alle brukerturer
  nopmt   - p3s inndata, uten prompt (til kontroll av at vi reproduserer p3)
"""
import json, os, sys, time
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "NbAiLab/nb-bert-base"
BATCH = 48
MAXLEN = 256          # hevet fra p3s 192; full inndata er maks 222


def first_segment(r, variant, tok=None):
    """Segment A. For allturns forkortes prompten FRA STARTEN per rad, slik at
    hele setningen og promptens hale faar plass innenfor MAXLEN.

    Uten dette kutter tokenizeren det lengste segmentet fra ENDEN, altsa
    nettopp der sporsmalet staar - malt til 52 % av radene i forste kjoring.
    """
    if variant == "turn0":
        return r["prompt_turn0"] + " [SEP] " + r["fact_desc"]
    if variant == "allturns":
        tail = " [SEP] " + r["fact_desc"]
        if tok is None:
            return r["prompt_all"] + tail
        budget = (MAXLEN - 4
                  - len(tok(r["sentence"], add_special_tokens=False)["input_ids"])
                  - len(tok(tail, add_special_tokens=False)["input_ids"]))
        ids = tok(r["prompt_all"], add_special_tokens=False)["input_ids"]
        if budget < 8:
            budget = 8
        if len(ids) > budget:
            return tok.decode(ids[-budget:]) + tail
        return r["prompt_all"] + tail
    return r["fact_desc"]


def main(variant="turn0", limit=None):
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    if limit:
        rows = rows[:limit]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, output_hidden_states=True).to(dev).eval()
    assert tok.convert_tokens_to_ids("[SEP]") == tok.sep_token_id, "[SEP] er ikke separatoren"
    print(f"variant={variant}  n={len(rows)}  enhet={dev}  maxlen={MAXLEN}", flush=True)

    out = np.empty((len(rows), 13, 768), dtype=np.float16)
    n_trunc = 0
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(rows), BATCH):
            ch = rows[i:i + BATCH]
            a = [first_segment(r, variant, tok) for r in ch]
            b = [r["sentence"] for r in ch]
            raw = tok(a, b, add_special_tokens=True)["input_ids"]
            n_trunc += sum(1 for x in raw if len(x) > MAXLEN)
            enc = tok(a, b, return_tensors="pt", padding=True, truncation=True,
                      max_length=MAXLEN).to(dev)
            hs = model(**enc).hidden_states
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pooled = torch.stack([(h * mask).sum(1) / mask.sum(1) for h in hs], 1)
            out[i:i + len(ch)] = pooled.cpu().numpy().astype(np.float16)
            if (i // BATCH) % 40 == 0 or i + BATCH >= len(rows):
                done = min(i + BATCH, len(rows))
                print(f"  {done}/{len(rows)}  {time.time()-t0:.0f}s", flush=True)
    p = os.path.join(ROOT, "results", "cache", f"sent_{variant}.npz")
    np.savez(p, mean=out)
    print(f"skrevet {p}  ({os.path.getsize(p)/1e6:.0f} MB, {time.time()-t0:.0f}s)  "
          f"kuttet ved maxlen: {n_trunc} rader ({n_trunc/len(rows):.2%})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "turn0",
         int(sys.argv[2]) if len(sys.argv) > 2 else None)
