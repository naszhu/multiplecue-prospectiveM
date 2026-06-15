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

# Debug PM smoke session (12 trials). Does not apply to session 1 (center single-cue training).
DEBUG_CONFIG = {
    "enabled": False,
}

# Display / monitor (match multiplecue-responsebox/exp/testmain.py paradigm)
WIN_SIZE_PIX = (1920, 1080)
FULL_SCREEN = False
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60
USE_UNITS = "deg"
CIRCLE_EDGES = 200

# Paradigm StimFactor=0.04 sizing (no extra display scale factors).
STIM_FACTOR = 0.04
INSTRUCTION_WRAP_WIDTH_DEG = 800 * STIM_FACTOR

# Cue disk sizes (ColorTargetSize=20*SF, CueBoxSize/2=8.75*SF, CueTextSize=14*SF).
CUE_OUTER_RADIUS_DEG = 20 * STIM_FACTOR
CUE_INNER_RADIUS_DEG = 8.75 * STIM_FACTOR
CUE_TEXT_HEIGHT_DEG = 14 * STIM_FACTOR

# Color-key legend (ResponseColorSize=30*SF, ResponseColorDistance=50*SF).
RESPONSE_COLOR_SIZE_DEG = 30 * STIM_FACTOR
RESPONSE_COLOR_DISTANCE_DEG = 50 * STIM_FACTOR
KEYMAP_TEXT_HEIGHT_DEG = 0.55 * RESPONSE_COLOR_SIZE_DEG
KEYMAP_GAP_BELOW_TRIANGLE_ROW_UNITS = 0.6 * 3  # paradigm row_h ratio × 3 below lowest cue disk

# Triangle cue positions (paradigm-style coordinates * STIM_FACTOR).
# Top (0, 60*SF); bottom pair at y=-50*SF, x=±60*SF.
_TRIANGLE_TOP_Y_DEG = 60 * STIM_FACTOR
_TRIANGLE_BOTTOM_Y_DEG = -50 * STIM_FACTOR
_TRIANGLE_BOTTOM_X_DEG = 60 * STIM_FACTOR
POSITIONS = {
    "top": (0.0, _TRIANGLE_TOP_Y_DEG),
    "bottom_left": (-_TRIANGLE_BOTTOM_X_DEG, _TRIANGLE_BOTTOM_Y_DEG),
    "bottom_right": (_TRIANGLE_BOTTOM_X_DEG, _TRIANGLE_BOTTOM_Y_DEG),
}
POSITION_NAMES = list(POSITIONS.keys())
N_POSITIONS = len(POSITION_NAMES)

# Aliases used in the trial loop (same names as paradigm).
CIRCLE_RADIUS = CUE_OUTER_RADIUS_DEG
INNER_CIRCLE_RADIUS = CUE_INNER_RADIUS_DEG
REWARD_TEXT_HEIGHT = CUE_TEXT_HEIGHT_DEG

FOCAL_PM_INNER_DOT_RADIUS = 3.5 * STIM_FACTOR
FOCAL_PM_RING_RADIUS = (CUE_OUTER_RADIUS_DEG + CUE_INNER_RADIUS_DEG) / 2
FOCAL_PM_RING_LINE_WIDTH = 5
FOCAL_PM_PATCH_RADIUS = 5 * STIM_FACTOR
FOCAL_PM_PATCH_OFFSET = 0.55 * CUE_OUTER_RADIUS_DEG
FOCAL_PM_HALO_RADIUS = CUE_OUTER_RADIUS_DEG * 1.08
FOCAL_PM_HALO_LINE_WIDTH = 7
FOCAL_PM_MARKER_BG_RADIUS = CUE_INNER_RADIUS_DEG * 0.72
FOCAL_PM_STYLE = "center_ring"

BORDER_LINE_WIDTH = 4
DASHED_OUTLINE_LINE_WIDTH = 5

MONITOR_NAME = "testmain_demo_monitor"

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


def _lowest_cue_bottom_y_deg(*, single_center: bool = False) -> float:
    """Lowest point of the visible cue disk(s)."""
    if single_center:
        return CENTER_POSITION[1] - CUE_OUTER_RADIUS_DEG
    return min(pos[1] for pos in POSITIONS.values()) - CUE_OUTER_RADIUS_DEG


def _njk_keymap_positions(*, single_center: bool = False) -> dict:
    """
    NJK keyboard color-key legend below the cues.

    Geometry (d = RESPONSE_COLOR_DISTANCE_DEG):
      - J and K on the top row; K is d to the right of J.
      - N on the bottom row, d left of J (horizontal N–J = d).
      - Vertical row spacing = d (same as horizontal J–K and N–J).
      - Top row sits KEYMAP_GAP_BELOW_TRIANGLE_ROW_UNITS * d below the lowest cue disk.
    """
    d = RESPONSE_COLOR_DISTANCE_DEG
    row_spacing = d
    gap_below_cues = d * KEYMAP_GAP_BELOW_TRIANGLE_ROW_UNITS
    top_row_y = _lowest_cue_bottom_y_deg(single_center=single_center) - gap_below_cues
    bottom_row_y = top_row_y - row_spacing
    return {
        "j": (0.0, top_row_y),
        "k": (d, top_row_y),
        "n": (-d, bottom_row_y),
    }


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
    cfg = {**DEFAULT_DISPLAY, **SESSION_DISPLAY_OVERRIDES.get(session, {})}
    # Session 1: one single-cue disk at screen center (match testmain.py session 1).
    if session == 1:
        cfg.update(single_center=True, triangle_layout=False, show_color_keymap=True)
    return cfg


def get_session_generation_config(session: int) -> dict:
    """Trial-generation options per session (cue conditions, center layout)."""
    if session == 1:
        defaults = {
            "cue_conditions": SINGLE_CUE_CONDITIONS,
            "single_center": True,
            "n_cue_conditions": len(SINGLE_CUE_CONDITIONS),
        }
    else:
        defaults = {
            "cue_conditions": CUE_CONDITIONS,
            "single_center": False,
            "n_cue_conditions": N_CUE_CONDITIONS,
        }
    return {**defaults, **SESSION_GENERATION_OVERRIDES.get(session, {})}


CUE_CONDITIONS = [
    {"values": (1,), "label": "(1)"},
    {"values": (2,), "label": "(2)"},
    {"values": (3,), "label": "(3)"},
    {"values": (1, 2), "label": "(1,2)"},
    {"values": (1, 3), "label": "(1,3)"},
    {"values": (2, 3), "label": "(2,3)"},
]
SINGLE_CUE_CONDITIONS = CUE_CONDITIONS[:3]
CENTER_POSITION = (0.0, 0.0)
CENTER_POSITION_NAME = "center"
SESSION_GENERATION_OVERRIDES = {}


def _pool_for_cue_condition(cue_condition: dict, *, center: bool = False) -> list:
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

    # Session 1: one stimulus at center; only position 0 used (match testmain cfg["center"]).
    if center:
        reward_value = reward_values[0]
        out = []
        for color in all_colors:
            position_to_color = {i: color if i == 0 else None for i in range(N_POSITIONS)}
            position_to_reward = {i: reward_value if i == 0 else 0 for i in range(N_POSITIONS)}
            out.append(make_variant(position_to_color, position_to_reward))
        return out

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


def _cue_pools_for_session(session_number: int) -> list:
    gen = get_session_generation_config(session_number)
    return [
        _pool_for_cue_condition(c, center=gen["single_center"])
        for c in gen["cue_conditions"]
    ]


def _variant_to_lists(variant: dict, *, single_center: bool = False):
    """Convert pool variant maps to position-ordered lists."""
    if single_center:
        return (
            [variant["position_to_reward"][0], 0, 0],
            [variant["position_to_color"][0], "", ""],
            variant["cue_condition"],
        )
    reward_values = [variant["position_to_reward"][i] for i in range(N_POSITIONS)]
    trial_colors = [variant["position_to_color"][i] for i in range(N_POSITIONS)]
    return reward_values, trial_colors, variant["cue_condition"]


def _apply_variant_to_stub(stub: dict, variant: dict, *, single_center: bool = False):
    reward_values, trial_colors, cue_condition = _variant_to_lists(
        variant, single_center=single_center
    )
    stub["reward_values"] = reward_values
    stub["trial_colors"] = trial_colors
    stub["cue_condition"] = cue_condition
    stub["single_center"] = single_center


def _ongoing_reps_for_cue(cue_index: int, session_phase: str, n_cue_conditions: int) -> int:
    if session_phase in ("focal_pm", "nonfocal_pm"):
        base = ONGOING_PER_BLOCK_PM_PHASE // n_cue_conditions
        remainder = ONGOING_PER_BLOCK_PM_PHASE % n_cue_conditions
    else:
        base = TRIALS_PER_BLOCK // n_cue_conditions
        remainder = TRIALS_PER_BLOCK % n_cue_conditions
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
    session_number: int,
    *,
    burn_in_block: int = 0,
) -> list:
    """Build one block: cue-balanced stubs, pool draw per stub, within-block shuffle."""
    gen = get_session_generation_config(session_number)
    cue_conditions = gen["cue_conditions"]
    single_center = gen["single_center"]
    cue_pools = _cue_pools_for_session(session_number)
    pm_positions = [CENTER_POSITION_NAME] if single_center else POSITION_NAMES

    block_trials = []
    has_pm = session_phase in ("focal_pm", "nonfocal_pm")
    pm_kind = _pm_trial_kind_for_phase(session_phase)
    n_cue_conditions = gen["n_cue_conditions"]

    for cue_index, _cue_condition in enumerate(cue_conditions):
        pool = cue_pools[cue_index]
        n_ongoing = _ongoing_reps_for_cue(cue_index, session_phase, n_cue_conditions)

        if has_pm:
            pm_stub = {
                "session_phase": session_phase,
                "is_pm_trial": True,
                "pm_trial_kind": pm_kind,
                "pm_position": rng.choice(pm_positions),
                "warm_up": 0,
                "burn_in_block": burn_in_block,
            }
            _apply_variant_to_stub(pm_stub, rng.choice(pool), single_center=single_center)
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
            _apply_variant_to_stub(ongoing_stub, rng.choice(pool), single_center=single_center)
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
        burnin_block = _make_block(rng, session_phase, session_number, burn_in_block=1)
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
        block_trials = _make_block(rng, session_phase, session_number, burn_in_block=0)
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
            pool = _pool_for_cue_condition(_cue_condition, center=False)
            stub = {
                "session_phase": session_phase,
                "is_pm_trial": True,
                "pm_trial_kind": pm_kind,
                "pm_position": rng.choice(POSITION_NAMES),
                "warm_up": 0,
                "burn_in_block": 0,
            }
            _apply_variant_to_stub(stub, rng.choice(pool), single_center=False)
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

if DEBUG_CONFIG["enabled"] and SESSION != 1:
    # PM smoke test (sessions 2+ only). Session 1 always uses center single-cue training.
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
mon.setSizePix(WIN_SIZE_PIX)
mon.setWidth(MONITOR_WIDTH_CM)
mon.setDistance(MONITOR_DISTANCE_CM)

win = visual.Window(
    size=WIN_SIZE_PIX,
    fullscr=FULL_SCREEN,
    units=USE_UNITS,
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
    units=USE_UNITS,
)

feedback1 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK1_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=USE_UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback2 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK2_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=USE_UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback3 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK3_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=USE_UNITS,
    opacity=STIMULUS_OPACITY,
)
feedback4 = visual.TextStim(
    win,
    text="",
    pos=FEEDBACK4_POS_DEG,
    height=FEEDBACK_LETTER_SIZE_DEG * 0.2,
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    units=USE_UNITS,
    opacity=STIMULUS_OPACITY,
)
end_text = visual.TextStim(
    win,
    text=_load_instruction("instruction end.txt"),
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    units=USE_UNITS,
)
esc_confirm_text = visual.TextStim(
    win,
    text="Press ESC again to exit\n\nPress SPACE to continue",
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    units=USE_UNITS,
)
block_break_text = visual.TextStim(
    win,
    text="",
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
    units=USE_UNITS,
)

keymap_positions = _njk_keymap_positions(
    single_center=DISPLAY_CONFIG.get("single_center", False)
)
key_to_color = {key: color for color, key in COLOR_KEYS.items()}
keymap_stims = []
for key in ["n", "j", "k"]:
    pos = keymap_positions[key]
    square = visual.Rect(
        win,
        width=RESPONSE_COLOR_SIZE_DEG,
        height=RESPONSE_COLOR_SIZE_DEG,
        pos=pos,
        fillColor=COLORS[key_to_color[key]],
        fillColorSpace=COLOR_SPACE,
        lineColor=None,
        units=USE_UNITS,
    )
    label = visual.TextStim(
        win,
        text=key.upper(),
        pos=pos,
        height=KEYMAP_TEXT_HEIGHT_DEG,
        color=COLORS["white"],
        colorSpace=COLOR_SPACE,
        units=USE_UNITS,
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

    single_center = trial.get("single_center")
    if single_center is None:
        single_center = DISPLAY_CONFIG.get("single_center", False)
    if single_center:
        cue_slots = [(CENTER_POSITION_NAME, CENTER_POSITION, 0)]
    else:
        cue_slots = [
            (name, POSITIONS[name], i) for i, name in enumerate(POSITION_NAMES)
        ]

    for position_name, pos, color_index in cue_slots:
        normal_color = trial_colors[color_index]
        reward_value = trial["reward_values"][color_index]
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
            edges=CIRCLE_EDGES,
        )
        inner_circle = visual.Circle(
            win,
            radius=INNER_CIRCLE_RADIUS,
            pos=pos,
            fillColor=COLORS["white"],
            lineColor=None,
            fillColorSpace=COLOR_SPACE,
            edges=CIRCLE_EDGES,
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
            if single_center:
                actual_reward = (
                    trial["reward_values"][0]
                    if selected_color == trial_colors[0]
                    else 0
                )
            else:
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
            if single_center:
                actual_reward = (
                    trial["reward_values"][0]
                    if selected_color == trial_colors[0]
                    else 0
                )
            else:
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
