"""
PsychoPy version of the multiple-cue prospective memory experiment.

Full session structure: 26 sessions (5 practice + 7 baseline + 7 focal PM + 7 nonfocal PM).
Trial design is fully pre-assigned before the experiment starts (no randomization in the trial loop).
Keyboard only.
"""

import json
import math
import random
from itertools import permutations
from pathlib import Path

from psychopy import gui, visual, core, event, monitors

# =============================================================================
# CONFIG: CHANGE THESE VALUES FIRST
# =============================================================================

EXP_DIR = Path(__file__).resolve().parent
INSTRUCTION_DIR = EXP_DIR / "Instructions"

# Keep the normal window ratio, but allow easy scaling for high-res displays.
BASE_WINDOW_SIZE = (1000, 700)
WINDOW_SCALE = 1.35
WINDOW_SIZE = (
    int(BASE_WINDOW_SIZE[0] * WINDOW_SCALE),
    int(BASE_WINDOW_SIZE[1] * WINDOW_SCALE),
)
FULL_SCREEN = False
BACKGROUND_COLOR = (128, 128, 128)
COLOR_SPACE = "rgb255"

FIXATION_TIME = 0.5
MAX_RESPONSE_TIME = 3.0
FEEDBACK_WAIT_TIME = 1.5
ITI_TIME = 0.3
REWARD_MONEY_FACTOR = 0.05
STIMULUS_OPACITY = 1.0

# Session / phase design (see design.md)
N_PRACTICE_SESSIONS = 5
N_BASELINE_SESSIONS = 7
N_PM_SESSIONS_PER_KIND = 7
N_CUE_CONDITIONS = 6
N_BLOCKS = 9
TOTAL_TRIALS_PER_SESSION = 396
TRIALS_PER_BLOCK = TOTAL_TRIALS_PER_SESSION // N_BLOCKS
REPS_PER_CUE_PER_BLOCK = TRIALS_PER_BLOCK // N_CUE_CONDITIONS
BLOCK_TRIAL_REMAINDER = TRIALS_PER_BLOCK % N_CUE_CONDITIONS

PM_TRIALS_PER_CUE_PER_BLOCK = 1
PM_TRIALS_PER_BLOCK = N_CUE_CONDITIONS * PM_TRIALS_PER_CUE_PER_BLOCK
ONGOING_PER_BLOCK_PM_PHASE = TRIALS_PER_BLOCK - PM_TRIALS_PER_BLOCK
ONGOING_REPS_PER_CUE_PM = ONGOING_PER_BLOCK_PM_PHASE // N_CUE_CONDITIONS
ONGOING_REMAINDER_PM = ONGOING_PER_BLOCK_PM_PHASE % N_CUE_CONDITIONS

MAX_SESSION = (
    N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS + 2 * N_PM_SESSIONS_PER_KIND
)
MAX_PARTICIPANT_ID = 100
PARTICIPANT_CHOICES = ["test"] + [str(i) for i in range(1, MAX_PARTICIPANT_ID + 1)]
DEFAULT_PARTICIPANT = "test"

# Warm-up / burn-in hooks (not active in main sessions yet).
FIRST_WARMUP_TRIALS = 0
OTHER_WARMUP_TRIALS = 0
INCLUDE_BURNIN_BLOCK = False
BURNIN_TRIALS_PER_BLOCK = 20
BURNIN_BLOCK_NUMBER = 0
INSTRUCTION_LETTER_SIZE_DEG = 0.6

# Future per-practice-session trial-count overrides.
PRACTICE_SESSION_CONFIG_OVERRIDES = {}

# Future per-session welcome instruction paths (session number -> filename in Instructions/).
SESSION_WELCOME_INSTRUCTION_OVERRIDES = {}

# Future per-session display overrides (e.g. hide keymap, single center circle).
DEFAULT_DISPLAY = {
    "show_color_keymap": True,
    "triangle_layout": True,
    "n_positions": 3,
}
SESSION_DISPLAY_OVERRIDES = {}

# Debug: set enabled=True for a 12-trial PM smoke session (6 focal + 6 nonfocal, one per cue).
DEBUG_CONFIG = {
    "enabled": True,
}

UNITS = "deg"
BASE_STIM_FACTOR = 0.04
STIM_SCALE = 1.55
STIM_FACTOR = BASE_STIM_FACTOR * STIM_SCALE
INSTRUCTION_WRAP_WIDTH_DEG = 800 * STIM_FACTOR
POSITION_SCALE = 1.0
POSITION_FACTOR = BASE_STIM_FACTOR * POSITION_SCALE
MONITOR_NAME = "testmain_demo_monitor"
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60

CIRCLE_RADIUS = 20 * STIM_FACTOR
INNER_CIRCLE_RADIUS = 8.75 * STIM_FACTOR
REWARD_TEXT_HEIGHT = 14 * STIM_FACTOR
BORDER_LINE_WIDTH = 4
DASHED_OUTLINE_LINE_WIDTH = 5

FOCAL_PM_INNER_DOT_RADIUS = 3.5 * STIM_FACTOR
FOCAL_PM_RING_RADIUS = (CIRCLE_RADIUS + INNER_CIRCLE_RADIUS) / 2
FOCAL_PM_RING_LINE_WIDTH = 5
FOCAL_PM_PATCH_RADIUS = 5 * STIM_FACTOR
FOCAL_PM_PATCH_OFFSET = 0.55 * CIRCLE_RADIUS
FOCAL_PM_HALO_RADIUS = CIRCLE_RADIUS * 1.08
FOCAL_PM_HALO_LINE_WIDTH = 7
FOCAL_PM_MARKER_BG_RADIUS = INNER_CIRCLE_RADIUS * 0.72
FOCAL_PM_STYLE = "center_ring"

TOP_Y = 60 * POSITION_FACTOR
BOTTOM_Y = -50 * POSITION_FACTOR
BOTTOM_X = 60 * POSITION_FACTOR
POSITIONS = {
    "top": (0.0, TOP_Y),
    "bottom_left": (-BOTTOM_X, BOTTOM_Y),
    "bottom_right": (BOTTOM_X, BOTTOM_Y),
}
POSITION_NAMES = list(POSITIONS.keys())
N_POSITIONS = len(POSITION_NAMES)

COLORS = {
    "red": (220, 50, 50),
    "blue": (50, 100, 220),
    "green": (50, 180, 80),
    "orange": (240, 150, 30),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}

COLOR_KEYS = {
    "red": "n",
    "blue": "j",
    "green": "k",
}
COLOR_NAMES = list(COLOR_KEYS.keys())

PM_KEY = "d"
START_KEY = "space"
QUIT_KEY = "escape"
ALL_RESPONSE_KEYS = list(COLOR_KEYS.values()) + [PM_KEY, QUIT_KEY]

PM_REWARD = 5

FEEDBACK_LETTER_SIZE_DEG = 50 * STIM_FACTOR
FEEDBACK1_POS_DEG = (0, 70 * STIM_FACTOR)
FEEDBACK2_POS_DEG = (0, -70 * STIM_FACTOR)
FEEDBACK3_POS_DEG = (0, -140 * STIM_FACTOR)
FEEDBACK4_POS_DEG = (0, -200 * STIM_FACTOR)
FEEDBACK_TEXT_COLOR = COLORS["white"]
TOO_SLOW_TEXT = "TOO SLOW!"

KEYMAP_SQUARE_SIZE = 30 * STIM_FACTOR
KEYMAP_TEXT_HEIGHT = 0.55 * KEYMAP_SQUARE_SIZE
KEYMAP_DISTANCE = 50 * STIM_FACTOR
KEYMAP_EXTRA_DOWN = 0.75 * KEYMAP_DISTANCE
KEYMAP_BASE_Y = (-150 * STIM_FACTOR) - KEYMAP_EXTRA_DOWN
KEYMAP_ROW_OFFSET = 0.6 * KEYMAP_DISTANCE

CUE_CONDITIONS = [
    {"values": (1,), "label": "(1)"},
    {"values": (2,), "label": "(2)"},
    {"values": (3,), "label": "(3)"},
    {"values": (1, 2), "label": "(1,2)"},
    {"values": (1, 3), "label": "(1,3)"},
    {"values": (2, 3), "label": "(2,3)"},
]


# =============================================================================
# SESSION PHASE + TRIAL GENERATION (all randomization happens here)
# =============================================================================


def _participant_number(participant_id: str):
    """Return numeric participant ID, or None for non-numeric IDs like 'test'."""
    if participant_id == "test":
        return 1
    try:
        return int(participant_id)
    except ValueError:
        return None


def session_phase_for(session: int, participant_id: str) -> str:
    """Map 1-based session number to session_phase label."""
    if session < 1 or session > MAX_SESSION:
        raise ValueError(f"Session must be between 1 and {MAX_SESSION}.")

    if session <= N_PRACTICE_SESSIONS:
        return "practice"

    baseline_end = N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS
    if session <= baseline_end:
        return "baseline"

    pm_first_end = baseline_end + N_PM_SESSIONS_PER_KIND
    pm_second_end = pm_first_end + N_PM_SESSIONS_PER_KIND

    participant_num = _participant_number(participant_id)
    # Odd participant  → focal PM sessions first, then nonfocal PM sessions.
    # Even participant → nonfocal PM sessions first, then focal PM sessions.
    focal_first = participant_num is None or participant_num % 2 == 1

    if session <= pm_first_end:
        return "focal_pm" if focal_first else "nonfocal_pm"
    if session <= pm_second_end:
        return "nonfocal_pm" if focal_first else "focal_pm"

    raise ValueError(f"Session {session} is out of range.")


def get_session_display_config(session: int) -> dict:
    """Display options for a session; defaults unless overridden."""
    return {**DEFAULT_DISPLAY, **SESSION_DISPLAY_OVERRIDES.get(session, {})}


def _pool_for_cue_condition(cue_condition: dict) -> list:
    """
    Enumerate all trial variants for one cue condition (reward position + color layout).
    Adapted from multiplecue-responsebox/exp/testmain.py _pool_for_reward_condition.
    """
    reward_values = tuple(cue_condition["values"])
    condition_label = cue_condition["label"]
    all_colors = COLOR_NAMES[:]

    def make_variant(position_to_color, position_to_reward):
        return {
            "position_to_color": position_to_color,
            "position_to_reward": position_to_reward,
            "cue_condition": condition_label,
        }

    if len(reward_values) == 1:
        reward_value = reward_values[0]
        out = []
        for reward_pos in range(N_POSITIONS):
            for color_perm in permutations(all_colors):
                position_to_color = {i: color_perm[i] for i in range(N_POSITIONS)}
                position_to_reward = {i: 0 for i in range(N_POSITIONS)}
                position_to_reward[reward_pos] = reward_value
                out.append(make_variant(position_to_color, position_to_reward))
        return out

    reward_a, reward_b = reward_values[0], reward_values[1]
    out = []
    for pos_a, pos_b in permutations(range(N_POSITIONS), 2):
        for reward_at_a, reward_at_b in [(reward_a, reward_b), (reward_b, reward_a)]:
            for color_perm in permutations(all_colors):
                position_to_color = {i: color_perm[i] for i in range(N_POSITIONS)}
                position_to_reward = {i: 0 for i in range(N_POSITIONS)}
                position_to_reward[pos_a] = reward_at_a
                position_to_reward[pos_b] = reward_at_b
                out.append(make_variant(position_to_color, position_to_reward))
    return out


CUE_POOLS = [_pool_for_cue_condition(c) for c in CUE_CONDITIONS]


def _variant_to_lists(variant: dict):
    """Convert pool variant maps to position-ordered lists."""
    reward_values = [variant["position_to_reward"][i] for i in range(N_POSITIONS)]
    trial_colors = [variant["position_to_color"][i] for i in range(N_POSITIONS)]
    return reward_values, trial_colors, variant["cue_condition"]


def _apply_variant_to_stub(stub: dict, variant: dict):
    reward_values, trial_colors, cue_condition = _variant_to_lists(variant)
    stub["reward_values"] = reward_values
    stub["trial_colors"] = trial_colors
    stub["cue_condition"] = cue_condition


def _ongoing_reps_for_cue(cue_index: int, session_phase: str) -> int:
    if session_phase in ("focal_pm", "nonfocal_pm"):
        base = ONGOING_REPS_PER_CUE_PM
        remainder = ONGOING_REMAINDER_PM
    else:
        base = REPS_PER_CUE_PER_BLOCK
        remainder = BLOCK_TRIAL_REMAINDER
    return base + (1 if cue_index < remainder else 0)


def _pm_trial_kind_for_phase(session_phase: str):
    if session_phase == "focal_pm":
        return "focal"
    if session_phase == "nonfocal_pm":
        return "nonfocal"
    return None


def _make_block(
    rng: random.Random,
    session_phase: str,
    *,
    burn_in_block: int = 0,
) -> list:
    """Build one block: cue-balanced stubs, pool draw per stub, within-block shuffle."""
    block_trials = []
    has_pm = session_phase in ("focal_pm", "nonfocal_pm")
    pm_kind = _pm_trial_kind_for_phase(session_phase)

    for cue_index, cue_condition in enumerate(CUE_CONDITIONS):
        pool = CUE_POOLS[cue_index]
        n_ongoing = _ongoing_reps_for_cue(cue_index, session_phase)

        if has_pm:
            pm_stub = {
                "session_phase": session_phase,
                "is_pm_trial": True,
                "pm_trial_kind": pm_kind,
                "pm_position": rng.choice(POSITION_NAMES),
                "warm_up": 0,
                "burn_in_block": burn_in_block,
            }
            _apply_variant_to_stub(pm_stub, rng.choice(pool))
            block_trials.append(pm_stub)

        for _ in range(n_ongoing):
            ongoing_stub = {
                "session_phase": session_phase,
                "is_pm_trial": False,
                "pm_trial_kind": None,
                "pm_position": None,
                "warm_up": 0,
                "burn_in_block": burn_in_block,
            }
            _apply_variant_to_stub(ongoing_stub, rng.choice(pool))
            block_trials.append(ongoing_stub)

    rng.shuffle(block_trials)
    return block_trials


def build_session_trials(
    session_phase: str,
    session_number: int,
    participant_id: str,
    *,
    include_burnin_block: bool = False,
) -> list:
    """
    Pre-design the full session trial list before the experiment starts.
    All random draws use a seeded RNG (participant + session).
    """
    rng = random.Random(f"{participant_id}-{session_number}")
    trials = []
    trial_in_session = 0

    if include_burnin_block:
        burnin_block = _make_block(rng, session_phase, burn_in_block=1)
        if len(burnin_block) > BURNIN_TRIALS_PER_BLOCK:
            burnin_block = burnin_block[:BURNIN_TRIALS_PER_BLOCK]
        for trial_in_block, trial in enumerate(burnin_block, start=1):
            trial = dict(trial)
            trial.update(
                block=BURNIN_BLOCK_NUMBER,
                trial_in_block=trial_in_block,
                trial_in_session=trial_in_session + 1,
            )
            trials.append(trial)
            trial_in_session += 1

    for block_number in range(1, N_BLOCKS + 1):
        block_trials = _make_block(rng, session_phase, burn_in_block=0)
        for trial_in_block, trial in enumerate(block_trials, start=1):
            trial = dict(trial)
            trial.update(
                block=block_number,
                trial_in_block=trial_in_block,
                trial_in_session=trial_in_session + 1,
            )
            trials.append(trial)
            trial_in_session += 1

    expected = (
        (BURNIN_TRIALS_PER_BLOCK if include_burnin_block else 0)
        + N_BLOCKS * TRIALS_PER_BLOCK
    )
    if len(trials) != expected:
        raise ValueError(
            f"Expected {expected} trials, got {len(trials)} for phase {session_phase!r}."
        )
    return trials


def build_debug_pm_test_trials(participant_id: str, session_number: int) -> list:
    """
    Debug PM smoke session: 12 trials, all pre-assigned at build time.

    Trials 1-6 (block 1): focal PM, one per cue condition — order shuffled within block.
    Trials 7-12 (block 2): nonfocal PM, one per cue condition — order shuffled within block.

    Each trial draws a random reward-position/color variant from its cue pool and a random
    pm_position, so every cue condition and both PM kinds can be tested quickly.
    """
    rng = random.Random(f"debug-pm-{participant_id}-{session_number}")
    trials = []
    trial_in_session = 0

    for block_number, pm_kind in ((1, "focal"), (2, "nonfocal")):
        session_phase = "focal_pm" if pm_kind == "focal" else "nonfocal_pm"
        block_trials = []
        for cue_index, _cue_condition in enumerate(CUE_CONDITIONS):
            pool = CUE_POOLS[cue_index]
            stub = {
                "session_phase": session_phase,
                "is_pm_trial": True,
                "pm_trial_kind": pm_kind,
                "pm_position": rng.choice(POSITION_NAMES),
                "warm_up": 0,
                "burn_in_block": 0,
            }
            _apply_variant_to_stub(stub, rng.choice(pool))
            block_trials.append(stub)
        rng.shuffle(block_trials)
        for trial_in_block, trial in enumerate(block_trials, start=1):
            trial_in_session += 1
            trials.append(
                {
                    **trial,
                    "block": block_number,
                    "trial_in_block": trial_in_block,
                    "trial_in_session": trial_in_session,
                }
            )
    return trials


def _load_instruction(filename: str, **fmt) -> str:
    path = INSTRUCTION_DIR / filename
    if not path.exists():
        raise SystemExit(f"Instruction file not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    if fmt:
        text = text.format(**fmt)
    return text


def _load_session_welcome_instruction(session: int) -> str:
    override = SESSION_WELCOME_INSTRUCTION_OVERRIDES.get(session)
    if override:
        return _load_instruction(override)
    return _load_instruction("instruction welcome.txt")


# =============================================================================
# SESSION DIALOG
# =============================================================================

session_dlg = gui.Dlg(title="Prospective MCP Session")
session_dlg.addField(
    "Participant",
    initial=DEFAULT_PARTICIPANT,
    choices=PARTICIPANT_CHOICES,
)
session_dlg.addField("Session", initial="1")
session_dlg.show()
if not session_dlg.OK:
    core.quit()

PARTICIPANT = str(session_dlg.data[0]).strip()
if PARTICIPANT not in PARTICIPANT_CHOICES:
    raise SystemExit(
        f"Participant must be 'test' or an integer from 1 to {MAX_PARTICIPANT_ID}."
    )

SESSION = int(session_dlg.data[1])
if SESSION < 1 or SESSION > MAX_SESSION:
    raise SystemExit(f"Session must be between 1 and {MAX_SESSION}.")

SESSION_PHASE = session_phase_for(SESSION, PARTICIPANT)
DISPLAY_CONFIG = get_session_display_config(SESSION)
INCLUDE_BURNIN = INCLUDE_BURNIN_BLOCK  # hook for future session/day rules

if DEBUG_CONFIG["enabled"]:
    # Short PM test session: trials 1-6 focal PM, 7-12 nonfocal PM (one per cue condition).
    SESSION_PHASE = "focal_pm"
    trials = build_debug_pm_test_trials(PARTICIPANT, SESSION)
else:
    trials = build_session_trials(
        SESSION_PHASE,
        SESSION,
        PARTICIPANT,
        include_burnin_block=INCLUDE_BURNIN,
    )
N_TRIALS = len(trials)
SESSION_N_BLOCKS = max(t["block"] for t in trials) if trials else N_BLOCKS
_block_trial_counts = {}
for _t in trials:
    _block_trial_counts[_t["block"]] = _t["trial_in_block"]

# print(json.dumps(trials, indent=2))  # full pre-designed session structure


# =============================================================================
# WINDOW AND STIMULI
# =============================================================================

mon = monitors.Monitor(MONITOR_NAME)
mon.setSizePix(WINDOW_SIZE)
mon.setWidth(MONITOR_WIDTH_CM)
mon.setDistance(MONITOR_DISTANCE_CM)

win = visual.Window(
    size=WINDOW_SIZE,
    fullscr=FULL_SCREEN,
    units=UNITS,
    color=BACKGROUND_COLOR,
    colorSpace=COLOR_SPACE,
    monitor=mon,
)

fixation = visual.TextStim(
    win,
    text="+",
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=0.35,
)

instructions = visual.TextStim(
    win,
    text="",
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
    units=UNITS,
)

feedback1 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK1_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback2 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK2_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback3 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK3_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback4 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK4_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.2,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=UNITS,
    opacity=STIMULUS_OPACITY,
)
end_text = visual.TextStim(
    win,
    text=_load_instruction("instruction end.txt"),
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    units=UNITS,
)
esc_confirm_text = visual.TextStim(
    win,
    text="Press ESC again to exit\n\nPress SPACE to continue",
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    units=UNITS,
)
block_break_text = visual.TextStim(
    win,
    text="",
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
    units=UNITS,
)

keymap_center = (0.0, KEYMAP_BASE_Y)
top_row_y = KEYMAP_ROW_OFFSET
bottom_row_y = -KEYMAP_ROW_OFFSET
raw_key_offsets = {
    "n": (-0.6 * KEYMAP_DISTANCE, bottom_row_y),
    "j": (0.0, top_row_y),
    "k": (1.0 * KEYMAP_DISTANCE, top_row_y),
}
mean_x = sum(v[0] for v in raw_key_offsets.values()) / 3
mean_y = sum(v[1] for v in raw_key_offsets.values()) / 3
key_offsets = {
    key: (xy[0] - mean_x, xy[1] - mean_y)
    for key, xy in raw_key_offsets.items()
}

key_to_color = {key: color for color, key in COLOR_KEYS.items()}
keymap_stims = []
for key in ["n", "j", "k"]:
    offset = key_offsets[key]
    pos = (keymap_center[0] + offset[0], keymap_center[1] + offset[1])
    square = visual.Rect(
        win,
        width=KEYMAP_SQUARE_SIZE,
        height=KEYMAP_SQUARE_SIZE,
        pos=pos,
        fillColor=COLORS[key_to_color[key]],
        fillColorSpace=COLOR_SPACE,
        lineColor=None,
    )
    label = visual.TextStim(
        win,
        text=key.upper(),
        pos=pos,
        height=KEYMAP_TEXT_HEIGHT,
        color=COLORS["white"],
        colorSpace=COLOR_SPACE,
    )
    keymap_stims.append((square, label))


def draw_focal_pm_marker(win, pos, style, reward_value):
    """Draw an orange focal PM feature on a task-colored circle."""
    orange = COLORS["orange"]

    if style == "inner_dot":
        visual.Circle(
            win,
            radius=FOCAL_PM_INNER_DOT_RADIUS,
            pos=pos,
            fillColor=orange,
            lineColor=None,
            fillColorSpace=COLOR_SPACE,
            edges=64,
        ).draw()
        return

    if style == "center_ring":
        visual.Circle(
            win,
            radius=FOCAL_PM_RING_RADIUS,
            pos=pos,
            fillColor=None,
            lineColor=orange,
            lineColorSpace=COLOR_SPACE,
            lineWidth=FOCAL_PM_RING_LINE_WIDTH,
            edges=128,
        ).draw()
        return

    if style == "small_patch":
        patch_pos = (pos[0] + FOCAL_PM_PATCH_OFFSET, pos[1])
        visual.Circle(
            win,
            radius=FOCAL_PM_PATCH_RADIUS,
            pos=patch_pos,
            fillColor=orange,
            lineColor=None,
            fillColorSpace=COLOR_SPACE,
            edges=64,
        ).draw()
        return

    if style == "halo":
        visual.Circle(
            win,
            radius=FOCAL_PM_HALO_RADIUS,
            pos=pos,
            fillColor=None,
            lineColor=orange,
            lineColorSpace=COLOR_SPACE,
            lineWidth=FOCAL_PM_HALO_LINE_WIDTH,
            edges=128,
        ).draw()
        return

    if style == "marker_bg":
        visual.Circle(
            win,
            radius=FOCAL_PM_MARKER_BG_RADIUS,
            pos=pos,
            fillColor=orange,
            lineColor=None,
            fillColorSpace=COLOR_SPACE,
            edges=64,
        ).draw()
        if reward_value > 0:
            visual.TextStim(
                win,
                text=str(reward_value),
                pos=pos,
                color=COLORS["white"],
                colorSpace=COLOR_SPACE,
                height=REWARD_TEXT_HEIGHT,
            ).draw()
        return

    raise ValueError(f"Unknown focal PM style: {style}")


def _confirm_exit_or_continue():
    esc_confirm_text.draw()
    win.flip()
    keys = event.waitKeys(keyList=[QUIT_KEY, START_KEY])
    return bool(keys and keys[0] == QUIT_KEY)


def _wait_space_or_exit():
    while True:
        keys = event.waitKeys(keyList=[START_KEY, QUIT_KEY])
        if not keys:
            continue
        if keys[0] == START_KEY:
            return True
        if keys[0] == QUIT_KEY and _confirm_exit_or_continue():
            return False


def _show_instruction_text(text: str):
    instructions.setText(text)
    instructions.draw()
    win.flip()
    return _wait_space_or_exit()


def _trials_in_block(block_number):
    if block_number == BURNIN_BLOCK_NUMBER:
        return BURNIN_TRIALS_PER_BLOCK
    return _block_trial_counts.get(block_number, TRIALS_PER_BLOCK)


def _set_feedback4_text(trial):
    current_block = trial["block"]
    trial_in_block = trial["trial_in_block"]
    if trial.get("burn_in_block"):
        feedback4.setText(
            "Burn-in     Trial  "
            + str(trial_in_block)
            + " / "
            + str(BURNIN_TRIALS_PER_BLOCK)
        )
        return

    n_in_block = _trials_in_block(current_block)
    feedback4.setText(
        "Block  "
        + str(current_block)
        + " / "
        + str(SESSION_N_BLOCKS)
        + "     Trial  "
        + str(trial_in_block)
        + " / "
        + str(n_in_block)
    )


# =============================================================================
# EXPERIMENT START
# =============================================================================

if not _show_instruction_text(_load_session_welcome_instruction(SESSION)):
    win.close()
    core.quit()

if INCLUDE_BURNIN:
    if not _show_instruction_text(_load_instruction("instruction burnin intro.txt")):
        win.close()
        core.quit()

cum_reward = 0.0
prev_block = None
completed_normally = True

for trial in trials:
    current_block = trial["block"]
    if prev_block is not None and current_block != prev_block:
        if prev_block == BURNIN_BLOCK_NUMBER and current_block == 1:
            if not _show_instruction_text(_load_instruction("instruction burnin.txt")):
                completed_normally = False
                break
        else:
            block_break_text.setText(
                _load_instruction(
                    "instruction block break.txt",
                    prev_block=prev_block,
                    next_block=current_block,
                    n_blocks=SESSION_N_BLOCKS,
                )
            )
            block_break_text.draw()
            win.flip()
            if not _wait_space_or_exit():
                completed_normally = False
                break

    trial_colors = trial["trial_colors"]

    fixation.draw()
    win.flip()
    core.wait(FIXATION_TIME)

    event.clearEvents()

    for i, position_name in enumerate(POSITION_NAMES):
        pos = POSITIONS[position_name]
        normal_color = trial_colors[i]
        reward_value = trial["reward_values"][i]
        is_focal_pm_target = (
            trial["is_pm_trial"]
            and trial["pm_trial_kind"] == "focal"
            and position_name == trial["pm_position"]
        )
        is_nonfocal_pm_target = (
            trial["is_pm_trial"]
            and trial["pm_trial_kind"] == "nonfocal"
            and position_name == trial["pm_position"]
        )
        focal_pm_style = trial.get("focal_pm_style", FOCAL_PM_STYLE)

        outer_circle = visual.Circle(
            win,
            radius=CIRCLE_RADIUS,
            pos=pos,
            fillColor=COLORS[normal_color],
            lineColor=None if is_nonfocal_pm_target else COLORS["white"],
            lineColorSpace=COLOR_SPACE if not is_nonfocal_pm_target else None,
            lineWidth=0 if is_nonfocal_pm_target else BORDER_LINE_WIDTH,
            fillColorSpace=COLOR_SPACE,
            edges=128,
        )
        inner_circle = visual.Circle(
            win,
            radius=INNER_CIRCLE_RADIUS,
            pos=pos,
            fillColor=COLORS["white"],
            lineColor=None,
            fillColorSpace=COLOR_SPACE,
            edges=128,
        )
        reward_text = visual.TextStim(
            win,
            text=str(reward_value) if reward_value > 0 else "",
            pos=pos,
            color=COLORS["black"],
            colorSpace=COLOR_SPACE,
            height=REWARD_TEXT_HEIGHT,
        )

        outer_circle.draw()
        if is_focal_pm_target and focal_pm_style in ("center_ring", "halo"):
            draw_focal_pm_marker(win, pos, focal_pm_style, reward_value)
        inner_circle.draw()
        if is_focal_pm_target and focal_pm_style == "marker_bg":
            draw_focal_pm_marker(win, pos, focal_pm_style, reward_value)
        elif is_focal_pm_target and focal_pm_style in ("inner_dot", "small_patch"):
            draw_focal_pm_marker(win, pos, focal_pm_style, reward_value)
            reward_text.draw()
        else:
            reward_text.draw()

        if is_nonfocal_pm_target:
            for dash_start in range(0, 360, 24):
                angle1 = math.radians(dash_start)
                angle2 = math.radians(dash_start + 12)
                x1 = pos[0] + CIRCLE_RADIUS * math.cos(angle1)
                y1 = pos[1] + CIRCLE_RADIUS * math.sin(angle1)
                x2 = pos[0] + CIRCLE_RADIUS * math.cos(angle2)
                y2 = pos[1] + CIRCLE_RADIUS * math.sin(angle2)
                visual.Line(
                    win,
                    start=(x1, y1),
                    end=(x2, y2),
                    lineColor=COLORS["white"],
                    lineColorSpace=COLOR_SPACE,
                    lineWidth=DASHED_OUTLINE_LINE_WIDTH,
                ).draw()

    if DISPLAY_CONFIG["show_color_keymap"]:
        for square, label in keymap_stims:
            square.draw()
            label.draw()

    clock = core.Clock()
    win.flip()
    clock.reset()
    keys = event.waitKeys(
        keyList=ALL_RESPONSE_KEYS,
        maxWait=MAX_RESPONSE_TIME,
        timeStamped=clock,
    )

    max_reward_ccrp = max(trial["reward_values"]) if trial["reward_values"] else 0
    is_pm_trial = trial["is_pm_trial"]
    actual_reward = 0
    pressed_key = None
    rt = None
    timed_out = keys is None

    if timed_out:
        rt = MAX_RESPONSE_TIME * 1000
    else:
        pressed_key, rt_seconds = keys[0]
        rt = rt_seconds * 1000

    if pressed_key == QUIT_KEY:
        if _confirm_exit_or_continue():
            completed_normally = False
            break
        prev_block = current_block
        continue

    if timed_out:
        max_reward = PM_REWARD if is_pm_trial else max_reward_ccrp
        actual_reward = 0
    elif is_pm_trial:
        max_reward = PM_REWARD
        if pressed_key == PM_KEY:
            actual_reward = PM_REWARD
        elif pressed_key in key_to_color:
            selected_color = key_to_color[pressed_key]
            selected_position_index = trial_colors.index(selected_color)
            actual_reward = trial["reward_values"][selected_position_index]
        else:
            actual_reward = 0
    else:
        max_reward = max_reward_ccrp
        if pressed_key == PM_KEY:
            actual_reward = 0
        elif pressed_key in key_to_color:
            selected_color = key_to_color[pressed_key]
            selected_position_index = trial_colors.index(selected_color)
            actual_reward = trial["reward_values"][selected_position_index]
        else:
            actual_reward = 0

    cum_reward += actual_reward * REWARD_MONEY_FACTOR
    cum_reward = round(cum_reward, 2)

    if timed_out:
        feedback1.setText(TOO_SLOW_TEXT)
        feedback1.bold = True
    else:
        feedback1.setText(str(actual_reward) + " / " + str(max_reward))
        feedback1.bold = False
    feedback1.setColor(FEEDBACK_TEXT_COLOR)
    feedback2.setText("%.2f DKK" % cum_reward)
    feedback3.setText(("%5.0f" % rt + " ms") if rt is not None else "")
    _set_feedback4_text(trial)

    feedback1.draw()
    feedback2.draw()
    feedback3.draw()
    feedback4.draw()
    fixation.draw()
    win.flip()
    core.wait(FEEDBACK_WAIT_TIME)

    win.flip()
    core.wait(ITI_TIME)
    prev_block = current_block


# =============================================================================
# END
# =============================================================================

if completed_normally:
    end_text.draw()
    win.flip()
    event.waitKeys()

win.close()
core.quit()
