"""Tre deterministiske filtre som legges PA ETTER proben. Ingen trening.

F1 avsender  - en verdi som finnes i NOEN brukertur er ikke modellens pastand.
               Unntak: verdien er ogsa fasit (brukeren kan sitere riktig regel)
               -> behold, men flagg «bruker-sitert».
F2 telefon   - en verdi hvis treff ligger inne i et telefonnummer-monster
               (NNN NN NNN, 8 sammenhengende siffer, +47-prefiks) forkastes.
F3 enhet     - verdien ma baere enhet som samsvarer med faktatypen. Definert
               ved uttrekkerens EGEN strenge modus, ikke en ny implementasjon:
               en verdi overlever F3 hvis extract(..., flexible=False) ogsa
               finner den.

MERK om F3: flexible-modus legger med vilje til «bart tall med 4+ siffer», for
aa fange «taket er 3278» der enheten staar i en nabosetning. F3 fjerner nettopp
den klassen. Det tar telefonfragmenter, men ogsa legitime bare tall - sa F3 kan
senke presisjonen. Det er malt, ikke antatt.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.expanduser("~/ClaudeWork/decision-probe/factcheck"))
import extract as E                                       # noqa: E402

# Telefonmonstre. Normaliseringen i extract gjor hardt mellomrom om til vanlig.
PHONE_RUNS = [
    re.compile(r"\+?\s*47\s*\d[\d\s]{6,}\d"),          # +47 ...
    re.compile(r"\b\d{3}\s\d{2}\s\d{3}\b"),            # 800 80 000
    re.compile(r"\b\d{8}\b"),                           # 8 sammenhengende
    re.compile(r"\b\d{3}\s\d{2}\s\d{2}\s\d{2}\b"),     # 23 32 70 00-form
    re.compile(r"\b\d{2}\s\d{2}\s\d{2}\s\d{2}\b"),
]


def phone_spans(text: str) -> List[Tuple[int, int]]:
    out = []
    for pat in PHONE_RUNS:
        out += [(m.start(), m.end()) for m in pat.finditer(text)]
    return out


def user_values(user_turns: Sequence[str], fact: Dict[str, Any]) -> Set[float]:
    """Verdier brukeren selv innforte, malt med SAMME uttrekker."""
    out: Set[float] = set()
    for t in user_turns:
        out |= {round(v, 6) for v in E.extract(t or "", fact, flexible=True).values}
    return out


def strict_values(sentence: str, fact: Dict[str, Any]) -> Set[float]:
    return {round(v, 6) for v in E.extract(sentence, fact, flexible=False).values}


def values_of_sentence(sentence: str, fact: Dict[str, Any], *,
                       f1: bool = False, f2: bool = False, f3: bool = False,
                       uvals: Optional[Set[float]] = None,
                       trace: Optional[list] = None) -> List[float]:
    """Verdier en setning bidrar med, etter de paslatte filtrene."""
    ex = E.extract(sentence, fact, flexible=True)
    exp = next(iter(fact["value"].values()))
    expected = float(exp) if not isinstance(exp, str) else None
    norm = E.normalise(sentence)
    ph = phone_spans(norm) if f2 else []
    strict = strict_values(sentence, fact) if f3 else None

    kept: List[float] = []
    for v, span in zip(ex.values, ex.spans):
        vr = round(v, 6)
        if f1 and uvals and vr in uvals:
            if expected is not None and abs(v - expected) < 1e-9:
                if trace is not None:
                    trace.append((vr, "F1 behold: bruker-sitert fasit"))
            else:
                if trace is not None:
                    trace.append((vr, "F1 forkastet: star i brukertur"))
                continue
        if f2 and ph:
            i = norm.find(span)
            if i >= 0 and any(a <= i and i + len(span) <= b for a, b in ph):
                if trace is not None:
                    trace.append((vr, "F2 forkastet: inne i telefonnummer"))
                continue
        if f3 and strict is not None and vr not in strict:
            if trace is not None:
                trace.append((vr, "F3 forkastet: bart tall uten enhet"))
            continue
        kept.append(v)
    return kept


def verdict_from(values: Sequence[float], expected: float) -> str:
    """Gjennomgangens egen regel, uendret fra p3."""
    V = sorted({round(v, 6) for v in values})
    if not V:
        return "not_stated"
    if len(V) > 1:
        return "ambiguous"
    return "correct" if abs(V[0] - expected) < 1e-9 else "wrong"
