"""Frosne NB-BERT-representasjoner for «[faktabeskrivelse] [SEP] [setning]».
Alle 13 lag, mean-pool (som p1). Batchet pa MPS. float16 i cache.
"""
import json, os, sys, time
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "NbAiLab/nb-bert-base"
BATCH = 64
MAXLEN = 192


def main(limit=None):
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "data", "sentences.jsonl"))]
    if limit:
        rows = rows[:limit]
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, output_hidden_states=True).to(dev).eval()
    print(f"n={len(rows)}  enhet={dev}  batch={BATCH}", flush=True)

    out = np.empty((len(rows), 13, 768), dtype=np.float16)
    t0 = time.time()
    with torch.no_grad():
        for i in range(0, len(rows), BATCH):
            ch = rows[i:i + BATCH]
            enc = tok([r["fact_desc"] for r in ch], [r["sentence"] for r in ch],
                      return_tensors="pt", padding=True, truncation=True,
                      max_length=MAXLEN).to(dev)
            hs = model(**enc).hidden_states           # 13 x (B, T, 768)
            mask = enc["attention_mask"].unsqueeze(-1).float()
            dn = mask.sum(1)
            pooled = torch.stack([(h * mask).sum(1) / dn for h in hs], 1)  # (B,13,768)
            out[i:i + len(ch)] = pooled.cpu().numpy().astype(np.float16)
            if (i // BATCH) % 20 == 0 or i + BATCH >= len(rows):
                done = min(i + BATCH, len(rows))
                el = time.time() - t0
                print(f"  {done}/{len(rows)}  {el:.0f}s  "
                      f"(est. totalt {el/done*len(rows)/60:.1f} min)", flush=True)
    p = os.path.join(ROOT, "results", "cache", "sent_repr.npz")
    np.savez(p, mean=out)
    print(f"skrevet {p}  ({os.path.getsize(p)/1e6:.0f} MB, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
