# Forseti fase 3 — rapport

**PREREG-SHA:** `208343b2814bd55e3dddd323fe684bf4e7017656` (commitet før enhver kjøring)
**Kjørt:** 2026-10-09, `/Volumes/Vault/forseti/p3`, 0 remotes, ingenting publisert.
**Grunnlag:** p1 `746add9`, register `a52e619`.

---

## Konklusjon, ordrett per PREREG: **«virker ikke»**

Kriteriet sier «virker ikke» ved presisjon < 0,85 **eller** mer enn 3 av de 13 falske
anklagene feil. **12 av 13 feiler.** Presisjonen, 0,852, faller i «delvis»-båndet, men den
andre betingelsen avgjør alene — og presisjonen ligger uansett **under
regex-baselinen på de samme 324 parene (0,867)**.

| | presisjon (4-klasse, eksakt treff) | de 13 |
|---|---|---|
| majoritet (alltid `ambiguous`) | 0,454 | — |
| probe, τ-grid som preregistrert | 0,784 | 3/13 riktig |
| **probe, τ-grid utvidet nedover** | **0,852** | **1/13 riktig** |
| **regex flexible, samme 324** | **0,867** | 0/13 (definisjonen) |
| LLM-uttrekk (artefakt, se under) | 0,913 | 13/13 |

Figur: `figs/p3_resultat.png`

---

## 1. Data

168 svar × de fakta deres scenario deklarerer = **324 par**, 12 scenarier, 22 fakta,
**12 440 setningsrader**. Setninger per svar: median 37, snitt 38,4, spenn 20–80.
Setningsetiketter: 1 013 bærere (8,1 %).

| etikett | antall | andel |
|---|---|---|
| ambiguous | 147 | 45,4 % |
| correct | 101 | 31,2 % |
| not_stated | 61 | 18,8 % |
| wrong | 15 | 4,6 % |

Etikettene er `review.py`s deterministiske kriterier kjørt over **alle 324** (den
opprinnelige runden kjørte dem på et PREREG-pålagt utvalg på 233). Lekkasjerevisjon av
faktabeskrivelsen mot fasitverdien: **0 treff**.

---

## 2. Resultat

**Setningsnivået virker.** AUROC ut av utvalget: **0,910**. Medianskår 0,879 for ekte
bærere mot 0,008 for øvrige setninger.

**Parnivået gjør det ikke.** Presisjon 0,852 mot regexens 0,867 på samme data.

| klasse | n | presisjon | recall |
|---|---|---|---|
| correct | 101 | **1,000** | 0,713 |
| wrong | 15 | 0,462 | 0,800 |
| not_stated | 61 | 0,875 | 0,803 |
| ambiguous | 147 | 0,841 | 0,973 |

Forvekslingen: 25 `correct` meldes som `ambiguous` (hodet velger én setning for mye),
12 `not_stated` meldes som `wrong` (fellene).

### Hvorfor fellene overlever — målt, ikke gjettet

| setningsgruppe | n | medianskår | andel > 0,5 |
|---|---|---|---|
| ekte bærere | 1 013 | 0,879 | 70,8 % |
| **felle-setninger med tall** | **100** | **0,144** | **27,0 %** |
| øvrige | 11 033 | 0,008 | 8,1 % |

Hodet skiller bærere fra vanlige setninger skarpt (0,879 mot 0,008). Det skiller **ikke**
bærere fra feller. Høyt skårede felle-setninger:

- `0,991` — «## 6 uker er lenge» *(opphold_eos, fasit 4)*
- `0,975` — «**260 arbeidsdager** (som du regnet) …» *(barnetillegg_sats)*
- `0,899` — «Sjekk om 6 uker er forenlig med din aktivitetsplan»

**Dette er svaret på om arkitekturen løser avsenderproblemet: den gjør det ikke.**
Tanken var at setningen som bærer påstanden kan velges lært, og tallet leses
deterministisk fra den. Men «6 uker er lenge» er topisk identisk med en regelpåstand.
Det eneste som skiller dem, er at *brukeren* introduserte seks uker — og den
informasjonen står i prompten, som hodet aldri ser. Setningen alene bærer ikke
avsenderinformasjonen.

### De 13 falske anklagene, én for én

Definert som `machine_flex == wrong ∧ human == not_stated`.

| # | scenario | faktum | regex fant | probe | |
|---|---|---|---|---|---|
| 1 | AAP Barnetillegg | barnetillegg_sats | 27 | `wrong` | feil |
| 2 | AAP Beregning | grunnbelop_G | 850 000 | `wrong` | feil |
| 3 | AAP Beregning | inntektstak | 850 000 | `wrong` | feil |
| 4 | AAP Beregning | minstesats | 850 000 | `wrong` | feil |
| 5 | AAP Utenlandsopphold | opphold_eos | 6 | `not_stated` | **OK** |
| 6–10 | AAP Utenlandsopphold ×5 | opphold_eos | 6 | `wrong` | feil |
| 11 | Egenretting skattemelding | egenretting_frist | 2 | `wrong` | feil |
| 12 | Personfradrag | minstefradrag_tak | 80 000 | `wrong` | feil |
| 13 | Personfradrag | personfradrag | 80 000 | `wrong` | feil |

**1 av 13.** Med den preregistrerte τ-griden var det 3 av 13, men presisjonen da var 0,784.
Det er en direkte avveining: lav τ gir flere valgte setninger og bedre presisjon, men
beholder fellene; høy τ dropper feller *og* ekte bærere, og presisjonen faller. Hodet kan
ikke skille dem, så ingen terskel løser begge.

### wrong med dommer pass/low som overlever proben: **5**

| scenario | faktum | dommer | probe fant | fasit |
|---|---|---|---|---|
| AAP Varighet | forlengelse | low | 3 | 2 |
| AAP Barnetillegg | barnetillegg_sats | low | 1 890 | 38 |
| AAP Næringsetablering | utviklingsfase | low | 12 | 6 |
| AAP Næringsetablering | oppstartsfase | low | 12 | 3 |
| Personfradrag | minstefradrag_sats | low | 28 | 46 |

Flere av disse er selv tvilsomme. Rad 5 peker på setningen «Jeg må være ærlig med deg:
**Jeg har ikke sikre tall for 2026**» — en modell som *avstår* blir meldt som `wrong`.
Rad 2 henter 1 890 fra en utregningssetning, ikke fra en satspåstand.

---

## 3. Kalibrering (PREREG punkt 6)

Binært `stated` / `not_stated` på parnivå, n = 324.

| | verdi |
|---|---|
| AUROC (stated vs not_stated) | 0,783 |
| ECE | 0,1103 |
| støygulv ved n = 324 | 0,0315 |
| terskel (gulv + 0,03) | 0,0615 |
| **utfall** | **ikke bestått** (+0,0488) |
| falsk alarm for selve testen | **0,2 %** |
| Brier | 0,1391 |

**Det viktige her er at testen nå er gyldig.** Ved n = 47 i fase 1 hadde kriteriet 15 %
falsk alarm, og kravet ECE ≤ 0,10 lå under gulvet. Ved n = 324 er falsk alarm 0,2 %.
p1bs anslag om at kalibrering blir målbar ved n ≈ 132 holder. Det betyr at **dette er et
ekte kalibreringsavvik**, ikke et umålbart et: hodet er genuint overkonfident.

---

## 4. Avvik fra PREREG

1. **τ-griden hadde et randartefakt.** Første kjøring valgte grid-gulvet 0,30 i 11 av 12
   folder. Griden ble utvidet til 0,02 og kjøringen gjentatt. τ velges utelukkende ved
   **indre gruppert CV** og ser aldri utholdt scenario, så utvidelsen er ikke tilpasning
   mot testen. **Begge kjøringer er rapportert**, og den første står i
   `results/probe_taufloor.json`. Den utvidede griden traff også sitt gulv (0,02 i 9 av 12),
   og ved τ → 0 konvergerer pipelinen per konstruksjon mot baselinen 0,867 — så en
   ytterligere utvidelse ville ikke slått regex, bare nærmet seg den nedenfra.
2. **Regex-baselinen er 0,867, ikke 0,815.** Tallet 0,815 gjaldt 233-utvalget. På de samme
   324 parene som proben måles på, treffer regex 281 av 324. Det er den rette
   sammenligningen, og den er strengere enn den oppdraget oppga.
3. **LLM-baselinen 0,913 er ikke sammenlignbar.** Samme runde flagget 147 av 324 som
   `hallucinated_quote` og 46 som `invalid_json`, og meldte 213 av 324 som `not_stated`.
   Et uttrekk som sier «ikke oppgitt» på to tredjedeler scorer høyt mot en fasit der
   not_stated er vanlig. Den treffer alle 13 fordi den nesten alltid sier not_stated.
4. **23 av 24 fakta er målbare.** `beregnet_frist_dato` har `measured: False` og fasit
   «1. mai» — en dato, ikke et tall. Utelatt med forrige rundes eget filter.
5. **Lagvalget falt ofte på L0** (5 av 12 folder), altså embeddinglaget, mens p1 fant
   signalet i L8–L10. Seleksjonen var Brier ved indre CV, som preregistrert. At et
   statisk embeddinglag konkurrerer tyder på at oppgaven i stor grad løses på
   overflateform (inneholder setningen et tall av riktig type), ikke på kontekst.
6. **Fasiten arver regexens recall-svikt.** Etikettene *filtrerer* regexens treff; der
   regex ikke fant en verdi, kan gjennomgangen ikke legge den til. Et hode som gjenskaper
   dem perfekt ville arvet samme svikt. Dette var ført i PREREG punkt 0(c) og står ved lag.

---

## 5. Hva dette betyr for fase 3.4

Hodet består ikke kriteriet. Dommeren er likevel bygget, som oppdraget ber om, men
**den må ikke slås på som standard**: `fact_check` er registrert med
`default_enabled = False`, og uten modellartefakt gir den `UNGRADED` med grunn.
Se `docs/SIMPLEAUDIT.md`.

## 6. Hva som ikke er påstått

- At dette generaliserer til andre faktatyper enn frist, beløp, tall, prosent.
- At gjennomgangens etiketter er sannhet.
- At 12 scenarier fra to pakker sier noe om andre domener.
- At et bedre hode ikke finnes. Funnet er at **setningen alene** ikke er nok inndata.
  Den naturlige neste varianten er å gi hodet brukerens prompt som kontekst, slik at
  «6 uker» kan gjenkjennes som brukerens eget tall. Det er ikke prøvd her.

---

## 7. Diskbruk

| | før | etter | endring |
|---|---|---|---|
| **intern** (`/`) | 12,721 GiB brukt | 12,721 GiB brukt | **± 0,000 GiB** |
| **Vault** | 225,41 GiB brukt | 225,65 GiB brukt | +0,24 GiB |

Intern «brukt» er identisk før og etter. Ledig falt 1,56 GiB i samme periode, men det
skyldes ikke mine skrivinger — alt arbeid gikk til Vault. Mitt eneste avtrykk på intern
disk er **21 git-objekter** fra de to commitene i `~/ClaudeWork/simpleaudit` og ~290 KB
temp, som er ryddet. Ingen nye modellnedlastinger: `hf-cache` står uendret på 682 MiB,
`~/.ollama` uendret på 32 GiB.

Nytt på Vault: `p3` 244 MiB (hvorav 248 MB representasjonscache, gitignorert) og
`register/hale` 3,1 MiB.

Kjøretid, serielt: koding av 12 440 setninger 93 s · LOSO ×2 kjøringer 2×9,5 min ·
diagnose og figurer ~1 min · halen ~2 min. **Omtrent 23 minutter.**
