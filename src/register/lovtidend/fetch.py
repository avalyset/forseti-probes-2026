"""Hent Norsk Lovtidend avd. I fra api.lovdata.no til Vault.

Hjemmel for nedlastingen, lest direkte 2026-10-09 fra lovdata.no/info/vilkar
(sha256 7f2e9ddf50f6b669…):

  § 2.3 unntar «Regelverk i Norsk Lovtidend» fra bruksbegrensningene i § 2.1
  og § 2.2, under NLOD 2.0, mot kildeangivelse. Samme punkt sier at
  massenedlasting fra nettsidene ikke er tillatt, og henviser videre:
  «For større nedlastinger, bruk våre åpne API-er.» Det er nettopp det denne
  filen gjør.

  KI-forbudet («Det er ikke tillatt å bruke innholdet til trening eller
  utvikling av KI-algoritmer») staar i § 2.1/2.2 og gjelder Lovdatas egne
  nettjenester — ikke NLOD-datasettene, som § 2.3 unntar. Vi trener heller
  ikke paa innholdet: vi leser data-change-part-attributter.

Ingen konto, ingen autentisering, ingen skjema. Alt til Vault.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request

API = "https://api.lovdata.no/v1/publicData"
DEST = "/Volumes/Vault/forseti/lovdata"
UA = "forseti-register/1.0 (lokal faktaverifisering; eirikbnico@gmail.com)"
# 2025 finnes IKKE som egen arsfil - den ligger i samlearkivet 2001-2025.
WANT = ["lovtidend-avd1-2001-2025.tar.bz2", "lovtidend-avd1-2026.tar.bz2"]


def listing():
    req = urllib.request.Request(f"{API}/list", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return {f["filename"]: f for f in json.loads(r.read())}


def fetch(name, expect_bytes, dest=DEST):
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, name)
    req = urllib.request.Request(f"{API}/get/{name}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=900) as r, open(out, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    got = os.path.getsize(out)
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    ok = (got == int(expect_bytes))
    return {"filename": name, "path": out, "bytes": got,
            "expected_bytes": int(expect_bytes), "size_ok": ok, "sha256": sha}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=DEST)
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args(argv)
    L = listing()
    want = a.only or WANT
    print(f"{len(L)} arkiv tilgjengelig i /list")
    out = []
    for n in want:
        if n not in L:
            print(f"  {n}: FINNES IKKE i /list - hoppet over")
            continue
        m = fetch(n, L[n]["sizeBytes"], a.dest)
        out.append(m)
        print(f"  {n}")
        print(f"    {m['bytes']/1e6:.1f} MB  forventet {m['expected_bytes']/1e6:.1f} MB  "
              f"{'OK' if m['size_ok'] else 'AVVIK'}")
        print(f"    sha256 {m['sha256']}")
        print(f"    lastModified {L[n]['lastModified']}")
    meta = os.path.join(a.dest, "manifest.json")
    json.dump({"fetched_at": "2026-10-09", "source": API, "license": "NLOD 2.0",
               "files": out}, open(meta, "w"), indent=1)
    print(f"\nskrevet {meta}")
    return 0 if all(m["size_ok"] for m in out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
