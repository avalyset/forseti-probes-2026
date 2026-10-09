"""Frys-lesning av README mot det deponerte materialet. Kjores fra pub1/."""
import glob, os, re, subprocess, sys

readme = open("README.md", encoding="utf-8").read()
# Grunnlag for regel (a): fase 1-3c har RAPPORT og PREREG. Fase 0 og 2 har ingen,
# sa deres egne deponerte dokumenter er grunnlaget for pastander om dem.
ground = "\n".join(open(p, encoding="utf-8").read() for p in
                   glob.glob("RAPPORT/*.md") + glob.glob("PREREG/*.md") +
                   ["docs/ADR-0001-yaml-i-git.md", "src/register/hale/README.md"] +
                   glob.glob("src/register/data/*.yaml"))
NUM = re.compile(r"\b\d+[,.]\d+\b|\b\d{1,3}/\d{1,3}\b|\b\d{2,}\s?%|\b\d{2,}\b")
SKIP = ("ORCID", "0009-", "Apache-2", "CC BY 4", "python3.13", "nb-bert", "nb-llama",
        "3.1-8b", "LICENSE", "2026-10-09", "vz8xj", "exclusion_check", "ADR-0001",
        "| 5-word", "| 6-word", "| 7-word", "| 8-word", "| largest share")
# terskler og strukturtall som defineres i PREREG eller er rene tellinger av dette repoet
EXEMPT = {"0,90", "1,00", "0,0", "83", "2026", "0,88"}
fails = []

bad = []
for line in readme.split("\n"):
    if any(s in line for s in SKIP):
        continue
    for m in NUM.finditer(line):
        t = m.group(0).strip()
        if t in EXEMPT or t in ground:
            continue
        bad.append((t, line.strip()[:84]))
print(f"(a) tall uten opphav i deponert kildemateriale: {len(bad)}")
for t, l in bad:
    print(f"    «{t}»  {l}")
fails += bad

print("\n(b) noekkeltall mot navngitt rapport:")
R = {os.path.basename(p)[:-3]: open(p, encoding="utf-8").read() for p in glob.glob("RAPPORT/*.md")}
for tok, rep in [("0,870", "fase1"), ("0,471", "fase1"), ("0,410", "fase1b"),
                 ("0,566", "fase1b"), ("0,852", "fase3"), ("0,867", "fase3"),
                 ("0,910", "fase3"), ("1/13", "fase3"), ("0,6914", "fase3b"),
                 ("45,0 %", "fase3b"), ("0,8642", "fase3c"), ("0,8765", "fase3c"),
                 ("13/13", "fase3c"), ("0,219", "fase3c"), ("0,002", "fase3c")]:
    ok = tok in readme and tok in R.get(rep, "")
    if not ok:
        fails.append((tok, rep))
    print(f"    {tok:9s} -> {rep:7s} {'ok' if ok else 'FUNN'}")

print("\n(c) metrikk-overclaim:")
# «virker» uten «ikke» om en fase som konkluderte «virker ikke»
m = re.findall(r"[^.\n]*\b(?:works|succeeded|validated)\b[^.\n]*", readme, re.I)
m = [x for x in m if not re.search(r"\bnot\b|no claim|does not", x, re.I)]
print(f"    ubetingede «works/succeeded/validated»: {len(m)} "
      f"{'ok' if not m else 'FUNN: ' + str(m[:2])}")
fails += [("works", x) for x in m]
# presisjonsforbedring
p = re.findall(r"[^.\n]*precision (?:improved|rose|increased)[^.\n]*", readme, re.I)
pn = [x for x in p if re.search(r"no claim|did not|\bnot\b", x, re.I)]
print(f"    presisjonsforbedring: {len(p)} treff, {len(pn)} negerte "
      f"{'ok' if len(p) == len(pn) else 'FUNN'}")
if len(p) != len(pn):
    fails.append(("precision", "uneg"))
# forbeholdet MA sta naer pastanden - sok pa ENGELSK, som dokumentet er
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

print("\n(d) eksterne tall:")
ext = re.findall(r"(?:OSF|osf\.io|github\.com)[^\s)]*", readme)
print(f"    eksterne referanser uten tallpastand: {sorted(set(ext))}")

print("\n(e) stale status:")
for s in ["has not been pushed", "default_enabled: False"]:
    o = s in readme
    print(f"    «{s}»: {'ok' if o else 'FUNN'}")
    if not o:
        fails.append((s, "mangler"))

r = subprocess.run([sys.executable, "-I", "src/exclusion_check.py",
                    "/Volumes/Vault/forseti/p1/data/scenarios.jsonl"],
                   capture_output=True, text=True)
last = r.stdout.strip().splitlines()[-1] if r.stdout else "(ingen utdata)"
print(f"\neksklusjonssjekk: {last}")
if "CLEAN" not in last:
    fails.append(("eksklusjon", last))

print("\n" + ("RESULTAT: REN" if not fails else f"RESULTAT: {len(fails)} FUNN"))
sys.exit(1 if fails else 0)
