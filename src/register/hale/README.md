# hale — halen for satser

Finner at en sats på en offentlig side har endret seg, og foreslår endringen i
registeret. Sideinnhold er **data**: ingen LLM-kall i denne runden.

```bash
python run.py --as-of 2026-06-01            # alle ÅRLIG-rader som har passert datoen
python run.py --as-of 2026-06-01 --rows NAV-01 --no-fetch
python test_backwards.py                    # baklengs-test på to ekte snapshots
```

## Kjeden

`fetch.py` → snapshot (rå HTML + sha256 + dato) · `diff.py` → endrede tekstblokker ·
`extract.py` → kandidatverdi · `propose.py` → forslag eller sak · `run.py` → ett løp,
kalenderstyrt.

## Uttrekket bruker registerets eget sitat som mal

Keyword-nærhet alene ga **190 kandidater** på nav.no/grunnbelopet, fordi siden lister G
tilbake til 1967 og hver historisk verdi ligger «NOK nær grunnbeløpet».

Registeret har allerede det presise mønsteret: radens verbatim-sitat. Med verdien
wildcardet blir «Grunnbeløpet (G) per 1. mai ⟨år⟩ er ⟨N⟩ kroner» en mal som treffer
ledesetningen og ikke en tabellrad. Det tok kandidattallet fra 190 til **1**.
Keyword-nærhet er beholdt som fallback når sitatet er omskrevet på siden.

Bare tallet som **bærer enheten** teller. Uten det ble «1» og «2026» i «per 1. mai 2026»
også kandidater.

## Porten

Et forslag krever **begge**: ≥ 2 uavhengige kilder gir samme verdi, **og** |endring| < 10 %.
Ellers blir det en **sak** — ikke en feil, men en verdi et menneske må se på.

**Bokstavelig lest kan porten aldri fyre for en ny sats.** En fersk verdi finnes per
konstruksjon i null registerrader, siden registeret er det som skal oppdateres.
Implementert teller derfor også bekreftelse fra andre raders **verbatim claim** med en
annen kilde-URL — ny G nevnes i NAV-02/03 sine kontrollregninger fra nav.no/aap.
`independent_support(..., allow_claim_text=False)` gir den bokstavelige lesningen.

## Feiler høyt

404, manglende/ugyldig URL, tom tekst etter tagg-stripping, ingen kandidat i en endret
side — alt blir en sak i `saker/`. Ingenting svelges.

## Kalender

`calendar.yaml` har kjent endringsdato per rad (G 1. mai, statsbudsjett 1. januar,
studieår 1. august). `run.py --as-of DATE` kjører bare rader som har passert datoen.
Ingen cron i denne runden — datoen er et eksplisitt argument.
