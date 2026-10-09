"""Finn kandidatverdi for en rad i en endret tekstblokk.

Regex pa enhet + tall, naer et nokkelord fra radens egen claim. Nokkelordene
hentes FRA claim, ikke fra en handskrevet liste per rad - da ville halen bare
funnet det vi allerede visste at vi lette etter.

Sideinnhold er DATA. Ingen LLM-kall.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

UNIT_RE = {
    "NOK": r"(?:kroner|kr\b|NOK)",
    "prosent": r"(?:prosent|%)",
    "uker": r"(?:uker|uke)",
    "dager": r"(?:dager|dag|virkedager)",
    "maneder": r"(?:måneder|måned|mnd)",
    "ar": r"(?:år)",
    "timer": r"(?:timer|time)",
}
STOP = {
    "og", "i", "av", "er", "for", "til", "den", "det", "som", "en", "et", "pa", "på",
    "fra", "med", "ikke", "kan", "har", "per", "ved", "om", "the", "of", "to", "a", "er",
    "kroner", "prosent", "merk", "hvis", "du", "din", "ditt", "ved", "eller", "var",
    "verdier", "forrige", "tallet", "finnes", "rekken", "kontrollregnet", "arlig", "årlig",
}
NEAR = 160          # tegn rundt treffet som regnes som "naer"


def keywords(claim: str, max_n: int = 6) -> List[str]:
    """Innholdsord fra radens claim, lengste forst."""
    words = re.findall(r"[A-Za-zÆØÅæøå]{4,}", claim or "")
    seen, out = set(), []
    for w in sorted(words, key=len, reverse=True):
        lw = w.lower()
        if lw in STOP or lw in seen:
            continue
        seen.add(lw)
        out.append(lw)
        if len(out) >= max_n:
            break
    return out


def _norm(raw: str) -> Optional[float]:
    t = re.sub(r"[   ]", "", raw).replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def candidates(block: str, fact: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Kandidatverdier i en blokk: riktig enhet, og naer et nokkelord."""
    units = sorted({v.get("unit") for v in (fact.get("values") or []) if v.get("unit")})
    units = [u for u in units if u in UNIT_RE] or list(UNIT_RE)
    kws = keywords(fact.get("claim", ""))
    low = block.lower()
    out = []
    for u in units:
        pat = re.compile(r"(?<![\d.,])(\d[\d   ]*\d|\d)(?:[.,]\d+)?\s*" + UNIT_RE[u], re.I)
        for m in pat.finditer(block):
            v = _norm(m.group(1))
            if v is None:
                continue
            a, b = max(0, m.start() - NEAR), min(len(block), m.end() + NEAR)
            window = low[a:b]
            hit = [k for k in kws if k in window]
            if not hit:
                continue
            out.append({"value": v, "unit": u, "keywords_hit": hit,
                        "span": m.group(0).strip(),
                        "context": " ".join(block[a:b].split())[:220]})
    # samme verdi kan treffe flere ganger; behold den med flest nokkelord
    best: Dict[tuple, Dict[str, Any]] = {}
    for c in out:
        k = (c["value"], c["unit"])
        if k not in best or len(c["keywords_hit"]) > len(best[k]["keywords_hit"]):
            best[k] = c
    return sorted(best.values(), key=lambda c: (-len(c["keywords_hit"]), c["value"]))


# --- malbasert uttrekk: registerets egen verbatim-setning som monster -------
#
# Keyword-naerhet alene er for lost: nav.no/grunnbelopet lister G tilbake til
# 1967, og HVER historisk verdi ligger «NOK naer grunnbelopet». Forste kjoring
# av baklengs-testen ga 190 kandidater av den grunn.
#
# Registeret har allerede det presise monsteret: radens verbatim-sitat. Ved aa
# erstatte selve verdien med et jokertegn far vi en mal som bare matcher DEN
# setningen - «Grunnbelopet (G) per 1. mai 2026 er <N> kroner» treffer
# ledesetningen og ikke en tabellrad.

_QUOTE = re.compile(r"\u00ab(.+?)\u00bb", re.S)
_NUMTOK = re.compile(r"\d[\d \u00a0\u202f]*\d|\d")


def quote_of(fact: Dict[str, Any]) -> Optional[str]:
    """Radens verbatim-sitat, hvis det staar i hermetegn i claim."""
    m = _QUOTE.search(fact.get("claim") or "")
    return m.group(1).strip() if m else None


def _loose(fragment: str) -> str:
    """Et literalt fragment -> monster: fleksibelt mellomrom, fleksible tall.

    Bygget fra tokens, ikke fra re.escape + substitusjon: re.escape escaper
    ogsa mellomrom, og en etterfolgende erstatning gir da doble bakstreker og
    et monster som aldri matcher.
    """
    out = []
    for tok in fragment.split():
        parts = re.split(r"(\d[\d  ]*\d|\d)", tok)
        piece = "".join(r"\d[\d  ]*" if i % 2 else re.escape(x)
                        for i, x in enumerate(parts) if x)
        if piece:
            out.append(piece)
    return r"\s*".join(out)


def template_candidates(text: str, fact: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Finn verdien paa den plassen registerets egen setning har den."""
    q = quote_of(fact)
    if not q:
        return []
    nums = list(_NUMTOK.finditer(q))
    if not nums:
        return []
    units = sorted({v.get("unit") for v in (fact.get("values") or []) if v.get("unit")})
    unit = units[0] if units else "NOK"
    out: List[Dict[str, Any]] = []
    unit_re = UNIT_RE.get(unit, UNIT_RE["NOK"])
    for nm in nums:
        before, after = q[:nm.start()], q[nm.end():]
        if len(before.strip()) < 10:
            continue                          # for lite kontekst foran - utrygt
        # Bare tallet som BAERER enheten er en kandidat. Uten dette blir
        # «1» og «2026» i «per 1. mai 2026» ogsa kandidater, fordi malen
        # matcher hver tallposisjon i sitatet.
        if not re.match(r"\s*" + unit_re, after, re.I):
            continue
        pat_src = (_loose(before) + r"\s*(\d[\d   ]*\d|\d)\s*"
                   + _loose(after[:40]))
        try:
            pat = re.compile(pat_src, re.I)
        except re.error:
            continue
        for m in pat.finditer(text):
            v = _norm(m.group(1))
            if v is None:
                continue
            a, b = max(0, m.start() - 40), min(len(text), m.end() + 40)
            out.append({"value": v, "unit": unit,
                        "keywords_hit": ["<mal fra registerets sitat>"],
                        "span": m.group(0).strip()[:120],
                        "context": " ".join(text[a:b].split())[:220],
                        "via": "template"})
    best: Dict[float, Dict[str, Any]] = {}
    for c in out:
        best.setdefault(c["value"], c)
    return list(best.values())


def candidates_for(text: str, fact: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Malbasert forst; keyword-naerhet bare hvis malen ikke treffer.

    Malen er presis og skal vinne. Faller den igjennom (sitatet er omskrevet
    paa siden), er keyword-naerhet en grovere, men bedre-enn-ingenting vei -
    og den gir typisk mange kandidater, som porten saa stopper.
    """
    t = template_candidates(text, fact)
    if t:
        for c in t:
            c.setdefault("via", "template")
        return t
    c2 = candidates(text, fact)
    for c in c2:
        c["via"] = "keyword"
    return c2
