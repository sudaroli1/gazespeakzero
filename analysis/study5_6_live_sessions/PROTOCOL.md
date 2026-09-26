# Phase 1b study protocol — live selection with webcam gaze (revision 3)

**Status:** pre-registration draft. Revision 3, 25 September 2026, **before any participant is
run**. Register this (OSF or AsPredicted) and do not change it afterwards; anything added later
is reported as exploratory.

Revisions 1 and 2 specified a three-zone layout with direct and scanning patterns. Seven
single-operator pilot runs (`gazespeakzero-pilot-log.md`, `-pilot-result.md`) established that
the three-zone layout does not reach usable accuracy live and that the direct layout is
pathological at two zones. The design below is what the pilots support. No participant data
existed at any point in this process.

## Why this study exists

Every number in our end-to-end model (E4) rests on one substitution: **per-frame
zone-classification accuracy** on public datasets used as if it were **per-selection accuracy
in a live dwell interface**. The pilots show the substitution is wrong, and wrong in a
structured way. This study measures the live quantity with enough people to state it, and
tests what survives of the simulation.

## What the pilots established (one operator, 7 runs, ~500 selections)

1. **Three zones is not usable.** Per-selection accuracy 0.44 calibration-free / 0.52
   calibrated, against E1b's 0.838 per frame. Uncalibrated, the predictor is close to a
   constant that answers "centre".
2. **Two zones is.** With the cued word on screen: **0.868 calibration-free, 0.805 calibrated**.
3. **A "next" key at two zones destroys the task** — it occupies half the screen, and 92 page
   changes across 48 trials took the target off screen. The direct pattern is dropped.
4. **The repeat guard makes things worse**, in every pilot cell: wrong-item rate 0.08–0.25
   without it, 0.25–0.58 with it, at roughly four times the trial duration. E4 predicted the
   reverse because it modelled repeated looks as independent draws. Live errors are temporally
   correlated, so a second look largely re-confirms the first.
5. **Capture resolution is a controlled variable.** At 640×480 the iris signal-to-noise is 0.50
   and the whole pipeline sits at chance; at 1280×720 it is 7–8. Sessions run at 1280×720 or
   better, and the granted resolution and mean eye width in pixels are recorded per participant.
6. **A correction cannot be reused across sessions.** The raw model output occupied ranges from
   0.06–0.81 to 0.37–0.78 across seven runs by one person on one laptop. Calibration is
   per session or not at all.

## Sites (revision 4, 25 September 2026)

The study runs at **four institutions**, three participants each:

| Site | Institution | Site investigator |
|---|---|---|
| S1 | St. Joseph's College of Engineering, Chennai | Alexander R. |
| S2 | SRM Institute of Science and Technology, Ramapuram, Chennai | G. Sumathi |
| S3 | Chennai Institute of Technology, Chennai | M. Sindhu |
| S4 | Panimalar Engineering College, Chennai | Vanidha Sri R. |

**Ethics.** Each site obtains approval from its own institutional committee, or documents in
writing that its committee accepts the lead site's approval. **No site runs a session before
its own approval is in hand**, and the approval reference for each site is recorded in the
paper. Sites do not share participant-level data beyond the anonymised session logs.

**Why multi-site.** Four sites mean four rooms, four lighting conditions and four laptops.
Pilot work established that capture configuration alone can move this pipeline between chance
and working, so cross-site variation is a genuine test rather than noise --- *provided the
varying quantities are recorded*. They are treated as covariates, not ignored.

**What must be identical across sites**, and is checked before a site runs its first
participant:

1. the same code revision (git commit hash recorded in every session log);
2. the same model file (`gaze_model.joblib`, checksum recorded);
3. capture at **1280x720 or better** --- a site whose webcam cannot deliver it is reported
   separately and not pooled;
4. the same session script, the same cue set, the same block structure and the same
   instructions, read verbatim;
5. a calibration whose held-out accuracy is recorded before the blocks, at every session.

**What is recorded per participant, and reported:** site, laptop model, webcam, the resolution
actually granted, mean eye width in pixels, the held-out calibration accuracy, room lighting
(window in front / behind / neither, artificial only), and whether spectacles were worn.

**Analysis consequence.** Site is a random effect alongside participant wherever the model
allows it, and every headline figure is reported per site as well as pooled. With three
participants per site the study is **not powered to test for site differences**; reporting them
is descriptive, and any apparent site effect is a hypothesis for later work, not a finding.

## Participants

- **N = 12** adults (18+), three per site, no known uncorrected vision problems, able to sit at
  a laptop.
- **Not** people with motor impairment. This study is about the *sensor and interface*, and is
  framed that way throughout. Testing with AAC users is a separate application with a clinical
  partner.
- Recruitment: convenience sample from the institution; no payment, or a token equivalent to
  local norms.
- **Justification for 12:** 12 × 60 trials ≈ 720 selections; at an expected per-selection
  accuracy near 0.85 that is a 95% CI of about ±0.026 pooled. Each within-participant cell has
  15 trials, sufficient for the mixed-effects model below.

## Design

**Two zones, scanning layout** (two words side by side, auto-advancing every 3 s). Within
participants, **2 (guard: none / repeat) × 2 (calibration: none / 30 s per-session) = 4 blocks
× 15 trials = 60 trials**, about 25 minutes.

Block order: the two calibration halves are kept together, shuffled within each half, and which
half runs first is set by the participant seed — so practice and fatigue are counterbalanced
against the calibration factor.

Three zones and the direct pattern are **not** run. They are reported from the pilot, with the
reasons above.

**Cue presentation.** The target word is shown alone in the centre of a blank screen for 1.6 s;
the zones appear after it clears. Nothing is measured while the cue is on screen.

**Reading window.** Once the zones appear, selection is disarmed for 800 ms while the screen
shows "read the words". Gaze is measured and logged throughout but cannot select. Without it
the dwell fires mid-sweep, which lands in whichever zone the eyes happen to cross.

**Side balance.** Cues are drawn from the words on screen when the trial begins, and the layout
alternates sides per trial. Pilot runs where one side carried most of the cues produced pooled
accuracies of 0.81–1.00 from a predictor that was simply biased toward that side. **Every
accuracy in this study is reported per side as well as pooled**, and a pooled figure from an
unbalanced cue distribution is treated as uninterpretable.

**Calibration.** One 30-second procedure: a dot at five positions, twice. The first pass fits
the correction (a straight line and a monotone fit are both fitted; whichever scores higher on
the held-out pass is kept), the second pass is held out and reports its accuracy. Fitted
prediction-on-target and inverted — the reverse regression is attenuated by noise in the
prediction and yields a correction that does nothing.

## Measures (all from the session log)

- **per-selection accuracy**, primary, **conditioned on the cued word being on screen at that
  moment**, reported per side and pooled, per arm. The unconditioned figure is reported beside
  it; the two differ when a selection takes the target off screen.
- **wrong-item rate** per trial, and **time per trial** with the 800 ms reading window removed
  (E4 models selection time only);
- **held-out calibration accuracy** (2-zone), per participant;
- **capture resolution and mean eye width in pixels**, per participant;
- abandonment (trials skipped after 60 s); per-frame processing time (also E5).

## Hypotheses, stated in advance

| # | Hypothesis | Test | What refutes it |
|---|---|---|---|
| H1a | Live **calibration-free** per-selection accuracy at two zones is **at least 0.75** | pooled selections, participant-clustered bootstrap CI | the CI's lower bound falls below 0.75 |
| H1b | Live **calibrated** per-selection accuracy at two zones is **at least 0.75** | same | the CI's lower bound falls below 0.75 |
| H2 | **The repeat guard does not reduce the wrong-item rate, and may increase it.** This reverses the pre-registered direction of revisions 1–2 and contradicts E4; the pilot and the reason (correlated errors) are stated above | mixed-effects logistic regression, participant random intercept | a CI for the guard term that is wholly below zero, i.e. the guard does reduce errors |
| H3 | The E4 simulator, run at the accuracy measured in each arm, predicts each condition's wrong-item rate **within ±0.10** | prediction vs observation, per condition | any condition outside ±0.10 |
| H4 | Calibration raises per-selection accuracy | paired difference over participants, bootstrap CI | the CI includes 0 |
| H5 | Accuracy does **not** differ between the two sides | paired difference per participant | a CI excluding 0 — which would mean the predictor is side-biased and the pooled figure is not interpretable |

H3 is the one that matters for the paper. The pilot already predicts it fails for the guarded
conditions; if it does, the simulation section is rewritten as a bound with its independence
assumption named as the reason, and the failure is reported as a finding about simulating
dwell interfaces, not hidden.

## Analysis plan

- Exactly as above; `study/analyse_study.py` implements it and was written before collection.
- Participants are the unit of clustering everywhere; site is reported alongside and, where
  the model supports it, included as a second grouping factor.
- Bootstrap intervals resample participants within site.
- Trials where the face was not found for more than half the trial are reported separately and
  excluded from the accuracy estimate (pre-specified).
- No optional stopping: all 12 participants are run before the analysis is looked at.
- Anything not listed here is exploratory and labelled as such.

## Data protection and ethics

- **No video, no images, and no audio are stored at any point.** Frames are processed in
  memory; only landmark-derived numbers, decisions and timings reach the disk.
- The session log contains no identifiers beyond a participant code (P01…P12). The code-name
  link, if kept at all, is held separately by the local investigator.
- Participants may stop at any time without giving a reason, and may ask for their session
  file to be deleted up to the point of analysis.
- Risks: eye strain and fatigue from sustained screen use. Mitigation: breaks between blocks,
  a 25-minute cap, and an explicit instruction that stopping is fine.
- This study needs approval from the co-author's institutional ethics committee. The
  corresponding author has no institutional affiliation and cannot apply; that is why the
  study is run through the co-author's institution, which must be settled before recruitment.
- The public datasets used in Phase 1 (MPIIFaceGaze, EOTT, LVIS/COCO) carry their own
  licences and required no approval; this study is the first with human participants.

## Materials checklist

- `prototype/gaze_ui.py`, `prototype/engine.py`, `prototype/gaze_model.joblib`,
  `face_landmarker.task`
- `study/information_sheet.md` and `study/consent_form.md` (**to write with the co-author**,
  in the institution's template)
- `study/analyse_study.py`, plus the E4 simulator for the H4 comparison
- Exit questionnaire: which block felt most accurate, which felt fastest, free comments

## What this study does not do

It does not show the system works for people with motor impairment, and the paper must not
imply that. It measures whether calibration-free webcam gaze can drive this interface at all,
and whether our model of it is trustworthy. The clinical study is a separate protocol with a
clinical partner, a different consent process, and a different set of outcome measures.
