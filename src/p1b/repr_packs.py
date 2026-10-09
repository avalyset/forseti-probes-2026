"""Frosne representasjoner for de 85 pakkescenariene. Samme uttrekk som fase 1:
NB-BERT alle 13 lag (mean + [CLS]) og nb-llama via ollama-embed.
Logger ogsa tokenlengde, til lengdebaselinen i B-prime.
"""
import json, os, sys, time
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

P1 = "/Volumes/Vault/forseti/p1/src"
sys.path.insert(0, P1)
from repr_ollama import embed  # gjenbruk av fase 1-koden, uendret

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "packs_labeled.jsonl")
MODEL = "NbAiLab/nb-bert-base"


def main():
    rows = [json.loads(l) for l in open(DATA) if l.strip()]
    print(f"n={len(rows)} pakkescenarier", flush=True)
    packs = np.array([r["pack"] for r in rows], dtype=object)
    sids = np.array([r["scenario_id"] for r in rows], dtype=object)

    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, output_hidden_states=True)
    model.eval()
    mean_l, cls_l, ntok = [], [], []
    with torch.no_grad():
        for r in rows:
            enc = tok(r["prompt"], return_tensors="pt", truncation=True, max_length=512)
            ntok.append(int(enc["attention_mask"].sum()))
            hs = model(**enc).hidden_states
            mask = enc["attention_mask"][0].unsqueeze(-1).float()
            dn = mask.sum()
            mean_l.append(np.stack([((h[0] * mask).sum(0) / dn).numpy() for h in hs]))
            cls_l.append(np.stack([h[0, 0].numpy() for h in hs]))
    mean_arr, cls_arr = np.stack(mean_l), np.stack(cls_l)
    print(f"NB-BERT {mean_arr.shape}  ({time.time()-t0:.0f}s)", flush=True)
    np.savez_compressed(os.path.join(ROOT, "results", "cache", "packs_bert.npz"),
                        mean=mean_arr, cls=cls_arr, pack=packs, sid=sids,
                        ntok=np.array(ntok))

    t1 = time.time()
    vecs = []
    for i, r in enumerate(rows, 1):
        vecs.append(embed(r["prompt"]))
        if i % 25 == 0 or i == len(rows):
            print(f"  ollama {i}/{len(rows)}  ({time.time()-t1:.0f}s)", flush=True)
    arr = np.stack(vecs)
    np.savez_compressed(os.path.join(ROOT, "results", "cache", "packs_nbllama.npz"),
                        emb=arr, pack=packs, sid=sids, ntok=np.array(ntok))
    print(f"nb-llama {arr.shape}  ({time.time()-t1:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
