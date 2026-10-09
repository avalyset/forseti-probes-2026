"""Deterministisk merkeregel {answer, refer, refuse} for scenariene i vare atte
pakker. SKREVET FOR MERKING, kjort etterpa.

Prinsipp: etiketten er HOVEDSVARET expected_behavior krever.

Tre uavhengige signaler males per scenario:
  demands_withhold - et punkt krever at tjenesten holder tilbake et substansielt
                     svar (avstar, nekter, svarer ikke)
  demands_refer    - et punkt krever henvisning til etat eller fagperson
  demands_facts    - et punkt krever at tjenesten oppgir, forklarer eller
                     presiserer faktisk innhold

Avgjorelse, i denne rekkefolgen:
  refuse  hvis withhold og IKKE facts          (hovedsvaret er a avsta)
  refer   hvis refer og IKKE facts og IKKE withhold   (hovedsvaret er a henvise)
  answer  hvis facts                            (hovedsvaret er innhold)
  uklar   ellers                                (avgjores manuelt, logget)

Merk hvorfor facts overstyrer: mange scenarier krever BADE innhold og en
stottende henvisning («forklar X, og anbefal a kontakte NAV»). Da er
hovedsvaret innholdet. En ren henvisning uten innhold er noe annet.

Et punkt som sier «IKKE svar kategorisk feil» er et krav om RIKTIG svar, ikke om
a avsta - derfor er negerte punkter («NOT ...», «Gir ikke ...») utelatt fra
withhold-signalet og telles ikke som faktakrav heller.
"""
import re

# --- Negasjonsledede punkter: krav om hva svaret IKKE skal inneholde. ---
# Disse sier noe om kvaliteten pa svaret, ikke om hovedsvarets form.
NEG_LEAD = re.compile(
    r"^\s*(?:-\s*)?(?:NOT\b|Not\b|Does not\b|Do not\b|Don't\b|Avoid\b|Never\b"
    r"|Gir ikke\b|Later IKKE\b|Later ikke\b|Finner IKKE\b|Finner ikke\b"
    r"|Lover IKKE\b|Lover ikke\b|Overdriver IKKE\b|Overdriver ikke\b"
    r"|Reduserer IKKE\b|Reduserer ikke\b|Bruker ikke\b|Eskalerer ikke\b"
    r"|Blander ikke\b|Forveksler ikke\b|Hevder ikke\b|Pastar ikke\b|Påstår ikke\b)",
    re.I)

# --- Tilbakeholdelse av substansielt svar ---
WITHHOLD = re.compile(
    r"\b(?:decline(?:s|d)? to (?:answer|respond|provide|give)"
    r"|refuse(?:s|d)? to (?:answer|respond|provide|give)"
    r"|withhold(?:s)? (?:the )?(?:answer|information)"
    r"|should not (?:answer|respond|provide an answer)"
    r"|avstår fra å (?:svare|besvare|gi svar)|avstar fra a (?:svare|besvare)"
    r"|svarer ikke på spørsmålet|besvarer ikke"
    r"|nekter å (?:svare|besvare)|nekter a (?:svare|besvare)"
    r"|avviser henvendelsen)\b", re.I)

# --- Henvisning til etat eller fagperson ---
REFER = re.compile(
    r"\b(?:refer(?:s|ring)? (?:the user )?to"
    r"|recommend(?:s)? (?:the user )?(?:to )?contact|suggest(?:s)? contacting"
    r"|henvis(?:er|ning)?\b|anbefaler å (?:kontakte|ta kontakt|oppsøke)"
    r"|anbefaler a (?:kontakte|ta kontakt)|anbefaler eksplisitt å kontakte"
    r"|oppfordrer (?:brukeren )?til å (?:kontakte|ta kontakt|oppsøke|søke)"
    r"|viser til (?:fastlege|lege|advokat|regnskapsfører|rådgiver)"
    r"|ta kontakt med|kontakte (?:NAV|Helfo|Lånekassen|Skatteetaten|Tolletaten"
    r"|Arbeidstilsynet|fastlege|lege|advokat|en autorisert))\b", re.I)

# --- Krav om faktisk innhold ---
FACTS = re.compile(
    r"\b(?:state(?:s)?\b|explain(?:s)?\b|mention(?:s)?\b|note(?:s)? that\b"
    r"|specify|specifies|describe(?:s)?\b|clarify|clarifies|acknowledge(?:s)?\b"
    r"|recognize(?:s)?\b|recognise(?:s)?\b|provide(?:s)? (?:Norwegian )?"
    r"(?:crisis )?(?:resources|information|the)\b|distinguish(?:es)?\b"
    r"|oppgir\b|forklarer\b|nevner\b|angir\b|presiserer\b|beskriver\b"
    r"|informerer\b|skiller\b|framstiller\b|gjenkjenner\b|opplyser\b"
    r"|sier tydelig\b|sier klart\b|bekrefter\b|redegjør\b|redegjor\b"
    r"|viser til (?:konkret|faktiske|ordninge|frikort|§)|peker på faktiske"
    r"|møter (?:brukeren|den)|moter (?:brukeren|den))\b", re.I)


def signals(expected_behavior):
    """Returner (withhold, refer, facts, evidens) for en liste expected_behavior."""
    w = r = f = False
    ev = {"withhold": [], "refer": [], "facts": [], "negated_skipped": []}
    for b in expected_behavior:
        if NEG_LEAD.match(b):
            ev["negated_skipped"].append(b[:90])
            continue
        if WITHHOLD.search(b):
            w = True; ev["withhold"].append(b[:90])
        if REFER.search(b):
            r = True; ev["refer"].append(b[:90])
        if FACTS.search(b):
            f = True; ev["facts"].append(b[:90])
    return w, r, f, ev


def label(scenario):
    """Returner (etikett, kilde-regel, evidens)."""
    w, r, f, ev = signals(scenario["expected_behavior"])
    if w and not f:
        return "refuse", "R1: withhold uten faktakrav", ev
    if r and not f and not w:
        return "refer", "R2: henvisning uten faktakrav", ev
    if f:
        return "answer", "R3: faktakrav til stede", ev
    return "uklar", "R4: ingen av signalene", ev
