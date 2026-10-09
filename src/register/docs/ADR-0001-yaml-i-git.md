# ADR-0001 — Faktaregisteret som YAML i git, ikke database og ikke markdown

**Status:** vedtatt
**Dato:** 2026-10-09
**Kontekst:** Forseti fase 0

## Kontekst

NDVL-REG-0002 er i dag en markdown-fil med 118 rader fordelt på ni tabeller. Den har
tjent sitt formål som menneskelesbart revisjonsspor, men den kan ikke slås opp
maskinelt: en rad er én tekststreng der påstand, tall, dato og kilde ligger blandet i
samme celle. Når en scenariopakke påstår «grunnbeløpet er 130 030», finnes det ingen
mekanisk vei fra den påstanden til raden som motsier den.

Tre kandidater ble vurdert.

## Vurderte alternativer

### A. Beholde markdown
Lesbart i nettleser og i diff. Men verdiene er ikke adresserbare: for å finne «hva var G
den 1. mai 2025» må man lese prosa. Flere historiske verdier i samme celle
(«Forrige verdier: 130 160 (1.5.2025), 124 028 (1.5.2024)») kan ikke slås opp per dato.
Ingen validering — en rad kan mangle kilde uten at noe fanger det.

### B. Database (SQLite eller Postgres)
Gir spørringer og integritetsregler. Men en binærfil i git gir ubrukelig diff, og
revisjonssporet er hele poenget med registeret: når endret denne satsen seg, hvem endret
den, og mot hvilken kilde. En database flytter historikken fra git til en
`history`-tabell man selv må vedlikeholde, og dobler dermed sannheten. For 118 rader er
det dessuten en driftsbyrde uten motytelse.

### C. YAML i git — **valgt**
Én fil per domene, ett dokument per fakta, verdier som en tidsordnet liste.

## Beslutning

YAML i git, modellert etter **OpenFisca**s parametermønster: en parameter er ikke ett
tall, men en liste av verdier med gyldighetsdato. Det er den strukturen norsk forvaltning
faktisk har — satser endres ved en dato, og den gamle satsen gjelder fortsatt for
perioden før.

```yaml
- id: NAV-01
  domain: nav
  claim: "Grunnbeløpet (G) per 1. mai 2026 er 136 549 kroner."
  legal_basis: "folketrygdloven § 1-4"
  review_trigger: ÅRLIG
  review_by: "2027-05"
  values:
    - value: 136549
      unit: NOK
      valid_from: "2026-05-01"
      valid_to: null
      sources:
        - url: "https://www.nav.no/grunnbelopet"
          quote: "Grunnbeløpet (G) per 1. mai 2026 er 136 549 kroner."
          verified_at: "2026-10-07"
    - value: 130160
      unit: NOK
      valid_from: "2025-05-01"
      valid_to: "2026-04-30"
      sources: [...]
```

### Hvorfor dette løser det markdown ikke løste

- **Oppslag per dato.** «Hva var G den 12. mars 2025» er en listeoperasjon, ikke en
  tekstlesning. Det er forutsetningen for `check_packs.py`: en pakke påstår et tall *for
  et år*, og registeret må kunne svare for nettopp det året.
- **Historikk uten duplisering.** Den gamle satsen blir ikke slettet når en ny kommer.
  Den får `valid_to` og blir stående. Git forteller når *raden* ble endret; `valid_from`
  forteller når *regelen* ble endret. Det er to ulike ting, og markdown blandet dem.
- **Kilde per verdi, ikke per rad.** Hver verdi bærer sin egen URL, sitat og
  verifiseringsdato. En rad med fem historiske verdier har fem uavhengige kildespor.
- **Diff som revisjonsspor.** En satsendring er en lesbar diff på fire linjer.
- **Validering er mulig.** Et skjema kan kreve at hver verdi har minst én kilde med sitat
  og dato, og CI kan avvise en verdi uten.

### Hvorfor ikke database

Revisjonssporet er produktet. Et register der man må spørre en `history`-tabell om hvem
som endret hva, når git allerede svarer på det, har to sannheter om samme sak. Ved 118
rader — eller 1 180 — er YAML raskt nok til at ytelse ikke er et argument.

## Konsekvenser

**Positive.** Maskinelt oppslag per dato og per domene. Kildekrav kan håndheves. Diff er
lesbar. Ingen ny infrastruktur.

**Negative.** YAML tåler ikke vilkårlig dyp struktur godt, og håndredigering kan
introdusere syntaksfeil som markdown ikke hadde. Det krever en validator i CI.
Menneskelesbarheten er dårligere enn markdown for den som bare vil bla.

**Akseptert som følge.** Markdown-registeret blir ikke slettet. Det er kilden
konverteringen leser fra, og det bevarer prosaen — lærdomsavsnitt, hull-seksjoner,
kryss-tabeller — som ikke er fakta med verdier og derfor ikke hører hjemme i YAML-en.

## Et hull YAML-en gjør synlig, som markdown skjulte

Av de 118 radene mangler **30 kildefelt** og **46 neste-sjekk-dato**. I markdown står det
som en tankestrek og forsvinner i tabellen. I YAML blir det et tomt `sources: []` og et
manglende `review_by`, og det **flagges**. Konverteringen gjetter ikke — en ufullstendig
rad blir værende ufullstendig, med flagget synlig.
