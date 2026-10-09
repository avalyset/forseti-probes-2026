"""Hent radenes kilde-URL og lagre ra HTML med sha256 og dato.

Sideinnhold er DATA. Ingen LLM-kall i denne runden.
Feiler HOYT: 404, tom respons, manglende URL -> sak, aldri stille.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
import urllib.error
import urllib.request

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(os.path.dirname(HERE), "data")
SNAP = os.path.join(HERE, "snapshots")
SAKER = os.path.join(HERE, "saker")
UA = "forseti-hale/1.0 (lokal faktaverifisering; eirikbnico@gmail.com)"
ANNUAL_ROWS = ["NAV-01", "NAV-02", "NAV-03", "NAV-04", "NAV-05", "NAV-06",
               "SKATT-18", "SKATT-19", "SKATT-20", "HF-08", "HF-09", "LK-22"]


def sak(row_id: str, kind: str, detail: str, **extra) -> str:
    """Skriv en sak. Enhver feil blir en sak - ingenting svelges."""
    os.makedirs(SAKER, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    p = os.path.join(SAKER, f"{row_id}_{kind}_{stamp}.json")
    json.dump({"row_id": row_id, "kind": kind, "detail": detail,
               "opened_at": dt.date.today().isoformat(), **extra},
              open(p, "w"), indent=1, ensure_ascii=False)
    return p


def load_rows(ids=None):
    want = set(ids or ANNUAL_ROWS)
    out = {}
    for p in sorted(glob.glob(os.path.join(REG, "*.yaml"))):
        for f in yaml.safe_load(open(p, encoding="utf-8"))["facts"]:
            if f["id"] in want:
                out[f["id"]] = f
    return out


def url_of(fact):
    for v in fact.get("values") or []:
        for s in v.get("sources") or []:
            u = (s.get("url") or "").strip()
            if u:
                return u if u.startswith("http") else "https://" + u
    return None


def is_url(u):
    return bool(u) and re.match(r"^https?://[^\s/]+\.[^\s/]+", u or "")


def fetch_one(row_id, url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return body, r.status, r.geturl()


def snapshot(row_id, body, final_url, source_url):
    os.makedirs(os.path.join(SNAP, row_id), exist_ok=True)
    sha = hashlib.sha256(body).hexdigest()
    day = dt.date.today().isoformat()
    base = os.path.join(SNAP, row_id, f"{day}_{sha[:12]}")
    with open(base + ".html", "wb") as f:
        f.write(body)
    meta = {"row_id": row_id, "fetched_at": day, "sha256": sha,
            "bytes": len(body), "source_url": source_url, "final_url": final_url}
    json.dump(meta, open(base + ".json", "w"), indent=1, ensure_ascii=False)
    return meta


def latest_two(row_id):
    """De to nyeste snapshotene for en rad, nyest forst."""
    ms = sorted(glob.glob(os.path.join(SNAP, row_id, "*.json")), reverse=True)
    return [json.load(open(m)) | {"path": m[:-5] + ".html"} for m in ms[:2]]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="*", default=None)
    a = ap.parse_args(argv)
    facts = load_rows(a.rows)
    missing = [r for r in (a.rows or ANNUAL_ROWS) if r not in facts]
    for r in missing:
        print(f"  {r:9s} SAK: finnes ikke i registeret -> {sak(r, 'missing_row', 'row not in register')}")
    ok = fails = 0
    for rid in sorted(facts):
        u = url_of(facts[rid])
        if not is_url(u):
            fails += 1
            p = sak(rid, "no_url", f"no usable source URL in the register (got {u!r})",
                    claim=facts[rid]["claim"][:160])
            print(f"  {rid:9s} SAK: ingen brukbar URL ({u!r})")
            continue
        try:
            body, status, final = fetch_one(rid, u)
            if not body:
                raise RuntimeError("empty body")
            m = snapshot(rid, body, final, u)
            ok += 1
            print(f"  {rid:9s} {status} {m['bytes']:>7d} B  sha {m['sha256'][:12]}  {final[:60]}")
        except urllib.error.HTTPError as e:
            fails += 1
            sak(rid, f"http_{e.code}", f"HTTP {e.code} for {u}", url=u)
            print(f"  {rid:9s} SAK: HTTP {e.code}")
        except Exception as e:
            fails += 1
            sak(rid, "fetch_error", f"{type(e).__name__}: {e}", url=u)
            print(f"  {rid:9s} SAK: {type(e).__name__}: {str(e)[:70]}")
    print(f"\nhentet {ok}, saker {fails + len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
