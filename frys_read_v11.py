"""Frys-lesning av README mot det deponerte materialet, v1.1. Kjores fra repo-rota.

Tre slag kontroll, og skillet mellom dem er hele poenget:

  (a)-(e)  som i v1.0: hvert tall i README skal finnes ordrett i et deponert
           dokument, noekkeltall skal staa i den rapporten README navngir,
           metrikk-pastander skal ikke overdrive, og statusopplysninger om
           verden utenfor skal vaere daterte.
  (f)      NYTT: tall README oppgir som «maalt ved deponering» blir MAALT PAA
           NYTT her, ved aa kjore kommandoen som produserer dem. Et tall som
           bare finnes i en rapport er sporet; et tall som re-maales er
           verifisert. 2b og vakta har ingen RAPPORT, saa (f) er det eneste
           grunnlaget de kan ha.
  (g)      eksklusjonssjekken. Vindusskanningen krever den tilbakeholdte fila.
           Uten den rapporteres den som AAPENT PUNKT, ikke som bestaatt - og
           de to delkontrollene som ikke trenger fila kjores likevel.

frys_read.py er beholdt urort som v1.0-artefakt. Den kan ikke lese dette
README-et: grunnlaget dens kjenner ikke 2b eller vakta.

  python -I frys_read_v11.py [sti/til/scenarios.jsonl]
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(ROOT, "src", "register")
PY = sys.executable
fails: list[tuple[str, str]] = []


def read(p):
    return open(p, encoding="utf-8").read()


def run(args, cwd):
    r = subprocess.run([PY, "-I"] + args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


readme = read(os.path.join(ROOT, "README.md"))

# Grunnlag for regel (a). Fase 1-3c har RAPPORT og PREREG. Fase 0, 2, 2b og
# vakta har ingen, saa deres egne deponerte dokumenter er grunnlaget.
GROUND_FILES = (
    glob.glob(os.path.join(ROOT, "RAPPORT", "*.md"))
    + glob.glob(os.path.join(ROOT, "PREREG", "*.md"))
    + [os.path.join(ROOT, "docs", "ADR-0001-yaml-i-git.md"),
       os.path.join(ROOT, "docs", "ADR-0002-lovendringer.md"),
       os.path.join(ROOT, "docs", "forkortelser-lovdata.md"),
       os.path.join(REG, "hale", "README.md"),
       os.path.join(REG, "lovkart.yaml"),
       os.path.join(REG, "conversion_report.json"),
       os.path.join(REG, "lovtidend", "rapporter", "impact.md"),
       os.path.join(REG, "lovtidend", "fetch.py"),
       os.path.join(REG, "lovtidend", "impact.py")]
    + glob.glob(os.path.join(REG, "data", "*.yaml"))
    + glob.glob(os.path.join(REG, "vakt", "rapporter", "*.md"))
)
ground = "\n".join(read(p) for p in GROUND_FILES)

NUM = re.compile(r"\b\d+[,.]\d+\b|\b\d{1,3}/\d{1,3}\b|\b\d{2,}\s?%|\b\d{2,}\b")
SKIP = ("ORCID", "0009-", "Apache-2", "CC BY 4", "python3.13", "nb-bert", "nb-llama",
        "3.1-8b", "LICENSE", "2026-10-09", "vz8xj", "exclusion_check", "ADR-0001",
        "ADR-0002", "CITATION.cff", "cff-version",
        "| 5-word", "| 6-word", "| 7-word", "| 8-word", "| largest share",
        "zenodo", "Zenodo", "SimpleAudit/pull")
# Terskler, strukturtall og rene tellinger av dette repoet. Hvert tall som
# staar her maa daekkes av (f) eller av en SKIP-linje over.
EXEMPT = {"0,90", "1,00", "0,0", "83", "2026", "0,88", "1.1.0", "1.0.0",
          "97", "43", "121", "46", "20", "18", "77", "15", "12", "51"}
# Tall README selv oppgir som maalt ved deponering. Hvert av dem MAA ha en
# linje i (f) som maaler det paa nytt; MEASURED_COVERED under sjekker det.
MEASURED = {"5/5", "20/20", "1235", "146", "38", "12", "10", "8"}
EXEMPT |= MEASURED

print("=== (a) tall uten opphav i deponert kildemateriale ===")
bad = []
for line in readme.split("\n"):
    if any(s in line for s in SKIP):
        continue
    for m in NUM.finditer(line):
        t = m.group(0).strip()
        if t in EXEMPT or t in ground:
            continue
        bad.append((t, line.strip()[:84]))
print(f"    {len(bad)} uten opphav")
for t, l in bad:
    print(f"    «{t}»  {l}")
fails += bad

print("\n=== (b) noekkeltall mot navngitt rapport ===")
R = {os.path.basename(p)[:-3]: read(p) for p in glob.glob(os.path.join(ROOT, "RAPPORT", "*.md"))}
R["impact"] = read(os.path.join(REG, "lovtidend", "rapporter", "impact.md"))
R["vakt_2026-10-09"] = read(os.path.join(REG, "vakt", "rapporter", "vakt_2026-10-09.md"))
R["vakt_2027-05-02"] = read(os.path.join(REG, "vakt", "rapporter", "vakt_2027-05-02.md"))
R["ADR-0002"] = read(os.path.join(ROOT, "docs", "ADR-0002-lovendringer.md"))
for tok, rep in [("0,870", "fase1"), ("0,471", "fase1"), ("0,410", "fase1b"),
                 ("0,566", "fase1b"), ("0,852", "fase3"), ("0,867", "fase3"),
                 ("0,910", "fase3"), ("1/13", "fase3"), ("0,6914", "fase3b"),
                 ("45,0 %", "fase3b"), ("0,8642", "fase3c"), ("0,8765", "fase3c"),
                 ("13/13", "fase3c"), ("0,219", "fase3c"), ("0,002", "fase3c"),
                 # 2b
                 ("4499", "impact"), ("93,6 %", "impact"), ("6,4 %", "impact"),
                 ("LØST 70 · DOKUMENT 11", "ADR-0002"),
                 # vakt
                 ("46 (38.0%)", "vakt_2026-10-09"), ("1 (0.8%)", "vakt_2026-10-09"),
                 ("9** (7.4%)", "vakt_2026-10-09"), ("4 av 4", "vakt_2026-10-09"),
                 ("116 123, 23 32 70 00", "vakt_2026-10-09")]:
    ok = tok in readme and tok in R.get(rep, "")
    if not ok:
        fails.append((tok, rep))
    print(f"    {tok:24s} -> {rep:16s} {'ok' if ok else 'FUNN'}")

print("\n=== (c) metrikk-overclaim ===")
m = re.findall(r"[^.\n]*\b(?:works|succeeded|validated)\b[^.\n]*", readme, re.I)
m = [x for x in m if not re.search(r"\bnot\b|no claim|does not", x, re.I)]
print(f"    ubetingede «works/succeeded/validated»: {len(m)} "
      f"{'ok' if not m else 'FUNN: ' + str(m[:2])}")
fails += [("works", x) for x in m]
p = re.findall(r"[^.\n]*precision (?:improved|rose|increased)[^.\n]*", readme, re.I)
pn = [x for x in p if re.search(r"no claim|did not|\bnot\b", x, re.I)]
print(f"    presisjonsforbedring: {len(p)} treff, {len(pn)} negerte "
      f"{'ok' if len(p) == len(pn) else 'FUNN'}")
if len(p) != len(pn):
    fails.append(("precision", "uneg"))
i = readme.lower().find("superfluous")
near = readme[i:i + 1200] if i >= 0 else ""
ok = i < 0 or ("mcnemar" in near.lower() and "distinguishable from" in near.lower())
print(f"    «superfluous» med McNemar + «distinguishable from» innen 1200 tegn: "
      f"{'ok' if ok else 'FUNN'}")
if not ok:
    fails.append(("superfluous", "uten forbehold"))
for v in ["«trenger data»", "«overfører ikke»", "«virker ikke»"]:
    o = v in readme
    print(f"    verdikt {v}: {'ok' if o else 'FUNN'}")
    if not o:
        fails.append((v, "mangler"))
# 2b-spesifikt: paragrafnivaa maa ikke fremstilles som bredt tilgjengelig, og
# baklengs-testen maa ikke oppgis som paragrafnivaa.
for pat, needs, label in [
        (r"5/5", ["document level"], "baklengs 5/5 uten dokumentnivaa-forbehold"),
        (r"6,4 %", ["not most of them", "document level"], "6,4 % uten konsekvens"),
        (r"4 av 4", ["121"], "vakt-tallene uten registerstorrelse")]:
    j = readme.find(pat.replace(r"\\", ""))
    seg = readme[max(0, j - 400):j + 1600].lower() if j >= 0 else ""
    o = j < 0 or any(n.lower() in seg for n in needs)
    print(f"    {label}: {'ok' if o else 'FUNN'}")
    if not o:
        fails.append((label, "mangler forbehold"))

print("\n=== (d) eksterne tall ===")
ext = re.findall(r"(?:OSF|osf\.io|github\.com|lovdata\.no|api\.lovdata\.no)[^\s)]*", readme)
print(f"    eksterne referanser: {sorted(set(ext))}")
# Lovdata-prisene staar i ADR-0002 som ANNENHANDS og skal ikke gjentas i README.
for price in ["12 500", "15 000", "6 500"]:
    o = price not in readme
    print(f"    annenhaands pris «{price}» ikke gjentatt i README: {'ok' if o else 'FUNN'}")
    if not o:
        fails.append((price, "annenhaands pris i README"))

print("\n=== (e) stale status ===")
for s_, why in [("open, not merged", "PR-status datert"),
                ("default_enabled: False", "dommerens standardtilstand"),
                ("SimulaMet/SimpleAudit/pull/105", "PR-lenke"),
                ("This corrects ADR-0002", "vilkaarsrettelsen"),
                ("that was true when written", "gammel status merket")]:
    o = s_ in readme
    print(f"    «{s_}»: {'ok' if o else 'FUNN'}  ({why})")
    if not o:
        fails.append((s_, "mangler"))

print("\n=== (f) tall maalt ved deponering, re-maalt naa ===")


MEASURED_SEEN: list = []


def measured(label, expect, got, extra=""):
    MEASURED_SEEN.append(expect)
    ok = (expect == got)
    if not ok:
        fails.append((label, f"README {expect!r} != maalt {got!r}"))
    print(f"    {label:46s} README {str(expect):14s} maalt {str(got):14s} "
          f"{'ok' if ok else 'FUNN'}{extra}")


# f1: resolve_lovkart --check
rc, out = run([os.path.join(REG, "resolve_lovkart.py"), "--check"], REG)
tab = next((l.strip() for l in out.splitlines() if l.startswith("LØST")), "")
measured("resolve_lovkart --check exit 0", 0, rc)
measured("LØST 77 · DOKUMENT 7 · … (README)",
         "LØST 77  DOKUMENT 7  DELVIS 2  TVETYDIG 3  ULØST 0  UTENFOR 32", tab)
readme_tab = "LØST 77 · DOKUMENT 7 · DELVIS 2 · TVETYDIG 3 · ULØST 0 · UTENFOR 32"
measured("tabellen staar ordrett i README", True, readme_tab in readme)

# f2: trigger x utfall — «15 of 20 LOVENDRING»
sys.path.insert(0, REG)
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("rl", os.path.join(REG, "resolve_lovkart.py"))
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)
rows, kart = rl.load_register(), rl.load_lovkart()
res, _ = rl.resolve(rows, kart)
lov = [r for r in res if r["trigger"] == "LOVENDRING"]
measured("registerrader i alt", 121, len(res))
measured("LOVENDRING-rader", 20, len(lov))
measured("LOVENDRING paa paragrafniva (LØST)", 15,
         sum(1 for r in lov if r["verdict"] == "LØST"))
measured("«15 of 20» staar i README", True, "**15 of 20**" in readme)

# f3: baklengs-testen mot deponert impact.json
imp = json.load(open(os.path.join(REG, "lovtidend", "rapporter", "impact.json"),
                     encoding="utf-8"))
by_legacy = {a["legacy_id"]: a for a in imp}
exp = [e for e in (kart.get("endringsvedtak") or []) if e.get("expected_hit")]
hit = 0
doc_only = 0
for e in exp:
    a = by_legacy.get(e["legacy_id"])
    got = {h["row"] for h in a["hits"]} if a else set()
    if set(e["expected_hit"]) <= got:
        hit += 1
    if a and all(h["level"] != "paragraf" for h in a["hits"]):
        doc_only += 1
measured("baklengs: forventede treff", 5, hit)
measured("baklengs: forventninger i lovkart", 5, len(exp))
measured("…av dem bare dokumentniva", 4, doc_only)
measured("baklengs, slik README skriver det", "5/5", f"{hit}/{len(exp)}")
measured("«5/5» staar i README", True, "5/5" in readme)
measured("treff i impact.json", 146, len(imp))
measured("rad-treff i alt i impact.json", 1235,
         sum(len(a["hits"]) for a in imp))

# f4: vakt-testene
rc, out = run([os.path.join(REG, "vakt", "test_vakt.py")], REG)
last = out.strip().splitlines()[-1] if out.strip() else ""
measured("vakt/test_vakt.py", "20/20 bestått", last)
measured("«20/20 bestått» staar i README", True, "20/20 bestått" in readme)

# f5: vakt-rapportens toppseksjon regenerert
rep = os.path.join(REG, "vakt", "rapporter", "vakt_2026-10-09.md")
tmp = os.path.join(ROOT, ".frys_vakt_regen.md")
rc, out = run([os.path.join(REG, "vakt", "run.py"), "--as-of", "2026-10-09",
               "--out", tmp], REG)
regen = read(tmp) if os.path.exists(tmp) else ""
dep = read(rep)
top = lambda t: t.split("## V1 utløp")[0]          # noqa: E731
measured("toppseksjon regenererer ordrett", True, top(dep) == top(regen))
v1v2 = lambda t: t.split("## V3 kildehelse")[0]    # noqa: E731
measured("V1+V2 regenererer ordrett", True, v1v2(dep) == v1v2(regen))


def count(t, pat):
    m = re.search(pat, t)
    return int(m.group(1)) if m else None


measured("V3 «aldri hentet», deponert (med snapshots)", 10,
         count(dep, r"\*\*(\d+) aldri hentet"))
measured("V3 «aldri hentet», regenerert (uten snapshots)", 20,
         count(regen, r"\*\*(\d+) aldri hentet"))
measured("V4 stille, deponert", 8, count(dep, r"\n(\d+) ÅRLIG-fakta"))
measured("V4 stille, regenerert", 18, count(regen, r"\n(\d+) ÅRLIG-fakta"))
if os.path.exists(tmp):
    os.remove(tmp)

# f6: scenariokoblingen — bruddets siste ledd
import yaml  # noqa: E402

spec2 = importlib.util.spec_from_file_location(
    "imp", os.path.join(REG, "lovtidend", "impact.py"))
I = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(I)
measured("impact.load_scenarios() med innebygd sti", 0, len(I.load_scenarios()))
ef = yaml.safe_load(read(os.path.join(ROOT, "data", "expected_facts.yaml")))
couplings = [(sc["id"], f["key"]) for sc in ef["scenarios"] for f in sc["facts"]
             if isinstance(f.get("register"), dict)]
measured("register-koblinger i deponert expected_facts.yaml", 3, len(couplings))
measured("treff i impact.json med scenariokobling", 0,
         sum(1 for a in imp for h in a["hits"] if h.get("scenarios")))
measured("«2 rows and 3 couplings» staar i README", True,
         "**2 rows and 3 couplings**" in readme)

# f7: fvl. i arkivet
fvl = [a["legacy_id"] for a in imp
       if any(h["ref"] == "lov/1967-02-10" for h in a["hits"])]
fvl_para = [a["legacy_id"] for a in imp
            if any(h["ref"] == "lov/1967-02-10" and h["level"] == "paragraf"
                   for h in a["hits"])]
measured("fvl.: kunngjoringer i arkivet", 5, len(fvl))
measured("fvl.: av dem paa paragrafniva", 2, len(fvl_para))
measured("LOV-2025-06-20-81 blant dem", True, "LOV-2025-06-20-81" in fvl)
measured("README navngir LOV-2025-06-20-81", True, "LOV-2025-06-20-81" in readme)

# f8: filtelling. To ulike spoersmaal, holdt fra hverandre:
#   BASE..MERGE  hva de to grenene 2b og registeret bringer inn
#   BASE..naa    alt som er nytt i v1.1, inkludert denne lesningen selv
BASE, MERGE = "6fe9e63", "4ab2938"


def git(*a):
    return subprocess.run(["git"] + list(a), cwd=ROOT,
                           capture_output=True, text=True).stdout


mstat = git("diff", "--name-status", BASE, MERGE)
measured("filer de to grenene legger til", 38,
         sum(1 for l in mstat.splitlines() if l.startswith("A")))
measured("filer de to grenene endrer", 5,
         sum(1 for l in mstat.splitlines() if l.startswith("M")))
base_files = set(git("ls-tree", "-r", "--name-only", BASE).split())

print("\n=== (g) eksklusjonssjekk ===")
src = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FORSETI_WITHHELD", "")
if src and os.path.exists(src):
    rc, out = run([os.path.join(ROOT, "src", "exclusion_check.py"), src], ROOT)
    last = out.strip().splitlines()[-1] if out.strip() else "(ingen utdata)"
    print(f"    full vindusskanning: {last}")
    if "CLEAN" not in last:
        fails.append(("eksklusjon", last))
else:
    print("    full vindusskanning (5/6/7/8 ord + rekonstruerbarhet): "
          "KAN IKKE KJORES - den tilbakeholdte fila finnes ikke paa denne maskinen.")
    print("    AAPENT PUNKT, ikke bestaatt kontroll. Ma kjores fra Vault for deponering.")
# Navngitte unntak: lesningen soker etter strengen, og lesningens egne
# dokumenter omtaler pakken ved navn - som FRYS.md og src/exclusion_check.py
# gjorde i v1.0. Bare NAVNET, aldri innhold. Listen staar ogsaa i README.
SELF = {"frys_read_v11.py", "FRYS-v1.1.md"}
# FRYS-v1.1.txt er denne kjoringens EGEN utdata. Nar loggen skrives med
# omdirigering er fila tom i det skanningen leser treet, saa et treff i den
# ville avhengt av kjorerekkefolgen framfor av innholdet. Den holdes derfor
# utenfor tellingen ved navn - ikke fordi innholdet er uten betydning, men
# fordi tallet ellers ikke er deterministisk. Innholdet er loggen av denne
# lesningen, som omtaler pakken ved navn akkurat som FRYS-v1.1.md.
OWN_OUTPUT = "FRYS-v1.1.txt"

files = [p for p in glob.glob(f"{ROOT}/**/*", recursive=True)
         if os.path.isfile(p) and "/.git/" not in p]
hits = []
files = [p for p in files if os.path.basename(p) != OWN_OUTPUT]
for p in files:
    try:
        if "hei_refusal" in open(p, encoding="utf-8", errors="ignore").read():
            hits.append(os.path.relpath(p, ROOT))
    except OSError:
        pass
under_data = [p for p in hits if p.startswith("data/") or "/data/" in p]
# Nytt i v1.1 = ikke sporet i v1.0-treet. Fanger ogsaa ucommittede filer.
new_files = {h for h in hits if h not in base_files}
in_new = sorted((set(hits) & new_files) - SELF)
measured("filer med strengen «hei_refusal», egen logg utenom", 12, len(hits))
for h in sorted(hits):
    print(f"      {h}{'   (lesningen selv, navngitt unntak)' if h in SELF else ''}")
measured("av dem under data/", 0, len(under_data))
measured("av dem nye i v1.1, lesningen unntatt", 0, len(in_new))
measured("unntakene er navngitt i README", True,
         all(x in readme for x in SELF | {OWN_OUTPUT}))

print("\n=== (f2) er hvert «maalt ved deponering»-tall faktisk maalt? ===")
for tok in sorted(MEASURED):
    covered = any(tok in str(x) for x in MEASURED_SEEN)
    print(f"    {tok:8s} daekket av en maalelinje: {'ok' if covered else 'FUNN'}")
    if not covered:
        fails.append((tok, "staar i MEASURED men maales ikke i (f)"))

print("\n" + ("RESULTAT: REN" if not fails else f"RESULTAT: {len(fails)} FUNN"))
for f, d in fails:
    print(f"  FUNN  {f}: {d}")
sys.exit(1 if fails else 0)
