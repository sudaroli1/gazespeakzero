# E3 design (fixed 23 Sep 2026, before any E3 output was seen)

**Question (claim C3):** the user selects 1–3 objects from the scene. Can a
small open language model turn that selection into the message the person
meant — well enough that the message is in the top 3 offered for confirmation?

E1b fixed the interface: three items in a row, a 0.5 s dwell, confirm/undo. So
E3 is judged the same way the interface works: **top-1** (the message is
offered first) and **top-3** (the message is on the first screen of candidate
messages, which the user confirms with one more dwell).

## Intent bank (`intent_bank.json`, 60 intents)

Built before any model was run, and not changed afterwards.

**Provenance.** Intents are not invented freely. Each one is assigned to one of
Light's (1988) four communication purposes, in the proportions caregivers
report for people with ALS (Fried-Oken et al., 2006: expressing wants and
needs most often, then social closeness, then information, then etiquette),
and the wants-and-needs intents follow the message content reported for
bedside and critical-care communication boards (Patak et al., 2006; Happ et
al., 2011: pain, thirst, position, suction, temperature, family, sleep).

| Purpose (Light 1988) | Intents | Share |
|---|---|---|
| Wants and needs | 33 | 55% |
| Information exchange | 10 | 17% |
| Social closeness | 10 | 17% |
| Social etiquette | 7 | 11% |

Each intent has:

- `id`, `room` (bedroom, living room, kitchen, bathroom, dining), `purpose`;
- `utterance`: the reference message in the first person;
- `paraphrases`: two alternative wordings, used for scoring only;
- `objects`: the 1–3 items the person would select (41 intents need one
  selection, 13 need two, 6 need three), **in order**, all of them
  names from the E2 AAC vocabulary (`aac_vocab.py`), so that E2's output and
  E3's input are the same vocabulary;
- `source`: the category the intent comes from.

**Built-in ambiguity.** 14 intents share their first object with at least one
other intent (water bottle → "I am thirsty" and "I need my pill"; blanket →
"I am cold" and "please straighten my bed"). The task is therefore not a
lookup: the model has to use the rest of the selection and the room.

## Conditions

The same 60 intents are run under four conditions, so the paper can say what
happens when the earlier stages are wrong:

| Condition | What the model sees | Why |
|---|---|---|
| `clean` | the correct objects | ceiling |
| `partial` | the first object only | the user stopped early or the item was not offered |
| `wrong_label` | one object replaced by a wrong item **drawn from E2's actual errors** for that room | E2 measured that 20–40% of first-screen items are not in the photo |
| `wrong_pick` | one object replaced by its neighbour in the row of three | E1b measured the per-selection error of the 1×3 layout (13.3% at the frame level) |

The substitutions are drawn with a fixed seed and are identical for every
model.

## Methods

Every method returns a ranked list of candidate messages.

| Code | What it is | Why |
|---|---|---|
| `template` | "I want <objects>" | what a system with no language model can already say |
| `prior` | the most frequent intent containing the first object (leave-one-out over the bank) | a no-vision, no-LM frequency baseline |
| `embed` | sentence-transformers all-MiniLM-L6-v2: ranks the 60 intents by similarity to the object list | **the baseline that matters**: retrieval with no generative LM |
| `lm_rank_*` | a small open LM scores each of the 60 candidate messages by average token log-likelihood given the objects and the room | closed set, the way a real device would offer known messages |
| `lm_gen_*` | the same LM writes the message; it is mapped back to the nearest intent by embedding for automatic scoring, and rated by a human on a subset | open set, what the original paper claimed |

Models (all open, non-gated, fp16 on a T4): **Qwen2.5-1.5B-Instruct**,
**Qwen2.5-3B-Instruct**, **SmolLM2-1.7B-Instruct**, **Phi-3.5-mini-instruct
(3.8B)**. The original paper's model (a 1–3B open LM with a hand-written
prompt) is represented by `lm_gen_qwen2.5-1.5b`.

## Metrics

- **top-1** and **top-3** intent accuracy, per condition;
- accuracy per purpose (wants and needs vs the rest);
- for `lm_gen_*`: nearest-intent top-1, plus a blinded human rating of
  "does this message convey the intent?" on 60 generations;
- 95% bootstrap CIs over intents, and paired differences on the same intents;
- seconds per intent (E5 feeds on this).

## What would refute C3

If no LM beats `embed` on top-3 in the `clean` condition, the language-model
stage adds nothing over plain retrieval, and the paper says so: the
contribution would then be the vision stage plus retrieval, and the LM is
dropped. `template` and `prior` are floors; an LM that cannot beat `embed` is
not worth 2 GB of weights on a bedside device.

## Known limits

- The bank is ours, built from published categories rather than recorded
  patient messages, because no public corpus of AAC messages with the objects
  in view exists. The audit of Phase 2 will collect real messages.
- 60 intents is a small closed set. `lm_rank_*` scores against exactly those
  60, which flatters closed-set ranking; `lm_gen_*` is the open-set check.
- One rater for the human check, as in E2.
