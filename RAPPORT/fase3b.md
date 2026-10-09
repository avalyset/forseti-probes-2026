# Forseti fase 3b — rapport

**PREREG-SHA:** `c05903f72665a650be3b0ae058cbcffc5019309a` (commitet før enhver 3b-kjøring)
**Kjørt:** 2026-10-09, `/Volumes/Vault/forseti/p3b`, 0 remotes, ingenting publisert.
**Grunnlag:** p3 `7a13407` (PREREG `208343b2`).

---

## Konklusjon, ordrett per PREREG: **«virker ikke»**

Begge ledd feiler, og med god margin. Presisjonen falt **under p3**, ikke bare under regex.

| kjøring | presisjon | setnings-AUROC |
|---|---|---|
| majoritet (alltid `ambiguous`) | 0,4537 | — |
| **p3: hverken prompt eller felle-etikett** | **0,8519** | **0,910** |
| 3b abl. c: felle-etikett, uten prompt | 0,8179 | 0,855 |
| 3b abl. a: prompt, uten felle-etikett | 0,8302 | 0,807 |
| 3b abl. b: alle brukerturer + felle-etikett | 0,7407 | 0,718 |
| **3b HOVEDTALL: tur 0 + felle-etikett** | **0,6914** | **0,734** |
| regex flexible, samme 324 | 0,8673 | — |

Figur: `figs/p3b_resultat.png`

---

## 1. Hva som ble endret

Inndata per setning: `[CLS] prompt [SEP] faktum [SEP] setning [SEP]` mot p3s
`[CLS] faktum [SEP] setning [SEP]`. Strengen `"[SEP]"` mapper til token 102, tokenizerens
ekte separator — verifisert, ikke antatt.

Ny negativ setningsklasse: en setning hvis uttrukne tall også står i prompten merkes
**felle** og kan ikke være bærer.

| etikett | antall | andel |
|---|---|---|
| bærer | 899 | 7,2 % |
| **felle** | **262** | **2,1 %** |
| øvrig | 11 279 | 90,7 % |

**114 av p3s 1 013 bærere** (11 %) gjentar et tall fra prompten og ble omklassifisert.
p3 trente altså delvis på å peke på feller.

**Trunkering: 0 av 168.** Tur 0 er median 35 tokens, maks 89, mot grensen 256.

---

## 2. Attribusjon — 2 × 2

Oppdraget ba om én ablasjon (prompt uten felle-etikett). Den alene kan ikke tilskrive
fallet, så jeg la til den fjerde cellen (**abl. c**, felle-etikett uten prompt) som
diagnose. Den endrer ingen kriterier.

| | p3-etikett | **felle-etikett** |
|---|---|---|
| **uten prompt** | 0,8519 *(p3)* | 0,8179 *(abl. c)* |
| **med prompt** | 0,8302 *(abl. a)* | **0,6914** *(hovedtall)* |

- Felle-etiketten alene koster **−0,034**.
- Prompten alene koster **−0,022**.
- Begge koster **−0,161** — nesten tre ganger summen av delene.

**Interaksjonen er det som skader.** Hver endring for seg er en liten forverring; sammen
kollapser de. Med prompten i inndata får modellen et sterkt «overlapper prompten»-trekk.
Felle-etiketten ber den behandle nettopp det trekket som negativt — og på utholdte
scenarier generaliserer det motsatt vei, fordi de substansielle setningene i et svar
også gjentar spørsmålets innhold.

## 3. Mekanismen, målt

**Den delte prompten fortrenger setningssignalet.** Variansdekomponering av
representasjonen (lag L0), der signalet som skiller setninger *innenfor* samme
(svar, faktum)-par er det eneste brukbare:

| | varians innenfor par | mellom par |
|---|---|---|
| p3 (faktum + setning) | **45,0 %** | 55,0 % |
| 3b (prompt + faktum + setning) | **30,4 %** | 69,6 % |

Prompten er identisk for alle ~38 setninger i et svar. Når den mean-pooles inn, blir
representasjonene mer like hverandre, og andelen varians som faktisk skiller setninger
faller med en tredel. Hodet får mindre å jobbe med, ikke mer.

## 4. Setningsskårer — og en rettelse av min egen lesning

Målt på **samme** felle-definisjon i begge kjøringene:

| gruppe | n | p3 median | > 0,5 | 3b median | > 0,5 |
|---|---|---|---|---|---|
| ekte bærere | 899 | 0,822 | 67,2 % | **0,683** | 56,8 % |
| felle-setninger | 262 | **0,965** | 79,0 % | **0,972** | 75,6 % |
| øvrige | 11 279 | 0,007 | 7,3 % | 0,032 | 18,1 % |

**Rettelse:** jeg var i ferd med å rapportere at rangeringen «snudde» i 3b. Det er feil.
Fellene lå **allerede** høyest i p3 under denne definisjonen (0,965 mot bærernes 0,822).
p3-rapportens tall 0,144 gjaldt en **smalere** definisjon — setninger med tall i et
falsk-anklage-par, n = 100 — og er ikke sammenlignbar. På *den* definisjonen gikk 3b fra
0,144 til **0,312**, altså også verre.

Det 3b faktisk gjorde: senket bærerne (0,822 → 0,683) og hevet de øvrige (0,007 → 0,032).
Diskrimineringen kollapset i begge ender. Felle-etiketten flyttet ikke fellene i det hele
tatt.

## 5. De 13 fellene, én for én

| # | faktum | verdi | i tur 0 | p3 | 3b | maks skår |
|---|---|---|---|---|---|---|
| 1 | barnetillegg_sats | 27 | nei | wrong | **not_stated** ✓ | 0,604 |
| 2 | grunnbelop_G | 850 000 | ja | wrong | wrong | 0,989 |
| 3 | inntektstak | 850 000 | ja | wrong | wrong | 0,595 |
| 4 | minstesats | 850 000 | ja | wrong | wrong | 0,751 |
| 5 | opphold_eos | 6 | ja | **not_stated** | wrong ✗ | 0,447 |
| 6–10 | opphold_eos ×5 | 6 | ja | wrong | wrong | 0,698–0,789 |
| 11 | egenretting_frist | 2 | ja | wrong | wrong | 0,930 |
| 12 | minstefradrag_tak | 80 000 | nei | wrong | wrong | 0,163 |
| 13 | personfradrag | 80 000 | nei | wrong | wrong | 0,106 |

**1 av 13** — nøyaktig som p3. Og det er ikke engang framgang: 3b fikser #1 (hvis trap
ikke engang står i tur 0, så ikke av mekanismen) og **mister** #5, som p3 hadde riktig.

Ni av de 13 hadde tallet sitt i tur 0 og var altså innen rekkevidde. Ingen av dem ble
fikset. Mekanismen traff der den kunne treffe, og virket ikke.

**Taket var uansett 9 av 13** — ført i PREREG punkt 0(a) før kjøring. To feller ligger i
en senere brukertur, og to (80 000-paret) i ingen: de er fragmenter av Skatteetatens
servicetelefon **800 80 000** i *svaret*. Kriteriet «≤ 3 overlever» krevde 10 fikset og
var derfor ikke oppnåelig gjennom tur 0 alene. Det er likevel ikke derfor det feiler —
det feiler på 12.

## 6. Ablasjon b: alle brukerturer

0,7407, altså bedre enn hovedtallet (0,6914) men langt under p3. Flere turer når 11 av 13
feller i prinsippet, men gir også en lengre delt prefiks og dermed sterkere fortrengning.
13,4 % av radene måtte kuttes ved grensen. Valget av tur 0 koster altså ikke resultatet —
begge varianter er klart dårligere enn å ikke ha prompten der.

## 7. Kalibrering

| | 3b | p3 |
|---|---|---|
| ECE | **0,2837** | 0,1103 |
| støygulv (n = 324) | 0,0320 | 0,0320 |
| terskel (gulv + 0,03) | 0,0620 | 0,0620 |
| utfall | **ikke bestått** (+0,2217) | ikke bestått (+0,0483) |
| AUROC (stated/not_stated) | 0,658 | 0,783 |
| Brier | 0,2788 | 0,1391 |

Kalibreringen ble **fire og en halv gang verre**. Testen er gyldig ved n = 324
(0,2 % falsk alarm), så dette er et ekte avvik.

---

## 8. Siden kriteriet ikke er oppfylt

**SimpleAudit er ikke rørt.** Ingen artefakt eksportert, `feat/fact-judge` står uendret på
p3-versjonen, som allerede er `default_enabled: False`. Det var betingelsen i oppdraget.

## 9. Avvik fra PREREG

1. **`max_length` hevet 192 → 256.** Tvungen følge av lengre inndata (maks 222); ved 192
   ville 0,3 % fått setningen kuttet. Ført i PREREG punkt 1 før kjøring.
2. **Ablasjon c lagt til etter hovedkjøringen**, som diagnose. Uten den kan ikke fallet
   tilskrives prompten eller etiketten. Den bruker p3s representasjoner, som har
   `max_length` 192 mot 3b sine 256 — en liten uensartethet, nevnt her.
3. **Ablasjon b trunkeres fra starten.** Første koding lot tokenizeren kutte, og den
   kutter det lengste segmentet fra **enden** — altså der spørsmålet står — for 52 % av
   radene. Rettet til forhåndskutting per rad som bevarer setningen og promptens hale;
   13,4 % treffer fortsatt grensen.
4. **Rettelse i min egen lesning av p3**, se § 4: fellene lå allerede høyest i p3 under
   den nye definisjonen. p3-rapportens 0,144 gjaldt en smalere definisjon.

## 10. Hva dette sier, og ikke

Diagnosen fra p3 var at setningen alene ikke bærer avsenderinformasjon, og at tallet
brukeren innførte står i prompten. **Det stemmer fortsatt.** Det som er avkreftet, er at
*denne* måten å gi hodet prompten på hjelper.

To ting står i veien, og de er målt, ikke antatt:
- **Mean-pooling over en delt prefiks fortrenger det som skiller setninger** (45 % → 30 %).
- **«Overlapper prompten» generaliserer som et positivt trekk** på tvers av scenarier,
  så en etikett som sier at det er negativt lærer feil fortegn.

Det utelukker ikke promptkontekst som sådan. En arkitektur som holder prompten atskilt
fra setningsrepresentasjonen — et eksplisitt overlapps-trekk i stedet for konkatenering,
eller [CLS] framfor mean-pool, eller kryssattensjon — angriper begge problemene direkte.
Ingen av dem er prøvd her.

**Ikke påstått:** at dette generaliserer utover faktatypene frist, beløp, tall, prosent.
At gjennomgangens etiketter er sannhet — de filtrerer regexens treff og arver dens
recall-svikt. At 12 scenarier fra to pakker sier noe om andre domener.

---

## 11. Diskbruk

| | før | etter | endring |
|---|---|---|---|
| **intern** (`/`) | 13 339 292 KiB | 13 339 292 KiB | **byte-identisk** |
| **Vault** | 225,66 GiB | 226,14 GiB | +0,48 GiB |

Intern «brukt» er uendret til siste kibibyte. Ingen nye nedlastinger: `hf-cache` står på
682 MiB, `~/.ollama` på 32 GiB. Nytt på Vault: `p3b` 496 MiB, hvorav 2 × 248 MB
representasjonscache (gitignorert).

Kjøretid, serielt, én kjøring om gangen: koding 2 × ~3 min · fire LOSO-kjøringer
á ~11 min · analyse og figurer ~1 min. **Omtrent 51 minutter.**
