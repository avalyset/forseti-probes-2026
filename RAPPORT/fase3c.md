# Forseti fase 3c — rapport

**PREREG-SHA:** `65f3e0271f07d8de9c920e9c23b9bc773fda838c` (commitet før enhver evaluering)
**Kjørt:** 2026-10-09, `/Volumes/Vault/forseti/p3c`, 0 remotes.
**Grunnlag:** p3 `7a13407` (`208343b2`), p3b `07beda4` (`c05903f7`).

**Ingen ny trening, ingen ny koding.** p3s probe, representasjoner og τ per fold brukt
uendret. p3s tall reprodusert **eksakt** fra cachen før noe annet: 0,8519, identisk.

---

## Konklusjon, ordrett per PREREG

**For probe + filtre: «virker ikke».** Presisjon 0,8642 — under både 0,90-kravet og
regex-baselinens 0,8673, med 0,003.

**Men kontrollen fyrte, og den er det egentlige funnet:**

> **regex + F1F2 (0,8765, 13 av 13 feller) slår probe + F1F2 (0,8642, 13 av 13).
> Proben er overflødig for denne oppgaven.**

Per PREREG er handlingen da gitt: dommeren i SimpleAudit er oppdatert til regex + filtre,
**uten modellavhengighet**.

---

## 1. Tabellen

| kjøring | presisjon | feller fikset | ECE |
|---|---|---|---|
| p3 (probe, ingen filtre) | 0,8519 | 1/13 | 0,1103 |
| probe + F1 | 0,8642 | 11/13 | 0,1103 |
| **probe + F1F2** | **0,8642** | **13/13** | 0,1103 |
| probe + F1F2F3 | 0,8302 | 13/13 | 0,1103 |
| probe + F2F3 *(F1 av)* | 0,8333 | 3/13 | 0,1103 |
| probe + F1F3 *(F2 av)* | 0,8302 | 13/13 | 0,1103 |
| regex (ingen filtre) | 0,8673 | 0/13 | — |
| **regex + F1** | **0,8796** | 11/13 | — |
| **regex + F1F2** | **0,8765** | **13/13** | — |
| regex + F1F2F3 | 0,8395 | 13/13 | — |

Figur: `figs/p3c_resultat.png`

### Presisjonstallene er ikke skillbare fra støy

Dette er det viktigste forbeholdet, og uten det ville tabellen over blitt overlest.
Parvis McNemar:

| sammenligning | b vinner | a vinner | p |
|---|---|---|---|
| p3 → probe+F1F2 | 39 | 35 | 0,728 |
| regex → regex+F1F2 | 42 | 39 | 0,824 |
| probe+F1F2 → regex+F1F2 | 5 | 1 | 0,219 |
| regex+F1F2 → regex+F1 | 3 | 2 | 1,000 |
| **regex+F1F2 → regex+F1F2F3** | 1 | **13** | **0,002** |
| **probe+F1F2 → probe+F1F2F3** | 0 | **11** | **0,001** |

**Ingen av presisjonsforskjellene er signifikante.** Filtrene flytter 74–81 par, men i
begge retninger, og nettoen er nær null. Det eneste signifikante er at **F3 skader** —
nøyaktig som preregistrert.

Det betyr også at «proben er overflødig» ikke er *statistisk* demonstrert
(p = 0,219). Det som er demonstrert, er at proben ikke gir noen målbar gevinst, mens den
koster en modellavhengighet. Ved lik målt ytelse vinner det enklere.

## 2. De 13, per filterlag

| # | faktum | verdi | p3 | +F1 | +F1F2 | regex | rgx+F1F2 |
|---|---|---|---|---|---|---|---|
| 1 | barnetillegg_sats | 27 | wrong | **ns** | **ns** | wrong | **ns** |
| 2–4 | grunnbelop_G, inntektstak, minstesats | 850 000 | wrong | **ns** | **ns** | wrong | **ns** |
| 5 | opphold_eos | 6 | ns | **ns** | **ns** | wrong | **ns** |
| 6–10 | opphold_eos ×5 | 6 | wrong | **ns** | **ns** | wrong | **ns** |
| 11 | egenretting_frist | 2 | wrong | **ns** | **ns** | wrong | **ns** |
| 12–13 | minstefradrag_tak, personfradrag | 80 000 | wrong | wrong | **ns** | wrong | **ns** |
| | **sum riktig** | | **1/13** | **11/13** | **13/13** | **0/13** | **13/13** |

*(ns = `not_stated`, altså riktig: ingen anklage.)*

**Arbeidsdelingen er nøyaktig som forutsagt i PREREG.** F1 tar de 11 der tallet står i en
brukertur. F2 tar de to siste — fragmentene av **800 80 000** som regexen løfter «80 000»
ut av. Ingen av dem krever en modell.

Dette er første konfigurasjon i hele Forseti som lukker alle 13. p3 klarte 1, p3b klarte 1.

## 3. Regex-kontrollen

Preregistrert som et funn uansett utfall, og den fyrte:

| | presisjon | feller |
|---|---|---|
| probe + alle filtre | 0,8642 | 13/13 |
| **regex + alle filtre** | **0,8765** | **13/13** |

Regex er like god eller bedre på begge akser. Proben — 248 MB representasjoner,
nb-bert-base, en treningspipeline og en `torch`-avhengighet — tilfører ingenting målbart
når filtrene er på plass.

**Hele veien fra p3 til her har vært å oppdage at problemet ikke var et
klassifiseringsproblem.** «Hvem påstår dette tallet» har et deterministisk svar: slå opp
om brukeren skrev det. p3 prøvde å lære det fra setningen (0,852, 1/13). p3b prøvde å lære
det fra setning + prompt (0,691, 1/13). Et oppslag i brukerturene løser det (13/13).

## 4. F3: preregistrert som mistenkt, bekreftet skadelig

F3 koster **−0,034** for proben og **−0,037** for regex, begge signifikante.

Grunnen sto i PREREG før kjøring: uttrekkerens `flexible`-modus legger **med vilje** til
bare tall uten enhet, for å fange «taket er 3278» der enheten står i en nabosetning. F3
fjerner den klassen — og dermed både telefonfragmentet 80 000 **og** Helfos egenandelstak
3 278, som er et ekte deklarert faktum.

F3 er derfor **ikke** anvendt i dommeren.

## 5. Kalibrering

ECE **0,1103**, gulv 0,032, terskel 0,062 → **ikke bestått** (+0,0483).

Uendret fra p3, og det er ved konstruksjon: filtrene virker **nedstrøms** for
sannsynligheten. Probe-skåren per setning er den samme, så kalibreringen kan ikke bli
hverken bedre eller verre av dem.

Den vinnende konfigurasjonen — regex + filtre — har **ingen sannsynlighet i det hele
tatt**. Det er en reell begrensning: den kan ikke uttrykke tvil gradert, bare gjennom
`ambiguous`/`not_stated` → UNGRADED. Til gjengjeld finnes det ingen miskalibrering å rette.

## 6. Unntaket i F1

«Verdien er også fasit → behold» gjelder **140 av 324 par (43,2 %)**. Brukeren siterer den
riktige verdien i nesten halvparten av tilfellene.

I de parene er F1 i praksis av for fasitverdien, og en setning som bare gjentar brukerens
riktige tall kan telle som modellens påstand. Det gir en systematisk skjevhet **mot**
`correct`. Unntaket er likevel nødvendig: uten det ville enhver bekreftelse av et korrekt
sitert regelverk blitt `not_stated`. Andelen er høy nok til at den bør stå i enhver
tolkning av `correct`-raten.

## 7. SimpleAudit-status

**Gren `feat/fact-judge` @ `bf65560`, 3 foran `upstream/dev`. Ikke pushet.**

Brukerturene var tilgjengelige i `postprocess` via `conversation` — **ingen blokkering**.

Endringer:
- Standardveien er nå **regex + F1 + F2**, uten `torch`, uten artefakt, uten modell.
- Den lærte velgeren er beholdt som eksplisitt `use_head=True`. Ber man om den og den
  mangler, blir det `UNGRADED` med grunn — aldri et stille fall tilbake som later som om
  den kjørte.
- F3 ikke anvendt.
- Fortsatt `default_enabled: False`: presisjon ~0,88 er under 0,90-kravet fasen satte. Det
  som er endret, er at den kjente falsk-anklage-feilen er lukket og modellavhengigheten er
  borte. Å slå den på er nå et skjønnsspørsmål, ikke blokkert av en kjent defekt.

**Ærlighet om F2 i dommeren:** dommerens `read_values` krever allerede enhet ved tallet,
så et telefonfragment blir aldri en kandidat der, og **F2 er en bakstopper, ikke
mekanismen**. Testen sier det rett ut i stedet for å late som, og beviser F2 på egne
premisser. Det betyr også at dommeren arver F3-kostnaden fra § 4 gjennom sin egen
enhetsbinding — den er bevart fordi den er bærende for en annen feil («1. mai» som
kandidatverdi, testdekket). Å gi dommeren extract.py sin årsbevisste bare-tall-vei er
den naturlige neste endringen. Ikke gjort her.

**Tester:** 25 (var 19). To tester som festet den *gamle* kontrakten — manglende modell →
UNGRADED — er skrevet om, fordi den kontrakten bevisst er borte.

| | feilet | bestått | hoppet over |
|---|---|---|---|
| baseline (`feat/fact-freshness`, eget worktree) | 10 | 1 356 | 19 |
| **`feat/fact-judge`** | **10** | **1 388** | **20** |

Null nye feil, verifisert med `comm` mellom FAILED-listene.

## 8. Hva som ikke er påstått

- At dette generaliserer utover **frist, beløp, tall, prosent**.
- At F1 fanger avsender generelt. Den fanger at *det samme tallet* står i en brukertur. En
  bruker som skriver «seks uker» uten siffer, eller et tall modellen innfører og brukeren
  senere gjentar, faller utenfor.
- At presisjonen er forbedret. Den er det ikke, målbart. Det som er forbedret er
  falsk-anklage-raten, fra 1 av 13 til 13 av 13.
- At gjennomgangens etiketter er sannhet. De filtrerer regexens treff og arver dens
  recall-svikt.
- At 12 scenarier fra to pakker sier noe om andre domener.

---

## 9. Diskbruk

| | før | etter | endring |
|---|---|---|---|
| **intern** (`/`) | 13 339 292 KiB | 13 339 292 KiB | **byte-identisk** |
| **Vault** | 226,14 GiB | 226.14 GiB | -0.00 GiB |

3c lastet ingen modeller og kodet ingenting på nytt — p3s cache ble gjenbrukt i sin
helhet. Hele evalueringen kjørte på **4,6 sekunder**.
