# ADR-0002 — Lovendringer følges med snapshot-diff av Lovdatas åpne datasett, ikke med Lovdatas varsling

**Status:** vedtatt
**Dato:** 2026-10-09
**Kontekst:** Forseti fase 2b — rekognosering

## Kontekst

Registeret har 118 rader. Hver rad har et `legal_basis` skrevet for mennesker:
«ftrl. § 21-12», «fvl. § 29», «blåreseptforskriften § 8», «§ 10-4 fjerde ledd». Når en
paragraf en rad peker til endres, skal 2b liste de berørte radene og scenariene.

To ting måtte avgjøres: hvor endringen kommer fra, og hvordan prosaen i `legal_basis`
blir en maskinell nøkkel. Rekognoseringen leste alle 118 hjemmelsfelt og undersøkte hva
Lovdata faktisk tilbyr.

### Hva Lovdata tilbyr

Fire bulk-arkiv er åpne, lisensiert **NLOD 2.0**, uten konto og uten autentisering, og
legges ut på nytt hver natt:

| Arkiv | Innhold |
| --- | --- |
| `gjeldende-lover.tar.bz2` | 758 lover, konsolidert |
| `gjeldende-sentrale-forskrifter.tar.bz2` | 5 114 forskrifter, delegeringer, instrukser, stortingsvedtak |
| `lovtidend-avd1-<år>.tar.bz2` | årets kunngjøringer i Norsk Lovtidend avd. I |
| `lovtidend-avd1-2001-<år>.tar.bz2` | de samme tilbake til 2001 — 39 000 kunngjøringer |

De to første er 27 MB komprimert, Lovtidend 70 MB til. Hentes via
`https://api.lovdata.no/v1/publicData/get/<filnavn>`; filnavnene leses fra
`/v1/publicData/list`, som gir `filename`, `lastModified` og `sizeBytes` per pakke.

**Det avgjørende funnet:** de konsoliderte tekstene sier hva som gjelder nå, men
**Norsk Lovtidend avd. I sier hva som ble endret** — og fra 2023 er hver enkelt endring
merket ned til ledd:

```
<article class="change" data-change-part="lov/2005-06-17-62/§15-6/ledd/3">
```

Det er en maskinlesbar endringslogg på paragrafnivå, gratis, i det åpne datasettet.
Hvert dokument oppgir dessuten selv hvilke dokumenter det endrer
(`dd.changesToDocuments`), kunngjøringsdato (`dd.dateOfPublication`) og ikrafttredelse
(`dd.dateInForce`). De konsoliderte tekstene bærer `dd.lastChangeInForce` og
`dd.lastChangedBy` per dokument — men ikke per paragraf.

Kunngjøringer fra før 2023 har bare instruksjonen i klartekst — «§ 15-6 tredje ledd skal
lyde:» — under en innledning som «I lov 17. juni 2005 nr. 62 … gjøres følgende
endringer:». Formen er regelmessig nok å lese paragrafer ut av; en uavhengig
implementasjon måler uttrekket til **96 % presisjon og 88 % dekning** mot Lovdatas egen
merking i årgangene som har begge. For Forseti er det uten betydning: vi trenger
endringer framover, ikke historikk.

### Hva Lovdata ikke tilbyr gratis

Lovdatas varslingstjeneste har eksistert siden 2002 og kan settes på enkeltparagrafer.
Men den er **e-post til et menneske**, ikke et grensesnitt. Rekognoseringen fant ingen
RSS og ingen varslings-API. Den frittstående tjenesten er dessuten stengt for nye
kunder: varsling «er ikke lenger et eget tilbud til nye kunder», og funksjonen ligger nå
i Lovdata Pro, som koster **kr 12 500/år for 1–3 brukere** (prislisten oppgir også
kr 6 500 for én bruker; de to tallene spriker, og det er ikke avklart). En egen
API-nøkkel for strukturert regelverk koster **kr 15 000/år eks. mva.** pluss en avgift
per tegn.

Utenfor de åpne arkivene ligger historiske lovtekster, opphevede lover, lokale og
kommunale forskrifter, rundskriv og rettspraksis. Alt det er Lovdata Pro.

**Ikke lest:** `lovdata.no` og `api.lovdata.no` var sperret av sesjonens egress-policy
(403 på CONNECT) — ikke av innlogging. Alt om priser, vilkår og endepunkter over er
derfor **annenhånds**: korroborert via søk mot de levende sidene, og mot to uavhengige
implementasjoner som leser datasettet. Ingen vilkårsside er lest direkte, og ingen
datapakke er lastet ned. Det er en reell svakhet i grunnlaget, ikke en formalitet.

Vilkårene spriker på ett punkt som angår oss. De åpne datasettene er NLOD 2.0 og kan
«fritt brukes til alle formål». Samtidig sier en vilkårsside for prøvetilgang at dataene
«skal ikke brukes i språkmodeller eller andre KI-modeller», og brukervilkårene for
nettjenestene at det ikke er tillatt å trene KI på innholdet. Forseti **trener ikke** på
lovtekst — 2b sammenligner paragrafidentifikatorer og flagger rader — så bruken holder
seg innenfor også den strenge lesningen. Men motsetningen må avklares med Lovdata før
noen bruker korpuset til noe annet.

### Hva `legal_basis` faktisk inneholder

Alle 118 felt er lest. 76 distinkte verdier. Formen er ikke én, men fire:

1. **Stående bestemmelse** — «arbeidsmiljøloven § 10-4 første ledd». Løsbar.
2. **Bar paragraf** — «§ 10-4 fjerde ledd». **31 rader.** Loven er ikke navngitt.
3. **Endringsvedtaket selv** — LK-04 har `LOV-2026-06-19-60`, og paragrafen (§ 18) står
   i radens `claim`, ikke i hjemmelsfeltet.
4. **Ikke lovtekst** — rundskriv, etatsside, «Stortingets årlige vedtak», eller tomt.
   **30 rader har tomt felt.**

De 31 bare paragrafene er et markdown-artefakt: i den opprinnelige tabellen sto loven i
første rad og de neste sparte plass. `section`-feltet i YAML-en redder det **ikke** — det
navngir etat og tema («Tolletaten — reisegodskvoter og verdigrenser»), aldri loven. Arven
må derfor skrives eksplisitt. For Tolletaten er den internt bekreftet: TOLL-13 siterer
«Begrensningene i § 4-1-11 til § 4-1-13», en kryssreferanse til samme forskrift TOLL-01
navngir.

De 30 tomme feltene deler seg i tre, og skillet er avgjørende: rader som ikke *har* en
hjemmel (ISBN/ISSN-praksis, etatspraksis ved ID-kontroll, et kundetelefonnummer), rader
som er KORRIGERT og bærer en tidligere feil som historikk (HF-03, HF-04, LK-14), og
rader som mangler en hjemmel de burde hatt. Bare den siste gruppen er et hull å tette,
og rekognoseringen har ikke avgjort hvilke rader som faller der.

## Vurderte alternativer

### A. Lovdata Pro-varsling

Ferdig, presist, paragrafnivå, vedlikeholdt av Lovdata. Og forkastet: det er e-post til
et menneske. En varsling som havner i en innboks kan ikke koble seg til 118 YAML-rader,
kan ikke kjøres baklengs mot et kjent tilfelle, og etterlater ikke noe revisjonsspor i
git. Den koster kr 12 500/år for å gjøre et menneske til integrasjonslaget. Prosjektet
har dessuten alt avvist e-postvarsling implisitt: `hale` henter sider og foreslår diff i
git, nettopp fordi forslaget må være etterprøvbart.

### B. Lovdatas API-nøkkel for strukturert regelverk

Kr 15 000/år pluss avgift per tegn, og krever avtale. Den gir pene strukturerte
dokumenter og `renderRefID?refID=lov/2005-05-20-28/§4` for oppslag per paragraf. Men vi
trenger ikke å *lese* paragrafer pent — vi trenger å vite at de endret seg, og det
leveres gratis i Lovtidend-arkivet. Å betale for et bedre leseformat løser ikke
endringsproblemet.

### C. Diff av to snapshots av `gjeldende-lover`

Nærliggende, siden `hale` alt gjør snapshot-diff på etatssider, og det var vårt
utgangspunkt. Men det er den dårligere av de to gratisveiene. En diff av konsolidert
tekst gir *at teksten i et dokument er endret*, og paragrafen må leses ut av hvor i
dokumentet diffen traff. Det er hele parseproblemet på nytt, med vår egen feilrate, for
å utlede noe Lovdata alt har merket. Verre: `dd.lastChangeInForce` er per dokument, så en
billig forhåndssjekk sier bare «noe i arbeidsmiljøloven er endret» — ikke hvilken
paragraf. 27 MB hver natt for å gjenskape en merking som finnes.

### D. Norsk Lovtidend avd. I som hendelseskilde — **valgt**

## Beslutning

**Kilden er Norsk Lovtidend avd. I fra det åpne datasettet, med `data-change-part` som
paragrafnøkkel.** Hendelsen er en kunngjøring, ikke et tekstavvik.

Det snur problemet riktig vei. En kunngjøring *er* en endringshendelse, med dato,
ikrafttredelse, hvilket dokument den endrer, og — fra 2023 — hvilken paragraf. Vi
utleder ingenting Lovdata alt har sagt. Og årets årgang er 1,4 MB, mot 27 MB for et fullt
lovsnapshot: en daglig sjekk er billig nok at den kan gå uten kalenderstyring.

De konsoliderte arkivene hentes fortsatt, men til en annen oppgave: å vise den nye
ordlyden når en rad er flagget. De er oppslagsverket, ikke varsleren.

### Konsekvenskartet

Kartet har to ledd, og bare det første er nytt arbeid.

**Paragraf → rader.** `src/register/lovkart.yaml` oversetter forkortelse til
Lovdata-dokument, med `used_by` per rad, eksplisitt `arv` for de 31 bare paragrafene, og
`status` per ID som sier om den er registerfestet, korroborert eller ubekreftet.
`resolve_lovkart.py --check` feiler hvis registeret og kartet driver fra hverandre.
Matchen skjer på **paragraf**, med ledd som avgrensning når begge har det.

Registerets presisjon er finere enn merkingen: «§ 4-1-13 første ledd tredje punktum» har
tre nivåer, `data-change-part` når to. Punktum, bokstav og «siste punktum» finnes ikke
som adresserbart nivå. Å kreve punktum ville gitt tapte treff, ikke presisjon — så de
står som tekst mennesket leser.

**Rader → scenarier.** Dette leddet skal **ikke** bygges på nytt. `check_packs.py`
kobler alt pakkenes tall til `fact_id` og domene, og `data/expected_facts.yaml` har
`scenarios[].pack` med en `register`-referanse per fakta. 2b skal gjenbruke den
koblingen.

### Måltall, ikke anslag

`resolve_lovkart.py` måler dekningen mot registeret:

```
LØST 70 · DOKUMENT 11 · DELVIS 2 · TVETYDIG 3 · ULØST 0 · UTENFOR 32
```

70 rader kan følges på paragrafnivå. 11 har dokument men ingen paragraf. 2 har blandet
grunnlag der paragrafdelen kan følges. 3 krever et menneske. 32 kan ikke treffes av en
lovendring i det hele tatt.

### Baklengs-test før mekanikk

`hale` har en baklengs-test på to ekte snapshots. 2b skal ha sin, og rekognoseringen fant
tilfellet: **FOR-2025-12-17-2621** endret blåreseptforskriften § 8 til «60 prosent av
samlet utsalgspris, men ikke mer enn 400 kroner per utlevering» — ordrett det HF-09
påstår. Kjeden

```
FOR-2025-12-17-2621 → forskrift/2007-06-28-814/§8 → blåreseptforskriften § 8 → {HF-06, HF-09}
```

kan verifiseres ende til ende uten å gjette. Fire flere kjente endringer står i
`lovkart.yaml` under `endringsvedtak` med `expected_hit`, så fasiten finnes før koden.

## Konsekvenser

**Positive.** Gratis og uten konto. Paragrafnivå rett fra kilden, ikke utledet. NLOD 2.0
tillater bruken. Hendelsen bærer både kunngjøringsdato og ikrafttredelse, så en endring
kan flagges *før* den trer i kraft — registeret har alt rader som trenger det (LK-05
gjelder t.o.m. 31.7.2026). `futureLegalArticle` i de konsoliderte tekstene bærer samme
mulighet. 1,4 MB per sjekk.

**Negative.** Vi eier parsingen av Lovdatas XHTML, og formatet er maskingenerert men
udokumentert som kontrakt — det kan endres uten varsel. Ikrafttredelse står ofte som
«Kongen bestemmer», og datoen kommer da i en senere kgl.res., så ikrafttredelse er ikke
alltid kjent ved kunngjøring. Lokale forskrifter og rundskriv er ikke dekket i det hele
tatt.

**Akseptert som følge.** `fvl.` → `LOV-1967-02-10` er **ubekreftet**. Den ene IDen i
kartet som ingen kilde har bekreftet står der som hypotese, flagget, framfor å bli
utelatt eller presentert som verifisert. LK-01 er den eneste raden som rammes.

### Hullet 2b gjør synlig, som registeret skjulte

Dekningen er invertert mot behovet:

| trigger | LØST | DOKUMENT | DELVIS | TVETYDIG | UTENFOR | sum |
| --- | --- | --- | --- | --- | --- | --- |
| LOVENDRING | **8** | 7 | 0 | 0 | 2 | 17 |
| STABIL | 36 | 0 | 0 | 0 | 3 | 39 |
| ÅRLIG | 12 | 3 | 2 | 1 | 0 | 18 |
| PRAKSIS | 14 | 1 | 0 | 2 | 24 | 41 |

Av de 17 radene registeret selv har merket **LOVENDRING** — nettopp de 2b finnes for —
kan bare **8** følges på paragrafnivå. Sju er pliktavleveringsrader som oppgir loven uten
paragraf (NB-17 … NB-23), og to har rundskriv som grunnlag (HF-01, HF-02). Samtidig er 36
av 39 **STABIL**-rader fullt løsbare: de radene som endres sjeldnest, er de best
adresserte.

Mekanikken løser ikke dette. Enten får de sju NB-radene en paragraf, eller
pliktavleveringslova følges på dokumentnivå med støyen det gir. Det er registerarbeid,
ikke kode, og det er det første 2b bør bestille.

### Et brudd midt i konsekvenskartet

De **eneste** maskinelle koblingene fra en rad til et scenario er tre oppføringer i
`data/expected_facts.yaml`, og de peker ikke på YAML-registeret. De peker på markdown-
registerets kryss-tabell:

```
NDVL-REG-0002, seksjon «Kryss-domene: klagefrist varierer», linje 320
NAV | 6 uker fra mottatt vedtak | ftrl. § 21-12
```

Verken `ftrl. § 21-12` eller `skfvl. § 13-4` finnes blant de 118 YAML-radene.
Klagefrist-tabellen ble ikke konvertert — ADR-0001 sa det ville skje, og kalte
kryss-tabellene prosa «som ikke er fakta med verdier». Følgen er at kjeden paragraf →
rader → scenarier har et brudd i midten: paragrafkoblingen fester seg i YAML-en,
scenariokoblingen i en markdown-fil som ikke ligger i dette repoet.

`skfvl.` er derfor ført inn i `lovkart.yaml` med `used_by: []` — oppføringen er riktig og
brukes av ingen rad. Det er ikke en feil i kartet; det er bruddet, skrevet ned.

To veier ut, og valget er ikke tatt her: konvertere klagefrist-tabellen til YAML-rader,
eller la `expected_facts.yaml` peke på radene direkte. Det første er mer arbeid og
fjerner den andre sannheten.

## Det som gjenstår før 2b kan bygges

1. Bekreft `fvl.` → `LOV-1967-02-10`, og hent tittelen til `FOR-2020-06-18-1262`.
2. Avgjør de tre tvetydige: LK-22 («forskrift om utdanningsstøtte 2026–2027» — egen
   forskrift eller endring i FOR-2020-04-15-798?), LK-10 (to dokumenter i ett felt),
   LK-12 (hjemmel mangler og raden er **UVERIFISERT**).
3. Avgjør om HF-01/HF-02 har en forskriftshjemmel som kan følges. Rekognoseringen fant at
   blåreseptforskriften § 8 nå lyder «Barn under 18 år og minstepensjonister skal ikke
   betale egenandel», så aldersendringen ligger også i det åpne arkivet — men hvilken
   bestemmelse som bærer det *brede* egenandelsfritaket er ikke avgjort, og en gjettet
   kobling ville gitt to rader som ser overvåket ut uten å være det.
4. Gi NB-17 … NB-23 paragraf, eller godta dokumentnivå for pliktavleveringslova.
5. Lukk bruddet mot scenariene.
6. Les vilkårssidene direkte når egress tillater det, og avklar KI-klausulen med Lovdata.
   Alt om pris og vilkår i denne ADR-en er annenhånds.
