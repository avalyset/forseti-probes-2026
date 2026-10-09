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

## Runde 2 (Vault, 2026-10-09)

Lesningen under ble først kjørt i en container uten arkivene, uten den tilbakeholdte fila,
uten Zenodo-token og uten tag-push. Runde 2 er samme lesning kjørt fra Vault etter at
disse manglene var borte, og den **feilet første gang** — 4 FUNN, `exit 1` — på nettopp det
containeren ikke kunne se: det deponerte konsekvenskartet var utdatert mot `lovkart.yaml`
(FUNN 13). Kartet er regenerert, README og forventningene i `frys_read_v11.py` er rettet, og
lesningen er kjørt på nytt til `REN`. Runde 2 la til kontroll (h) (tittelen) og fant at et
README-tall hadde feil etikett (FUNN 14). FUNN 8 og FUNN 12, som runde 1 lot stå, er rettet.

---

## Fjorten funn

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

**Oppdatering i runde 2:** strengene finnes nå. `5,9 %` og `94,1 %` er målt av `parse.py`
på 2024–2026 (265 av 4499) og står i README med omfang i samme setning; loggen er deponert
som `src/register/lovtidend/rapporter/parse_log.txt`. Det som manglet i runde 1 var ikke
tallene, men målingen.

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

**Oppdatering i runde 2:** arkivene lå på Vault, `parse.py` ble kjørt på nytt, og loggen er
deponert (`parse_log.txt`). Tallene er nå *sporet* til en deponert logg. De kan fortsatt
ikke re-måles fra deponeringen alene, fordi arkivene ikke er deponert; kontroll (f6b) regner
derfor prosentene fra tellingene i loggen i stedet for å slå dem opp.

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

### FUNN 8 (reell, rettet i v1.1): `impact.py` leser `data/expected_facts.yaml` relativt

`impact.py` sin `load_scenarios()` leste `expected_facts.yaml` fra en hjemmekatalog-sti.
I runde 1 hadde alle 1235 radtreff i den deponerte `impact.json` derfor tom
`scenarier`-kolonne. Koden som lukker bruddet ADR-0002 beskriver *fantes* — den har en
egen gren for klagefrist-tabellens etatsnavn → `NAV-KLAGE-01`, `SKATT-KLAGE-01`,
`LK-KLAGE-01` — men stien den leste overlevde ikke deponering. Samme logikk, pekt på den
deponerte `data/expected_facts.yaml`, løste **2 rader og 3 koblinger**.

Runde 1 lot det stå, fordi kartet ikke kunne regenereres uten arkivene, og en endret sti
ville latt koden og rapporten stå i utakt — et nytt FUNN 3, bare omvendt.

**Rettet i runde 2**, fra Vault der arkivene finnes: `impact.py` leser nå
`data/expected_facts.yaml` med sti relativt til treet, og kartet er regenerert fra arkivene
i samme operasjon, så kode og rapport ikke står i utakt. Resultat: `load_scenarios()` gir 2
rader og 3 koblinger, og **56 av 1296 radtreff** har et scenario, i **52** kunngjøringer
(`NAV-KLAGE-01` 38, `SKATT-KLAGE-01` 18; 29 på paragrafnivå, 27 på dokumentnivå). Kontroll
(f6) måler alle tallene. Forventningene runde 1 hadde for tilstanden før rettingen (0 og 0)
er byttet ut.

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

### FUNN 12 (arvet fra v1.0, rettet i v1.1): tittelen telte feil

Tittelen sa «six preregistered experiments». Det er **fem**: fase 1, 1b, 3, 3b og 3c.
Tabellen i README har sagt fem hele tiden, også i v1.0 — avviket var mellom tittelen og
dokumentets eget innhold, og det sto der da deponeringen ble publisert første gang.

**Rettet i v1.1.** Tittelen er «Forseti probes 2026: five preregistered experiments on
Norwegian public-service fact checking», som versjonsmetadata: Zenodo-postens tittel
(`zenodo_v1.1.json`), overskriften i README og `CITATION.cff`. Konsept-DOI-en er uendret, og
v1.0-posten beholder tittelen den ble publisert med, så en sitering av v1.0 peker fortsatt
på en post som heter det samme som den siterte. Runde 1 lot tittelen stå som den var;
runde 2 rettet den etter nytt oppdrag. README forklarer retten og at v1.0 beholder sin
tittel.

Lesningen fanget det ikke i runde 1. Ingen kontroll sammenlignet tittelen med tabellen
under den, og (a) ser bare tall med to eller flere siffer, så «six» i prosa går rett
gjennom. Det er en tredje måte en kontroll kan være blind på, ved siden av de to v1.0 fant:
negasjon og språk. Kontroll (h) lukker det: tittelen skal være lik i README, `CITATION.cff`
og `zenodo_v1.1.json`, den skal si «five», og ingen tekst skal påstå at tittelen står som den
er med vilje.

### FUNN 13 (reell, funnet i runde 2): det deponerte konsekvenskartet var utdatert mot `lovkart.yaml`

FUNN 1 førte de tre klagefristradene inn i `used_by` i `lovkart.yaml` (`7a1178c`) og fikk
`resolve_lovkart.py --check` til `exit 0`. Men `impact.json` er *generert* fra
`lovkart.yaml`, og den ble ikke regenerert, fordi containeren ikke hadde arkivene. Dermed var
`lovkart.yaml` og kartet ikke lenger samme tilstand, selv om kontrollen mellom register og
lovkart var grønn.

Regenerert fra arkivene gir `impact.py` **157** kunngjøringer og **1296** radtreff der den
deponerte filen hadde 146 og 1235. De 61 ekstra er de tre klagefristradene (`NAV-KLAGE-01`
38, `SKATT-KLAGE-01` 18, `LK-KLAGE-01` 5); ingen av de 1235 gamle falt bort, og ingen fikk
endret felt utenom `scenarier`. Avviket er isolert fra FUNN 8: med scenariokoblingen slått av
gir koden fortsatt 157 og 1296, så det kommer av lovkartet og ikke av stien.

Runde 1 skrev under «To substansielle funn» at `LK-KLAGE-01` «flagges også» på
forvaltningslovens kunngjøring. Det var ikke sant i det deponerte kartet; det er sant i det
regenererte. Det er samme feilklasse som FUNN 3 — en generert fil etterlatt på forrige
tilstand — og ingen kontroll fanget den, fordi (f) målte filen mot README, og begge var like
utdaterte. Runde 2 fanget den fordi forventningene ble kjørt mot et nylagd kart.

**Rettet:** kartet regenerert fra arkivene. `parse.py --years 2024 2025 2026` gir en
`parsed.jsonl` byte-identisk med fila `impact.py` leste (sha256 `61e0e47a…`, hele hashen i
`parse_log.txt`). README og forventningene i `frys_read_v11.py` er oppdatert til 157 og 1296.

### FUNN 14 (reell, funnet i runde 2): «93,6 % dokumentnivå» er en feil etikett på et riktig tall

README og `impact.py` sin docstring kaller 93,6 % «dokumentnivå tilgjengelig»
(`changesToDocuments`). Tallet er riktig, men det måler noe annet: andelen kunngjøringer
**uten `data-change-part`**. Av 2880 kunngjøringer (2025+2026) har 2546 (88,4 %) minst ett
endret dokument i `changesToDocuments`, mens 334 (11,6 %) ikke oppgir noen endring i det
hele tatt. På 2024–2026 er tallene 3927 av 4499 (87,3 %) og 572 (12,7 %). Kontroll (b) fant
det ikke, fordi den sjekker at tallet står i rapporten og ikke hva det teller. Det ble funnet
ved å spørre hva komplementet til 6,4 % er.

**Rettet i README, ikke i docstringen og ikke i `impact.md`**: begge er deponerte artefakter
og er ikke endret. README-raden heter nå «no paragraph level, so document level at best»,
sier at 87,3 % faktisk navngir et dokument, og sier at overskriften i `impact.md` bærer
2025+2026-tall uten omfang. Målingen er deponert i `parse_log.txt`.

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
| (f) 53 tall målt på nytt | rent — 53 av 53 |
| (f2) hvert «målt ved deponering»-tall har en målelinje | rent — 18 av 18 |
| (h) tittelen lik i README, `CITATION.cff` og `zenodo_v1.1.json`, og sier «five» | rent |
| (g) full vindusskanning, 5/6/7/8 ord | `CLEAN` — 0 treff, 0,0 % gjenopprettbart |
| (g) `hei_refusal` under `data/` | rent — 0 filer |
| (g) `hei_refusal`-strengen i filer nye i v1.1 | rent — 0, med ett navngitt unntak |

`FRYS-v1.1.txt` er full logg. **RESULTAT: REN**, `exit 0`.

De tre nye (c)-mønstrene er der fordi 2b inviterer til tre bestemte overdrivelser: at
baklengs-testen bestod *på paragrafnivå* (den gjorde det ikke), at paragrafnivå er bredt
tilgjengelig (6,4 % på 2025+2026), og at vaktens tall gjelder et større register enn 121 rader. Hvert
mønster krever at forbeholdet står innenfor samme avsnitt som påstanden, ikke bare et sted
i dokumentet — det var FUNN 4 i v1.0.

---

## Det åpne punktet fra runde 1 er lukket

Runde 1 kunne ikke kjøre eksklusjonssjekkens vindusskanning, fordi den krever den
tilbakeholdte `scenarios.jsonl` med de 47 `hei_refusal`-promptene, og rapporterte det som
**ÅPENT PUNKT, ikke som bestått kontroll** — en kontroll som ikke kunne kjøres er ikke en
kontroll som gikk gjennom, og det var den hardeste lærdommen fra v1.0.

**Kjørt i runde 2**, fra Vault, med den tilbakeholdte fila (sha256 begynner `7157b091`, lik
hashen fase 1-preregistreringen oppgir) og over den utpakkede release-tarballen: 0 treff av
262, 235, 211 og 187 vinduer ved 5, 6, 7 og 8 ord, 0,0 % av noen enkeltprompt
gjenopprettbart, 0 `hei_refusal`-filer under `data/`. Utskriften er `CLEAN`.

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

Vindusskanningen er dermed ikke lenger noe åpent punkt. `frys_read_v11.py` tar stien som
argument og kjører den som del av lesningen (g); uten argumentet rapporterer den fortsatt
skanningen som åpent punkt, ikke som bestått.

Deponeringen og taggen som runde 1 ikke kunne gjøre er gjort fra Vault etter at lesningen
ble `REN`. Versjons-DOI står i README, og taggen heter `v1.1.0`.

---

## Fire ting lesningen ikke kan fange, ført som kjent begrensning

De to første er arvet fra v1.0 og gjelder fortsatt. Den tredje er ny med 2b, den fjerde med runde 2.

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

4. **Et riktig tall kan ha feil etikett, og (a)–(f) ser ikke etiketten.** FUNN 14: 93,6 %
   var riktig målt og feil navngitt som «dokumentnivå». Kontrollene sjekker at tallet står i
   en rapport og at koden gir det, ikke hva tallet teller. Det ble funnet ved å lese tallet
   og spørre hva komplementet er, og det er den eneste kontrollen som finnes for det.
