# PMCP (prospective memory + CCP) — trial number design

Source: `testmain_demo_v3.py` / `testmain_demo.py` (`PRACTICE_SESSION_TRIAL_CONFIG`, `N_BLOCKS`, `TRIALS_PER_BLOCK`, `build_session_trials`).

Participants complete **26 sessions**: **5 practice + 7 baseline + 7 PM phase A + 7 PM phase B**.

PM phase order is counterbalanced by participant ID (odd → focal then nonfocal; even → nonfocal then focal).

Practice sessions **1–5** use the same **blocks × trials/block** structure as CCRP (`multiplecue-responsebox/exp/trial_number_design.md`). Sessions **6+** use the full experimental layout (9 × 42).

## Session phases

| Sessions | Phase | `session_phase` label |
|---------:|-------|----------------------|
| 1–5 | Practice | `practice` |
| 6–12 | Baseline (ongoing task only) | `baseline` |
| 13–19 | PM phase A | `focal_pm` or `nonfocal_pm` |
| 20–26 | PM phase B | `nonfocal_pm` or `focal_pm` |

## Per-session trial counts

### Practice (sessions 1–5) — CCRP-matched block structure

| Session | Cue conditions | Layout | Blocks | Trials/block | **Total** | CCRP total (with warm-up) |
|--------:|----------------|--------|-------:|-------------:|----------:|--------------------------:|
| 1 | 3 single | Center only | 10 | 20 | **200** | 222 |
| 2 | 3 single | Triangle | 10 | 20 | **200** | 222 |
| 3 | 3 dual | Triangle | 4 | 50 | **200** | 210 |
| 4 | 3 dual | Triangle | 4 | 30 | **120** | 130 |
| 5 | 6 single+dual | Triangle | 4 | 50 | **200** | 210 |

PMCP practice totals are **slightly lower than CCRP** because PMCP has **no warm-up trials** (CCRP adds 4 + 2×(n_blocks−1) warm-up trials per session). Block counts and main trials per block match CCRP.

### Experimental (sessions 6–26)

**9 blocks × 42 trials/block = 378 trials** per standard session.

Block length **42** is chosen so cue counts divide evenly (6 cue conditions):

- Baseline: exactly **7** ongoing trials per cue
- PM (k=1): exactly **1 PM + 6 ongoing** per cue (PM rate 6/42 ≈ 14.3%)

| Session(s) | Cue conditions | Layout | **Standard total** | Notes |
|------------|----------------|--------|-------------------:|-------|
| 6–12 | 6 single+dual | Triangle | **378** | Baseline |
| 13–19 | 6 single+dual | Triangle | **378** (+ add-ons below) | PM phase A |
| 20–26 | 6 single+dual | Triangle | **378** (+ add-ons below) | PM phase B |

### Add-ons (sessions 6+ only)

| Condition | Extra trials | Sessions affected |
|-----------|-------------:|-------------------|
| Burn-in block (block 0) | **+20** | Session ≥ 6, first session of day, participation day > 1 |
| PM practice block (block −1) | **+42** | **13** and **20** only (first session of each PM phase) |

| Session type | Total trials |
|--------------|-------------:|
| Standard experimental | **378** |
| + burn-in only | **398** |
| + PM practice only (ses 13 or 20) | **420** |
| + burn-in + PM practice (ses 13 or 20) | **440** |

Warm-up trials: **0** (unlike CCRP).

### Trials per block — experimental (42)

**Baseline blocks** — cue-balanced ongoing trials only:

| Sessions | Cue conditions | Reps per cue per block |
|----------|---------------:|------------------------|
| 6–26 | 6 | **7** (42 = 7×6) |

**PM phase blocks** (sessions 13–19 and 20–26) — per block:

| Trial type | Count per block |
|------------|----------------:|
| PM trials (1 per cue condition) | **6** |
| Ongoing trials (6 per cue) | **36** |
| **Total** | **42** |

Per PM session: 9 × 6 = **54 PM trials**.  
Per PM phase (7 sessions): 7 × 54 = **378 PM trials** (plus 42 on the phase-intro practice block at session 13 or 20).

## Grand totals (26 sessions)

| Component | Sessions | Trials each | Subtotal |
|-----------|----------|------------:|---------:|
| Practice | 5 | 200 / 200 / 200 / 120 / 200 | **920** |
| Baseline | 7 | 378 | 2,646 |
| PM phase A | 7 | 378 (+42 on ses 13) | 2,688 |
| PM phase B | 7 | 378 (+42 on ses 20) | 2,688 |
| **Standard total** | **26** | | **8,942** |

Optional burn-in (not in base total): up to **+20** per eligible session.

## Comparison to CCRP practice totals

| | CCRP (ses 1–5) | PMCP (ses 1–5) |
|---|---------------:|---------------:|
| Block structure | 10×20, 10×20, 4×50, 4×30, 4×50 | Same |
| Warm-up trials | Yes | No |
| **Total trials** | **994** | **920** |

## Estimated session duration

No PM lab timing data yet. Estimates extrapolate from CCRP response-box data (`session_times_minutes.csv`) and adjust for PM timing parameters in `testmain_demo.py`.

### Timing comparison (per trial)

| Event | CCRP (`testmain.py`) | PM (`testmain_demo.py`) |
|-------|---------------------|-------------------------|
| Pre-stimulus wait | Jitter ~1.5 s (mean) | Fixation **0.5 s** (fixed) |
| Stimulus → response | Until keypress | Until keypress |
| Response deadline | 2.0 s | 3.0 s |
| Feedback | 1.5 s | 1.5 s |
| Post-trial ITI | — | **0.3 s** |

### Estimated minutes per session

| Session type | Trials | Block gaps | **Est. duration** |
|--------------|-------:|-----------:|------------------:|
| Practice 1–2 | 200 | 9 | **~12 min** |
| Practice 3, 5 | 200 | 3 | **~12 min** |
| Practice 4 | 120 | 3 | **~8 min** |
| Baseline 6–12 | 378 | 8 | **~23 min** |
| PM 14–19, 21–26 | 378 | 8 | **~23 min** |
| PM transition **13** or **20** (+ practice block) | 420 | 9 | **~26 min** |
| Any session + burn-in | +20 | — | **+1 min** |
| Session 13/20 + burn-in + practice | 440 | 9 | **~27 min** |

### Estimated total time (26 sessions)

| Scope | Sessions | Estimate |
|-------|----------|----------|
| Practice (1–5) | 5 | ~56 min (~0.9 h) |
| Baseline (6–12) | 7 | ~161 min (~2.7 h) |
| PM phase A (13–19) | 7 | ~164 min (~2.7 h) |
| PM phase B (20–26) | 7 | ~164 min (~2.7 h) |
| **All 26 sessions** | **26** | **~545 min (~9.1 h)** |

*Assumes typical break behavior similar to CCRP, no burn-in, and average response times. Actual duration will vary with self-paced breaks.*

### Comparison to CCRP (17 sessions)

| Experiment | Sessions | Total trials | Est. total time |
|--------------|----------|-------------:|----------------:|
| CCRP (response-box) | 17 | 6,010 | ~7.2 h (empirical) |
| PMCP | 26 | 8,942 | ~9.1 h (estimated) |
