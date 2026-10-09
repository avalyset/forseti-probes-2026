"""Kandidat -> forslag, eller sak.

Porten, begge ledd ma holde:
  1. minst TO uavhengige kilder i registeret gir samme verdi
  2. |endring| < 10 % fra forrige verdi

Ellers blir det en SAK. En sak er ikke en feil - det er en verdi som skal
sees paa av et menneske fordi automatikken ikke tor.
"""
from __future__ import annotations

import datetime as dt
import glob
import re
import json
import os
from typing import Any, Dict, List, Optional

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(os.path.dirname(HERE), "data")
SAKER = os.path.join(HERE, "saker")
FORSLAG = os.path.join(HERE, "forslag")
MAX_CHANGE = 0.10
MIN_SOURCES = 2


def all_facts() -> List[Dict[str, Any]]:
    out = []
    for p in sorted(glob.glob(os.path.join(REG, "*.yaml"))):
        out += yaml.safe_load(open(p, encoding="utf-8"))["facts"]
    return out


def _row_urls(fact: Dict[str, Any]) -> set:
    return {(s.get("url") or "").strip().lower()
            for v in (fact.get("values") or []) for s in (v.get("sources") or [])
            if (s.get("url") or "").strip()}


def _claim_mentions(fact: Dict[str, Any], value: float) -> bool:
    """Nevner radens VERBATIM claim denne verdien?

    Dette er det som gjor porten operativ. Tolket bokstavelig — «verdien star
    som en VERDI i to rader» — kan porten aldri fyre for en NY sats: en fersk
    verdi finnes per konstruksjon i null registerrader, siden registeret er
    det som skal oppdateres. Men en ny G nevnes typisk ogsa i NAV-02/03 sine
    kontrollregninger, fra en annen kilde-URL (nav.no/aap). Det er to
    uavhengige kilder i registerets egen forstand.
    """
    txt = re.sub(r"[ \u00a0\u202f]", "", fact.get("claim") or "")
    iv = int(value) if float(value).is_integer() else None
    return bool(iv is not None and str(iv) in txt)


def independent_support(value: float, unit: str, exclude_row: str,
                        facts: Optional[List[Dict[str, Any]]] = None,
                        allow_claim_text: bool = True) -> List[str]:
    """Hvilke ANDRE registerrader bekrefter samme verdi, fra en ANNEN kilde?

    «Uavhengig» = en annen rad hvis kilde-URL ikke overlapper med den raden
    vi oppdaterer. To verdier i samme rad er ikke to kilder.
    """
    facts = facts if facts is not None else all_facts()
    me = next((f for f in facts if f["id"] == exclude_row), None)
    my_urls = _row_urls(me) if me else set()
    seen_urls, rows = set(), []
    for f in facts:
        if f["id"] == exclude_row:
            continue
        urls = _row_urls(f)
        if urls and my_urls and urls <= my_urls:
            continue                       # samme kilde = ikke uavhengig
        as_value = any(v.get("unit") == unit and abs(float(v["value"]) - value) < 1e-9
                       for v in (f.get("values") or []))
        as_claim = allow_claim_text and _claim_mentions(f, value)
        if not (as_value or as_claim):
            continue
        key = tuple(sorted(urls)) or (f["id"],)
        if key in seen_urls:
            continue
        seen_urls.add(key)
        rows.append(f["id"])
    return sorted(set(rows))


def previous_value(fact: Dict[str, Any], unit: str) -> Optional[float]:
    vals = [v for v in (fact.get("values") or []) if v.get("unit") == unit]
    if not vals:
        return None
    dated = [v for v in vals if v.get("valid_from")]
    if dated:
        return float(max(dated, key=lambda v: v["valid_from"])["value"])
    return float(vals[0]["value"])


def sak(row_id: str, kind: str, detail: str, **extra) -> str:
    os.makedirs(SAKER, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")[:-3]
    p = os.path.join(SAKER, f"{row_id}_{kind}_{stamp}.json")
    json.dump({"row_id": row_id, "kind": kind, "detail": detail,
               "opened_at": dt.date.today().isoformat(), **extra},
              open(p, "w"), indent=1, ensure_ascii=False)
    return p


def yaml_diff(fact: Dict[str, Any], cand: Dict[str, Any], prev: float,
              valid_from: str, source_url: str) -> str:
    new_entry = {
        "value": cand["value"], "unit": cand["unit"], "valid_from": valid_from,
        "valid_to": None,
        "sources": [{"url": source_url, "quote": cand["context"],
                     "verified_at": dt.date.today().isoformat()}],
    }
    body = yaml.safe_dump([new_entry], allow_unicode=True, sort_keys=False, width=100)
    return (f"# {fact['id']}: {prev:g} -> {cand['value']:g} {cand['unit']}\n"
            f"# foran de eksisterende verdiene i values:\n"
            + "\n".join("+" + ln for ln in body.rstrip().split("\n")) + "\n")


def propose(fact: Dict[str, Any], cand: Dict[str, Any], source_url: str,
            valid_from: Optional[str] = None,
            facts: Optional[List[Dict[str, Any]]] = None,
            allow_claim_text: bool = True) -> Dict[str, Any]:
    """Porten. Returnerer {'kind': 'forslag'|'sak', ...}."""
    rid, unit, val = fact["id"], cand["unit"], float(cand["value"])
    prev = previous_value(fact, unit)
    support = independent_support(val, unit, rid, facts, allow_claim_text)
    n_src = 1 + len(support)            # sida selv + bekreftende rader

    if prev is not None and abs(val - prev) < 1e-9:
        return {"kind": "uendret", "row_id": rid, "value": val}

    reasons = []
    if n_src < MIN_SOURCES:
        reasons.append(f"bare {n_src} kilde(r), krever {MIN_SOURCES}")
    if prev is None:
        reasons.append("ingen forrige verdi aa male endringen mot")
    else:
        rel = abs(val - prev) / abs(prev) if prev else float("inf")
        if rel >= MAX_CHANGE:
            reasons.append(f"endring {rel:.1%} >= {MAX_CHANGE:.0%}")

    if reasons:
        p = sak(rid, "needs_review", "; ".join(reasons), value=val, unit=unit,
                previous=prev, supporting_rows=support, span=cand["span"],
                context=cand["context"], source_url=source_url)
        return {"kind": "sak", "row_id": rid, "value": val, "unit": unit,
                "reasons": reasons, "path": p, "supporting_rows": support}

    os.makedirs(FORSLAG, exist_ok=True)
    vf = valid_from or dt.date.today().isoformat()
    diff = yaml_diff(fact, cand, prev, vf, source_url)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")[:-3]
    p = os.path.join(FORSLAG, f"{rid}_{stamp}.diff")
    open(p, "w", encoding="utf-8").write(diff)
    json.dump({"row_id": rid, "value": val, "unit": unit, "previous": prev,
               "change": (val - prev) / prev, "supporting_rows": support,
               "n_sources": n_src, "valid_from": vf, "source_url": source_url,
               "span": cand["span"], "context": cand["context"]},
              open(p[:-5] + ".json", "w"), indent=1, ensure_ascii=False)
    return {"kind": "forslag", "row_id": rid, "value": val, "unit": unit,
            "previous": prev, "path": p, "supporting_rows": support,
            "change": (val - prev) / prev}
