"""Konverter NDVL-REG-0002 (118 rader) til YAML etter OpenFisca-monsteret.

Prinsipp: GJETTER ALDRI. Et felt som ikke star i raden blir tomt og flagges.
En verdi som ikke kan leses entydig ut av pastanden gir values: [] og flagget
value_not_extractable - ikke et tall vi fant pa.

NAV-01 (grunnbelopet) far full historikk fra nav.no/grunnbelopet, hentet
verbatim fra ra-HTML (sha256 i kilden).
"""
import json, os, re, sys, hashlib, datetime
import yaml

REG = os.path.expanduser("~/dev/norpref/docs/NDVL-REG-0002_kildeverifisering.md")
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data")
GHIST = os.path.join(ROOT, "data", "g_history_raw.json")
GSRC_SHA = "54ce2b6dc755f1a827330a572b8eb5168b5ed98c96bea7a776e6bcf594b56490"
GSRC_URL = "https://www.nav.no/grunnbelopet"
FETCHED = "2026-10-09"

DOMAIN = {"NAV": "nav", "SKATT": "skatteetaten", "HF": "helfo", "LK": "lanekassen",
          "NB": "nasjonalbiblioteket", "TOLL": "tolletaten", "AT": "arbeidstilsynet"}
EMPTY = {"", "—", "-", "–"}

# Entydige verdimonstre. Rekkefolge = prioritet. Bare treff med enhet teller.
VALUE_PATTERNS = [
    (re.compile(r"(\d[\d   ]*\d|\d)\s*(?:kroner|kr\b|NOK)", re.I), "NOK"),
    (re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:prosent|%)"), "prosent"),
    (re.compile(r"(\d+)\s*(?:uker|uke)\b", re.I), "uker"),
    (re.compile(r"(\d+)\s*(?:dager|dag|virkedager)\b", re.I), "dager"),
    (re.compile(r"(\d+)\s*(?:måneder|måned|mnd)\b", re.I), "maneder"),
    (re.compile(r"(\d+)\s*(?:timer|time)\b", re.I), "timer"),
    (re.compile(r"(\d+)\s*(?:år)\b", re.I), "ar"),
]
DATE_IN_CLAIM = re.compile(r"(?:per|fra|gjeldende fra|med virkning fra)\s+"
                           r"(\d{1,2})\.?\s*(januar|februar|mars|april|mai|juni|juli|"
                           r"august|september|oktober|november|desember)\s+(\d{4})", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(
    ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
     "september", "oktober", "november", "desember"])}


def norm_num(s):
    return re.sub(r"[   ]", "", s)


def parse_rows(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    rows, section = [], None
    for ln in lines:
        if ln.startswith("## "):
            section = ln[3:].strip()
        if not re.match(r"^\| [A-ZÆØÅ]+-\d+ \|", ln):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) < 7:
            continue
        rows.append({"id": c[0], "claim": c[1], "legal_basis": c[2], "source": c[3],
                     "status": c[4], "trigger": c[5], "review_by": c[6],
                     "section": section})
    return rows


def extract_values(claim):
    """Hent ALLE tall-enhet-par verbatim ut av pastanden.

    Ett par  -> en verdi.
    Flere    -> alle verdiene, hver med `context` = den verbatime omgivelsen,
                og flagget flere_verdier_uten_strukturert_merkelapp. Registeret
                gir ingen strukturert merkelapp som skiller «sats» fra «ovre
                grense», sa vi velger ikke en av dem - vi forer alle, med
                konteksten som star der.
    Ingen    -> tom liste, flagget value_not_extractable.

    Dette er registrering av det som star, ikke gjetning.
    """
    found = []
    seen = set()
    for pat, unit in VALUE_PATTERNS:
        for m in pat.finditer(claim):
            raw = norm_num(m.group(1)).replace(",", ".")
            try:
                v = float(raw) if "." in raw else int(raw)
            except ValueError:
                continue
            key = (v, unit)
            if key in seen:
                continue
            seen.add(key)
            a, b = max(0, m.start() - 55), min(len(claim), m.end() + 55)
            found.append({"value": v, "unit": unit,
                          "context": " ".join(claim[a:b].split())})
    return found


def extract_valid_from(claim):
    m = DATE_IN_CLAIM.search(claim)
    if m:
        return f"{m.group(3)}-{MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m2 = re.search(r"\bfor (\d{4})\b|\b(\d{4})[–-](\d{4})\b|årvelger satt til (\d{4})", claim)
    if m2:
        y = m2.group(1) or m2.group(2) or m2.group(4)
        if y:
            return f"{y}-01-01"
    return None


def norm_review_by(s):
    s = s.strip()
    if s in EMPTY:
        return None, "review_by_mangler"
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", s):
        return s, None
    return None, f"review_by_uparselig:{s[:40]}"


def norm_trigger(s):
    s = s.strip()
    if s in EMPTY:
        return None, "review_trigger_mangler"
    for t in ("ÅRLIG", "LOVENDRING", "PRAKSIS", "STABIL"):
        if s.upper().startswith(t):
            return t, None
    return None, f"review_trigger_ukjent:{s[:40]}"


def g_history():
    rows = json.load(open(GHIST))
    rows.sort(key=lambda r: r["valid_from"], reverse=True)
    vals = []
    for i, r in enumerate(rows):
        nxt = rows[i - 1]["valid_from"] if i > 0 else None
        vto = None
        if nxt:
            d = datetime.date.fromisoformat(nxt) - datetime.timedelta(days=1)
            vto = d.isoformat()
        vals.append({
            "value": r["value"], "unit": "NOK",
            "valid_from": r["valid_from"], "valid_to": vto,
            "sources": [{"url": GSRC_URL, "quote": " ".join(r["quote"].split())[:160],
                         "verified_at": FETCHED, "raw_sha256": GSRC_SHA}],
        })
    return vals


def main():
    raw = open(REG, "rb").read()
    reg_sha = hashlib.sha256(raw).hexdigest()
    rows = parse_rows(REG)
    print(f"{len(rows)} rader lest fra NDVL-REG-0002 (sha256 {reg_sha[:12]}…)")

    by_domain, all_facts, flagcount = {}, [], {}
    for r in rows:
        pre = r["id"].split("-")[0]
        dom = DOMAIN.get(pre, "ukjent")
        flags = []
        rb, f1 = norm_review_by(r["review_by"])
        if f1: flags.append(f1)
        tg, f2 = norm_trigger(r["trigger"])
        if f2: flags.append(f2)
        src_raw = r["source"]
        if src_raw in EMPTY:
            flags.append("kilde_mangler")
            sources = []
        else:
            sources = [{"url": src_raw, "quote": None, "verified_at": None}]
            flags.append("kildesitat_mangler_i_registeret")
        st = r["status"]
        if "UVERIFISERT" in st.upper():
            flags.append("status_uverifisert")
        if "KORRIGERT" in st.upper():
            flags.append("status_korrigert")
        if "KONFLIKT" in st.upper():
            flags.append("status_konflikt")
        if "FORFALT" in st.upper() or "UTGÅTT" in st.upper() or "UTGÅENDE" in st.upper():
            flags.append("status_forfalt")

        if r["id"] == "NAV-01":
            values = g_history()
            flags = [f for f in flags if f not in
                     ("kilde_mangler", "kildesitat_mangler_i_registeret")]
            flags.append("historikk_hentet_verbatim_fra_nav.no")
        else:
            found = extract_values(r["claim"])
            vf = extract_valid_from(r["claim"])
            if not found:
                values = []
                flags.append("value_not_extractable")
            else:
                values = [{"value": f["value"], "unit": f["unit"],
                           "valid_from": vf, "valid_to": None,
                           "context": f["context"], "sources": sources}
                          for f in found]
                if len(found) > 1:
                    flags.append("flere_verdier_uten_strukturert_merkelapp")
                if vf is None:
                    flags.append("valid_from_mangler")

        fact = {
            "id": r["id"], "domain": dom, "claim": r["claim"],
            "legal_basis": None if r["legal_basis"] in EMPTY else r["legal_basis"],
            "register_status": st, "review_trigger": tg, "review_by": rb,
            "section": r["section"], "values": values, "flags": sorted(set(flags)),
        }
        if fact["legal_basis"] is None:
            fact["flags"] = sorted(set(fact["flags"] + ["legal_basis_mangler"]))
        for f in fact["flags"]:
            flagcount[f.split(":")[0]] = flagcount.get(f.split(":")[0], 0) + 1
        by_domain.setdefault(dom, []).append(fact)
        all_facts.append(fact)

    os.makedirs(OUT, exist_ok=True)
    header = {"schema_version": "1.0",
              "generated_from": {"register": os.path.basename(REG), "sha256": reg_sha,
                                 "converted_at": FETCHED}}
    for dom, facts in sorted(by_domain.items()):
        with open(os.path.join(OUT, f"{dom}.yaml"), "w", encoding="utf-8") as f:
            yaml.safe_dump({**header, "domain": dom, "facts": facts}, f,
                           allow_unicode=True, sort_keys=False, width=100)
    print(f"\nskrevet {len(by_domain)} domenefiler til data/:")
    for dom, facts in sorted(by_domain.items()):
        nv = sum(1 for x in facts if x["values"])
        print(f"  {dom:22s} {len(facts):3d} fakta   {nv:3d} med verdi   "
              f"{len(facts)-nv:3d} uten")
    print(f"\ntotalt: {len(all_facts)} fakta, "
          f"{sum(1 for f in all_facts if f['values'])} med minst én verdi, "
          f"{sum(1 for f in all_facts if f['flags'])} med minst ett flagg")
    print("\nflagg:")
    for k, v in sorted(flagcount.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k}")
    json.dump({"n_facts": len(all_facts), "flags": flagcount,
               "register_sha256": reg_sha,
               "n_with_value": sum(1 for f in all_facts if f["values"]),
               "per_domain": {d: len(v) for d, v in by_domain.items()}},
              open(os.path.join(ROOT, "conversion_report.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
