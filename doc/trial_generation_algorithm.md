# Trial design & randomization — how `testmain_demo_v3.py` builds a session

**File:** `exp/testmain_demo_v3.py`

**Key idea:** All trials for a session are **fully pre-built before the trial loop**. The loop only plays that list; it does not re-randomize (see file header ~L7–8, and `for trial in trials:` ~L3869).

This note is a **pseudocode walkthrough** of condition management, counts, and randomization, with line pointers so you can jump into the code.

---

## Quick numbers (main experiment, sessions 6+)

| Quantity | Value | Where |
|---|---|---|
| Total sessions | 26 = 5 practice + 7 baseline + 7 focal PM + 7 nonfocal PM | L156–159, L228–230 |
| Main blocks / session | 9 | `N_BLOCKS` L161 |
| Trials / main session | 378 | `TOTAL_TRIALS_PER_SESSION` L162 |
| Trials / main block | 42 (= 378 / 9) | `TRIALS_PER_BLOCK` L163 |
| Cue conditions | 6: `(1),(2),(3),(1,2),(1,3),(2,3)` | `CUE_CONDITIONS` L1616–1623 |
| PM rate (real) | **1 PM trial per cue per block** → **6 PM / 42** (≈14.3%) | L173–176 |
| PM rate (`participant == "test"`) | 3 PM per cue per block → 18 PM / 42 | L64–66, L205–211 |
| Ongoing in a PM main block | 42 − 6k (k = PM per cue); with k=1 → **exactly 6 per cue** | L176–178, L199–202 |

Practice sessions 1–5 use **different** block counts (see step 1).

---

## Pseudocode overview

```
1. DEFINE global counts, screen positions, cue conditions (config)
2. AFTER dialog: decide this session’s PHASE and optional extra blocks
3. SEED RNG from (participant, session)
4. BUILD full trial list:
     optional burn-in block
     optional PM-practice block
     for each main block:
         for each cue condition:
             add N_PM stubs  (0 if baseline/practice)
             add N_ongoing stubs
             each stub draws a random stimulus VARIANT from that cue’s pool
                 → variant fixes: which disk(s) show reward digits,
                   and which color sits at top / bottom_left / bottom_right
         SHUFFLE the block   ← this is how cue conditions are MIXED in time
5. RUN: for trial in prebuilt_list:
         map list indices → screen (x,y) via POSITIONS; draw disks
```

Three separable ideas:

| Idea | Meaning | Where decided |
|---|---|---|
| **Cue condition** | Which reward digit set is present: `(1)`, `(2)`, `(3)`, `(1,2)`, `(1,3)`, `(2,3)` | Counts fixed per block; **order mixed by shuffle** |
| **Cue / screen position** | Where disks sit on the monitor: triangle `top` / `bottom_left` / `bottom_right` (or center in session 1) | Fixed geometry `POSITIONS` |
| **Color at a position** | Which of red/blue/green fills each disk | Random permutation inside the variant pool |
---

## 1. Define numbers, phases, cue conditions (configuration)

### 1a. Session / block / PM counts

```156:178:multiplecue-prospectiveM/exp/testmain_demo_v3.py
# Session / phase design (see design.md)
N_PRACTICE_SESSIONS = 5
N_BASELINE_SESSIONS = 7
N_PM_SESSIONS_PER_KIND = 7
N_CUE_CONDITIONS = 6
N_BLOCKS = 9
TOTAL_TRIALS_PER_SESSION = 378
TRIALS_PER_BLOCK = TOTAL_TRIALS_PER_SESSION // N_BLOCKS
...
PM_TRIALS_PER_CUE_PER_BLOCK_DEFAULT = 1
...
PM_TRIALS_PER_BLOCK = N_CUE_CONDITIONS * PM_TRIALS_PER_CUE_PER_BLOCK
ONGOING_PER_BLOCK_PM_PHASE = TRIALS_PER_BLOCK - PM_TRIALS_PER_BLOCK
```

Derived counts are refreshed by `_refresh_pm_trial_counts()` (L184–202). For participant `"test"`, `_apply_test_pm_frequency()` raises `PM_TRIALS_PER_CUE_PER_BLOCK` (L205–211).

### 1b. Practice vs main block sizes

```248:255:multiplecue-prospectiveM/exp/testmain_demo_v3.py
PRACTICE_SESSION_TRIAL_CONFIG = {
    1: {"n_blocks": 10, "n_per_block": 20},
    2: {"n_blocks": 10, "n_per_block": 20},
    3: {"n_blocks": 4, "n_per_block": 50},
    4: {"n_blocks": 4, "n_per_block": 30},
    5: {"n_blocks": 4, "n_per_block": 50},
}
```

From session 6 onward, `get_session_trial_config()` returns `{n_blocks: 9, n_per_block: 42}` (L1576–1584).

### 1c. Which cue conditions exist this session

```1587:1625:multiplecue-prospectiveM/exp/testmain_demo_v3.py
# session 1: single-cue, one center disk
# session 2: single-cue, triangle layout
# sessions 3–4: dual-cue only
# sessions 5+: all 6 cue conditions
CUE_CONDITIONS = [
    {"values": (1,), "label": "(1)"},
    ...
    {"values": (2, 3), "label": "(2,3)"},
]
```

`get_session_generation_config(session)` (L1587–1614) picks the cue list and whether layout is `single_center`.

What a cue condition **means**: the `values` tuple is the set of **reward digits** that appear on the disks this trial (other disks get digit blank / reward 0).

| Label | Digits shown | Type |
|---|---|---|
| `(1)` | only 1 | single |
| `(2)` | only 2 | single |
| `(3)` | only 3 | single |
| `(1,2)` | 1 and 2 | dual |
| `(1,3)` | 1 and 3 | dual |
| `(2,3)` | 2 and 3 | dual |

### 1d. Screen positions of the cue disks (`POSITIONS`)

The three disks form an **equilateral triangle** (visual degrees), scaled by `CUE_DISPLAY_SCALE`:

```865:877:multiplecue-prospectiveM/exp/testmain_demo_v3.py
# Equilateral triangle: keep the original vertical span, set half-base = height / √3
POSITIONS = {
    "top": (0.0, _TRIANGLE_TOP_Y_DEG),
    "bottom_left": (-_TRIANGLE_BOTTOM_X_DEG, _TRIANGLE_BOTTOM_Y_DEG),
    "bottom_right": (_TRIANGLE_BOTTOM_X_DEG, _TRIANGLE_BOTTOM_Y_DEG),
}
POSITION_NAMES = list(POSITIONS.keys())   # ["top", "bottom_left", "bottom_right"]
N_POSITIONS = 3
```

**Index ↔ name ↔ screen** (this index is used everywhere in trial lists):

| Index `i` | Name | Screen `(x, y)` |
|---|---|---|
| 0 | `top` | `(0, top_y)` |
| 1 | `bottom_left` | `(-half_base, bottom_y)` |
| 2 | `bottom_right` | `(+half_base, bottom_y)` |

Session 1 only: one disk at `CENTER_POSITION = (0, 0)` named `"center"` (L1626–1627). Display uses a single slot instead of the triangle (L3928–3934).

```text
        top (0)
       /       \
 bottom_left   bottom_right
     (1)            (2)
```

These coordinates are **fixed for the whole experiment**. Randomization never moves the triangle; it only chooses what color/digit/PM marker goes on which named slot.

### 1e. Map session number → phase (practice / baseline / focal_pm / nonfocal_pm)

```1519:1544:multiplecue-prospectiveM/exp/testmain_demo_v3.py
def session_phase_for(session, participant_id):
    # 1–5  practice
    # 6–12 baseline
    # 13–19 first PM kind, 20–26 second PM kind
    # odd participant  → focal first, then nonfocal
    # even participant → nonfocal first, then focal
```

So phase **order** is counterbalanced by participant ID parity; block structure is the same.

Optional extras:

- **Burn-in** (20 trials, block `0`): first session of day, day > 1, session ≥ 6 — `_should_include_burnin_block` L1720–1724
- **PM practice** (one full 42-trial block, block `-1`): sessions 13 and 20 — `session_needs_pm_practice_block` L1547–1549

---

## 2. After dialog: decide this session, then build the list once

Around L2598–2615:

```text
SESSION_PHASE     = session_phase_for(SESSION, PARTICIPANT)
INCLUDE_BURNIN    = _should_include_burnin_block(...)
INCLUDE_PM_PRACTICE = session_needs_pm_practice_block(SESSION)

trials = build_session_trials(
    SESSION_PHASE, SESSION, PARTICIPANT,
    include_burnin_block=INCLUDE_BURNIN,
    include_pm_practice_block=INCLUDE_PM_PRACTICE,
)
```

That is the **only** place the schedule is created for the run.

---

## 3. Build the trial list (`build_session_trials`) — L1918–1998

### Pseudocode

```text
FUNCTION build_session_trials(phase, session, participant, burnin?, pm_practice?):
    rng = Random(seed = f"{participant}-{session}")   # reproducible

    trials = []

    IF burnin?:
        source_phase, source_session = burnin_source(...)
        append _make_burnin_block(rng, source_phase, source_session)
        # block number = 0, warm_up=1

    IF pm_practice?:
        append _make_block(..., pm_practice_block=1, trials_per_block=42)
        # block number = -1

    FOR block_number IN 1 .. n_blocks:
        append _make_block(..., trials_per_block=n_per_block)
        # each trial gets: block, trial_in_block, trial_in_session

    ASSERT len(trials) == expected_total
    RETURN trials
```

Seeded RNG: **L1930**. Main block loop: **L1971–1987**.

---

## 4. Make one block (`_make_block`) — L1774–1839

This is the core of **condition balancing + PM insertion + within-block shuffle**.

### Pseudocode

```text
FUNCTION _make_block(rng, phase, session, trials_per_block):
    cue_conditions = generation_config(session).cue_conditions
    cue_pools      = for each cue: enumerate all color/position variants

    block_trials = []
    has_pm = (phase in {focal_pm, nonfocal_pm})
    pm_kind = "focal" or "nonfocal" or None

    FOR each cue_index, cue IN cue_conditions:
        pool = cue_pools[cue_index]

        # How many ongoing trials for THIS cue in THIS block?
        n_ongoing = _ongoing_reps_for_cue(cue_index, phase, n_cues, trials_per_block)

        # How many PM trials for THIS cue?
        n_pm = PM_TRIALS_PER_CUE_PER_BLOCK if has_pm else 0

        REPEAT n_pm times:
            stub = {is_pm_trial=True, pm_trial_kind=pm_kind,
                    pm_position=rng.choice(positions), ...}
            pick variant = rng.choice(pool)   # colors + reward layout
            attach variant fields to stub
            append stub

        REPEAT n_ongoing times:
            stub = {is_pm_trial=False, ...}
            pick variant = rng.choice(pool)
            append stub

    rng.shuffle(block_trials)                 # order randomized WITHIN block
    ASSERT len(block_trials) == trials_per_block
    RETURN block_trials
```

### How many ongoing trials per cue? (`_ongoing_reps_for_cue` L1727–1745)

```text
IF PM phase:
    ongoing_total = trials_per_block - n_cues * k     # k = PM per cue
ELSE:
    ongoing_total = trials_per_block

base = ongoing_total // n_cues
remainder = ongoing_total % n_cues
# first `remainder` cue indices get base+1; others get base
```

**Example (main PM block, k=1, 6 cues, 42 trials):**

- PM: 1 × 6 = **6**
- Ongoing total: 36
- Per cue ongoing: **exactly 6** (36 = 6×6)
- Per cue total trials in block: 1 PM + 6 ongoing = **7**

**Example (baseline with 6 cues, 42 trials):**

- No PM
- Per cue: **exactly 7** (42 = 7×6)

### How cue conditions are mixed within a block

Mixing is **not** “sample a condition each trial.” It is **quota then shuffle**.

For the detailed walkthrough (formulas + worked count tables), see **[cue_condition_assignment.md](cue_condition_assignment.md)**.

```text
1. Append trials in cue-condition order (condition 0, then 1, …):
     [ (1)×n0, (2)×n1, (3)×n2, (1,2)×n3, (1,3)×n4, (2,3)×n5 ]
   (plus the PM stubs for that cue when in a PM phase)

2. rng.shuffle(block_trials)   # L1832
```
So after the shuffle, trial order looks like a random interleaving of all six conditions, but **counts stay exact**. There is no constraint like “no two same conditions in a row.”

Same rule for PM: each cue condition gets exactly `k` PM trials in the block; after shuffle, those PM trials are scattered among ongoing trials.

### Color positions and reward-digit positions (the “variant” pool)

Colors are `STIMULUS_COLOR_NAMES = ["red", "blue", "green"]` (L914). On a normal triangle trial, **all three colors always appear**, one per disk — never two reds.

`_pool_for_cue_condition` (L1631–1678) **enumerates every legal layout** for one cue condition, then each trial does `rng.choice(pool)`.

For the detailed walkthrough of `reward_pos` / dual-cue placement (with tables), see **[color_and_reward_position_pool.md](color_and_reward_position_pool.md)**.

#### Stored on each trial after a draw

Via `_variant_to_lists` / `_apply_variant_to_stub` (L1689–1709):

```text
trial["trial_colors"]   = [color_at_index_0, color_at_index_1, color_at_index_2]
                          # e.g. ["green", "red", "blue"]
                          # index 0=top, 1=bottom_left, 2=bottom_right

trial["reward_values"]  = [digit_at_0, digit_at_1, digit_at_2]
                          # e.g. [0, 2, 0]  for cue "(2)" with digit at bottom_left
                          # e.g. [1, 0, 3]  for cue "(1,3)" with 1 at top, 3 at bottom_right

trial["cue_condition"]  = "(2)" or "(1,3)" etc.
```

#### How the pool is built (pseudocode)

**A. Session 1 (center layout)** — only index 0 used:

```text
FOR color IN {red, blue, green}:
    position_to_color  = {0: color, 1: None, 2: None}
    position_to_reward = {0: reward_digit, 1: 0, 2: 0}
→ pool size = 3
```

**B. Single-cue conditions** `(1)` / `(2)` / `(3)` — triangle:

```text
FOR reward_pos IN {0, 1, 2}:              # which disk gets the digit
    FOR color_perm IN permutations(red,blue,green):  # 3! = 6
        assign color_perm[i] to disk i
        put the reward digit only on reward_pos; others = 0
→ pool size = 3 × 6 = 18 per single-cue condition
```

Example variants for cue `(2)`:

| `trial_colors` | `reward_values` | meaning |
|---|---|---|
| `["red","blue","green"]` | `[2,0,0]` | digit 2 on **top**; colors R/B/G around triangle |
| `["green","red","blue"]` | `[0,0,2]` | digit 2 on **bottom_right** |

**C. Dual-cue conditions** `(1,2)` / `(1,3)` / `(2,3)` — triangle:

```text
FOR (pos_a, pos_b) IN all ordered pairs of distinct positions:  # 3×2 = 6
    FOR (reward_at_a, reward_at_b) IN {(A,B), (B,A)}:         # which digit on which of the two
        FOR color_perm IN permutations(red,blue,green):         # 6
            assign colors
            put those two digits on pos_a / pos_b; third disk = 0
→ pool size = 6 × 2 × 6 = 72 per dual-cue condition
```

The empty disk (reward 0) still has a **color**; it just shows no digit (blank white center).

#### Draw with replacement

Each trial independently picks `rng.choice(pool)` (L1815, L1829). The same exact color+digit layout can therefore repeat within a block; there is no “deal without replacement” across the pool.

### Where PM sits relative to colors

`pm_position` is chosen separately: `rng.choice(["top","bottom_left","bottom_right"])` (or `"center"` in session 1) — L1756–1759, L1790, L1809.

It does **not** have to be the disk that shows the reward digit. Color layout and PM marker location are independent random draws.

### How the trial loop maps lists → screen (L3928–3970)

```text
cue_slots = [
  ("top",          POSITIONS["top"],          0),
  ("bottom_left",  POSITIONS["bottom_left"],  1),
  ("bottom_right", POSITIONS["bottom_right"], 2),
]

FOR (position_name, screen_xy, i) IN cue_slots:
    fill outer disk with COLORS[ trial_colors[i] ]
    draw digit trial_reward_values[i] if > 0
    IF this trial is PM and position_name == trial["pm_position"]:
        draw focal / nonfocal PM marker on that disk
```

So:

1. **Cue position on screen** = fixed triangle geometry.
2. **Color at that position** = `trial_colors[i]`.
3. **Digit at that position** = `reward_values[i]` (which cue condition you are in).
4. **Temporal mix of cue conditions** = balanced counts + within-block shuffle.
---

## 5. Special blocks

### Burn-in (`_make_burnin_block` L1853–1915)

- Always **20** trials (`BURNIN_TRIALS_PER_BLOCK`).
- Uses the **previous** phase’s task when entering a new PM phase (sessions 13 / 20) — `_burnin_source_for_session` L1712–1717.
- PM count is scaled to the main-block PM rate:  
  `round(20 * (6k / 42))`, at least 1 if PM phase — `_burnin_pm_trial_count` L1842–1850.
- Same pattern: stubs per cue → shuffle.

### PM practice block

Same as a normal main `_make_block` for the current PM phase, but flagged `pm_practice_block=1` and numbered `block=-1` (L1952–1969).

---

## 6. Run the prebuilt list (no more design)

```3869:3870:multiplecue-prospectiveM/exp/testmain_demo_v3.py
for trial in trials:
    current_block = trial["block"]
```

Each dict already has fields like:

- `block`, `trial_in_block`, `trial_in_session`
- `session_phase`, `cue_condition`, `reward_values`, `trial_colors`
- `is_pm_trial`, `pm_trial_kind`, `pm_position`, PM style fields
- `burn_in_block`, `pm_practice_block`, `warm_up`

Display / response / saving use those fields; they do not re-sample the design.

---

## Map: “I want to understand X” → go here

| Question | Function / constant | Lines |
|---|---|---|
| How many sessions / phases? | `N_*`, `session_phase_for` | 156–159, 1519–1544 |
| Trials per block / session? | `N_BLOCKS`, `TOTAL_*`, `PRACTICE_SESSION_TRIAL_CONFIG`, `get_session_trial_config` | 161–163, 248–255, 1576–1584 |
| What are the 6 cue conditions? | `CUE_CONDITIONS`, `get_session_generation_config` | 1587–1625 |
| Where do disks sit on screen? | `POSITIONS`, `POSITION_NAMES`, `CENTER_POSITION` | 865–877, 1626–1627 |
| How are cue conditions mixed in time? | quota in `_make_block` + `rng.shuffle` | 1797–1832 |
| How are colors assigned to disks? | `permutations(STIMULUS_COLOR_NAMES)` in `_pool_for_cue_condition` | 1631–1678, 914 |
| How are reward digits placed on disks? | `reward_pos` / `pos_a,pos_b` loops in the pool | 1657–1678 |
| How does display use those lists? | trial loop `cue_slots` | 3928–3970 |
| How many PM trials? | `PM_TRIALS_PER_CUE_PER_BLOCK`, `_ongoing_reps_for_cue` | 167–202, 1727–1745 |
| How is a block assembled? | `_make_block` | 1774–1839 |
| How is the whole session list built? | `build_session_trials` | 1918–1998 |
| When is it called? | module-level after dialog | 2598–2615 |
| When is it played? | `for trial in trials` | 3869+ |
| Is randomization reproducible? | `random.Random(f"{participant}-{session}")` | 1930 |

---

## Tiny worked example (one main PM block, real rate k=1)

```text
phase = focal_pm, trials_per_block = 42, cues = 6, k = 1

# --- counts (not yet ordered) ---
for cue in [(1),(2),(3),(1,2),(1,3),(2,3)]:
    add 1 PM trial
    add 6 ongoing trials
    each trial:
        trial_colors  = random permutation of {red,blue,green} on (top, BL, BR)
        reward_values = digits for this cue on random disk(s); other disks 0
        pm_position   = random among {top, bottom_left, bottom_right}  # if PM

→ 6 + 36 = 42 trials still grouped by cue condition

# --- mix ---
shuffle(42)   # now (1), (1,3), (2), … appear interleaved

# --- at display time for one trial ---
draw disk at POSITIONS["top"]          with trial_colors[0], digit reward_values[0]
draw disk at POSITIONS["bottom_left"]  with trial_colors[1], digit reward_values[1]
draw disk at POSITIONS["bottom_right"] with trial_colors[2], digit reward_values[2]
if PM: overlay marker on POSITIONS[pm_position]
```

Nine such blocks → 378 main trials. Plus optional burn-in (20) and/or PM practice (42) at the front of the list when those flags are on.