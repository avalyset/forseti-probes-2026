# Frys-lesning av README.md, v1.1

Lest fra disk, mot `RAPPORT/*.md`, `PREREG/*.md`, ADR-ene, `lovkart.yaml`,
`lovtidend/rapporter/impact.md`, `vakt/rapporter/*.md` og `conversion_report.json` — ikke
mot noen oppsummering i minnet, og ikke mot oppdragsteksten.

Kjørt 2026-10-09, etter at `rekon/2b-lovdata` (`ea540cb`) og `register-3361df1`
(`ec0a17c`) var slått sammen i `main`. Merge-SHA `4ab29386c1de66f0c6780cfe38e5870dc59b9d26`.

Hele lesningen er lagt ved som `frys_read_v11.py`, og loggen som `FRYS-v1.1.txt`, slik at
den kan kjøres på nytt framfor å tas på tro. `frys_read.py` er beholdt urørt som
v1.0-artefakt; den kan ikke lese dette README-et, fordi grunnlaget dens ikke kjenner 2b
eller vakta.

**Én ting er nytt i metoden, og den er grunnen til at 2b og vakta kan deponeres i det
hele tatt.** De to har ingen RAPPORT å måles mot. Derfor har lesningen fått en kontroll
(f) som **måler tallene på nytt** ved å kjøre kommandoen som produserer dem, i stedet for
å slå dem opp i et dokument. Et tall som bare finnes i en rapport er *sporet*. Et tall som
re-måles er *verifisert*. Kontroll (f2) sjekker dessuten at hvert tall README oppgir som
«målt ved deponering» faktisk har en målelinje — en liste over unntak som ingen kontrollerer
er nøyaktig feilen runde 1 i v1.0 gjorde to ganger.

---

## Tolv funn

### FUNN 1 (alvorligst): prosjektets egen driftkontroll feilet på den sammenslåtte tilstanden

`resolve_lovkart.py --check` finnes nettopp for å feile når registeret og lovkartet driver
fra hverandre; ADR-0002 sier det med de ordene. Kjørt på `main` rett etter merge:

```
3 avvik mellom register og lovkart:
  rad LK-KLAGE-01 er ikke nevnt noe sted i lovkart.yaml
  rad NAV-KLAGE-01 er ikke nevnt noe sted i lovkart.yaml
  rad SKATT-KLAGE-01 er ikke nevnt noe sted i lovkart.yaml
exit 1
```

De tre klagefristradene var lagt inn i registeret på `register-3361df1`, men lovkartet var
bygget på `rekon/2b-lovdata`, før de fantes. Hver av de tre har en hjemmel kartet alt
kjenner — `fvl. § 29`, `ftrl. § 21-12`, `skfvl. § 13-4` — så de var usynlige for 2b uten
at noe sa det. `skfvl.` sto til og med i kartet med `used_by: []` og en note som sa at
ingen rad brukte den.

**Rettet:** de tre radene ført inn i `used_by` på dokumentet deres eget `legal_basis`
navngir. Notene som sa noe annet er skrevet om. `--check` gir nå `exit 0` og
«lovkart stemmer med registeret: 121 rader dekket».

Dette er den eneste feilen i runden som ville gjort deponeringen direkte selvmotsigende: et
kart som påstår å dekke registeret, ved siden av et register det ikke dekker.

### FUNN 2 (reell, og den som koster mest hvis den står): to rader løst til feil dokument

`NB-18` og `NB-23` oppgir `forskrift FOR-2018-07-01-1139 § 8` og `§ 6`. I kartet sto de i
`used_by` på **pliktavleveringslova**, fra rekognoseringen, da feltene deres bare sa
«pliktavleveringslova» uten paragraf. Resultatet var at de ble rapportert `LØST` med
forskriftens paragrafnummer parret med lovens dokument-ID. Feil i begge retninger: en
endring i lovens § 8 ville flagget `NB-18` uten grunn, og en endring i forskriftens § 8
ville ikke flagget den i det hele tatt.

**Rettet:** flyttet til forskriftens `used_by`. Det måtte bli en *flytting*, ikke et
tillegg: `check` tillater to dokumenter bare for fem navngitte rader, og `NB-18`/`NB-23` er
ikke blant dem. Designet krevde altså svaret — kontrollen var sterkere enn kartet.

### FUNN 3 (reell): generert fil og docstring etterlatt på 118 rader

`docs/forkortelser-lovdata.md` er generert av `resolve_lovkart.py`. Etter merge var den
fortsatt 118-radersversjonen: tabellen manglet de tre klagefristradene, og de fire
pliktavleveringsradene sto som `DOKUMENT` der registeret nå gir dem en paragraf.
Docstringen i `resolve_lovkart.py` sa «de 118 radenes».

**Rettet:** tabellen regenerert i begge kopiene (`docs/` og `src/register/docs/`, som er
identiske), docstring til 121. At filen *kunne* regenereres og avviket vises som en diff er
grunnen til at den er generert og ikke skrevet.

### FUNN 4 (feil i oppdraget, ikke i deponeringen): to av de forespurte tallene finnes ikke

Oppdraget ba om at README skulle bære «5,9 % paragrafnivå, 94 % dokumentnivå», ordrett fra
rapportene. **Ingen av de to strengene finnes noe sted i repoet.** Målingen som er deponert
er `93,6 %` dokumentnivå og `6,4 %` paragrafnivå, målt på årgangene 2025+2026, og den står
i `impact.md`, i `impact.py` sin docstring og i rapportens overskriftslinje.

README bærer de deponerte tallene. Et tall ingen rapport har er ikke et tall README kan ha,
uansett hvor det kom fra — det var FUNN 2 i v1.0, og regelen gjelder også når kilden er
oppdraget.

### FUNN 5 (reell begrensning): to tall i en deponert rapport kan ikke etterprøves fra deponeringen

`93,6 %` og `6,4 %` er **strengliteraler** i `impact.py`, skrevet inn i rapportens
overskrift. Skriptet som skriver dem regner dem ikke ut. Det er `parse.py` som måler dem, og
den trenger Lovtidend-arkivene, som ikke er deponert.

Det er ikke mistillit til tallene — `impact.py` sin docstring sier eksplisitt at de er
«malt pa 2025+2026», og hele poenget deres er at de **motsier** rekognoseringens antakelse,
altså en retting forfatteren gjorde mot seg selv. Men de er det eneste 2b-tallet som ikke
kan re-måles fra deponeringen, og README sier hvor de kommer fra. Arkivene er dessuten den
ene manglende inndataen hvem som helst kan skaffe: `fetch.py` henter dem uten konto, uten
nøkkel og uten skjema.

### FUNN 6 (reell): `vakt_2027-05-02.md` er en artefakt fra før rettingen

Den rapporten sier 118 fakta og 43 med verdi, og har en `FEIL`-linje som navngir `LK-12`
som et `ÅRLIG`-fakta uten `review_by`. Den ble generert før de tre klagefristradene og før
`LK-12` fikk `review_by: 2027-08`. Kjørt mot registeret som deponert gir samme dato 121
fakta, 46 med verdi og ingen `FEIL`-linje.

**Ikke regenerert, og det er et valg.** En ny kjøring ville endret V3 og V4 til det
dårligere, fordi `hale/snapshots/` er holdt utenfor deponeringen — se FUNN 7. Begge
rapportene er beholdt: den ene er dokumentasjon på at vakta fant noe, og rettingen er
grunnen til at den andre er ren. README forklarer hvorfor de to topptallene spriker, slik at
en leser ikke må gjette.

### FUNN 7 (reell begrensning): V3 og V4 reproduserer ikke fra deponeringen

Toppseksjonen, V1 og V2 i `vakt_2026-10-09.md` regenererer **ordrett** fra deponeringen —
kontrollert med streng likhet, ikke med øyemål. V3 og V4 gjør det ikke: de leser
`hale/snapshots/`, som er utelatt for størrelse. En ny kjøring melder 20 kilder «aldri
hentet» der den deponerte rapporten sier 10, og 18 stille `ÅRLIG`-fakta der den sier 8. Den
deponerte rapporten er den som ble laget med snapshotene til stede.

README sier dette med tallene i, framfor å si at rapporten «kan kjøres på nytt».

### FUNN 8 (reell, IKKE rettet): konsekvenskjedens siste ledd leser en sti utenfor deponeringen

`impact.py` sin `load_scenarios()` leser `expected_facts.yaml` fra en hjemmekatalog-sti.
Konsekvensen er at **alle 1235 radtreff i den deponerte `impact.json` har tom
`scenarier`-kolonne**. Koden som lukker bruddet ADR-0002 beskriver *finnes* — den har en
egen gren for klagefrist-tabellens etatsnavn → `NAV-KLAGE-01`, `SKATT-KLAGE-01`,
`LK-KLAGE-01` — men stien den leser overlever ikke deponering. Samme logikk, pekt på den
deponerte `data/expected_facts.yaml`, løser **2 rader og 3 koblinger**.

**Ikke rettet, og grunnen er at den ikke kan verifiseres herfra.** Et fall-back til den
deponerte fila er én linje, men kartet kan ikke regenereres uten arkivene, så koden og
rapporten ville blitt stående i utakt — et nytt FUNN 3, bare omvendt. Det er ført som
første punkt på hva som bør gjøres, med målingen vedlagt, framfor å bli rettet blindt.

### FUNN 9 (stale status, kontroll (e)): README v1.0 sin status om SimpleAudit-grenen var utdatert

v1.0 sa at grenen `feat/fact-judge` «has not been pushed». Den er nå pushet og ligger som
**åpen** pull request: [SimulaMet/SimpleAudit#105](https://github.com/SimulaMet/SimpleAudit/pull/105),
«Add a deterministic fact_check judge over metadata.facts», fra `avalyset:feat/fact-judge`
mot `SimulaMet:dev`. **Åpen, ikke merget** — lest fra PR-sida 2026-10-09.
`default_enabled: False` er verifisert mot fila på PR-grenen, ikke antatt fra v1.0.

README bærer nå statusen med dato, og sier at den gamle formuleringen var sann da den ble
skrevet. En udatert statuspåstand om verden utenfor er den eneste typen som garantert blir
feil over tid.

### FUNN 10 (vilkår): ADR-0002 sitt åpne spørsmål er avklart, og README bærer avklaringen

ADR-0002 lot Lovdatas vilkår stå som en motsetning, og skrev at ingen vilkårsside var lest
fordi `lovdata.no` og `api.lovdata.no` var egress-sperret (403 på CONNECT). I sesjonen som
bygget kjeden var de nåbare: `fetch.py` sin docstring oppgir at
`lovdata.no/info/vilkar` ble lest direkte 2026-10-09, med sha256 av sida.

**§ 2.3 unntar «Regelverk i Norsk Lovtidend» fra bruksbegrensningene i § 2.1 og § 2.2,
under NLOD 2.0, mot kildeangivelse.** KI-forbudet står i § 2.1/2.2 og gjelder Lovdatas egne
nettjenester, ikke NLOD-datasettene § 2.3 unntar. Samme punkt forbyr massenedlasting fra
nettsidene og henviser til de åpne API-ene, som er nettopp det `fetch.py` bruker. Forseti
trener ikke på teksten uansett.

ADR-en er deponert **urørt**, med sin egen «ikke lest»-advarsel intakt. README-avsnittet er
rettingen, og `fetch.py` sin docstring er primærkilden. Å redigere en datert
beslutningslogg i etterkant ville fjernet sporet av at grunnlaget var svakere da valget ble
tatt.

### FUNN 11 (reell, arvet fra v1.0): tre reproduksjonskommandoer kan ikke kjøres fra deponeringen

README v1.0 listet `hale/test_backwards.py`, `check_packs.py` og `test_check_packs.py`
under «How to reproduce» uten å si at de trenger materiale som ikke er deponert. Alle tre
feiler: den første på `hale/snapshots/`, de to andre på SimpleAudit-utsjekkingen. Kontrollert
ved å kjøre dem.

**Rettet:** README har nå en tabell over de fire manglende inndataene og hvilke kommandoer
hver av dem feller, og sier eksplisitt hvilke fire kommandoer som går ende til ende fra
deponeringen alene. Alle fire ble kjørt ved deponering.

### FUNN 12 (arvet fra v1.0, ikke rettet, og det er et valg): tittelen teller feil

Tittelen sier «six preregistered experiments». Det er **fem**: fase 1, 1b, 3, 3b og 3c.
Tabellen i README har sagt fem hele tiden, også i v1.0 — avviket er mellom tittelen og
dokumentets eget innhold, og det sto der da deponeringen ble publisert første gang.

**Ikke rettet.** Tittelen er den publiserte tittelen på en post med konsept-DOI, og
oppdraget holder den uendret. Å gi v1.1 et annet navn ville gjort at siteringen i v1.0
peker på noe som heter noe annet; det er en verre feil enn å telle én for mange, og den er
ikke reversibel. Avviket er i stedet skrevet ned i README med begrunnelsen, og her.

Lesningen fanget det ikke. Ingen kontroll sammenligner tittelen med tabellen under den, og
(a) ser bare tall med to eller flere siffer, så «six» i prosa går rett gjennom. Det er en
tredje måte en kontroll kan være blind på, ved siden av de to v1.0 fant: negasjon og språk.

---

## To substansielle funn 2b gjorde, som ikke er feil i deponeringen

Disse er ikke lesningens funn om README. De er 2b som gjør jobben sin, og de hører i
registerets kø.

1. **`fvl.` → `lov/1967-02-10` er korroborert mot Lovdatas egne data.** Det var den ene
   dokument-IDen i kartet ingen kilde hadde bekreftet, deponert som `ubekreftet` framfor å
   bli utelatt. Den opptrer som endret dokument i **fem** kunngjøringer i arkivet, to av
   dem på paragrafnivå (§ 12, § 51). `status`-feltet er **ikke** endret: vokabularet der
   beskriver hvordan rekognoseringen fant en ID, og en oppgradering er registerarbeid, ikke
   en konsekvens av denne lesningen. Beviset er skrevet inn i oppføringens note.

2. **`LOV-2025-06-20-81 — Lov om saksbehandlingen i offentlig forvaltning
   (forvaltningsloven)`** er én av de fem, i kraft «Kongen bestemmer», og oppgir at den
   endrer `lov/1967-02-10`. Kartet flagger `LK-01` (klagefrist 3 uker) på den, og etter
   FUNN 1 flagges `LK-KLAGE-01` også. **Hva en ny forvaltningslov gjør med treukersfristen
   er ikke avgjort her.** Deponeringen inneholder flagget, ikke en lesning av loven. Det er
   skillet hele registeret er bygget på.

---

## Rundens øvrige kontroller

| kontroll | utfall |
|---|---|
| (a) hvert tall i README har opphav i deponert materiale | rent — 0 uten opphav |
| (b) 24 nøkkeltall mot navngitt rapport | rent — 24 av 24 |
| (c) metrikk-overclaim, inkl. tre nye 2b/vakt-mønstre | rent |
| (d) eksterne tall | rent — og de annenhånds Lovdata-prisene i ADR-0002 er **ikke** gjentatt i README, kontrollert eksplisitt |
| (e) stale status: PR #105, `default_enabled`, vilkårsrettelsen | rent etter FUNN 9 og 10 |
| (f) 32 tall målt på nytt ved deponering | rent — 32 av 32 |
| (f2) hvert «målt ved deponering»-tall har en målelinje | rent — 8 av 8 |
| (g) `hei_refusal` under `data/` | rent — 0 filer |
| (g) `hei_refusal`-strengen i filer nye i v1.1 | rent — 0, med ett navngitt unntak |

`FRYS-v1.1.txt` er full logg. **RESULTAT: REN**, `exit 0`.

De tre nye (c)-mønstrene er der fordi 2b inviterer til tre bestemte overdrivelser: at
baklengs-testen bestod *på paragrafnivå* (den gjorde det ikke), at paragrafnivå er bredt
tilgjengelig (6,4 %), og at vaktens tall gjelder et større register enn 121 rader. Hvert
mønster krever at forbeholdet står innenfor samme avsnitt som påstanden, ikke bare et sted
i dokumentet — det var FUNN 4 i v1.0.

---

## Ett åpent punkt, og det blokkerer deponering

**Eksklusjonssjekkens vindusskanning er ikke kjørt.** `src/exclusion_check.py` krever den
tilbakeholdte `scenarios.jsonl` med de 47 `hei_refusal`-promptene, og denne maskinen holder
den ikke. Lesningen rapporterer det som **ÅPENT PUNKT, ikke som bestått kontroll** — en
kontroll som ikke kunne kjøres er ikke en kontroll som gikk gjennom, og det var den
hardeste lærdommen fra v1.0.

Det som *kunne* kontrolleres på v1.1-treet, og som er rent:

| kontroll | utfall |
|---|---|
| filer under `data/` med `hei_refusal` | **0** |
| filer med strengen `hei_refusal` i det hele tatt | **12** |
| av dem nye i v1.1, lesningens egne dokumenter unntatt | **0** |
| `hei_refusal`-innhold i de 43 filene de to grenene bringer inn | **0** |

De to unntakene er `frys_read_v11.py`, som inneholder navnet fordi den søker etter det, og
`FRYS-v1.1.md`, som rapporterer hva den fant — samme selvreferanse som
`src/exclusion_check.py` og `FRYS.md` har i v1.0. Begge er navngitt i skriptet, påstått i
README og kontrollert mot README der, så unntaket kan ikke utvides stille. Bare navnet,
aldri innhold.

**Og én ting mer, fordi tallet ellers ikke var deterministisk.** Loggen `FRYS-v1.1.txt` er
kjøringens egen utdata. Skrives den med omdirigering, er fila tom i det øyeblikket
skanningen leser treet, så et treff i den ville avhengt av kjørerekkefølgen framfor av
innholdet — to kjøringer på rad ga først 12, så 13. Den holdes derfor utenfor tellingen
**ved navn**, med grunnen skrevet inn i skriptet, og tallet er nå likt på to kjøringer etter
hverandre. Et tall som endrer seg med rekkefølgen er ikke en måling, og en telling man
justerer til den stemmer er verre enn ingen telling.

**Vindusskanningen ved 5, 6, 7 og 8 ord, og per-prompt-rekonstruerbarheten, må kjøres på
den utpakkede tarballen fra maskinen som holder fila, og må gi `CLEAN`, før v1.1.0
deponeres.** `frys_read_v11.py` tar stien som argument og kjører den da som del av
lesningen.

Zenodo-deponeringen er ikke kjørt av samme grunn i annen form: `ZENODO_TOKEN` er ikke satt
i dette miljøet.

Og et tredje, mindre punkt av samme slag: **taggen `v1.1.0` er laget, men ikke pushet.**
Hver push til en tagg-ref gir 403 i dette miljøet — kontrollert med både annotert og
lettvektstagg, mens grenpush til samme repo går gjennom, og ingenting ble opprettet på
fjernsiden. Commiten taggen peker på ligger på `main`. Taggen må settes og pushes fra samme
maskin som kjører deponeringen.

---

## Tre ting lesningen ikke kan fange, ført som kjent begrensning

De to første er arvet fra v1.0 og gjelder fortsatt. Den tredje er ny med 2b.

1. **At et tall finnes ordrett i en rapport beviser ikke at det er brukt riktig.**
   Kontroll (b) sammenligner tall mot navngitt rapport, men en setning kan sitere riktig
   tall om feil ting. De 24 nøkkeltallene er derfor også lest manuelt mot sin kontekst.

2. **Fase 0, 2, 2b og vakta har ingen PREREG og ingen RAPPORT å lese README mot.** For 2b
   og vakta er dette delvis bøtet med kontroll (f), som måler på nytt framfor å slå opp —
   et sterkere grunnlag enn fase 0 og 2 har. Men det er en annen slags forankring enn en
   preregistrert fase, og README sier eksplisitt at ingen av de fire er preregistrert.

3. **Kontroll (f) måler at koden gir det tallet README oppgir. Den sier ingenting om at
   koden måler det riktige.** `resolve_lovkart.py` kan være enig med seg selv og likevel
   løse en rad til feil dokument — det var nettopp FUNN 2, og den ble funnet ved å lese
   `legal_basis` mot utfallet, ikke av noen kontroll. En re-måling er sterkere enn et
   oppslag og svakere enn en lesning.
