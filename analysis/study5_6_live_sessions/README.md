# Studies 5 and 6 — the system in use (Sec. 4.5 and 4.6)

Study 5 is one person, the first author, using the system across eleven sessions. Study 6 is
two other people installing the same software on machines we have never seen and running a
session each.

Between them they are where the paper's claim is tested and where four of its findings
contradict the earlier studies. Read `PROTOCOL.md` before anything else in this folder: it is
the pre-registered plan, written before any session, and it is what makes the departures from
it visible.

## The files

| File | What it is |
|---|---|
| `PROTOCOL.md` | the study plan, fixed before data collection: design, hypotheses, thresholds |
| `information_sheet.md`, `consent_form.md` | what operators were told and what they signed |
| `SECOND_OPERATOR.md` | the instructions the two Study 6 operators worked from |
| `analyse_study.py` | the pre-registered analysis, written before the data existed |
| `verify_study5_numbers.py` | recomputes every number in Sec. 4.5 from the logs; non-zero exit on disagreement |
| `verify_paper_numbers.py` | the same for Sec. 4.6 and its table |
| `make_fig_deploy.py` | draws `figures/fig_deployment.pdf` |

## Reproducing Study 5

```
python verify_study5_numbers.py        # 40 checks against the published numbers
python analyse_study.py --out results  # the pre-registered analysis, all sessions pooled
```

**Start with the verifier, not the analysis.** Section 4.5 reports several sessions
separately, because pooling them would be wrong: they differ in the number of zones, and in
whether the capture fault was still present. `analyse_study.py` pools everything in the
folder, which answers a different question from the one the paper's tables answer. The
verifier names the session and the rule behind each published figure and recomputes it.

The mapping, for anyone who wants to work through it by hand
(`--include` takes a substring of a file name):

| Published result | Session | Rule |
|---|---|---|
| Three-zone accuracy, 0.443 free / 0.524 calibrated | `PILOT_study_20260924-165155` | every selection, no exclusion |
| The per-zone breakdown (0.083 / 0.974 / 0.231 free) | the same session | by the zone the cued word was in |
| The capture fault: the centre zone in 35 of 37 selections | `P00_study_20260924-150417` | before the capture fix |
| Two-zone accuracy, 0.868 free / 0.805 calibrated | `PILOT3` | selections made while the cued word was on screen |
| The guard table, and its s/trial ranges | `PILOT3` | per block; the range is min to max over blocks |
| The paging pathology: 92 page changes in 48 trials | `PILOT3` | the direct condition alone |

```
python analyse_study.py --include PILOT3 --out results_two_zone
```

Two things `analyse_study.py` does that are worth knowing before reading its output:

- **It reports the unreachable-cue exclusion before applying it**, with per-participant
  counts: 43 of 627 trials had the cued word off screen when the trial began, because of our
  own fault (the cue was chosen before the interface reset its page). Those trials could not
  be completed by any gaze behaviour. The exclusion was not pre-registered and the paper says
  so.
- **It keeps the sessions where the judgement cannot be made.** Two early logs predate the
  `cue_zone` column, so for them reachability is unknown. Unknown is not the same as
  unreachable, and treating a missing column as evidence would have discarded two whole
  sessions and inflated the exclusion from 43 trials to 143. That distinction is printed, not
  assumed.

`python analyse_study.py --demo` runs the whole analysis on synthetic logs with a known
answer, which is how it was checked before any session was recorded.

## Reproducing Study 6

The two operator logs are **not in this repository** yet; the top-level README explains why.
When they are added as `data/sessions/study6_deployment/`, one command checks all 25 published
numbers:

```
python verify_paper_numbers.py --sessions ../../data/sessions/study6_deployment
```

What Study 6 establishes does not depend on its accuracy figures, and is the reason it is in
the paper: **the same code on a machine we do not own cost about 20 points of per-trial
accuracy**, because one operator's machine ran the pipeline at 88.9 ms per frame against the
other's 14.7, which is 5.6 gaze readings per 500 ms dwell against 15.1. A decision resting on
five readings is a different system from one resting on fifteen, and nothing in Studies 1 to 4
would have revealed it. `make_fig_deploy.py` draws that comparison.

## The operators, and what was and was not obtained

Both operators gave **written informed consent** for their session data to be published.
Their logs are pseudonymised: they appear as P1 and P2, as in the paper, and no name, machine
identifier or email address appears in any file. No image or video of either person exists —
the session software has no image-writing path at all.

**Institutional ethics review was not sought.** The co-authors reviewed and approved the
consent materials, which is a different thing, and the paper's ethics statement says exactly
that rather than implying an approval that was not obtained.

One artefact of how the sessions were run is worth stating so it does not read as an error:
both operators left the software's default participant and site tags (`T01`, `PILOT`) in the
session metadata. The file names carry the pseudonyms; the recorded fields are left exactly as
logged rather than rewritten after the fact.
