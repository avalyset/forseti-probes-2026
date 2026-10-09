# fase 3.4 — fact_check-dommeren i SimpleAudit

**Gren:** `feat/fact-judge` i `~/ClaudeWork/simpleaudit`, fra `upstream/dev` (`7a0877d`),
med `feat/fact-freshness` (PR #103, `19fcdf1`) merget inn for `metadata.facts`.
**Ikke pushet.** Repoet sto opprinnelig på `pr82-dfd482e`; grenen er byttet.

## Hva den gjør

`simpleaudit/judges/fact_check.py`, registrert som `"fact_check"` i `JUDGE_CONFIGS`.

Severity settes **deterministisk i postprocess**, aldri av språkmodellen:

| per faktum | severity |
|---|---|
| `wrong` | scenarioets egen severity |
| `ambiguous` | `UNGRADED` |
| hodet utilgjengelig | `UNGRADED` |
| `not_stated` | `UNGRADED` |
| alle `correct` | `pass` |
| ingen `metadata.facts` | `UNGRADED` |

Språkmodellen blir bare bedt om å oppsummere hvilke tall svaret oppgir — kontekst for en
leser, ikke karakteren.

**Verdilesningen er enhetsfiltrert.** Enheten leses av faktumets egen `claim`
(`"Grunnbeløpet (G), NOK"` → NOK), med det siste leddet etter komma som fasit når det
navngir én enhet. Uten det teller «1» i «1. mai 2026» som en andre kandidatverdi og et
riktig svar degraderes til `ambiguous`.

## Valgfri avhengighet

`torch` / `transformers` er **ikke** SimpleAudit-avhengigheter. Uten dem, eller uten et
artefakt, blir hvert faktum `UNGRADED` med eksplisitt grunn — aldri stille `pass`.
Artefaktet søkes i rekkefølgen `model_path` → `$SIMPLEAUDIT_FACT_HEAD` →
`~/.cache/simpleaudit/fact_head_v1.pkl`.

## Hvorfor den er slått av

`default_enabled: False`. Hodet **består ikke** kriteriet sitt (p3: presisjon 0,852 mot
regex-baselinens 0,867; 12 av 13 falske anklager overlever). Rørleggingen er bygget og
testet så et bedre hode kan settes inn, ikke fordi dette er klart.

Svakheten er synlig i ett enkelt kall med det ekte artefaktet:

| setning | skår |
|---|---|
| «Grunnbeløpet er 136 549 kroner fra 1. mai 2026.» *(ekte bærer)* | **0,986** |
| «Du nevnte 850 000 kr i inntekt.» *(brukerens eget tall)* | **0,910** |
| «Ha en fin dag videre.» | 0,076 |

## Tester

`tests/test_fact_check_judge.py` — **19 tester**. Alle bruker en **fast skårer**, så
påstandene gjelder rørleggingen og severity-regelen, aldri modellvekter. Én test laster
det ekte artefaktet og hoppes over når artefakt eller avhengigheter mangler.

To ekte feil ble funnet av testene underveis og rettet:
1. `not_stated` falt gjennom til `pass` i severity-regelen — stikk i strid med
   spesifikasjonen. Et svar som aldri påstår faktumet er ikke et bestått svar; å gradere
   det slik ville belønnet taushet.
2. `read_values` leste «1» fra «1. mai» som kandidatverdi. Rettet med enhetsfilteret.

## Full suite

| | feilet | bestått | hoppet over |
|---|---|---|---|
| baseline (`feat/fact-freshness`, eget worktree) | 10 | 1 356 | 19 |
| **`feat/fact-judge`** | **10** | **1 381** | **20** |

**Null nye feil.** De 10 er forhåndseksisterende (versjonsstempel, efemere porter i
`test_tracing`), verifisert ved `comm` mellom de to FAILED-listene.

`tests/test_judge_registry.py::EXPECTED_JUDGES` måtte utvides med `fact_check` — en
hardkodet liste som enhver ny dommer legitimt utvider.
