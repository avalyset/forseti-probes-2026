"""Tokenlengde for de 47 hei_refusal-promptene. Ingen prompttekst lagres."""
import json, os
import numpy as np
from transformers import AutoTokenizer
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "/Volumes/Vault/forseti/p1/data/scenarios.jsonl"
tok = AutoTokenizer.from_pretrained("NbAiLab/nb-bert-base")
rows = [json.loads(l) for l in open(SRC) if l.strip()]
n = [int(tok(r["prompt"], truncation=True, max_length=512, return_tensors="pt")["attention_mask"].sum())
     for r in rows]
y = [1 if r["expected_outcome"] == "refuse" else 0 for r in rows]
np.savez(os.path.join(ROOT, "results", "cache", "tok47.npz"),
         ntok=np.array(n), labels=np.array(y))
print(f"47 tokenlengder: median {np.median(n):.0f}, spenn {min(n)}-{max(n)}")
