# Forseti probes 2026: six preregistered experiments on Norwegian public-service fact checking

Eirik Botten Nicolaysen · [ORCID 0009-0001-9188-6788](https://orcid.org/0009-0001-9188-6788) · EcoDeco AS
**Version 1.1.0** · 2026-10-09

**Concept DOI** (always the latest version): [10.5281/zenodo.23260755](https://doi.org/10.5281/zenodo.23260755)
**v1.0.0**: [10.5281/zenodo.23260756](https://doi.org/10.5281/zenodo.23260756)
**v1.1.0**: version DOI minted at deposit — see «Deposit status» below.

Cite the concept DOI unless you need to pin an exact version. Machine-readable
metadata is in `CITATION.cff`.

### What v1.1.0 adds

Two engineering tasks, both on the register side, neither preregistered:

- **2b — lovendringer**: a consequence map from an amendment published in Norsk
  Lovtidend to the register rows that rest on the amended paragraph.
- **Metningsvakt**: four guards that fire when the register stops being something
  we can see — expired rates, rates the packs claim and the register does not know,
  sources that no longer answer, and a tail that went quiet.

Nothing in fase 1–3c changed. Those reports, preregistrations and figures are
byte-identical to v1.0.0.

---

## What was tested

Whether a language model's handling of Norwegian public-service facts can be checked
mechanically — first by probing frozen representations, then by giving up on that and
writing the check as code.

Nine pieces of work are deposited. Five are preregistered experiments with a hypothesis,
a criterion fixed before running, and a verdict. Four are engineering tasks with no
hypothesis to preregister.

| | what | preregistered |
|---|---|---|
| fase 1 | can a linear probe on frozen representations classify refuse/answer? | yes, `b7251a28` |
| fase 1b | does that signal hold on public-service prompts from five domains? | yes, `d35342b2` |
| fase 0 | the fact register as structured YAML, and a pack checker | no — see below |
| fase 2 | a tail that notices when a published rate changes | no — see below |
| fase 3 | a learned sentence picker for "does this answer state fact X?" | yes, `208343b2` |
| fase 3b | the same picker, given the user's prompt as context | yes, `c05903f7` |
| fase 3c | the picker replaced by two deterministic filters | yes, `65f3e027` |
| fase 2b | an amendment in Norsk Lovtidend → the register rows it touches | no — see below |
| vakt | four guards over register and tail saturation | no — see below |

Each preregistration was committed as its own commit **before** the run it governs. The
SHA is in the filename under `PREREG/`, and the matching report is in `RAPPORT/`.

**The title says six preregistered experiments. There are five.** The count in this table
is the accurate one, and it was already five in v1.0.0 — the title overstated it by one
when the deposit was first published. The title is left unchanged anyway: it is the
published title of a record with a concept DOI, and renaming it between versions would make
the citation in v1.0.0 point at something with a different name. The error is recorded
here and in `FRYS-v1.1.md` rather than quietly corrected.

**Fase 0, fase 2, fase 2b and the vakt have no `PREREG.md` and no `RAPPORT.md`, and none
has been written after the fact.** They were engineering tasks — convert a register, build
a change detector, map amendments onto rows, watch for staleness — not hypothesis tests.
Their design documents are `docs/ADR-0001-yaml-i-git.md`,
`src/register/hale/README.md`, `docs/ADR-0002-lovendringer.md` and the dated reports under
`src/register/vakt/rapporter/`, written while the work was done. The six-document symmetry
of the other phases does not exist for these four, and inventing it would misrepresent
what happened.

## 2b — lovendringer

Fase 2b asks the question the tail cannot: not «has this page changed?» but «has the
paragraph this row rests on been amended?». The answer source is **Norsk Lovtidend
avd. I** from Lovdata's open bulk dataset — NLOD 2.0, no account, no authentication —
and the event is a *kunngjøring*, not a text diff. `docs/ADR-0002-lovendringer.md` is
the decision record, including the three alternatives it rejected and what each would
have cost.

| measure | value | source |
|---|---|---|
| announcements read from the archive | **4499** | `lovtidend/rapporter/impact.md` |
| announcements that touch a register row | **146** | `impact.md`; `impact.json` carries 146 entries |
| document level available (`changesToDocuments`) | **93,6 %** | `impact.md`, measured on 2025+2026 |
| paragraph level available (`data-change-part`) | **6,4 %** | `impact.md`, same measurement |

### The recon was wrong about the paragraph level, and the code says so

ADR-0002 read Lovdata's markup and concluded that «fra 2023 er hver enkelt endring
merket ned til ledd» — a machine-readable change log at paragraph level. Measured
against the archive it is present in **6,4 %** of announcements, not most of them.
`src/register/lovtidend/impact.py` records the correction in its own docstring:
«Rekognoseringen antok at paragrafnivaet var bredt tilgjengelig «fra 2023». Det er det
ikke.» The map is therefore built on document level, with paragraph as a refinement
where it exists.

The ADR is deposited **unedited**, with its prediction intact, next to the measurement
that contradicts it. That is the point of dating a decision record.

### Coverage of the register

`resolve_lovkart.py` resolves each row's `legal_basis` prose against `lovkart.yaml` and
counts the outcome. Measured at deposit time on the 121 rows in this version:

```
LØST 77 · DOKUMENT 7 · DELVIS 2 · TVETYDIG 3 · ULØST 0 · UTENFOR 32
```

ADR-0002 reported `LØST 70 · DOKUMENT 11 · DELVIS 2 · TVETYDIG 3 · ULØST 0 · UTENFOR 32`
over 118 rows. The difference is four pliktavlevering rows that were given a paragraph
and three klagefrist rows that did not exist then.

The gap the ADR made visible was that coverage ran **opposite** to need: of the 17 rows
the register itself marks `LOVENDRING` — the rows 2b exists for — only **8** could be
followed at paragraph level, while 36 of 39 `STABIL` rows could. Measured now, at 121
rows, it is **15 of 20** `LOVENDRING` rows at paragraph level, 3 at document level and 2
outside reach. Both of the register changes that moved it are listed above; neither is
mechanism work, which is what the ADR predicted.

### The backwards test, and the level it actually hits

`lovkart.yaml` names five amendments under `endringsvedtak` with an `expected_hit`
written down before the map was built. All five are found:

```
5/5 forventede treff
```

**Four of the five, including the main criterion, hit at document level, not paragraph
level.** `FOR-2025-12-17-2621 → {HF-06, HF-09}` is the chain ADR-0002 described as
`FOR-2025-12-17-2621 → forskrift/2007-06-28-814/§8 → blåreseptforskriften § 8 →
{HF-06, HF-09}`. The announcement carries no `data-change-part`, so the `/§8` link in
that chain does not exist in the archive. `test_backwards.py` prints this caveat under
its own verdict rather than beside it.

Document level is also **wider than the expectation**: the criterion is that the expected
rows are among those found, and `FOR-2026-04-24-649` brings seven further `LK` rows along
with the `LK-11` it was meant to hit. A document-level flag says the document changed, so
every row resting on that document is a candidate. That is noise a human must filter, not
a false positive the code can remove.

### What 2b surfaced about the register

- `lov/1967-02-10` (`fvl.`) is the one document ID in `lovkart.yaml` that ADR-0002 could
  not confirm from any source and deposited as `ubekreftet`. It appears as an amended
  document in **five** announcements in the archive, two of them at paragraph level
  (§ 12, § 51) — so the ID exists in Lovdata's own data. The status field is left
  `ubekreftet` anyway: that vocabulary describes how the recon found an ID, and changing
  it is register work, not a consequence of this reading. The evidence is recorded in the
  entry's own note.
- One of those five is `LOV-2025-06-20-81 — Lov om saksbehandlingen i offentlig
  forvaltning (forvaltningsloven)`, in force «Kongen bestemmer», which declares that it
  amends `lov/1967-02-10`. The map flags `LK-01` (klagefrist 3 uker) on it. **What a new
  forvaltningslov does to the three-week appeal deadline is not determined here** — the
  deposit contains the flag, not a reading of the act.
- The row → scenario link, the last leg of the chain, is **still broken in the deposited
  map**: all 1235 hits carry an empty `scenarier` column. `impact.py` reads
  `expected_facts.yaml` from a path outside this repository, so the deposited
  `data/expected_facts.yaml` — which holds exactly the three `register:` couplings
  ADR-0002 identified — is never seen. Pointed at the deposited file, the same function
  resolves **2 rows and 3 couplings** (`NAV-KLAGE-01`, `SKATT-KLAGE-01`). The code that
  closes the break exists; the path it reads does not survive deposit. Fixing that is the
  first thing to do next, and it is not fixed here because the map cannot be regenerated
  without the archive.

## Metningsvakt

«Saturation» here is not that everything is correct, but that we are still seeing what we
think we are seeing. Four guards, each with a fixed `--as-of` date and no clock:
**V1 utløp** (rates past `review_by`), **V2 dekning** (figures the packs claim and the
register does not know), **V3 kildehelse** (sources that never answered or answered long
ago), **V4 stillhet** (annual rates whose calendar date passed with no fetch).

Quoted from `src/register/vakt/rapporter/vakt_2026-10-09.md`:

| measure | value |
|---|---|
| fakta i registeret | **121** |
| med minst én verdi | 46 (38.0%) |
| med kildesitat | 1 (0.8%) |
| utløpt review_by | **9** (7.4%) |
| **Vakter som fyrer** | **4 av 4** |

V2 names **19** figures in the packs' `expected_behavior` that the register does not
cover; the guard calls it «hullet som lot 130 030 stå», the stale grunnbeløp fase 0 was
built to catch.
Of 51 `UKJENT` rows from `check_packs`, 24 are years (`for 2026`) and 8 are phone numbers
(116 123, 23 32 70 00); they are separated out in the guard rather than filtered away
upstream, so the filtering is visible.

**Every guard is tested twice: on a constructed case it must fire on, and on a clean case
it must stay silent.** A guard tested only against real data cannot be told apart from one
that always fires. Measured at deposit time:

```
20/20 bestått
```

### What the vakt reports do and do not reproduce

The top section, V1 and V2 of `vakt_2026-10-09.md` regenerate **exactly** from this
deposit. V3 and V4 do not: they read `src/register/hale/snapshots/`, which is withheld for
size, so a rerun reports 20 sources as «aldri hentet» where the deposited report says 10,
and 18 silent annual rows where it says 8. The deposited report is the one made with the
snapshots present.

`vakt_2027-05-02.md` is a projection — the same guards run against a future date — and it
was generated **before** the three klagefrist rows and `LK-12`'s `review_by` were added.
That is why its top section reads 118 rows and 43 with a value, and why it carries a
`FEIL` line naming `LK-12` as an `ÅRLIG` rate with no `review_by`. The register was then
changed to close exactly that error. Rerunning the same date against the register as
deposited gives 121 rows, 46 with a value, and no `FEIL` line. Both reports are kept: the
second one is the record of a guard finding something, and the fix is the reason the first
one is clean.

## The verdicts, verbatim from the reports

Each phrase below is quoted from the `KONKLUSJON` line of the report named beside it.

| phase | verdict | report |
|---|---|---|
| fase 1 | **«trenger data»** *(needs data)* | `RAPPORT/fase1.md` |
| fase 1b | **«overfører ikke»** *(does not transfer)* | `RAPPORT/fase1b.md` |
| fase 3 | **«virker ikke»** *(does not work)* | `RAPPORT/fase3.md` |
| fase 3b | **«virker ikke»** | `RAPPORT/fase3b.md` |
| fase 3c | **«virker ikke»** for probe + filters | `RAPPORT/fase3c.md` |

Four of five preregistered criteria were not met. Fase 3c's criterion was also not met —
but its preregistered control fired, and that is where the useful result is.

## Headline numbers

Every figure here is quoted from the report in the right-hand column.

| phase | measure | value | report |
|---|---|---|---|
| fase 1 | AUROC, nb-bert-base / mean-pool, LOO on 47 | **0,870 [0,755; 0,966]** | `fase1.md` |
| fase 1 | same task, reading the model's own text answer | 0,471 [0,289; 0,657] | `fase1.md` |
| fase 1b | one-class manifold, packs → the 47, mean (L10) | **0,410 [0,255; 0,594]** | `fase1b.md` |
| fase 1b | prompt-length baseline on the same test set | 0,566 [0,389; 0,730] | `fase1b.md` |
| fase 3 | pair precision, learned picker | **0,852** | `fase3.md` |
| fase 3 | pair precision, plain regex on the same 324 pairs | **0,867** | `fase3.md` |
| fase 3 | sentence-level AUROC, out of fold | 0,910 | `fase3.md` |
| fase 3 | known false accusations caught | **1/13** | `fase3.md` |
| fase 3b | pair precision, prompt concatenated into the input | **0,6914** | `fase3b.md` |
| fase 3c | pair precision, probe + F1F2 | 0,8642 | `fase3c.md` |
| fase 3c | pair precision, **regex + F1F2** | **0,8765** | `fase3c.md` |
| fase 3c | known false accusations caught, either config | **13/13** | `fase3c.md` |

## What the arc shows

The question «who is claiming this number?» looked like a classification problem and was
not one. An answer that repeats the figure a user typed looks, to a regex, exactly like
an answer that states it as the rule.

- **Fase 3** tried to learn the distinction from the sentence: 0,852 against a 0,867 regex
  baseline, 1 of 13 false accusations caught.
- **Fase 3b** tried to learn it from the sentence plus the user's prompt: 0,6914, worse.
  Two mechanisms were measured. Mean-pooling over a shared prompt prefix pushed the share
  of variance *within* an answer — the only variance that separates its sentences — from
  **45,0 %** down to 30,4 %. And «overlaps the prompt» generalises as a *positive* feature
  across scenarios, so a label calling it negative learns the wrong sign.
- **Fase 3c** looked the figure up instead: is it in any user turn? That filter (F1) plus
  one for phone-number fragments (F2) caught **13 of 13**.

### The caveat that belongs with «the probe is superfluous»

In fase 3c, regex + filters scored 0,8765 against the picker's 0,8642, both at 13/13.
**None of the pairwise precision differences in that phase are distinguishable from
noise** — McNemar p = 0,219 for exactly this comparison, and p = 0,22–1,00 across all of
them. So the claim is not that regex is better. It is that the picker bought no *measurable*
gain while costing a 248 MB artifact and a `torch` dependency, and at equal measured
performance the simpler thing wins.

The one difference that *is* significant is that a third filter on strict unit binding
**hurts** (p = 0,002): it discards legitimate bare figures such as «taket er 3278»
alongside the phone fragments. It is not applied.

Precision was never the right instrument for this. Thirteen pairs out of 324 is 4 % of the
data and drowns in an aggregate score. The failure mode was the measurement.

## What is not claimed

Collected from the reports' own «hva som ikke påstås» sections:

- **No generalisation beyond the fact types tested**: deadlines, amounts, counts,
  percentages. Dates were explicitly excluded (one declared fact carries `measured: False`).
- **No claim that the review labels are ground truth.** They are a deterministic rule
  applied to a regex extractor's hits, and they inherit that extractor's recall failures.
  A head that reproduced them perfectly would inherit the same blind spot.
- **No claim that twelve scenarios from two packs say anything about other domains.**
- **No claim that precision improved in fase 3c.** It did not, measurably. The
  false-accusation rate did, from 1 of 13 to 13 of 13.
- **No claim that F1 captures authorship in general.** It captures that *the same figure*
  appears in a user turn. A user who writes «seks uker» without digits, or a figure the
  model introduces and the user later repeats, falls outside it.
- **No claim that a linear probe «knows» anything.** It measures that information is
  linearly available in a representation, not that the model uses it.
- **No claim that the register is complete.** Fase 0's conversion report covers the 118
  rows it converted: 43 carry an extractable value and 75 do not; 117 lack a source quote,
  46 lack a review date, 30 lack a legal basis. Each is flagged rather than guessed. The
  register as deposited in v1.1 has **121** rows, of which **46** carry a value and **1**
  carries a source quote — the three added rows are the klagefrist table, and they close
  ADR-0002's break on the register side.
- **No claim that 2b is a mechanism.** What is deposited is a map and a measurement: an
  archive read once, 146 announcements matched against the register, and a backwards test
  on five known amendments. Nothing fetches on a schedule, nothing files a proposal, and
  nothing has run against a change that happened after the map was built.
- **No claim that document-level flagging is precise.** 93,6 % of announcements can be
  resolved only to the document they amend. Every register row resting on that document is
  then a candidate, and the backwards test shows that widening in practice.

Three preregistered criteria turned out to be unreachable or unreadable as written, and
each is documented in the report that found it: fase 1's absolute ECE bound sat *below*
the noise floor at n = 47; fase 1b's domain criterion compared in-sample to out-of-sample
distances with d ≫ n; fase 3b's trap criterion needed 10 of 13 fixed through an input that
could reach only 9.

## hei_refusal is not included, and why

Fase 1 and fase 1b were run against `hei_refusal`, a pack of 47 Norwegian prompts on
adolescent health. **That pack is SimulaMet's, not ours, and its content is sensitive. No
prompt text, and nothing from which a prompt could be reconstructed, is in this deposit.**

Rights, stated plainly:

- The eight scenario packs used in fase 1b and fase 3–3c (`nav_aap`, `skatteetaten`,
  `helfo`, `lanekassen`, `nb_kryss_ordning`, `skatteetaten_legitimasjon`,
  `toll_reisegodskvote`, `arbeidstilsynet_arbeidstid`) are this author's own work, MIT in
  SimpleAudit, and may be redistributed.
- `hei_refusal` is SimulaMet's and is **test-only**: never used for training in any phase,
  and not deposited here.

What was verified before deposit, against every file in this repository. These six
figures are **not** from a phase report — they were measured at deposit time by
`src/exclusion_check.py`, which is included so the table can be rechecked rather than
taken on trust. Running it needs the withheld file, so only someone holding it can
reproduce the check:

| check | result |
|---|---|
| 5-word windows from the 47 prompts | **0 hits** of 262 |
| 6-word windows | **0 hits** of 235 |
| 7-word windows | **0 hits** of 211 |
| 8-word windows | **0 hits** of 187 |
| largest share of any single prompt recoverable | **0,0 %** |
| `hei_refusal` content in `data/` | **0 files** |

```bash
python -I src/exclusion_check.py /path/to/scenarios.jsonl   # prints CLEAN or FAILED
```

**Status of that table in v1.1.** The six figures were measured against the v1.0.0 tree.
The window counts in the left column are a property of the 47 prompts and do not change.
The hit counts have **not** been re-measured against the files v1.1 adds, because the
window scan needs the withheld file and this version was assembled on a machine that does
not hold it. What was verified here instead, on the v1.1 tree:

| check | result |
|---|---|
| files under `data/` containing `hei_refusal` | **0** |
| files anywhere containing the string `hei_refusal` | **12** |
| of those, new in v1.1, the reading and its own document aside | **0** |

Ten are pre-existing: two preregistrations, two reports, two source files under
`src/p1b/`, this README, `FRYS.md`, `src/exclusion_check.py` and `LICENSE-CC-BY-4.0` —
the pack's *name* in each, and in fase 1's preregistration the sha256 of the withheld file.
The other two are new in v1.1 and are the reading of this version talking about the
exclusion: `frys_read_v11.py`, which contains the name because it searches for it, exactly
as `src/exclusion_check.py` does, and `FRYS-v1.1.md`, which reports what it found. Both are
listed by name in the script and asserted against this README, so the exception cannot
widen silently. The run's own log, `FRYS-v1.1.txt`, is held out of the count by name: when
the log is written by redirection the file is empty at the moment the scan reads the tree,
so counting it would make the number depend on run order rather than on content. **None of the 43 files the two merged branches bring in —
38 added, 5 changed — carries any `hei_refusal` content**, and nor does any other file new
in v1.1. **The full window scan at 5, 6, 7 and 8 words must be rerun
from the machine holding the withheld file before this version is deposited**, and
`FRYS-v1.1.md` records that as an open item rather than a passed check.

The string `hei_refusal` does appear, as the pack's *name*, in two preregistrations, two
reports and two source files, and the sha256 of the withheld file appears once in fase 1's
preregistration. That hash is what makes the preregistration auditable without exposing
the data, which is the point of recording it.

One 5-word window did collide during an earlier scan of the working trees, in files not
deposited: an everyday Norwegian phrase expressing apprehension, inside an unrelated
passage about NAV meldekort. It is a phrase collision, not a leak, and it is the reason
the check above also runs at 6, 7 and 8 words and measures per-prompt recoverability
rather than counting hits alone.

The phrase is not quoted anywhere in this repository. It was, in the first draft of
`src/exclusion_check.py`, and the script promptly failed on its own documentation — a
fragment of the withheld data had been written into the deposit to explain why that
fragment did not matter. The check caught it. That is the check working.

## Licences

Two licences. Which applies to what:

| | licence | file |
|---|---|---|
| everything under `src/` | **Apache-2.0** | `LICENSE-Apache-2.0` |
| everything under `PREREG/`, `RAPPORT/`, `docs/`, `data/`, `figs/`, this README | **CC BY 4.0** | `LICENSE-CC-BY-4.0` |

`src/register/lovkart.yaml` and the reports under `src/register/lovtidend/rapporter/` and
`src/register/vakt/rapporter/` fall under `src/` and are Apache-2.0. They carry Lovdata
document identifiers, titles and dates from the NLOD 2.0 archives; those are attributed to
Lovdata, not relicensed.

`LICENSE` is a copy of `LICENSE-Apache-2.0`, present so GitHub's detector reports the
repository as Apache-2.0. It does not override the table above: the non-code material is
CC BY 4.0.

`data/expected_facts.yaml` and the register YAML under `src/register/data/` quote short
passages from Norwegian public-sector web pages, each with its source URL and the date it
was verified. Those quotations are cited, not relicensed.

### Lovdata's terms, read directly

The four bulk archives fase 2b uses are **NLOD 2.0**, open, without an account. The
relevant clause was read directly from `lovdata.no/info/vilkar` on 2026-10-09 (sha256
recorded in `src/register/lovtidend/fetch.py`):

**§ 2.3 exempts «Regelverk i Norsk Lovtidend» from the use restrictions in § 2.1 and
§ 2.2, under NLOD 2.0, against attribution.** The prohibition on AI — «Det er ikke tillatt
å bruke innholdet til trening eller utvikling av KI-algoritmer» — sits in § 2.1/2.2 and
governs Lovdata's own web services, not the NLOD datasets that § 2.3 exempts. The same
clause forbids bulk downloading from the web pages and points onward: «For større
nedlastinger, bruk våre åpne API-er.» That is what `fetch.py` does, via
`api.lovdata.no/v1/publicData`.

Forseti does not train on the text in any case: 2b compares paragraph identifiers and
flags rows.

**This corrects ADR-0002.** The ADR left the terms as an open contradiction and recorded
that no terms page had been read, because `lovdata.no` and `api.lovdata.no` were blocked by
the session's egress policy (403 on CONNECT). They were reachable in the session that built
the chain, the clause was read, and the contradiction resolves in § 2.3. The ADR is
deposited unedited; this paragraph is the correction, and `fetch.py`'s docstring is the
primary record.

## How to reproduce

The probes need a GPU-free Apple-silicon or CPU setup and about 1 GB for the backbone.

```bash
python3.13 -m venv venv && . venv/bin/activate
export HF_HOME=$PWD/hf-cache          # keep the backbone off the system disk
pip install torch transformers scikit-learn scipy numpy matplotlib pyyaml
```

Models: `NbAiLab/nb-bert-base` via `transformers`, and `nb-llama-3.1-8b` via a local
`ollama` for fase 1 only. Fase 1 and 1b also need the `hei_refusal` pack, **which is not
included** — those two phases cannot be rerun end to end from this deposit. Fase 3 onward
can; what else is missing is listed after the commands.

```bash
# fase 3: build the pair and sentence data, encode, run leave-one-scenario-out
python -I src/p3/build_data.py && python -I src/p3/repr_sent.py && python -I src/p3/run_probe.py

# fase 3c: no training and no encoding — reuses fase 3's cached scores
python -I src/p3c/build_turns.py && python -I src/p3c/run_eval.py

# fase 0: convert the register and check the packs against it
python -I src/register/convert.py
python -I src/register/check_packs.py upstream/dev
python -I src/register/test_check_packs.py        # 32c494f must flag 130 030

# fase 2: the tail, calendar-gated
python -I src/register/hale/run.py --as-of 2026-06-01
python -I src/register/hale/test_backwards.py     # 130 160 -> 136 549, and nothing else
```

```bash
cd src/register

# fase 2b: resolve the register against the law map, and check the two agree
python -I resolve_lovkart.py --check              # exit 1 if register and map drift
python -I resolve_lovkart.py --markdown docs/forkortelser-lovdata.md

# fase 2b: fetch the archive, parse it, build the consequence map
python -I lovtidend/fetch.py
python -I lovtidend/parse.py --years 2025 2026
python -I lovtidend/impact.py
python -I lovtidend/test_backwards.py             # 5/5 expected hits

# vakt: one run at a fixed date, and the guard tests
python -I vakt/run.py --as-of 2026-10-09
python -I vakt/test_vakt.py                       # 20/20
```

Fase 3's run takes about 10 minutes per configuration; fase 3c's evaluation takes about
5 seconds. Paths in `src/` point at the working trees they were written in and will need
adjusting.

### What cannot be rerun from this deposit

Four inputs are referenced but not included, and the commands that need them fail rather
than silently produce something different:

| missing input | why | what fails |
|---|---|---|
| `hei_refusal` (47 prompts) | SimulaMet's, and sensitive | fase 1, fase 1b, `src/exclusion_check.py` |
| the SimpleAudit checkout | a separate repository | `check_packs.py`, `test_check_packs.py` |
| `src/register/hale/snapshots/` | size | `hale/test_backwards.py`; V3 and V4 of the vakt |
| the Lovdata archives (~97 MB) | size | `lovtidend/parse.py`, `impact.py`, `lovtidend/test_backwards.py` |

Only the first is withheld on rights grounds. The Lovdata archives are the one missing
input anybody can obtain: `lovtidend/fetch.py` downloads them from
`api.lovdata.no/v1/publicData` with no account, no key and no form, and checks each size
against the API's own listing. `convert.py` reads the source markdown register from a path
outside this repository; the YAML it produced is deposited in full under
`src/register/data/`.

Four commands run end to end from the deposit alone, and all four were run at deposit
time: `resolve_lovkart.py --check`, `resolve_lovkart.py --markdown`,
`vakt/run.py --as-of 2026-10-09` and `vakt/test_vakt.py`.

## Related work

- **SimpleAudit** — the evaluation framework the scenario packs live in:
  https://github.com/SimulaMet/SimpleAudit
- A `fact_check` judge implementing fase 3c's filters is **open as a pull request**:
  [SimulaMet/SimpleAudit#105](https://github.com/SimulaMet/SimpleAudit/pull/105),
  «Add a deterministic fact_check judge over metadata.facts», from
  `avalyset:feat/fact-judge` into `SimulaMet:dev`. **It is open, not merged** — checked
  against the PR page on 2026-10-09. v1.0.0 of this deposit said the branch «has not been
  pushed»; that was true when written and is now stale, which is why the status is dated
  here. The judge is not part of this deposit either way.
  It ships `default_enabled: False` (verified on the PR head): pair precision of about
  0,88 is under the 0,90 bar the phase set, and what changed is that the known
  false-accusation failure mode is closed and the model dependency is gone. See
  `docs/SIMPLEAUDIT.md`.
- Judge-stability study, source of the stored transcripts: OSF `vz8xj`.

## Deposit status

v1.1.0 was assembled, merged and read on 2026-10-09 in a cloud container that holds
neither the Zenodo token nor the withheld `hei_refusal` pack, and whose git credentials
accept branch pushes but refuse `refs/tags/*`. Three steps therefore remain, and all three
must run from the machine that holds what they need:

1. **The full exclusion scan** — `src/exclusion_check.py` against the withheld
   `scenarios.jsonl`, over the extracted tarball. It must print `CLEAN`.
2. **The tag** — `v1.1.0` was created in the container and could not be pushed: every
   push to a tag ref returns 403 here, lightweight and annotated alike, while branch pushes
   to the same repository succeed. The commit it points at is on `main`.
3. **The Zenodo deposit** — a new version under concept DOI
   [10.5281/zenodo.23260755](https://doi.org/10.5281/zenodo.23260755), same metadata,
   title unchanged, this README as the description. The version DOI it mints replaces the
   placeholder line at the top of this file.

Everything else is done and recorded: the merge, this README, `CITATION.cff`, and the
frys-reading in `FRYS-v1.1.md` with its log in `FRYS-v1.1.txt`.
`frys_read_v11.py` reruns the reading — it takes the withheld file's path as an argument,
and reports the exclusion scan as an open item rather than a passed check when that file is
absent. `frys_read.py` is kept untouched as the v1.0.0 artifact; it cannot read this README,
because its ground corpus does not know 2b or the vakt.
