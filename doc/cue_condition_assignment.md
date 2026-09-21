# How each trial gets its cue condition

**Code:** `_make_block` + `_ongoing_reps_for_cue` in `exp/testmain_demo_v3.py`  
(≈ L1727–1839; cue list ≈ L1616–1614)

**Question this note answers:**  
Which trial is assigned to which cue condition — `(1)`, `(2)`, `(3)`, `(1,2)`, `(1,3)`, `(2,3)`? Is that a random draw per trial?

**Short answer:** **No.** Cue condition is assigned by a **fixed quota per block**, then the block is **shuffled**. The condition is written onto each trial stub **before** the experiment runs (same time as the color/digit pool draw). During the trial loop, the cue condition is already frozen on the trial dict.

Related: color/digit layouts are a separate random draw — see [color_and_reward_position_pool.md](color_and_reward_position_pool.md).

---

## What a “cue condition” is

| Label | Meaning on the screen |
|---|---|
| `(1)` | only digit **1** appears (on one disk) |
| `(2)` | only digit **2** |
| `(3)` | only digit **3** |
| `(1,2)` | digits **1** and **2** (on two disks) |
| `(1,3)` | digits **1** and **3** |
| `(2,3)` | digits **2** and **3** |

Full list in code: `CUE_CONDITIONS` (L1616–1623).

Which subset is used depends on session (`get_session_generation_config`, L1587–1614):

| Session | Cue conditions used | Count |
|---|---|---|
| 1 | single only `(1),(2),(3)` + center layout | 3 |
| 2 | single only `(1),(2),(3)` + triangle | 3 |
| 3–4 | dual only `(1,2),(1,3),(2,3)` | 3 |
| 5+ | all six | 6 |

Below, examples use the main case: **6 cues, 42 trials/block** (sessions 6+).

---

## Timing: when is cue condition decided?

```text
SESSION START (after dialog)
  │
  ├─ for each block:
  │      for each cue condition C in order:
  │          create N_C trial stubs already labeled cue_condition = C
  │          (each stub also draws colors/digits from C’s pool)
  │      shuffle the block                         ← only randomizes ORDER
  │
  └─ THEN run: for trial in trials:
         use trial["cue_condition"] as already stored
```

So:

| Decision | Random? | When |
|---|---|---|
| How many trials of each cue condition | **No** (formula) | while building the block |
| Which stub is labeled `(2)` vs `(1,3)` | **No** (assigned in the cue loop) | while building the block |
| Order of those stubs in the block | **Yes** (`shuffle`) | while building the block |
| Colors / which disk shows the digit | **Yes** (`choice` from pool) | while building the block |
| Anything about cue condition during display | **No** | already fixed |

---

## The assignment rule: quota, not sampling

The code does **not** do:

```text
❌  for each trial slot:
        cue = random.choice(six_conditions)
```

It does:

```text
✅  for each cue condition C:
        create exactly n_C trials of type C
    then shuffle the list
```

That is why counts stay balanced even though the participant sees a mixed sequence.

### Pseudocode (`_make_block`)

```text
block_trials = []

FOR cue_index, cue IN cue_conditions:          # e.g. 0..(1), 1..(2), ...
    pool = pool_for_this_cue                   # 18 or 72 color/digit layouts

    n_pm      = k if PM phase else 0           # k = PM_TRIALS_PER_CUE_PER_BLOCK
    n_ongoing = _ongoing_reps_for_cue(...)     # see next section

    REPEAT n_pm times:
        stub = { is_pm_trial=True, ... }
        apply random variant from pool         # sets cue_condition label + colors
        append stub

    REPEAT n_ongoing times:
        stub = { is_pm_trial=False, ... }
        apply random variant from pool
        append stub

shuffle(block_trials)
```

The cue condition label is set inside `_apply_variant_to_stub` from the variant’s `cue_condition` field (which came from that cue’s pool). Every stub created in the `(2)` iteration gets label `"(2)"`.

---

## How many trials per cue? (`_ongoing_reps_for_cue`)

### Formula

```text
IF PM phase (focal_pm / nonfocal_pm):
    ongoing_total = trials_per_block - n_cues * k
ELSE:
    ongoing_total = trials_per_block

base      = ongoing_total // n_cues
remainder = ongoing_total %  n_cues

n_ongoing(cue_index) = base + 1   if cue_index < remainder
                     = base       otherwise
```

`cue_index` is the position in the cue list (0 = first cue `(1)`, 1 = `(2)`, …).  
The first `remainder` cues get one extra ongoing trial so the block length stays exact.

For PM phases, each cue also gets exactly **`k` PM trials** on top of its ongoing count  
(`k = PM_TRIALS_PER_CUE_PER_BLOCK`, usually 1).

### Worked example A — baseline (no PM), 42 trials, 6 cues

```text
ongoing_total = 42
base = 42 // 6 = 7
remainder = 42 % 6 = 0

cue_index 0  (1)    → 7 ongoing
cue_index 1  (2)    → 7 ongoing
cue_index 2  (3)    → 7 ongoing
cue_index 3  (1,2)  → 7 ongoing
cue_index 4  (1,3)  → 7 ongoing
cue_index 5  (2,3)  → 7 ongoing
                 sum = 42
```

### Worked example B — PM phase, k=1, 42 trials, 6 cues

```text
PM total      = 6 * 1 = 6
ongoing_total = 42 - 6 = 36
base = 36 // 6 = 6
remainder = 36 % 6 = 0

                PM   ongoing   total for that cue
(1)    idx 0     1      6           7
(2)    idx 1     1      6           7
(3)    idx 2     1      6           7
(1,2)  idx 3     1      6           7
(1,3)  idx 4     1      6           7
(2,3)  idx 5     1      6           7
                         sum = 6 + 36 = 42
```

So **before shuffle**, the list looks conceptually like:

```text
[ seven "(1)" stubs (1 PM + 6 ongoing),
  seven "(2)" stubs,
  seven "(3)" stubs,
  seven "(1,2)" stubs,
  seven "(1,3)" stubs,
  seven "(2,3)" stubs ]
```

### After shuffle

```text
rng.shuffle(block_trials)
```

Now the participant might see:

```text
(2), (1,3), (1), (2,3), (1), (1,2), (3), ...
```

The **sequence** is random; the **counts** are not. There is no rule like “no two identical cues in a row.”

---

## One trial’s identity after assignment

After `_apply_variant_to_stub`, a stub has at least:

```text
cue_condition   = "(2)"              # which cue condition (THIS note)
reward_values   = [0, 2, 0]          # digits (from pool draw)
trial_colors    = ["green","red","blue"]
is_pm_trial     = False or True
pm_position     = None or "top"/...  # only if PM
```

Cue condition and color/digit layout are related but decided differently:

```text
cue condition  → fixed quota in the cue loop
layout         → random.choice(that cue’s pool)   # with replacement
```

You never get a trial labeled `(2)` whose `reward_values` contain a `1` and a `3` — the pool for `(2)` only contains single-digit-2 layouts.

---

## Mental contrast with the color/digit pool

| | Cue condition | Color + digit layout |
|---|---|---|
| Goal | balance how often each condition appears | vary how it looks |
| Method | exact counts per cue | list all layouts, then `choice` |
| Replacement? | N/A (counts fixed) | yes (same layout can repeat) |
| Order | shuffled after quotas filled | N/A (bound to that stub) |

```text
❌  randomly pick a cue condition for trial #17
✅  create the required number of each cue, then randomly order them
```

---

## Sessions with fewer than 6 cues

Same quota logic; only `n_cue_conditions` and the cue list change.

Example: session 2, 20 trials/block, 3 single cues, no PM:

```text
base = 20 // 3 = 6
remainder = 20 % 3 = 2

(1) → 7
(2) → 7
(3) → 6
sum = 20
```

---

## Burn-in block (brief)

`_make_burnin_block` (L1853–1915) uses the same idea: spread ongoing (and scaled PM) across the session’s cue list, then shuffle. Counts differ because the block is only 20 trials, but assignment is still **quota → shuffle**, not per-trial cue sampling.

---

## Jump links in the experiment code

| Step | Lines |
|---|---|
| Cue condition definitions | `CUE_CONDITIONS` L1616–1623 |
| Which cues this session uses | `get_session_generation_config` L1587–1614 |
| How many ongoing trials per cue | `_ongoing_reps_for_cue` L1727–1745 |
| Create stubs labeled by cue, then shuffle | `_make_block` L1774–1839 |
| Build all blocks for the session | `build_session_trials` L1918–1998 |
| Play frozen list | `for trial in trials` L3869+ |

---

## One-sentence summary

**Each block forces exact equal counts of each cue condition (7 total per cue in baseline; 1 PM + 6 ongoing per cue in PM phases); shuffle only mixes their order; that labeling is finished before the first trial is shown.**
