"""Hent frosne representasjoner fra NB-BERT-base: alle lag, mean-pool og [CLS].

Ingen finjustering, ingen gradient. Skriver en .npz til results/cache/.
Ingen prompttekst til stdout.
"""
import json, os, sys, time
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

MODEL = "NbAiLab/nb-bert-base"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "scenarios.jsonl")
OUT = os.path.join(ROOT, "results", "cache", "bert_repr.npz")


def load_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    t0 = time.time()
    rows = load_rows(DATA)
    labels = np.array([1 if r["expected_outcome"] == "refuse" else 0 for r in rows], dtype=np.int64)
    ids = [r["id"] for r in rows]
    print(f"n={len(rows)}  refuse={int(labels.sum())}  answer={int((1-labels).sum())}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, output_hidden_states=True)
    model.eval()
    print(f"lastet {MODEL}: {sum(p.numel() for p in model.parameters())/1e6:.0f}M param", flush=True)

    mean_layers, cls_layers = [], []
    with torch.no_grad():
        for r in rows:
            enc = tok(r["prompt"], return_tensors="pt", truncation=True, max_length=512)
            out = model(**enc)
            hs = out.hidden_states  # tuple (n_layers+1) av (1, T, H)
            mask = enc["attention_mask"][0].unsqueeze(-1).float()  # (T,1)
            denom = mask.sum()
            mean_layers.append(
                np.stack([((h[0] * mask).sum(0) / denom).numpy() for h in hs])
            )
            cls_layers.append(np.stack([h[0, 0].numpy() for h in hs]))

    mean_arr = np.stack(mean_layers)  # (n, L, H)
    cls_arr = np.stack(cls_layers)
    print(f"mean-pool {mean_arr.shape}  cls {cls_arr.shape}  ({time.time()-t0:.1f}s)", flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, mean=mean_arr, cls=cls_arr, labels=labels, ids=np.array(ids, dtype=object))
    print(f"skrevet {OUT}  ({os.path.getsize(OUT)/1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
