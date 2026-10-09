"""Hent frosne embeddings fra nb-llama-3.1-8b via ollama.

Begrensning: ollamas /api/embed gir ÉN vektor per input (siste lag, pooled).
Per-lag hidden states er ikke tilgjengelige gjennom dette grensesnittet, så
lagvalg er ikke mulig for denne backbonen. Det føres i rapporten.

Ingen prompttekst til stdout.
"""
import json, os, sys, time, urllib.request
import numpy as np

MODEL = "nb-llama-3.1-8b:latest"
URL = "http://localhost:11434/api/embed"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "scenarios.jsonl")
OUT = os.path.join(ROOT, "results", "cache", "nbllama_repr.npz")


def embed(text, retries=3):
    body = json.dumps({"model": MODEL, "input": text}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                d = json.loads(resp.read())
            embs = d.get("embeddings")
            if not embs:
                raise RuntimeError("tomt embeddings-felt")
            return np.asarray(embs[0], dtype=np.float32)
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"embed feilet etter {retries} forsøk: {last}")


def main():
    t0 = time.time()
    rows = [json.loads(l) for l in open(DATA) if l.strip()]
    labels = np.array([1 if r["expected_outcome"] == "refuse" else 0 for r in rows], dtype=np.int64)
    vecs = []
    for i, r in enumerate(rows, 1):
        vecs.append(embed(r["prompt"]))
        if i % 10 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)}  ({time.time()-t0:.0f}s)", flush=True)
    arr = np.stack(vecs)
    print(f"nb-llama embeddings {arr.shape}  ({time.time()-t0:.1f}s)", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savez_compressed(OUT, emb=arr, labels=labels,
                        ids=np.array([r["id"] for r in rows], dtype=object))
    print(f"skrevet {OUT}  ({os.path.getsize(OUT)/1e6:.1f} MB)", flush=True)


if __name__ == "__main__":
    main()
