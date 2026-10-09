"""Verify that no hei_refusal prompt text, and nothing from which a prompt
could be reconstructed, is present in this repository.

hei_refusal is SimulaMet's pack of 47 Norwegian prompts on adolescent health.
It was used as a TEST SET in fase 1 and fase 1b and is deliberately not
deposited. This script is what produced the exclusion table in the README,
and it is included so the table can be rechecked rather than taken on trust.

It needs the withheld file, so only someone holding that file can run it:

    python -I src/exclusion_check.py /path/to/scenarios.jsonl

Why it checks at several window lengths. A five-word window is not unique in
Norwegian. During an earlier scan of the working trees, one everyday five-word
phrase expressing apprehension collided inside an unrelated passage about NAV
meldekort. Counting hits alone would call that a leak. What matters is whether
any prompt is RECOVERABLE, so the script also reports, per prompt, the share of
its windows that appear anywhere in the repository.

The colliding phrase is deliberately NOT quoted here. Writing it down would put
a fragment of the withheld data into the very repository this script certifies,
and the script would then fail on its own documentation — which is exactly what
happened on the first run.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW_SIZES = (5, 6, 7, 8)


def windows(text: str, n: int) -> set:
    w = re.findall(r"\w+", (text or "").lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def main(src: str) -> int:
    rows = [json.loads(l) for l in open(src, encoding="utf-8") if l.strip()]
    sha = hashlib.sha256(open(src, "rb").read()).hexdigest()
    print(f"withheld file: {src}")
    print(f"sha256:        {sha}")
    print(f"prompts:       {len(rows)}")

    files = [p for p in glob.glob(f"{ROOT}/**/*", recursive=True)
             if os.path.isfile(p) and "/.git/" not in p]
    text = "\n".join(open(p, encoding="utf-8", errors="ignore").read().lower()
                     for p in files)
    print(f"files scanned: {len(files)}\n")

    failed = False
    for n in WINDOW_SIZES:
        wins = set()
        for r in rows:
            wins |= windows(r["prompt"], n)
        hits = sorted(w for w in wins if w in text)
        print(f"  {n}-word windows: {len(wins):5d} unique -> {len(hits)} hit(s)"
              + (f"  {hits}" if hits else ""))
        if hits:
            failed = True

    worst = 0.0
    for r in rows:
        w = windows(r["prompt"], 5)
        if w:
            worst = max(worst, sum(1 for x in w if x in text) / len(w))
    print(f"\n  largest share of any single prompt recoverable: {worst:.1%}")
    if worst > 0:
        failed = True

    data_hits = [p for p in files if "/data/" in p and "hei_refusal" in
                 open(p, encoding="utf-8", errors="ignore").read().lower()]
    print(f"  hei_refusal content under data/: {len(data_hits)} file(s)")
    if data_hits:
        failed = True

    print("\n" + ("FAILED — do not deposit" if failed else "CLEAN"))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("usage: python -I src/exclusion_check.py <path to scenarios.jsonl>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
