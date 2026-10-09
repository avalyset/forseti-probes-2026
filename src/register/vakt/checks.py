"""Fire metningsvakter over registeret og halen.

«Metning» her er ikke at alt er riktig, men at vi faktisk ser det vi tror vi
ser: at satser ikke har gatt ut pa dato, at pakkene ikke pastar tall registeret
ikke kjenner, at kildene fortsatt svarer, og at halen faktisk har kjort nar
kalenderen sa den skulle.

INGEN KLOKKE. Hver vakt tar as_of som argument. Et script som spor systemet
hva dagen er kan ikke testes mot en fast dato, og en vakt som ikke kan testes
er ikke en vakt.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import re
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.dirname(HERE)
STALE_DAYS = 90


# --------------------------------------------------------------------------
# innlesing
# --------------------------------------------------------------------------

def load_facts(data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    import yaml
    d = data_dir or os.path.join(REG, "data")
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.yaml"))):
        out += yaml.safe_load(open(p, encoding="utf-8"))["facts"]
    return out


def load_snapshots(snap_dir: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """row_id -> snapshot-metadata, nyest forst."""
    d = snap_dir or os.path.join(REG, "hale", "snapshots")
    out: Dict[str, List[Dict[str, Any]]] = {}
    for meta in sorted(glob.glob(os.path.join(d, "*", "*.json"))):
        try:
            m = json.load(open(meta, encoding="utf-8"))
        except Exception:
            continue
        out.setdefault(m.get("row_id") or os.path.basename(os.path.dirname(meta)), []).append(m)
    for k in out:
        out[k].sort(key=lambda m: m.get("fetched_at") or "", reverse=True)
    return out


def load_cases(saker_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    d = saker_dir or os.path.join(REG, "hale", "saker")
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            out.append(json.load(open(p, encoding="utf-8")))
        except Exception:
            pass
    return out


def load_calendar(path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    import yaml
    p = path or os.path.join(REG, "hale", "calendar.yaml")
    if not os.path.exists(p):
        return {}
    return (yaml.safe_load(open(p, encoding="utf-8")) or {}).get("rows") or {}


def load_unknown(check_json: Optional[str] = None) -> List[Dict[str, Any]]:
    """UKJENT-radene fra check_packs: tall pakkene pastar som registeret
    ikke kjenner. Det er hullet som lot 130 030 sta."""
    p = check_json or os.path.join(REG, "check_upstream_dev.json")
    if not os.path.exists(p):
        return []
    d = json.load(open(p, encoding="utf-8"))
    return [r for r in d.get("rows", []) if r.get("verdict") == "UKJENT"]


def _date(s) -> Optional[dt.date]:
    if not s or not isinstance(s, str):
        return None
    m = re.match(r"^(\d{4})-(\d{2})(?:-(\d{2}))?$", s.strip())
    if not m:
        return None
    y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)
    try:
        return dt.date(y, mo, da)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# V1 utlop
# --------------------------------------------------------------------------

def v1_expiry(facts, as_of: dt.date) -> Dict[str, Any]:
    """Fakta med review_by i fortiden, og ARLIG-fakta uten review_by i det
    hele tatt. Det andre er en FEIL, ikke bare en advarsel: en arlig sats
    uten forfallsdato kan ikke ga ut pa dato, og ser derfor evig frisk ut."""
    expired, missing = [], []
    for f in facts:
        rb = _date(f.get("review_by"))
        if rb and rb < as_of:
            expired.append({"id": f["id"], "domain": f["domain"],
                            "review_by": f["review_by"],
                            "days_overdue": (as_of - rb).days,
                            "trigger": f.get("review_trigger")})
        if not rb and f.get("review_trigger") == "ÅRLIG":
            missing.append({"id": f["id"], "domain": f["domain"],
                            "review_by": f.get("review_by"),
                            "claim": (f.get("claim") or "")[:70]})
    expired.sort(key=lambda r: -r["days_overdue"])
    return {"name": "V1 utløp", "expired": expired, "annual_without_review_by": missing,
            "fired": bool(expired or missing)}


# --------------------------------------------------------------------------
# V2 dekning
# --------------------------------------------------------------------------

def _is_year(v: float) -> bool:
    return float(v).is_integer() and 1900 <= int(v) <= 2100


# Samme telefonformer som fact_check-dommeren kjenner. En UKJENT-verdi som er
# loftet ut av et telefonnummer er ikke et registerhull - det er et tall som
# aldri skulle vaert en kandidat.
_PHONE_RUNS = [
    re.compile(r"\+?\s*47\s*\d[\d\s]{6,}\d"),
    re.compile(r"\b\d{3}\s\d{2}\s\d{3}\b"),
    re.compile(r"\b\d{3}\s\d{2}\s\d{2}\s\d{2}\b"),
    re.compile(r"\b\d{2}\s\d{2}\s\d{2}\s\d{2}\b"),
    re.compile(r"\b\d{3}\s\d{3}\b"),
]
_KNOWN_HELPLINES = {116123.0, 116117.0, 80080000.0, 23327000.0, 80030196.0, 2400.0}


def _is_phone(v: float, snippet: str) -> bool:
    if v in _KNOWN_HELPLINES:
        return True
    digits = str(int(v)) if float(v).is_integer() else None
    if not digits or len(digits) < 5:
        return False
    for pat in _PHONE_RUNS:
        for m in pat.finditer(snippet or ""):
            if re.sub(r"\s", "", m.group(0)).endswith(digits) or \
               digits in re.sub(r"\s", "", m.group(0)):
                return True
    return False


def v2_coverage(unknown_rows) -> Dict[str, Any]:
    """Tall pakkene pastar som registeret ikke dekker, per pakke.

    UKJENT-kategorien fra check_packs teller ethvert belop med >=4 siffer som
    ikke star i registeret - ogsa arstall. «for 2026» er et slikt tall, men
    ikke en sats registeret skal dekke. Vi filtrerer dem derfor IKKE bort
    (det ville endret check_packs' semantikk), men skiller dem ut, slik at
    tallet som rapporteres er det som faktisk er et hull.
    """
    per: Dict[str, List[Dict[str, Any]]] = {}
    years: Dict[str, int] = {}
    phones: Dict[str, int] = {}
    for r in unknown_rows:
        if _is_year(r["value"]):
            years[r["pack"]] = years.get(r["pack"], 0) + 1
            continue
        if _is_phone(r["value"], r.get("snippet") or ""):
            phones[r["pack"]] = phones.get(r["pack"], 0) + 1
            continue
        per.setdefault(r["pack"], []).append(
            {"value": r["value"], "scenario": (r.get("scenario") or "")[:50],
             "snippet": (r.get("snippet") or "")[:90]})
    out = [{"pack": p, "n": len(v), "n_years_excluded": years.get(p, 0),
            "n_phones_excluded": phones.get(p, 0), "examples": v[:3]}
           for p, v in sorted(per.items(), key=lambda kv: -len(kv[1]))]
    return {"name": "V2 dekning", "per_pack": out,
            "total": sum(x["n"] for x in out),
            "total_raw": len(unknown_rows),
            "years_excluded": sum(years.values()),
            "phones_excluded": sum(phones.values()),
            "fired": bool(out)}


# --------------------------------------------------------------------------
# V3 kildehelse
# --------------------------------------------------------------------------

_URLISH = re.compile(r"^(?:https?://)?[\w.-]+\.[a-z]{2,}(?:/|$)", re.I)


def is_fetchable(u: str) -> bool:
    """Er kildefeltet en URL halen kan hente, eller er det prosa?

    Registeret har kildefelt som «korpus sha256 729aff34d2…» og
    «Vault `lov/forvaltningsloven.xml`». De er sporbare referanser, men ikke
    noe halen kan GET-e. A telle dem som «aldri hentet» ville lært leseren at
    V3 alltid fyrer.
    """
    u = (u or "").strip()
    return bool(u) and bool(_URLISH.match(u))


def v3_source_health(facts, snapshots, cases, as_of: dt.date,
                     stale_days: int = STALE_DAYS) -> Dict[str, Any]:
    """URL-er uten ferskt snapshot, eller med siste henting mislykket.

    Halen skriver en sak per mislykket henting; en rad med sak og uten
    snapshot teller som ikke-200.
    """
    failed_rows = {c.get("row_id") for c in cases
                   if str(c.get("kind", "")).startswith(("http_", "fetch_error", "no_url"))}
    stale, failing, never, not_a_url = [], [], [], []
    for f in facts:
        raw = sorted({(s.get("url") or "").strip()
                      for v in (f.get("values") or [])
                      for s in (v.get("sources") or []) if (s.get("url") or "").strip()})
        if not raw:
            continue
        urls = [u for u in raw if is_fetchable(u)]
        if not urls:
            not_a_url.append({"id": f["id"], "domain": f["domain"],
                              "source": raw[0][:70]})
            continue
        snaps = snapshots.get(f["id"]) or []
        last = _date(snaps[0]["fetched_at"]) if snaps else None
        rec = {"id": f["id"], "domain": f["domain"], "url": urls[0],
               "last_snapshot": snaps[0]["fetched_at"] if snaps else None,
               "age_days": (as_of - last).days if last else None}
        if f["id"] in failed_rows:
            failing.append(rec)
        elif last is None:
            never.append(rec)
        elif (as_of - last).days > stale_days:
            stale.append(rec)
    for lst in (stale, never, failing):
        lst.sort(key=lambda r: -(r["age_days"] or 10**6))
    not_a_url.sort(key=lambda r: r["id"])
    return {"name": "V3 kildehelse", "stale": stale, "never_fetched": never,
            "last_fetch_failed": failing, "not_a_url": not_a_url,
            "stale_days": stale_days,
            "fired": bool(stale or never or failing or not_a_url)}


# --------------------------------------------------------------------------
# V4 stillhet
# --------------------------------------------------------------------------

def v4_silence(facts, calendar, snapshots, as_of: dt.date) -> Dict[str, Any]:
    """ARLIG-fakta der kalenderdatoen har passert i ar, men halen ikke har
    hentet siden den datoen. Stillhet er ikke det samme som uendret."""
    out = []
    for f in facts:
        if f.get("review_trigger") != "ÅRLIG":
            continue
        spec = calendar.get(f["id"])
        if not spec:
            out.append({"id": f["id"], "domain": f["domain"], "due": None,
                        "last_snapshot": None,
                        "why": "ÅRLIG uten kalenderoppføring — halen kjører den aldri"})
            continue
        try:
            due = dt.date(as_of.year, int(spec["month"]), int(spec["day"]))
        except (ValueError, KeyError, TypeError):
            out.append({"id": f["id"], "domain": f["domain"], "due": None,
                        "last_snapshot": None, "why": "ugyldig kalenderoppføring"})
            continue
        if as_of < due:
            continue
        snaps = snapshots.get(f["id"]) or []
        last = _date(snaps[0]["fetched_at"]) if snaps else None
        if last is None or last < due:
            out.append({"id": f["id"], "domain": f["domain"], "due": due.isoformat(),
                        "last_snapshot": snaps[0]["fetched_at"] if snaps else None,
                        "why": "ingen henting etter forfallsdatoen"})
    out.sort(key=lambda r: (r["due"] or "", r["id"]))
    return {"name": "V4 stillhet", "silent": out, "fired": bool(out)}


# --------------------------------------------------------------------------
# toppseksjon
# --------------------------------------------------------------------------

def summary(facts, as_of: dt.date) -> Dict[str, Any]:
    n = len(facts)
    with_value = sum(1 for f in facts if f.get("values"))
    with_quote = sum(1 for f in facts
                     if any(s.get("quote") for v in (f.get("values") or [])
                            for s in (v.get("sources") or [])))
    expired = sum(1 for f in facts
                  if (_date(f.get("review_by")) or dt.date.max) < as_of)
    return {"n_facts": n, "with_value": with_value, "with_quote": with_quote,
            "expired": expired,
            "share_value": with_value / n if n else 0.0,
            "share_quote": with_quote / n if n else 0.0,
            "share_expired": expired / n if n else 0.0}


def run_all(as_of: dt.date, *, data_dir=None, snap_dir=None, saker_dir=None,
            calendar_path=None, check_json=None) -> Dict[str, Any]:
    facts = load_facts(data_dir)
    snaps = load_snapshots(snap_dir)
    cases = load_cases(saker_dir)
    cal = load_calendar(calendar_path)
    unknown = load_unknown(check_json)
    return {"as_of": as_of.isoformat(), "summary": summary(facts, as_of),
            "v1": v1_expiry(facts, as_of), "v2": v2_coverage(unknown),
            "v3": v3_source_health(facts, snaps, cases, as_of),
            "v4": v4_silence(facts, cal, snaps, as_of)}
