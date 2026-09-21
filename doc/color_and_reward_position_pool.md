# How color layouts and reward-digit positions are defined

**Code:** `_pool_for_cue_condition` in `exp/testmain_demo_v3.py` (≈ L1631–1678)

**Question this note answers:**  
When the doc says “put the reward digit only on `reward_pos`,” how does the code know *where* to put it? Is that computed somehow, or listed in advance?

**Short answer:** It is **not computed from a formula**. The code **lists every legal placement in advance** into a *pool*. Later, each trial just does `rng.choice(pool)` and uses whatever placement that randomly chosen variant already has.

---

## The two things that get combined

On a normal (triangle) trial there are always **3 disks**:

| Index | Name |
|---|---|
| 0 | top |
| 1 | bottom_left |
| 2 | bottom_right |

Two independent choices make one **variant**:

1. **Color layout** — which color sits on which disk.  
   Always a permutation of `{red, blue, green}` → **6** possibilities (`3! = 6`).

2. **Reward-digit layout** — which disk(s) show the digit(s) for this cue condition; the other disk(s) get `0` (blank).

A variant is just a pair of maps:

```text
position_to_color  = {0: "red", 1: "blue", 2: "green"}   # e.g.
position_to_reward = {0: 0,     1: 2,      2: 0}         # e.g. digit 2 on bottom_left
```

Later these become the trial fields:

```text
trial_colors  = ["red", "blue", "green"]   # index order
reward_values = [0, 2, 0]
```

---

## Timing: when is this decided?

```text
SESSION START
  │
  ├─ for each cue condition:
  │      build POOL = list of ALL legal variants   ← exhaustive enumeration
  │
  ├─ for each trial stub of that cue:
  │      variant = random.choice(POOL)             ← pick one ready-made layout
  │      copy colors + reward digits onto the trial
  │
  └─ shuffle trial order within the block
```

So “where does the digit go?” is answered **early, by enumeration**: every possible disk is included as its own pool entry. The trial does not calculate a position; it **samples a pre-listed variant**.

---

## Part A — Single-cue conditions `(1)`, `(2)`, `(3)`

### What must be true

Cue `(2)` means: **exactly one disk shows digit 2**; the other two show blank (`0`).

The code does **not** pick a clever position. It loops over all positions:

```python
# L1657–1666 (simplified)
reward_value = 2   # because cue condition is (2)

for reward_pos in {0, 1, 2}:                 # WHERE the digit can sit
    for color_perm in permutations(R,B,G):   # HOW colors can sit
        colors  = color_perm on disks 0,1,2
        rewards = [0, 0, 0]
        rewards[reward_pos] = 2              # put digit ONLY there
        save this as one variant
```

### Reading the nested loops

| Loop | Meaning | Count |
|---|---|---|
| outer `reward_pos` | “Try putting the digit on top; then on bottom_left; then on bottom_right.” | 3 |
| inner `color_perm` | “For that digit placement, try every color arrangement.” | 6 |
| **total** | every digit location × every color layout | **3 × 6 = 18** |

So for cue `(2)`, the pool always contains exactly these 18 layouts. Nothing is left out; nothing is invented later.

### Concrete: all 18 variants for cue `(2)`

Color permutations (fixed order of listing):

```text
P0 = (red,   blue,  green)
P1 = (red,   green, blue)
P2 = (blue,  red,   green)
P3 = (blue,  green, red)
P4 = (green, red,   blue)
P5 = (green, blue,  red)
```

| # | `reward_pos` | digit on | `trial_colors` | `reward_values` |
|---|---|---|---|---|
| 1 | 0 | top | R B G | **2**, 0, 0 |
| 2 | 0 | top | R G B | **2**, 0, 0 |
| 3 | 0 | top | B R G | **2**, 0, 0 |
| 4 | 0 | top | B G R | **2**, 0, 0 |
| 5 | 0 | top | G R B | **2**, 0, 0 |
| 6 | 0 | top | G B R | **2**, 0, 0 |
| 7 | 1 | bottom_left | R B G | 0, **2**, 0 |
| 8 | 1 | bottom_left | R G B | 0, **2**, 0 |
| … | 1 | … | … | 0, **2**, 0 |
| 12 | 1 | bottom_left | G B R | 0, **2**, 0 |
| 13 | 2 | bottom_right | R B G | 0, 0, **2** |
| … | 2 | … | … | 0, 0, **2** |
| 18 | 2 | bottom_right | G B R | 0, 0, **2** |

Same structure for `(1)` (digit is `1`) and `(3)` (digit is `3`). Only the number written on the chosen disk changes.

### What happens on one real trial

```text
pool_for_(2) has 18 variants ready
trial needs cue "(2)"
→ pick e.g. variant #9 at random
→ that variant ALREADY says:
     colors = (blue, green, red)
     rewards = (0, 2, 0)          # digit already fixed on bottom_left
→ trial_colors / reward_values are just copied from that variant
```

There is no second step that “calculates where the digit goes.” The chosen row in the table *is* the answer.

---

## Part B — Dual-cue conditions `(1,2)`, `(1,3)`, `(2,3)`

### What must be true

Cue `(1,3)` means: **two disks show digits 1 and 3**; the third disk is blank (`0`).

Now two disks must be chosen, and the two digits can be swapped between them.

```python
# L1668–1678 (simplified)
reward_a, reward_b = 1, 3   # because cue is (1,3)

for (pos_a, pos_b) in all ordered pairs of distinct positions:  # 3×2 = 6
    for (digit_on_a, digit_on_b) in [(1,3), (3,1)]:            # 2 swaps
        for color_perm in permutations(R,B,G):                 # 6
            colors  = color_perm on disks
            rewards = [0, 0, 0]
            rewards[pos_a] = digit_on_a
            rewards[pos_b] = digit_on_b
            # the remaining disk stays 0
            save this as one variant
```

### Reading the nested loops

| Loop | Meaning | Count |
|---|---|---|
| `(pos_a, pos_b)` | which two disks get digits (ordered) | 6 = `P(3,2)` |
| digit swap | which of the two digits goes on `pos_a` vs `pos_b` | 2 |
| `color_perm` | color arrangement | 6 |
| **total** | | **6 × 2 × 6 = 72** |

`permutations(range(3), 2)` yields the ordered pairs:

```text
(0,1)  top + bottom_left      (blank = bottom_right)
(0,2)  top + bottom_right     (blank = bottom_left)
(1,0)  bottom_left + top      (blank = bottom_right)  ← same disks as (0,1), opposite order
(1,2)  bottom_left + bottom_right
(2,0)  bottom_right + top
(2,1)  bottom_right + bottom_left
```

Why ordered pairs *and* a separate digit-swap loop? Together they cover every way to put `{1,3}` onto two of the three disks. (Some combinations are listed more than once via different `(pos_a,pos_b)` orderings; the pool is used only for uniform-ish random draws via `choice`, not as a unique set.)

### Concrete examples for cue `(1,3)`

**Example 1** — digits on top and bottom_right; `1` on top, `3` on bottom_right; colors R B G:

```text
pos_a=0, pos_b=2
digit_on_a=1, digit_on_b=3
color_perm = (red, blue, green)

trial_colors  = ["red", "blue", "green"]
reward_values = [1, 0, 3]
                 ↑ top shows 1
                    ↑ bottom_left blank
                       ↑ bottom_right shows 3
```

**Example 2** — same two disks, digits swapped:

```text
pos_a=0, pos_b=2
digit_on_a=3, digit_on_b=1

trial_colors  = ["red", "blue", "green"]   # colors can be anything from the 6 perms
reward_values = [3, 0, 1]
```

**Example 3** — digits on bottom_left and bottom_right; top blank:

```text
pos_a=1, pos_b=2
digit_on_a=1, digit_on_b=3
color_perm = (green, red, blue)

trial_colors  = ["green", "red", "blue"]
reward_values = [0, 1, 3]
                 ↑ top blank, still colored green
```

Again: on a real trial, `rng.choice(pool)` picks one of these 72 ready-made rows. The digit locations come from that row.

---

## Part C — Side-by-side mental model

```text
SINGLE cue (2)
──────────────
  Ask: "Which ONE disk gets digit 2?"
  Answer set: {top, bottom_left, bottom_right}     → 3 choices
  Cross with: 6 color layouts                       → 18 variants in the pool

DUAL cue (1,3)
──────────────
  Ask: "Which TWO disks get digits, and which digit on which?"
  Answer set: choose 2 disks + assign {1,3} to them
  Cross with: 6 color layouts                       → 72 variants in the pool
```

Colors and digit placement are **crossed**, not sequential decisions at trial time:

```text
❌  first pick colors, then somehow compute where digit should go
✅  list every (colors × digit-placement) pair up front; sample one pair
```

---

## Part D — What is *not* decided in this pool

These are separate random draws (or fixed config), not part of `_pool_for_cue_condition`:

| Thing | How it is chosen |
|---|---|
| Which cue condition this trial is | Fixed quota per block, then block shuffle |
| Whether this trial is a PM trial | Fixed `k` PM stubs per cue in the block |
| `pm_position` (which disk gets the PM marker) | Separate `rng.choice` among position names |
| Trial order in the block | `rng.shuffle` after all stubs exist |

So a PM trial with cue `(2)` still draws a normal `(2)` color+digit variant from the same 18-item pool; the PM marker is overlaid on whatever `pm_position` was chosen, which may or may not be the disk that shows the digit.

---

## Part E — Tiny code walk for one line

```python
position_to_reward = {i: 0 for i in range(N_POSITIONS)}  # start all blank
position_to_reward[reward_pos] = reward_value            # write the digit
```

If `reward_pos == 1` and `reward_value == 2`:

```text
before: {0:0, 1:0, 2:0}
after:  {0:0, 1:2, 2:0}
```

That is the entire “calculation.” `reward_pos` is simply the current value of the `for reward_pos in range(3)` loop variable while the pool is being built.

---

## Jump links in the experiment code

| Step | Lines |
|---|---|
| Build pool for one cue condition | `_pool_for_cue_condition` L1631–1678 |
| Build all pools for this session | `_cue_pools_for_session` L1681–1686 |
| Convert maps → `trial_colors` / `reward_values` lists | `_variant_to_lists` L1689–1699 |
| Attach a random pool entry to a trial stub | `_apply_variant_to_stub` + `rng.choice(pool)` L1702–1709, L1815, L1829 |
| Draw disks using those lists | trial loop L3928–3970 |
