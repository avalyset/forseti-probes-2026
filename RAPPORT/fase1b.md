# Forseti fase 1b — rapport

**PREREG-SHA:** `d35342b204365bd2c0ec807b4d803bb2d6e732cd` (commitet før enhver 1b-kjøring)
**Kjørt:** 2026-10-09, `/Volumes/Vault/forseti/p1b`, 0 remotes, ingenting publisert.
**Grunnlag:** fase 1, commit `746add9`.
**Kilde for pakkene:** `upstream/dev` @ `7a0877d` i `~/ClaudeWork/simpleaudit`, lest med
`git show` uten å røre arbeidstreet (en annen gren var sjekket ut der).
Ingen prompttekst fra `hei_refusal` i denne rapporten eller i figurene.

---

## Hovedfunnet, før alle tall

**De åtte pakkene inneholder ikke ett eneste `refuse`-scenario.** Merkingen ga
**85 av 85 `answer`**. Det gjør spørsmål A og B, slik de er spesifisert, strukturelt
ukjørbare — ikke vanskelige, men umulige: en refuse-detektor kan ikke trenes på null
positive eksempler.

Pakkene og `hei_refusal` måler to forskjellige ting. `hei_refusal` måler *om tjenesten
skal svare*. De åtte pakkene måler *om svaret er riktig*. Det er ingen felles etikettakse
mellom dem.

Jeg har ikke fabrikkert etiketter for å gjøre A og B kjørbare, og ikke trent på
`hei_refusal`. Under de to bindingene finnes én gyldig treningskilde (våre pakker, én
klasse) og ett gyldig testsett (de 47). Det tillater énklasse-metoder, og ikke mer.
A′ og B′ nedenfor er de nærmeste gyldige spørsmålene, med kriterier satt i PREREG før
kjøring.

---

## 1. Merking

Regelen (`src/label_rules.py`) ble skrevet **før** merking og måler tre uavhengige
signaler per scenario — krever `expected_behavior` at tjenesten *holder tilbake* svaret,
at den *henviser*, eller at den *oppgir innhold*? Etiketten er hovedsvaret: faktakrav
overstyrer støttende henvisning, fordi «forklar X, og anbefal å kontakte NAV» er et
innholdssvar.

| etikett | automatisk | etter manuell runde |
|---|---|---|
| answer | 82 | **85** |
| refer | 0 | **0** |
| refuse | 0 | **0** |
| uklar | 3 | 0 |

**Manuell andel: 3 av 85 = 3,5 %** (grensen var 30 %). Alle tre uklare hadde ledeverbet
«Svarer at …», som `FACTS`-mønsteret mitt ikke dekket — et hull i regelen, ikke i
scenariene. Hver avgjørelse er logget med begrunnelse og hvilket regelhull den avdekket i
`data/labels_manual.jsonl`.

Per pakke: nav_aap 15, nb_kryss_ordning 13, skatteetaten_legitimasjon 11,
toll_reisegodskvote 11, arbeidstilsynet_arbeidstid 11, skatteetaten 8, helfo 8,
lanekassen 8. Alle `answer`.

**Hvorfor også krisescenariene er `answer`.** Kategoriene *Crisis Response*,
*Dangerous Advice*, *Confidentiality* og *Hallucination* ser ut som avståelseskandidater,
men krever alle et substansielt svar. Hallusinasjonsscenariene krever «si tydelig at
ordningen ikke finnes» — et **korrekt negativt faktasvar**, ikke en avståelse. Det nærmeste
avståelse er «Avgrenser seg fra å gi personlig skatterådgivning», men samme scenario
krever først «Forklarer generelle forskjeller mellom AS og ENK skattemessig». Hovedsvaret
er innhold.

---

## 2. Spørsmål A — **ukjørbart**

> «LOO på de merkede pakkene (n≈85). Binært: refuse vs ikke-refuse.»

Den positive klassen er tom. Ingen tall oppgis. Merkefordelingen over er belegget.

## 3. Spørsmål A′ — per-domene-avvik

Figur: `figs/a_prime_domener.png`

**PREREGs eget kriterium var ugyldig, og kjøringen avslørte det.** Kriteriet var «den
utholdte pakkens median over 95-persentilen av avstandene *innenfor* treningspakkene».
Men avstandene innenfor måles på de samme punktene som kovariansen er tilpasset på, med
d = 768 ≫ n = 74. De er drastisk underestimerte, og **alle åtte pakker ble flagget,
15–120× over**. Det er en egenskap ved målestokken, ikke ved domenene.

Rettet, med begge sider målt **utenfor** utvalget (LOO-referanse for NB-BERT):

| pakke | mean (L10) ratio · z | cls (L8) ratio · z | nb-llama ratio · z |
|---|---|---|---|
| nb_kryss_ordning | 2,70 · **+4,07** ⚑ | 2,18 · +0,78 | 2,43 · +0,73 |
| arbeidstilsynet_arbeidstid | 2,66 · **+2,44** ⚑ | 1,38 · −0,01 | 1,29 · −0,66 |
| nav_aap | 3,33 · −0,24 | 3,84 · +0,65 | 2,58 · +0,91 |
| toll_reisegodskvote | 2,07 · +0,33 ⚑ | 1,21 · −0,72 | 1,27 · −0,68 |
| helfo | 2,41 · +0,07 ⚑ | 2,10 · +0,01 | 1,85 · +0,03 |
| skatteetaten | 2,34 · −0,07 | 3,94 · +1,75 | 1,84 · +0,01 |
| lanekassen | 2,18 · −1,02 | 1,66 · −0,70 | 1,15 · −0,84 |
| skatteetaten_legitimasjon | 1,61 · −1,61 | 1,61 · −0,17 | 1,83 · −0,01 |
| **flagget** | **4 av 8** | **0 av 8** | **0 av 8** |

Som oppdraget ber om: **rapportert, ikke tolket.** Det eneste domenet med påfallende
robust z noe sted er **nb_kryss_ordning** (+4,07 på mean), og det er konsistent positivt
på alle tre (+0,78, +0,73) uten å være ekstremt noe annet sted. Flaggingen er ikke
konsistent på tvers av poolingene — mean flagger fire, cls og nb-llama ingen — så
p95-terskelen er ustabil ved disse n-ene (referansen hviler på ~74 verdier, den utholdte
medianen på 8–15).

**Avvik:** nb-llama fikk en **grovere referanse**. LOO ved d = 4096 ble målt til 21,2 s per
tilpasning × 592 = **210 minutter**, uforholdsmessig for den minst informative delen.
Erstattet med 10-folds ut-av-utvalget-referanse regnet én gang på alle 85 og delt mellom
pakkene — derfor er `p95` identisk nedover nb-llama-kolonnen. Merket som grovere.

## 4. Spørsmål B — **ukjørbart**. Spørsmål B′ — overfører signalet uten refuse-eksempler?

Figur: `figs/b_prime.png`

Énklasse-manifold (Mahalanobis, Ledoit-Wolf-krymping) tilpasset på alle 85 pakkescenarier,
de 47 skåret, AUROC mot deres ekte etiketter. Lag forhåndsvalgt i PREREG til fase 1s
modale lag.

| backbone | B′ AUROC | 95 % KI | kNN-5 (robusthet) | fase 1 til sammenligning |
|---|---|---|---|---|
| nb-bert-base / mean (L10) | **0,410** | [0,255; 0,594] | 0,379 [0,228; 0,561] | 0,870 |
| nb-bert-base / [CLS] (L8) | **0,634** | [0,467; 0,801] | 0,640 [0,475; 0,805] | 0,866 |
| nb-llama-3.1-8b | **0,460** | [0,274; 0,646] | 0,515 [0,337; 0,690] | 0,852 |
| lengdebaseline (tokens) | 0,566 | [0,389; 0,730] | — | — |

### Konklusjon B′, ordrett per PREREG: **«overfører ikke»**

Alle tre konfidensintervall inneholder 0,50. Kriteriet for «overfører» (AUROC ≥ 0,70,
nedre grense > 0,55, og slår lengdebaselinen) er ikke oppfylt av noen. Beste backbone,
[CLS] på 0,634, har nedre grense 0,467 og ligger innenfor lengdebaselinens intervall.

**Mean-pool ligger systematisk under 0,50 — på alle 13 lag (0,264–0,450).** Retningen er
at refuse-promptene ligger *nærmere* forvaltningsmanifolden enn answer-promptene. Det er
konsistent, men intervallet dekker 0,50, så det rapporteres som retning, ikke som funn.

Post-hoc var [CLS] L12 best med 0,711. Det er **post-hoc** — lag ble forhåndsvalgt til L8,
og maksimum over 13 lag er ikke et estimat.

**Hva B′ ikke kan forklares bort med.** Både refuse- og answer-delen av de 47 er
ungdomshelse og like langt fra forvaltningspakkene i domene. En ren domeneeffekt ville
flyttet begge like mye og gitt AUROC ≈ 0,50. Separasjon over 0,50 måtte altså kommet fra
noe som skiller refuse fra answer *innenfor* samme domene. Den kom ikke.

**Hva dette betyr sammen med fase 1.** Samme representasjoner, samme testsett, samme
backbones gir 0,85–0,87 med 47 ekte refuse/answer-eksempler i treningen, og 0,41–0,63
uten. Signalet fase 1 fant er ikke noe som faller ut av «hvordan et legitimt norsk
forvaltningsspørsmål ser ut». Det må læres fra eksempler på avståelse.

---

## 5. Spørsmål C — kan kalibrering måles nå?

Figur: `figs/sporsmal_c.png`

### C1 — ved hvilken n blir ECE i det hele tatt en test?

| n | ECE-støygulv (median) | terskel = gulv + 0,03 | falsk alarm når modellen ER perfekt kalibrert |
|---|---|---|---|
| 47 | 0,1059 | 0,1359 | **15,2 %** |
| 85 | 0,0799 | 0,1099 | 9,2 % |
| **132** | 0,0655 | 0,0955 | **4,6 %** |
| 200 | 0,0531 | 0,0831 | 2,4 % |
| 500 | 0,0332 | 0,0632 | 0,1 % |
| 1000 | 0,0241 | 0,0541 | 0,0 % |

**Svaret er nei ved n = 47, og så vidt ja ved n ≈ 132.** Ved 47 stryker en perfekt
kalibrert modell på kriteriet i 15 % av tilfellene — testen anklager seg selv hver sjette
gang. Først ved rundt 132 faller falsk alarm under 5 %. Det er tallet å planlegge mot.

Til sammenligning: fase 1s absolutte krav ECE ≤ 0,10 lå **under** gulvet ved n = 47
(0,103–0,124). Det var ikke en streng test, det var ingen test.

### C2 — fase 1 skåret om mot det relative kriteriet

| backbone | ECE etter | gulv | terskel | margin | utfall |
|---|---|---|---|---|---|
| nb-bert-base / mean | 0,189 | 0,117 | 0,147 | +0,043 | ikke bestått |
| nb-bert-base / [CLS] | 0,159 | 0,103 | 0,133 | +0,026 | ikke bestått |
| **nb-llama-3.1-8b** | 0,151 | 0,124 | 0,154 | **−0,003** | **bestått** |

Under et kriterium som er relativt til hva n tillater å måle, klarer **én av tre**
backbones kalibreringskravet. Under fase 1s absolutte krav klarte ingen — og kunne ingen.
Marginen for nb-llama er −0,003, altså på terskelen, og ved n = 47 har den testen 15 %
falsk alarm. Det er ikke et bestått kalibreringsbevis; det er fraværet av et avvis.

**Grense:** ingen ny kalibrert klassifikator finnes i 1b, siden ingen toklasse-treningskilde
er tillatt. C er besvart på gulvkurven og på fase 1s prediksjoner, ikke på en ny modell.

---

## 6. Avvik fra PREREG

1. **A′-kriteriet var ugyldig** (avstand i utvalget som referanse). Oppdaget ved at alle
   åtte pakker ble flagget. Rettet med ut-av-utvalget-referanse på begge sider; begge
   kjøringer står i rapporten.
2. **nb-llamas A′-referanse ble grovere** enn NB-BERTs — 10-fold delt mellom pakkene
   framfor LOO per pakke. Målt grunn: 210 minutter.
3. **Ingen prompt fra `hei_refusal` ble brukt til trening**, og fase 1s hode ble ikke
   gjenbrukt. Å tilpasse det på alle 47 ville vært trening på `hei_refusal` i 1b. Det
   koster en informativ spesifisitetstest, og det er prisen for bindingen.
4. **`metadata.facts` finnes ikke i `upstream/dev`** — det ligger i åpen PR #103.
   `check_packs.py` leser det der det finnes og faller ellers tilbake på
   `expected_behavior` og `metadata.rationale`.
5. Merkeregelens `FACTS`-mønster manglet det bare ledeverbet «Svarer at», som ga de tre
   uklare. Rettet manuelt og logget, ikke ved å patche regelen i etterkant.

---

## 7. Diskbruk

| | før 1b | etter 1b | endring |
|---|---|---|---|
| **intern** (`/`) | 12,7 GiB brukt / 21,6 GiB ledig | 12,7 GiB brukt / 21,6 GiB ledig | **± 0,0 GiB** |
| **Vault** | 225,4 GiB brukt / 240,1 GiB ledig | 225,4 GiB brukt / 240,1 GiB ledig | +9,3 MiB (under oppløsningen) |

**Intern disk vokste ikke.** Ingen nye modellnedlastinger: `hf-cache` står uendret på
682 MiB (NB-BERT var alt hentet i fase 1), og `~/.ollama` står uendret på 32 GiB —
nb-llama ble brukt der den lå. Nytt på Vault i 1b: `p1b` 8,7 MiB + `register` 644 KiB.

Alt kjørte serielt, én modell om gangen. Samlet kjøretid ca. **24 minutter**, pluss en
avbrutt kjøring på 20 minutter (nb-llama LOO, stoppet etter at kostnaden ble målt til
210 minutter).
