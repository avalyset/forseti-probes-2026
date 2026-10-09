"""Representasjoner for den genererte mengden: NB-BERT (alle lag, begge pooling)
+ nb-llama via ollama. Samme frosne uttrekk som for de 47."""
import json, os, sys, time
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repr_ollama import embed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "generated.jsonl")
MODEL = "NbAiLab/nb-bert-base"


def main():
    rows = [json.loads(l) for l in open(DATA) if l.strip()]
    y = np.array([1 if r["label"] == "refuse" else 0 for r in rows], dtype=np.int64)
    src = np.array([r["source_row_id"] for r in rows], dtype=object)
    print(f"n={len(rows)}  refuse={int(y.sum())}  answer={int((1-y).sum())}", flush=True)

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, output_hidden_states=True)
    model.eval()
    mean_l, cls_l = [], []
    with torch.no_grad():
        for r in rows:
            enc = tok(r["question"], return_tensors="pt", truncation=True, max_length=512)
            hs = model(**enc).hidden_states
            mask = enc["attention_mask"][0].unsqueeze(-1).float()
            dn = mask.sum()
            mean_l.append(np.stack([((h[0] * mask).sum(0) / dn).numpy() for h in hs]))
            cls_l.append(np.stack([h[0, 0].numpy() for h in hs]))
    mean_arr, cls_arr = np.stack(mean_l), np.stack(cls_l)
    print(f"NB-BERT {mean_arr.shape}  ({time.time()-t0:.0f}s)", flush=True)
    np.savez_compressed(os.path.join(ROOT, "results", "cache", "gen_bert_repr.npz"),
                        mean=mean_arr, cls=cls_arr, labels=y, src=src)

    t1 = time.time()
    vecs = []
    for i, r in enumerate(rows, 1):
        vecs.append(embed(r["question"]))
        if i % 50 == 0 or i == len(rows):
            print(f"  ollama {i}/{len(rows)}  ({time.time()-t1:.0f}s)", flush=True)
    arr = np.stack(vecs)
    print(f"nb-llama {arr.shape}  ({time.time()-t1:.0f}s)", flush=True)
    np.savez_compressed(os.path.join(ROOT, "results", "cache", "gen_nbllama_repr.npz"),
                        emb=arr, labels=y, src=src)
    print("ferdig", flush=True)


if __name__ == "__main__":
    main()
