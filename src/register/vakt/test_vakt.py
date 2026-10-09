"""Hver vakt testes to ganger: pa et konstruert tilfelle den SKAL fyre pa, og
pa et rent tilfelle der den skal tie. En vakt som bare er testet pa ekte data
kan ikke skilles fra en som alltid fyrer.

Faste datoer overalt. Ingen klokke.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C                                     # noqa: E402
import yaml                                            # noqa: E402

AS_OF = dt.date(2026, 10, 9)


def fact(fid, domain="nav", trigger="ÅRLIG", review_by="2027-05",
         url="https://example.no/a", value=100, quote=None):
    return {"id": fid, "domain": domain, "claim": f"{fid} påstand",
            "legal_basis": "x § 1", "register_status": "VERIFISERT",
            "review_trigger": trigger, "review_by": review_by, "section": "s",
            "values": ([{"value": value, "unit": "NOK", "valid_from": "2026-01-01",
                         "valid_to": None,
                         "sources": [{"url": url, "quote": quote,
                                      "verified_at": "2026-01-01"}]}]
                       if url else []),
            "flags": []}


def write_facts(d, facts):
    os.makedirs(d, exist_ok=True)
    yaml.safe_dump({"schema_version": "1.0", "domain": "t", "facts": facts},
                   open(os.path.join(d, "t.yaml"), "w", encoding="utf-8"),
                   allow_unicode=True, sort_keys=False)


def write_snap(d, row_id, fetched_at):
    p = os.path.join(d, row_id)
    os.makedirs(p, exist_ok=True)
    json.dump({"row_id": row_id, "fetched_at": fetched_at, "sha256": "x",
               "bytes": 1, "source_url": "u", "final_url": "u"},
              open(os.path.join(p, f"{fetched_at}_x.json"), "w"))


def run(name, cond):
    print(f"  {'OK  ' if cond else 'FEIL'}  {name}")
    return cond


def main():
    ok = []
    print("V1 utløp")
    ok.append(run("fyrer på utløpt review_by",
                  C.v1_expiry([fact("A", review_by="2026-01")], AS_OF)["fired"]))
    ok.append(run("fyrer på ÅRLIG uten review_by",
                  bool(C.v1_expiry([fact("B", review_by=None)], AS_OF)
                       ["annual_without_review_by"])))
    ok.append(run("tier på rent (framtidig dato)",
                  not C.v1_expiry([fact("C", review_by="2027-05")], AS_OF)["fired"]))
    ok.append(run("tier på STABIL uten review_by",
                  not C.v1_expiry([fact("D", trigger="STABIL", review_by=None)],
                                  AS_OF)["fired"]))

    print("V2 dekning")
    gap = [{"pack": "p", "value": 45000.0, "scenario": "s", "snippet": "grensen er 45 000 kr"}]
    year = [{"pack": "p", "value": 2026.0, "scenario": "s", "snippet": "for 2026"}]
    phone = [{"pack": "p", "value": 116123.0, "scenario": "s", "snippet": "ring 116 123"}]
    ok.append(run("fyrer på ekte hull", C.v2_coverage(gap)["fired"]))
    ok.append(run("tier på tomt", not C.v2_coverage([])["fired"]))
    ok.append(run("årstall telles ikke som hull",
                  C.v2_coverage(year)["total"] == 0 and C.v2_coverage(year)["years_excluded"] == 1))
    ok.append(run("telefonnummer telles ikke som hull",
                  C.v2_coverage(phone)["total"] == 0 and C.v2_coverage(phone)["phones_excluded"] == 1))

    print("V3 kildehelse")
    with tempfile.TemporaryDirectory() as td:
        sd = os.path.join(td, "snap")
        write_snap(sd, "A", "2026-10-01")          # ferskt
        write_snap(sd, "B", "2026-01-01")          # 281 dager
        snaps = C.load_snapshots(sd)
        ok.append(run("tier på ferskt snapshot",
                      not C.v3_source_health([fact("A")], snaps, [], AS_OF)["fired"]))
        ok.append(run("fyrer på gammelt snapshot",
                      bool(C.v3_source_health([fact("B")], snaps, [], AS_OF)["stale"])))
        ok.append(run("fyrer på aldri hentet",
                      bool(C.v3_source_health([fact("Z")], snaps, [], AS_OF)["never_fetched"])))
        ok.append(run("fyrer på mislykket henting",
                      bool(C.v3_source_health([fact("A")], snaps,
                                              [{"row_id": "A", "kind": "http_404"}],
                                              AS_OF)["last_fetch_failed"])))
        ok.append(run("hopper over fakta uten URL",
                      not C.v3_source_health([fact("Q", url=None)], snaps, [], AS_OF)["fired"]))

    print("V4 stillhet")
    cal = {"A": {"month": 5, "day": 1}, "B": {"month": 5, "day": 1}}
    with tempfile.TemporaryDirectory() as td:
        sd = os.path.join(td, "snap")
        write_snap(sd, "A", "2026-06-01")          # etter 1. mai -> stille? nei
        write_snap(sd, "B", "2026-02-01")          # for 1. mai  -> stille
        snaps = C.load_snapshots(sd)
        ok.append(run("tier når halen hentet etter forfall",
                      not C.v4_silence([fact("A")], cal, snaps, AS_OF)["fired"]))
        ok.append(run("fyrer når siste henting er før forfall",
                      C.v4_silence([fact("B")], cal, snaps, AS_OF)["fired"]))
        ok.append(run("tier før forfallsdatoen i år",
                      not C.v4_silence([fact("B")], cal, snaps, dt.date(2026, 3, 1))["fired"]))
        ok.append(run("fyrer på ÅRLIG uten kalenderoppføring",
                      C.v4_silence([fact("X")], {}, snaps, AS_OF)["fired"]))
        ok.append(run("tier på ikke-ÅRLIG uten kalender",
                      not C.v4_silence([fact("Y", trigger="PRAKSIS")], {}, snaps,
                                       AS_OF)["fired"]))

    print("helt rent register: ingen vakt fyrer")
    with tempfile.TemporaryDirectory() as td:
        sd = os.path.join(td, "snap")
        write_snap(sd, "A", "2026-10-01")
        snaps = C.load_snapshots(sd)
        f = [fact("A", review_by="2027-05", quote="sitat")]
        clean = all([not C.v1_expiry(f, AS_OF)["fired"],
                     not C.v2_coverage([])["fired"],
                     not C.v3_source_health(f, snaps, [], AS_OF)["fired"],
                     not C.v4_silence(f, {"A": {"month": 5, "day": 1}}, snaps, AS_OF)["fired"]])
        ok.append(run("alle fire tier", clean))
        s = C.summary(f, AS_OF)
        ok.append(run("toppseksjon: 1 fakta, 100 % med verdi og sitat, 0 utløpt",
                      s["n_facts"] == 1 and s["share_value"] == 1.0
                      and s["share_quote"] == 1.0 and s["expired"] == 0))

    print(f"\n{sum(ok)}/{len(ok)} bestått")
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
