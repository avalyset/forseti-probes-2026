"""Les Lovtidend-kunngjoringer og trekk ut hvilke paragrafer de endrer.

To niva av presisjon, og forskjellen er viktig:

  data-change-part  - paragrafniva: «lov/2005-06-17-62/§15-6/ledd/3».
                      Lovdata begynte med dette i 2023. Dette er det vi vil ha.
  changesToDocuments - dokumentniva: «forskrift/2007-06-28-814». Finnes i alle
                      ar. Grovere: sier AT dokumentet er endret, ikke hvor.

Begge rapporteres. En kunngjoring uten change-part er ikke en kunngjoring uten
endring - den er en vi bare kjenner pa dokumentniva.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tarfile
from typing import Any, Dict, Iterator, List

LOVDATA = "/Volumes/Vault/forseti/lovdata"
CHANGE_PART = re.compile(r'data-change-part="([^"]+)"')
LEGACY = re.compile(r'<dd class="legacyID">([^<]+)</dd>')
DOKID = re.compile(r'<dd class="dokid">([^<]+)</dd>')
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
INFORCE = re.compile(r'<dd class="dateInForce">([^<]+)</dd>')
CHANGES_BLOCK = re.compile(r'<dd class="changesToDocuments">(.*?)</dd>', re.S)
LI = re.compile(r"<li>(.*?)</li>", re.S)
TAG = re.compile(r"<[^>]+>")


def _text(s):
    return TAG.sub("", s or "").strip()


def iter_docs(archives: List[str], years=None) -> Iterator[Dict[str, Any]]:
    for arc in archives:
        with tarfile.open(arc, "r:bz2") as tf:
            for m in tf:
                if not m.isfile() or not m.name.endswith(".xml"):
                    continue
                if years and not any(f"/{y}/" in m.name for y in years):
                    continue
                fh = tf.extractfile(m)
                if fh is None:
                    continue
                yield m.name, fh.read().decode("utf-8", "replace")


def parse_doc(name: str, raw: str) -> Dict[str, Any]:
    parts = []
    for p in CHANGE_PART.findall(raw):
        seg = p.split("/")
        doc = "/".join(seg[:2]) if len(seg) >= 2 else p
        para = next((s for s in seg if s.startswith("§")), None)
        ledd = None
        if "ledd" in seg:
            i = seg.index("ledd")
            if i + 1 < len(seg):
                ledd = seg[i + 1]
        parts.append({"raw": p, "document": doc, "paragraph": para, "ledd": ledd})
    cb = CHANGES_BLOCK.search(raw)
    changes_doc = [_text(x) for x in LI.findall(cb.group(1))] if cb else []
    return {
        "file": name,
        "legacy_id": (LEGACY.search(raw).group(1).strip() if LEGACY.search(raw) else None),
        "dokid": (DOKID.search(raw).group(1).strip() if DOKID.search(raw) else None),
        "title": _text(TITLE.search(raw).group(1)) if TITLE.search(raw) else None,
        "in_force": (INFORCE.search(raw).group(1).strip() if INFORCE.search(raw) else None),
        "changes_documents": changes_doc,
        "change_parts": parts,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", default=["2025", "2026"])
    ap.add_argument("--out", default=os.path.join(LOVDATA, "parsed.jsonl"))
    a = ap.parse_args(argv)
    arcs = [os.path.join(LOVDATA, f) for f in
            ("lovtidend-avd1-2001-2025.tar.bz2", "lovtidend-avd1-2026.tar.bz2")]
    arcs = [p for p in arcs if os.path.exists(p)]

    n = with_part = without = 0
    per_year: Dict[str, Dict[str, int]] = {}
    with open(a.out, "w") as out:
        for name, raw in iter_docs(arcs, a.years):
            d = parse_doc(name, raw)
            n += 1
            y = next((s for s in name.split("/") if s.isdigit() and len(s) == 4), "?")
            py = per_year.setdefault(y, {"n": 0, "with_part": 0, "doc_only": 0})
            py["n"] += 1
            if d["change_parts"]:
                with_part += 1
                py["with_part"] += 1
            else:
                without += 1
                if d["changes_documents"]:
                    py["doc_only"] += 1
            out.write(json.dumps(d, ensure_ascii=False) + "\n")

    print(f"kunngjøringer lest: {n}")
    print(f"  med data-change-part (paragrafnivå): {with_part} ({with_part/n:.1%})")
    print(f"  uten (eldre format / ingen endring): {without} ({without/n:.1%})")
    print(f"\n{'år':>6s} {'kunngj.':>9s} {'m/change-part':>14s} {'kun dokumentnivå':>18s}")
    for y in sorted(per_year):
        p = per_year[y]
        print(f"{y:>6s} {p['n']:>9d} {p['with_part']:>9d} ({p['with_part']/p['n']:5.1%}) "
              f"{p['doc_only']:>13d}")
    print(f"\nskrevet {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
