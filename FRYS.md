# Frys-lesning av README.md

Lest fra disk, mot `RAPPORT/*.md` og `PREREG/*.md`, ikke mot noen oppsummering i minnet.
Kjørt 2026-10-09, før deponering.

---

## Runde 1 — fire funn

### FUNN 1 (reelt, alvorligst): deponeringen inneholdt et fragment av de tilbakeholdte dataene

`src/exclusion_check.py` ble lagt til for å gjøre README-ets eksklusjonstabell
reproduserbar. Scriptet skanner hele repoet — **inkludert seg selv** — og feilet
umiddelbart:

```
5-word windows: 262 unique -> 1 hit(s)  [<frasen>]
largest share of any single prompt recoverable: 12.5%
FAILED — do not deposit
```

Årsaken: jeg hadde sitert den kolliderende frasen ordrett i scriptets docstring og i
README, for å forklare hvorfor kollisjonen var harmløs. Dermed var et femords-fragment av
`hei_refusal` skrevet inn i nettopp det repoet som skulle være fritt for det.

Innholdet var harmløst — en alminnelig norsk frase uten identifiserende verdi — men regelen
er 0 treff, og å sitere biter av tilbakeholdte data for å forklare at de ikke betyr noe er
feil uansett hvor små bitene er.

**Rettet:** frasen fjernet fra både script og README; begge beskriver den nå uten å
gjengi den. Ny kjøring: `CLEAN`, 0 treff på alle fire vindusstørrelser, 0,0 %
rekonstruerbarhet.

**Merk at det var den automatiske sjekken som fanget dette, ikke lesningen.** Min egen
første skanning rapporterte 0 treff, fordi den kjørte før scriptet eksisterte.

### FUNN 2 (reelt): tall i README uten opphav i noen rapport

Regel (a) krever at hvert tall i README finnes ordrett i en RAPPORT. Eksklusjonstabellens
tall — **235**, **211**, **187** vinduer — finnes i ingen rapport. De er nye målinger gjort
i selve deponeringssteget.

Funnet slapp gjennom kontroll (a) fordi mitt eget sjekkeregex bare så på desimaltall,
brøker og prosent, ikke på bare heltall. Kontrollen hadde et hull.

**Rettet på to måter.** Sjekken utvidet til heltall. Og tallene gjort etterprøvbare i
stedet for å slettes: `src/exclusion_check.py` er lagt ved, og README sier nå eksplisitt
at disse seks figurene ikke er fra en fase-rapport, men målt ved deponering med det
scriptet.

### FUNN 3 (feil i kontrollen, ikke i README)

Kontroll (c) meldte «påstår presisjonsforbedring i 3c». Linjen den traff på var:

> **No claim that precision improved in fase 3c.** It did not, measurably.

En negasjon. Mønsteret håndterte ikke «No claim that …». **Kontrollen rettet**, README
uendret.

### FUNN 4 (alvorligst av kontrollfeilene): to av tre (c)-kontroller kunne ikke feile

Kontrollen for det viktigste forbeholdet i hele deponeringen — at «proben er overflødig»
må bære McNemar-forbeholdet — søkte etter det **norske** ordet «overflødig» i et
**engelsk** dokument. Ordet finnes ikke der. Runde 1 meldte «ok» fordi betingelsen
`"overflødig" in readme` var usann; runde 2 meldte «FUNN» av samme grunn. Begge var
vakuøse: kontrollen testet ingenting.

Sammen med FUNN 3 betyr det at **to av tre overclaim-kontroller ikke kunne feile** — én på
negasjon, én på språk. En kontroll som ikke kan feile er verre enn ingen kontroll, fordi
den gir dekning.

**Rettet:** kontrollene søker nå på engelsk (`superfluous`, `works/succeeded/validated`),
krever at både «McNemar» og «distinguishable from» står innenfor 1200 tegn etter
påstanden, og håndterer negasjon. Hele lesningen er lagt ved som `frys_read.py`, slik at
den kan kjøres på nytt framfor å tas på tro.

**README var substansielt riktig hele veien** på dette punktet: eneste forekomst av
«superfluous» er overskriften på selve forbeholds-avsnittet, umiddelbart fulgt av
McNemar-tallene. Men det visste jeg ikke før kontrollen faktisk testet det.

---

## Rundens øvrige kontroller, runde 1

| kontroll | utfall |
|---|---|
| (a) hvert desimaltall/brøk i README finnes ordrett i en RAPPORT | rent (15 av 15 nøkkeltall sporet til navngitt rapport) |
| (b) påstander mot tabeller | rent |
| (c) «virker» der rapporten sier «virker ikke» | rent |
| (c) «proben er overflødig» uten McNemar-forbeholdet i nærheten | rent |
| (d) uverifiserte eksterne tall | ingen — eneste eksterne referanse er OSF `vz8xj`, uten tall |
| (e) stale status: SimpleAudit-grenen | rent — README sier «has not been pushed» og `default_enabled: False` |

---

## Runde 2 — etter retting

Alle kontroller kjørt på nytt med `frys_read.py`: heltallssjekk, negasjonshåndtering,
engelske søkeord, og grunnlaget for regel (a) utvidet til fase 0 og 2 sine egne deponerte
dokumenter (ADR-0001, `hale/README.md`, register-YAML-ene), siden de to fasene ikke har
noen rapport å måles mot.

Full logg i `FRYS-runde2.txt`. **RESULTAT: REN** — 0 tall uten opphav, 15 av 15 nøkkeltall
sporet til navngitt rapport, 0 ubetingede «works/succeeded/validated», forbeholdet står
der det skal, alle tre verdikter ordrett til stede, status om SimpleAudit-grenen korrekt,
og eksklusjonssjekken `CLEAN`.

---

## To ting lesningen ikke kan fange, ført som kjent begrensning

1. **At et tall finnes ordrett i en rapport beviser ikke at det er brukt riktig.**
   Kontroll (b) sammenligner tall mot navngitt rapport, men en setning kan sitere riktig
   tall om feil ting. De 15 nøkkeltallene er derfor også lest manuelt mot sin kontekst i
   rapporten.

2. **Fase 0 og fase 2 har ingen PREREG og ingen RAPPORT å lese README mot.** Påstandene om
   dem — 118 rader, 43 med verdi, 75 uten, 117/46/30 flagg — er sjekket mot
   `register/conversion_report.json` og mot `src/register/data/*.yaml` direkte, ikke mot en
   rapport. Det er en svakere forankring enn de fem andre fasene har, og README sier
   eksplisitt at disse to fasene ikke er preregistrert.
