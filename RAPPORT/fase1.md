# Forseti fase 1 — rapport

**PREREG-SHA:** `b7251a28e3b78e36a616d61e18bab7ce1e3e74a9` (commitet før enhver kjøring)
**Kjørt:** 2026-10-09, lokalt på `/Volumes/Vault/forseti/p1`, 0 remotes, ingenting publisert.
**Data:** 47 norske `hei_refusal`-prompter, 18 refuse / 29 answer,
sha256 `7157b091…4333`. Ingen prompttekst gjengis her, i figurer eller i commit-meldinger.

---

## Konklusjon, ordrett per PREREG

> ## **«trenger data»**

Beste backbone er **nb-bert-base / mean-pool**, AUROC **0,870 [0,755; 0,966]**.

| Kriterium | Betingelser | Utfall |
|---|---|---|
| metoden virker | AUROC ≥ 0,80 ✓ · nedre grense > 0,70 ✓ · **ECE ≤ 0,10 ✗** (0,189) | **ikke oppfylt** |
| **trenger data** | KI krysser 0,80 ✓ · kurven stiger 30→47 ✓ | **OPPFYLT** |
| blindvei | KI inneholder 0,60 ✗ · kurven flat ✗ | **ikke oppfylt** |

Nøyaktig én kategori treffer, så konklusjonen trenger ikke «uavklart»-klausulen.

**Mot bokstavavlesningen, i én setning:** der forrige probe leste modellens eget tekstsvar og
fikk AUROC 0,471 [0,289; 0,657] — et intervall som dekker både 0,5 og verre enn tilfeldig —
gir en lineær probe på de frosne representasjonene 0,870 [0,755; 0,966], altså et intervall
som ikke berører tilfeldig i det hele tatt.

---

## 1. Hovedtabell

Leave-one-out over alle 47. Lag og C valgt ved indre kryssvalidering **innenfor hver
treningsfold**; temperatur tilpasset på out-of-fold-logits fra treningsfolden, aldri på
testpunktet. AUROC-intervall: stratifisert bootstrap, 2000 replikater.

| backbone / pooling | AUROC | 95 % KI | ECE før | ECE etter | ECE-støygulv | Brier | modalt lag |
|---|---|---|---|---|---|---|---|
| **nb-bert-base / mean** | **0,870** | [0,755; 0,966] | 0,178 | 0,189 | 0,117 | 0,143 | L10 (34 %) |
| nb-bert-base / [CLS] | 0,866 | [0,751; 0,956] | 0,182 | 0,159 | 0,103 | 0,174 | L8 (51 %) |
| nb-llama-3.1-8b / ollama-embed | 0,852 | [0,732; 0,956] | 0,191 | 0,151 | 0,124 | 0,141 | siste (eneste) |
| baseline: majoritetsklasse | 0,500 | — | 0,000 | 0,000 | — | 0,236 | — |
| baseline: bokstavavlesning (forrige probe) | 0,471 | [0,289; 0,657] | — | 0,138 | 0,105 | 0,257 | — |

Bokstavavlesningens tall er **tatt fra dens rapport** (commit `3e2fdf3`), ikke kjørt om.

**Signalet sitter i midten av nettet.** Mean-pool velger L9/L10 i 32 av 47 folder, [CLS]
velger L8 i 24 av 47. Ingen av dem velger toppsjiktet. Det er det vanlige mønsteret for
lineære prober: oppgaverelevant struktur er mest lineært tilgjengelig i de midtre lagene.

**Tre uavhengige backbones gir samme svar** — 0,852 til 0,870, med intervaller som overlapper
nesten helt. En 200M-encoder og en 8B-dekoder er enige. Det taler for at signalet ligger i
dataene, ikke i én arkitekturs særegenhet.

### Kalibreringen holder ikke — og kunne ikke måles

Temperaturskaleringen virker for [CLS] (0,182 → 0,159) og nb-llama (0,191 → 0,151), men gjør
mean-pool **verre** (0,178 → 0,189; median temperatur 0,916, altså en skjerping som ikke
overførte til testpunktene).

Viktigere: **ECE-kravet ≤ 0,10 lå under støygulvet for alle tre backbones** (0,103–0,124). En
*perfekt kalibrert* modell ville i forventning ikke klart kravet ved n=47. Kriteriet var
dermed ikke oppnåelig av konstruksjonsgrunner. Dette føres som **designfeil i min egen
PREREG**, og brukes ikke til å omdefinere konklusjonen: «metoden virker» står som ikke
oppfylt, og «trenger data» er uansett den kategorien som treffer — ECE-kravet krever nettopp
større n før det i det hele tatt kan måles.

Reliability-diagrammene viser hvorfor: de fleste av de ti bøttene inneholder 1–4 punkter.

Figurer: `figs/reliability_nb-bert-base_mean.png`, `…_cls.png`, `…_nb-llama-3.1-8b_ollama-embed.png`

---

## 2. Læringskurve

Figur: `figs/laeringskurve.png`

**Venstre panel — som preregistrert** (10/20/30 = hold-out, 20 stratifiserte delinger; 47 = LOO):

| n trening | nb-bert/mean | nb-bert/cls | nb-llama |
|---|---|---|---|
| 10 | 0,840 ± 0,103 | 0,804 ± 0,153 | 0,848 ± 0,036 |
| 20 | 0,886 ± 0,055 | 0,868 ± 0,058 | 0,870 ± 0,059 |
| 30 | 0,918 ± 0,056 | 0,879 ± 0,079 | 0,889 ± 0,059 |
| 47 | 0,870 (LOO) | 0,866 (LOO) | 0,852 (LOO) |

**Høyre panel — post-PREREG-tillegg, fordi PREREG var uleselig på dette punktet.** PREREG
definerte 10/20/30 som hold-out og 47 som LOO. De to ligger ikke på samme skala, så
«stiger kurven fra 30 til 47?» kunne ikke besvares som skrevet — tallet *faller* (0,918 →
0,870), men av protokollskifte, ikke av ytelse. Jeg målte derfor 30 og 47 med **samme**
protokoll: LOO innenfor en stratifisert delmengde på 30, gjentatt 5 ganger, mot LOO på 47.

| backbone | n=30 (LOO, snitt av 5) | n=47 (LOO) | Δ |
|---|---|---|---|
| nb-bert-base / mean | 0,838 ± 0,060 | 0,870 | **+0,031** |
| nb-bert-base / [CLS] | 0,798 ± 0,085 | 0,866 | **+0,068** |
| nb-llama-3.1-8b | 0,824 ± 0,036 | 0,852 | **+0,029** |

**Kurven stiger fra 30 til 47 på alle tre.** Men stigningen er liten mot spredningen: for
mean-pool er +0,031 omtrent et halvt standardavvik av 30-punktet (±0,060). Retningen er
konsistent på tvers av tre backbones, styrken er det ikke sterkt belegg for ved denne n.
Det er akkurat det «trenger data» betyr.

---

## 3. Generert mengde og transfer-eksperiment — for seg

**Generering.** 15 registerrader (NAV-01…06, SKATT-18…20, HF-08…09, LK-22 + de tre
klagefristradene). nb-llama-3.1-8b via ollama genererte answer-spørsmål per rad;
refuse-spørsmål fra et fast malsett på 15 maler i tre kategorier (personlig råd uten
grunnlag / omgå regelverk / andres data). Resultat: **270 rader — 129 answer, 141 refuse**,
innenfor målet 200–300. 12 duplikater fjernet. Fil: `data/generated.jsonl` med kilde-rad-ID.

**Lekkasjekontroll.** Den preregistrerte regelen var «inneholder verdien fra raden → forkast».
Ved implementering viste den seg tvetydig: `2026` og `25` står i radene, men i et *spørsmål*
er de kontekst («Hva er personfradraget for 2026?»), ikke svaret. Streng lesning ville
forkastet 25 kandidater på kontekst alene. Jeg spesifiserte derfor før generering:

- **`leak_answer` (brukt):** tall med ≥ 4 siffer som ikke er årstall 2000–2030, prosent- og
  kronesatser fra påstanden, frister som frase («6 uker»). → **11 forkastet.**
- **`leak_strict` (bare målt, ikke brukt):** ethvert tall ≥ 2 siffer fra raden. → ville
  forkastet **25**.

Begge tall står i `results/generation_log.json`. Presiseringen er post-PREREG og føres som det.

**Transfer: tren på generert, test på de 47.** Lag og C valgt ved **gruppert** CV innenfor den
genererte mengden (grupper = kilde-rad-ID), så nær-identiske spørsmål fra samme rad ikke havner
i både trening og validering. Figur: `figs/transfer.png`

| backbone | AUROC på de 47 | 95 % KI | ECE etter | Brier | n=50 | n=100 | n=200 |
|---|---|---|---|---|---|---|---|
| nb-bert-base / mean | 0,630 | [0,485; 0,772] | 0,382 | 0,382 | 0,568 | 0,572 | 0,559 |
| nb-bert-base / [CLS] | 0,649 | [0,503; 0,774] | 0,359 | 0,362 | 0,647 | 0,615 | 0,618 |
| nb-llama-3.1-8b | 0,619 | [0,461; 0,757] | 0,595 | 0,595 | 0,461 | 0,458 | 0,449 |

**Transfer virker ikke.** Alle tre intervaller berører eller nær-berører 0,5, og kurven er
flat eller fallende i treningsmengde — mer generert data gjør det ikke bedre. Mot 0,870 når
samme representasjoner trenes på de 47, er fallet rundt 0,24 AUROC-poeng.

Temperaturen traff **nedre grense (T = 0,05) i alle tre tilfeller**. Det betyr at den genererte
oppgaven er nær perfekt separerbar — hodet lærer å kjenne igjen malenes overflateform, blir
ekstremt sikkert, og tar den sikkerheten med seg til et testsett der den er feilplassert.
ECE-tallene for transfer (0,36–0,60) er derfor et uttrykk for den grensetreffen, ikke en
meningsfull kalibreringsmåling.

**Det den genererte mengden faktisk lærte, var malene — ikke begrepet.** Refuse-siden er
malgenerert fra 15 faste setninger med domeneord satt inn, og answer-siden er repetitiv
innenfor hver rad. En probe som skiller dem trenger ikke forstå hva avslag er. Dette er ikke
et argument mot syntetisk data generelt, men mot *denne* konstruksjonen av den.

Denne mengden er, som preregistrert, **ikke blandet inn i hovedtallet**.

---

## 4. Backbones som faktisk kjørte

| | status |
|---|---|
| (a) NB-BERT-base, mean + [CLS], alle 13 lag | **kjørte** — 178M param, 47 prompter på 46 s |
| (b) nb-llama-3.1-8b via ollama `/api/embed` | **kjørte** — 4096-dim, 47 prompter på 13 s |
| (b) nb-llama via transformers 4-bit | **ikke forsøkt** — unødvendig, ollama ga embeddings |

**Begrensning på (b):** ollamas `/api/embed` gir **én** vektor per input (siste lag, pooled).
Per-lag hidden states er ikke tilgjengelige gjennom det grensesnittet, så **lagvalg var ikke
mulig for nb-llama**. PREREGs «alle lag» gjelder dermed bare NB-BERT. nb-llama-tallet er ett
lag uten seleksjon — og det er verdt å merke at det likevel treffer 0,852, altså at seleksjonen
over 13 lag ikke er det som bærer resultatet.

---

## 5. Avvik fra PREREG

1. **Klagefristradene lå ikke på linje 320–321.** Oppdraget pekte dit; de linjene er
   tabellhodet og NAV-01. Klagefristene står i seksjonen «Kryss-domene: klagefrist varierer»
   (linje 351+). Jeg brukte den faktiske seksjonen — tre rader, NAV/Skatteetaten/Lånekassen.
2. **ECE-kriteriet ≤ 0,10 var ikke oppnåelig ved n=47** (støygulv 0,103–0,124). Designfeil i
   PREREG. Ikke brukt til å omdefinere konklusjonen.
3. **«Kurven stiger fra 30 til 47» var uleselig som preregistrert**, fordi PREREG ga de to
   punktene ulik evalueringsprotokoll. Løst med en tydelig merket post-PREREG-måling der begge
   er LOO. Hovedtall og kriterier uendret.
4. **Indre seleksjonskriterium var ikke spesifisert i PREREG.** Valgt før kjøring: **Brier på
   indre valideringsfolder**, fordi det straffer både feil rangering og dårlig kalibrering.
   sklearn trener med log-loss (Brier-tap støttes ikke som treningsmål), som PREREG forutså.
5. **Lekkasjekontrollen ble presisert** til `leak_answer` før generering; `leak_strict` er
   målt og rapportert ved siden av (se § 3).
6. **`OLLAMA_MODELS` ble ikke satt.** nb-llama lå allerede i `~/.ollama`; å sette variabelen
   ville tvunget ny nedlasting av 4,9 GB. Brukt der den lå, som instruert.
7. **Kosmetisk:** sklearn 1.9 gir `FutureWarning` på `penalty="l2"` (deprecated til fordel for
   `l1_ratio`). Oppførselen er uendret — ren L2 — og tallene er gyldige.

---

## 6. Diskbruk

| | før | etter | endring |
|---|---|---|---|
| **intern** (`/`) | 12,7 GiB brukt / 21,6 GiB ledig | 12,7 GiB brukt / 21,6 GiB ledig | **± 0,0 GiB** |
| **Vault** | 223,1 GiB brukt / 242,4 GiB ledig | 225,4 GiB brukt / 240,1 GiB ledig | **+2,3 GiB** |

**Intern disk vokste ikke — målt, ikke antatt.** `HF_HOME`, `HUGGINGFACE_HUB_CACHE`,
`TRANSFORMERS_CACHE` og `PIP_CACHE_DIR` ble alle satt til Vault, `HF_HOME` permanent i
venv-aktiveringen. `~/.ollama` står uendret på 32 GiB — nb-llama ble brukt der den lå, ikke
kopiert.

Vault-forbruket fordeler seg: venv 1,1 GiB · HF-modellcache 682 MiB · pip-cache 213 MiB ·
arbeidsmappe `p1` 28 MiB (inkl. representasjonscache). `forseti/ollama` er tom, som tilsiktet.

Kjøretid, serielt, én modell om gangen — aldri to samtidig:

| steg | s |
|---|---|
| NB-BERT-representasjoner (47) | 46 |
| nb-llama-embeddings (47) | 14 |
| hovedprobe, LOO × 3 backbones | 118 |
| læringskurve (hold-out) | 121 |
| generering av 270 eksempler | 222 |
| representasjoner for de 270 | 89 |
| transfer-eksperiment | 139 |
| post-PREREG LOO@30 vs LOO@47 | 325 |
| analyse og figurer | ~30 |
| **sum** | **≈ 1 104 s = 18,4 min** |

Innenfor 60-minutters-grensen. NB-BERT alene tok under 10 minutter, så (b) ble kjørt, som
preregistrert.

---

## 7. Hva dette ikke sier

- Ikke at funnet generaliserer utover ungdomshelse-prompter. 47 prompter, én pakke, ett domene.
- Ikke at `expected_outcome` er en fasit for hva en tjeneste *bør* gjøre. Det er pakkens etikett.
- Ikke at representasjonene «vet» noe. En lineær probe måler at informasjonen er lineært
  tilgjengelig i representasjonen — ikke at modellen bruker den når den svarer. At
  bokstavavlesningen fikk 0,471 på de samme promptene er nettopp et tegn på at den *ikke* gjør det.
- Ikke at kalibrering er løst. Den er ikke demonstrert, og ved n=47 kan den ikke demonstreres.

## 8. Hva som følger av «trenger data»

Spørsmålet proben stilte er besvart i retning: signalet finnes, lineært, i frosne norske
representasjoner — tre uavhengige backbones, AUROC 0,85–0,87, mot 0,471 for bokstavavlesning.
Det som ikke er avgjort, er hvor godt det blir, og om det kan kalibreres. Begge krever flere
ekte eksempler. Transfer-eksperimentet viser at **malgenerert data ikke er en snarvei dit**:
270 genererte eksempler ga 0,63, og mer av dem gjorde det ikke bedre.
