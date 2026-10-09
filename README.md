# Forseti probes 2026: six preregistered experiments on Norwegian public-service fact checking

Eirik Botten Nicolaysen · [ORCID 0009-0001-9188-6788](https://orcid.org/0009-0001-9188-6788) · EcoDeco AS
2026-10-09

**Concept DOI** (always the latest version): [10.5281/zenodo.23260755](https://doi.org/10.5281/zenodo.23260755)
**This version (v1.0.0)**: [10.5281/zenodo.23260756](https://doi.org/10.5281/zenodo.23260756)

Cite the concept DOI unless you need to pin this exact version.

---

## What was tested

Whether a language model's handling of Norwegian public-service facts can be checked
mechanically — first by probing frozen representations, then by giving up on that and
writing the check as code.

Seven pieces of work are deposited. Five are preregistered experiments with a hypothesis,
a criterion fixed before running, and a verdict. Two are engineering tasks with no
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

Each preregistration was committed as its own commit **before** the run it governs. The
SHA is in the filename under `PREREG/`, and the matching report is in `RAPPORT/`.

**Fase 0 and fase 2 have no `PREREG.md` and no `RAPPORT.md`, and none has been written
after the fact.** They were engineering tasks — convert a register, build a change
detector — not hypothesis tests. Their design documents are
`docs/ADR-0001-yaml-i-git.md` and `src/register/hale/README.md`, written while the work
was done. The six-document symmetry of the other phases does not exist for these two, and
inventing it would misrepresent what happened.

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
- **No claim that the register is complete.** Of 118 converted rows, 43 carry an
  extractable value and 75 do not; 117 lack a source quote, 46 lack a review date, 30 lack
  a legal basis. Each is flagged rather than guessed.

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

`data/expected_facts.yaml` and the register YAML under `src/register/data/` quote short
passages from Norwegian public-sector web pages, each with its source URL and the date it
was verified. Those quotations are cited, not relicensed.

## How to reproduce

The probes need a GPU-free Apple-silicon or CPU setup and about 1 GB for the backbone.

```bash
python3.13 -m venv venv && . venv/bin/activate
export HF_HOME=$PWD/hf-cache          # keep the backbone off the system disk
pip install torch transformers scikit-learn scipy numpy matplotlib pyyaml
```

Models: `NbAiLab/nb-bert-base` via `transformers`, and `nb-llama-3.1-8b` via a local
`ollama` for fase 1 only. Fase 1 and 1b also need the `hei_refusal` pack, **which is not
included** — those two phases cannot be rerun end to end from this deposit. Everything
from fase 3 onward can.

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

Fase 3's run takes about 10 minutes per configuration; fase 3c's evaluation takes about
5 seconds. Paths in `src/` point at the working trees they were written in and will need
adjusting.

## Related work

- **SimpleAudit** — the evaluation framework the scenario packs live in:
  https://github.com/SimulaMet/SimpleAudit
- A `fact_check` judge implementing fase 3c's filters exists on the branch
  `feat/fact-judge`. **That branch has not been pushed** and is not part of this deposit.
  It ships `default_enabled: False`: pair precision of about 0,88 is under the 0,90 bar
  the phase set, and what changed is that the known false-accusation failure mode is
  closed and the model dependency is gone. See `docs/SIMPLEAUDIT.md`.
- Judge-stability study, source of the stored transcripts: OSF `vz8xj`.
