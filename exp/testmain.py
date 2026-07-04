"""
Prospective-memory multiple-cue experiment (full 26-session structure).

Run one session per launch. Trial schedule is pre-built via trial_schedule.py.
"""

from __future__ import annotations

import csv
import math
import random
import time
from itertools import permutations
from pathlib import Path

from psychopy import visual, core, event, monitors, gui

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

from trial_schedule import (
    N_BLOCKS_PER_SESSION,
    N_PRACTICE_SESSIONS,
    N_BASELINE_SESSIONS,
    N_PM_SESSIONS_PER_PHASE,
    TOTAL_SESSIONS,
    TrialPlan,
    apply_debug_pm_to_first_n,
    block_sizes_for_session,
    build_session_schedule,
    display_profile_for_session,
    get_pm_phase_order,
    print_trial_schedule,
    resolve_session_phase,
    should_include_burnin_block,
    trial_plan_to_log_dict,
    validate_session_schedule,
)

EXP_DIR = Path(__file__).resolve().parent
INSTRUCTION_DIR = EXP_DIR / "Instructions"
DATA_DIR = EXP_DIR / "data_written"
PARTICIPANT_COLOR_KEY_MAPPING_PATH = EXP_DIR / "participant_color_key_mapping.csv"

NUM_COLOR_SLOTS = 3
MAX_PARTICIPANT_ID = 100
COLOR_LETTER_TO_ID = {"r": 1, "b": 2, "g": 3}
ALL_COLOR_KEY_MAPPINGS = sorted({"".join(p) for p in permutations("rgb")})
COLOR_KEY_MAPPING_AUTO_CHOICE = "as assigned"
COLOR_KEY_MAPPING_DIALOG_CHOICES = [COLOR_KEY_MAPPING_AUTO_CHOICE] + ALL_COLOR_KEY_MAPPINGS

# =============================================================================
# DISPLAY / TIMING
# =============================================================================

BASE_WINDOW_SIZE = (1000, 700)
WINDOW_SCALE = 1.35
WINDOW_SIZE = (
    int(BASE_WINDOW_SIZE[0] * WINDOW_SCALE),
    int(BASE_WINDOW_SIZE[1] * WINDOW_SCALE),
)
FULL_SCREEN = False
BACKGROUND_COLOR = (128, 128, 128)
COLOR_SPACE = "rgb255"
UNITS = "deg"

FIXATION_TIME = 0.5
MAX_RESPONSE_TIME = 3.0
FEEDBACK_WAIT_TIME = 1.5
ITI_TIME = 0.3
REWARD_MONEY_FACTOR = 0.05
STIMULUS_OPACITY = 1.0

# Stimulus sizing and layout (same paradigm formulas as multiplecue-responsebox/exp/testmain.py)
STIM_FACTOR = 0.04
CUE_OUTER_RADIUS_DEG = 20 * STIM_FACTOR   # ColorTargetSize = 0.8 deg
CUE_INNER_RADIUS_DEG = 8.75 * STIM_FACTOR  # CueBoxSize/2 = 0.35 deg
CUE_TEXT_HEIGHT_DEG = 14 * STIM_FACTOR    # CueTextSize = 0.56 deg
CIRCLE_EDGES = 200
MONITOR_NAME = "pm_ccrp_monitor"
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60

BORDER_LINE_WIDTH = 2.5
DASHED_OUTLINE_LINE_WIDTH = 2.5

FOCAL_PM_RING_RADIUS = (CUE_OUTER_RADIUS_DEG + CUE_INNER_RADIUS_DEG) / 2
FOCAL_PM_RING_LINE_WIDTH = 2.5
FOCAL_PM_STYLE = "center_ring"

# 3-position triangle: paradigm coefficients * StimFactor (not scaled separately)
TRIANGLE_TOP_Y = 60 * STIM_FACTOR
TRIANGLE_BOTTOM_Y = -50 * STIM_FACTOR
TRIANGLE_BOTTOM_X = 60 * STIM_FACTOR
POSITIONS = [
    (0.0, TRIANGLE_TOP_Y),
    (-TRIANGLE_BOTTOM_X, TRIANGLE_BOTTOM_Y),
    (TRIANGLE_BOTTOM_X, TRIANGLE_BOTTOM_Y),
]
POSITION_NAMES = ["top", "bottom_left", "bottom_right"]

COLORS = {
    "red": (220, 50, 50),
    "blue": (50, 100, 220),
    "green": (50, 180, 80),
    "orange": (240, 150, 30),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}
COLOR_ID_TO_NAME = {1: "red", 2: "blue", 3: "green"}

# Fixed response slots (right hand): index / middle / ring → N J K or pins 8 9 10
RESPONSE_SLOT_KEYS = ["n", "j", "k"]
SELF_MADE_COLOR_SLOT_PINS = ["8", "9", "10"]

PM_KEY = "d"
START_KEY = "space"
QUIT_KEY = "escape"

RESPONSE_DEVICE_KEYBOARD = "keyboard"
RESPONSE_DEVICE_SELF_MADE = "self-made-response-box"
DEFAULT_RESPONSE_DEVICE = RESPONSE_DEVICE_SELF_MADE
CEDRUS_VID = 0x0403
CEDRUS_PID = 0x6001
SERIAL_BAUDRATE = 115200

# PM = left middle finger (CCRP slot C0, pin 6). Color pins are slot-fixed, not color-fixed.
SELF_MADE_PM_PIN = "6"
SELF_MADE_PIN_TO_LOGICAL_KEY = {
    SELF_MADE_PM_PIN: PM_KEY,
    **dict(zip(SELF_MADE_COLOR_SLOT_PINS, RESPONSE_SLOT_KEYS)),
}

ALL_RESPONSE_KEYS = RESPONSE_SLOT_KEYS + [PM_KEY, QUIT_KEY]
PM_REWARD = 5

# Set after session dialog from participant_color_key_mapping.csv
COLOR_KEY_MAPPING = "rgb"
COLOR_KEY_MAPPING_ASSIGNED = "rgb"
COLOR_KEY_MAPPING_OVERRIDDEN = False
SLOT_TO_COLOR_ID: list[int] = [1, 2, 3]
KEY_TO_COLOR_ID: dict[str, int] = {}


def _load_participant_color_key_mapping_table() -> dict[str, str]:
    path = PARTICIPANT_COLOR_KEY_MAPPING_PATH
    if not path.is_file():
        raise SystemExit(f"Missing color-key mapping table: {path}")
    table: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        if (
            reader.fieldnames is None
            or "participant_id" not in reader.fieldnames
            or "color_key_mapping" not in reader.fieldnames
        ):
            raise SystemExit(f"Invalid mapping table columns in {path}")
        for row in reader:
            pid = str(row["participant_id"]).strip()
            mapping = str(row["color_key_mapping"]).strip().lower()
            if mapping not in ALL_COLOR_KEY_MAPPINGS:
                raise SystemExit(f"Invalid mapping {mapping!r} for participant {pid} in {path}")
            table[pid] = mapping
    for p in range(1, MAX_PARTICIPANT_ID + 1):
        if str(p) not in table:
            raise SystemExit(f"Mapping table missing participant_id {p} in {path}")
    return table


PARTICIPANT_COLOR_KEY_MAPPING = _load_participant_color_key_mapping_table()


def _slot_color_ids(mapping: str) -> list[int]:
    return [COLOR_LETTER_TO_ID[c] for c in mapping.lower()]


def _validate_color_key_mapping(mapping: str) -> str:
    mapping = str(mapping).strip().lower()
    if mapping not in ALL_COLOR_KEY_MAPPINGS:
        raise SystemExit(f"Invalid color key mapping: {mapping!r}")
    return mapping


def _assigned_color_key_mapping(participant: str) -> str:
    if participant == "test":
        return random.choice(ALL_COLOR_KEY_MAPPINGS)
    return PARTICIPANT_COLOR_KEY_MAPPING[participant]


def _resolve_color_key_mapping_from_dialog(
    participant: str, dialog_choice: str
) -> tuple[str, str, bool]:
    assigned = _assigned_color_key_mapping(participant)
    choice = str(dialog_choice).strip()
    if choice.lower() == COLOR_KEY_MAPPING_AUTO_CHOICE.lower():
        return assigned, assigned, False
    used = _validate_color_key_mapping(choice)
    return assigned, used, used != assigned


def _apply_color_key_mapping(mapping: str) -> None:
    global SLOT_TO_COLOR_ID, KEY_TO_COLOR_ID
    SLOT_TO_COLOR_ID = _slot_color_ids(mapping)
    KEY_TO_COLOR_ID = {
        RESPONSE_SLOT_KEYS[slot]: SLOT_TO_COLOR_ID[slot] for slot in range(NUM_COLOR_SLOTS)
    }


def _color_key_mapping_description(mapping: str, response_device: str) -> str:
    slot_colors = [COLOR_ID_TO_NAME[cid] for cid in _slot_color_ids(mapping)]
    order = ", ".join(slot_colors)
    if response_device == RESPONSE_DEVICE_KEYBOARD:
        keys = ", ".join(k.upper() for k in RESPONSE_SLOT_KEYS)
        return (
            f"Mapping {mapping}: slot colors left-to-right are {order} "
            f"on keys {keys} (N, J, K; right index, middle, ring)."
        )
    pins = ", ".join(SELF_MADE_COLOR_SLOT_PINS)
    return (
        f"Mapping {mapping}: self-made color pins left-to-right ({pins}) are {order}. "
        f"PM pin {SELF_MADE_PM_PIN} (left middle)."
    )

FEEDBACK_LETTER_SIZE_DEG = 50 * STIM_FACTOR
FEEDBACK1_POS_DEG = (0, 70 * STIM_FACTOR)
FEEDBACK2_POS_DEG = (0, -70 * STIM_FACTOR)
FEEDBACK3_POS_DEG = (0, -140 * STIM_FACTOR)
FEEDBACK4_POS_DEG = (0, -200 * STIM_FACTOR)
FEEDBACK_TEXT_COLOR = COLORS["white"]
INSTRUCTION_LETTER_SIZE_DEG = 0.6
INSTRUCTION_WRAP_WIDTH_DEG = 800 * STIM_FACTOR

RESPONSE_COLOR_SIZE_DEG = 30 * STIM_FACTOR
RESPONSE_COLOR_DISTANCE_DEG = 50 * STIM_FACTOR
COLOR_MAP_Y_DEG = -150 * STIM_FACTOR
COLOR_MAP_LAYOUT = "keyboard"  # "horizontal" or "keyboard" (responsebox options)


def _logical_key_from_response(pressed) -> str | None:
    """Normalize keyboard key or self-made pin to logical key (n/j/k/d) or escape."""
    if pressed is None:
        return None
    if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE:
        if pressed == QUIT_KEY:
            return QUIT_KEY
        return SELF_MADE_PIN_TO_LOGICAL_KEY.get(str(pressed))
    return pressed


def _find_self_made_response_box_port() -> str:
    if list_ports is not None:
        for port in list_ports.comports():
            if port.vid == CEDRUS_VID and port.pid == CEDRUS_PID:
                continue
            if port.device.startswith(("/dev/ttyACM", "/dev/ttyUSB")):
                return port.device
    return "/dev/ttyACM0"


def _open_self_made_response_box():
    if serial is None:
        raise SystemExit("pyserial is required for self-made-response-box.")

    port_name = _find_self_made_response_box_port()
    box = serial.Serial(port_name, baudrate=SERIAL_BAUDRATE, timeout=0.001)
    time.sleep(2.0)
    box.reset_input_buffer()
    print(f"Using {RESPONSE_DEVICE_SELF_MADE} on {port_name}.")
    return box


def _wait_for_self_made_response_box(box, clock, max_wait):
    buffer = ""
    start = clock.getTime()

    while clock.getTime() - start < max_wait:
        escape_keys = event.getKeys(keyList=[QUIT_KEY], timeStamped=clock)
        if escape_keys:
            return (QUIT_KEY, escape_keys[0][1], None)

        buffer += box.read(box.in_waiting or 1).decode("ascii", errors="ignore")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            parts = line.strip().split(",")
            if len(parts) != 2:
                continue

            pin, latency_us = parts
            if pin in SELF_MADE_PIN_TO_LOGICAL_KEY:
                return (pin, clock.getTime(), float(latency_us) / 1000)

    return None


def _color_map_positions(layout: str, n_slots: int) -> list[tuple[float, float]]:
    """Same geometry as multiplecue-responsebox/exp/testmain.py _color_map_positions."""
    d = RESPONSE_COLOR_DISTANCE_DEG
    base_y = COLOR_MAP_Y_DEG
    if layout == "horizontal":
        return [
            (d * (-n_slots / 2 + 0.5 + i), base_y)
            for i in range(n_slots)
        ]
    row_h = d * 0.6
    col_w = d * 1.4
    stagger = d * 0.35
    four = [
        (-col_w, base_y + row_h),
        (-col_w + stagger, base_y - row_h),
        (col_w, base_y + row_h),
        (col_w - stagger, base_y - row_h),
    ]
    if n_slots == 3:
        # NJK: bottom-left, top-left, top-right (C, D, K slots from 4-key keyboard layout)
        return [four[1], four[0], four[2]]
    return four[:n_slots]

EXPERIMENT_NAME = "PM_MCP"
CODE_VERSION = "1.0.0"

# Debug: run only first N trials, all forced to PM (role follows session phase assignment).
DEBUG_CONFIG = {
    "enabled": True,
    "n_trials": 10,
    "simulate_response_box": True,
}


# =============================================================================
# INSTRUCTIONS
# =============================================================================


def _load_instruction(filename: str) -> str:
    path = INSTRUCTION_DIR / filename
    if not path.exists():
        raise SystemExit(f"Instruction file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def instruction_file_for_session(session: int, kind: str) -> str:
    """Hook for per-session instruction files later; same files for all sessions now."""
    mapping = {
        "welcome": "PM welcome.txt",
        "focal_intro": "PM phase_focal_intro.txt",
        "nonfocal_intro": "PM phase_nonfocal_intro.txt",
        "block_break": "PM block_break.txt",
        "esc_confirm": "PM esc_confirm.txt",
        "end_session": "PM end_session.txt",
        "too_slow": "PM feedback_too_slow.txt",
    }
    return mapping[kind]


def is_first_session_of_pm_phase(session_number: int) -> bool:
    first_pm = N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS + 1
    second_pm = first_pm + N_PM_SESSIONS_PER_PHASE
    return session_number in (first_pm, second_pm)


# =============================================================================
# SESSION DIALOG
# =============================================================================

session_dlg = gui.Dlg(title="PM MCP Session")
session_dlg.addField("Participant", initial="1")
session_dlg.addField("Session", initial="1")
session_dlg.addField("First session of day?", initial="yes", choices=["yes", "no"])
session_dlg.addField("Participation day", initial="1")
session_dlg.addField(
    "Debug mode (first 10 trials = PM)?",
    initial="no" if not DEBUG_CONFIG["enabled"] else "yes",
    choices=["no", "yes"],
)
session_dlg.addField(
    "Response device",
    initial=DEFAULT_RESPONSE_DEVICE,
    choices=[RESPONSE_DEVICE_KEYBOARD, RESPONSE_DEVICE_SELF_MADE],
)
session_dlg.addField(
    "Color key mapping",
    initial=COLOR_KEY_MAPPING_AUTO_CHOICE,
    choices=COLOR_KEY_MAPPING_DIALOG_CHOICES,
    tip="Default uses table assignment (random for test). Pick a mapping only to override.",
)
dlg_data = session_dlg.show()
if not session_dlg.OK:
    core.quit()

PARTICIPANT = str(dlg_data[0]).strip()
SESSION = int(dlg_data[1])
FIRST_SESSION_OF_DAY = dlg_data[2] == "yes"
PARTICIPATION_DAY = int(dlg_data[3])
DEBUG_MODE = dlg_data[4] == "yes" or DEBUG_CONFIG["enabled"]
RESPONSE_DEVICE = dlg_data[5]

if PARTICIPANT == "test":
    PARTICIPANT_ID = 0
    _counterbalance_participant_id = 1
else:
    try:
        PARTICIPANT_ID = int(PARTICIPANT)
    except ValueError as exc:
        raise SystemExit(
            f"Participant must be 'test' or an integer from 1 to {MAX_PARTICIPANT_ID}."
        ) from exc
    if not 1 <= PARTICIPANT_ID <= MAX_PARTICIPANT_ID:
        raise SystemExit(f"Participant must be 1..{MAX_PARTICIPANT_ID}")
    _counterbalance_participant_id = PARTICIPANT_ID

COLOR_KEY_MAPPING_ASSIGNED, COLOR_KEY_MAPPING, COLOR_KEY_MAPPING_OVERRIDDEN = (
    _resolve_color_key_mapping_from_dialog(PARTICIPANT, dlg_data[6])
)
_apply_color_key_mapping(COLOR_KEY_MAPPING)
print(_color_key_mapping_description(COLOR_KEY_MAPPING, RESPONSE_DEVICE))

if not 1 <= SESSION <= TOTAL_SESSIONS:
    raise SystemExit(f"Session must be 1..{TOTAL_SESSIONS}")

PHASE_CONFIG = resolve_session_phase(SESSION, _counterbalance_participant_id)
PM_PHASE_ORDER = get_pm_phase_order(_counterbalance_participant_id)
PARTICIPANT_PARITY = "odd" if _counterbalance_participant_id % 2 == 1 else "even"
print(
    f"Participant {PARTICIPANT} ({PARTICIPANT_PARITY}): "
    f"PM order = {PM_PHASE_ORDER[0]} → {PM_PHASE_ORDER[1]}"
)
print(f"Session {SESSION}: running phase = {PHASE_CONFIG.session_phase}")
DISPLAY_PROFILE = display_profile_for_session(SESSION)
_schedule_participant = _counterbalance_participant_id if PARTICIPANT != "test" else 999
SCHEDULE_RNG_SEED = _schedule_participant * 1000 + SESSION
_schedule_rng = __import__("random").Random(SCHEDULE_RNG_SEED)
trial_data_list = build_session_schedule(PHASE_CONFIG, _schedule_rng)
if not DEBUG_MODE:
    validate_session_schedule(trial_data_list, PHASE_CONFIG)
else:
    trial_data_list = apply_debug_pm_to_first_n(
        trial_data_list,
        PHASE_CONFIG,
        n_trials=DEBUG_CONFIG["n_trials"],
        rng=_schedule_rng,
    )
    print(
        f"DEBUG MODE: running {len(trial_data_list)} trials; "
        f"all PM role = {PHASE_CONFIG.pm_trial_role or 'focal'}"
    )

# print_trial_schedule(trial_data_list)  # Uncomment to inspect full session schedule before run

BLOCK_SIZES = block_sizes_for_session(PHASE_CONFIG.trials_per_session, N_BLOCKS_PER_SESSION)
TOO_SLOW_TEXT = _load_instruction(instruction_file_for_session(SESSION, "too_slow"))

DATA_DIR.mkdir(parents=True, exist_ok=True)
csv_path = DATA_DIR / f"p{PARTICIPANT}_ses{SESSION}_trials.csv"

# =============================================================================
# WINDOW
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
    win, text="+", color=COLORS["white"], colorSpace=COLOR_SPACE, height=0.35
)

instruction_stim = visual.TextStim(
    win,
    text="",
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
    units=UNITS,
)

feedback1 = visual.TextStim(
    win, text="", pos=FEEDBACK1_POS_DEG, height=FEEDBACK_LETTER_SIZE_DEG,
    color=FEEDBACK_TEXT_COLOR, colorSpace=COLOR_SPACE, units=UNITS, opacity=STIMULUS_OPACITY,
)
feedback2 = visual.TextStim(
    win, text="", pos=FEEDBACK2_POS_DEG, height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR, colorSpace=COLOR_SPACE, units=UNITS, opacity=STIMULUS_OPACITY,
)
feedback3 = visual.TextStim(
    win, text="", pos=FEEDBACK3_POS_DEG, height=FEEDBACK_LETTER_SIZE_DEG * 0.6,
    color=FEEDBACK_TEXT_COLOR, colorSpace=COLOR_SPACE, units=UNITS, opacity=STIMULUS_OPACITY,
)
feedback4 = visual.TextStim(
    win, text="", pos=FEEDBACK4_POS_DEG, height=FEEDBACK_LETTER_SIZE_DEG * 0.2,
    color=FEEDBACK_TEXT_COLOR, colorSpace=COLOR_SPACE, units=UNITS, opacity=STIMULUS_OPACITY,
)

# Color-response legend: slot order follows counterbalanced COLOR_KEY_MAPPING
# Keyboard-style NJK legend (staggered like responsebox), same for keyboard and self-made box
color_map_positions = _color_map_positions(COLOR_MAP_LAYOUT, NUM_COLOR_SLOTS)
slot_color_names = [COLOR_ID_TO_NAME[cid] for cid in SLOT_TO_COLOR_ID]
keymap_stims = []
if RESPONSE_DEVICE == RESPONSE_DEVICE_KEYBOARD:
    for key, color_name, pos in zip(RESPONSE_SLOT_KEYS, slot_color_names, color_map_positions):
        square = visual.Rect(
            win,
            width=RESPONSE_COLOR_SIZE_DEG,
            height=RESPONSE_COLOR_SIZE_DEG,
            pos=pos,
            fillColor=COLORS[color_name],
            fillColorSpace=COLOR_SPACE,
            lineColor=None,
            units=UNITS,
        )
        label = visual.TextStim(
            win,
            text=key.upper(),
            pos=pos,
            height=CUE_TEXT_HEIGHT_DEG,
            color=COLORS["white"],
            colorSpace=COLOR_SPACE,
            units=UNITS,
        )
        keymap_stims.append((square, label))
else:
    for color_name, pos in zip(slot_color_names, color_map_positions):
        square = visual.Rect(
            win,
            width=RESPONSE_COLOR_SIZE_DEG,
            height=RESPONSE_COLOR_SIZE_DEG,
            pos=pos,
            fillColor=COLORS[color_name],
            fillColorSpace=COLOR_SPACE,
            lineColor=None,
            units=UNITS,
        )
        keymap_stims.append((square, None))


def draw_focal_pm_marker(pos):
    visual.Circle(
        win, radius=FOCAL_PM_RING_RADIUS, pos=pos, fillColor=None,
        lineColor=COLORS["orange"], lineColorSpace=COLOR_SPACE,
        lineWidth=FOCAL_PM_RING_LINE_WIDTH, edges=CIRCLE_EDGES,
    ).draw()


def draw_nonfocal_dashed_outline(pos):
    for dash_start in range(0, 360, 24):
        angle1 = math.radians(dash_start)
        angle2 = math.radians(dash_start + 12)
        x1 = pos[0] + CUE_OUTER_RADIUS_DEG * math.cos(angle1)
        y1 = pos[1] + CUE_OUTER_RADIUS_DEG * math.sin(angle1)
        x2 = pos[0] + CUE_OUTER_RADIUS_DEG * math.cos(angle2)
        y2 = pos[1] + CUE_OUTER_RADIUS_DEG * math.sin(angle2)
        visual.Line(
            win, start=(x1, y1), end=(x2, y2),
            lineColor=COLORS["white"], lineColorSpace=COLOR_SPACE,
            lineWidth=DASHED_OUTLINE_LINE_WIDTH,
        ).draw()


def _confirm_exit_or_continue() -> bool:
    instruction_stim.setText(_load_instruction(instruction_file_for_session(SESSION, "esc_confirm")))
    instruction_stim.draw()
    win.flip()
    keys = event.waitKeys(keyList=[QUIT_KEY, START_KEY])
    return bool(keys and keys[0] == QUIT_KEY)


def _wait_space_or_exit() -> bool:
    while True:
        keys = event.waitKeys(keyList=[START_KEY, QUIT_KEY])
        if not keys:
            continue
        if keys[0] == START_KEY:
            return True
        if keys[0] == QUIT_KEY and _confirm_exit_or_continue():
            return False


def _show_instruction_text(text: str) -> bool:
    instruction_stim.setText(text)
    instruction_stim.draw()
    win.flip()
    return _wait_space_or_exit()


def _trials_in_block(block_number: int) -> int:
    return BLOCK_SIZES[block_number - 1]


def _set_feedback4_text(trial: TrialPlan):
    feedback4.setText(
        "Block  "
        + str(trial.block)
        + " / "
        + str(N_BLOCKS_PER_SESSION)
        + "     Trial  "
        + str(trial.trial_in_block)
        + " / "
        + str(_trials_in_block(trial.block))
    )


def _draw_trial_stimulus(trial: TrialPlan):
    for pos_idx, pos in enumerate(POSITIONS):
        color_id = trial.position_to_color_id[pos_idx]
        color_name = COLOR_ID_TO_NAME[color_id]
        reward_value = trial.position_to_reward.get(pos_idx) or 0
        is_focal = trial.trial_pm_role == "focal" and trial.pm_position_idx == pos_idx
        is_nonfocal = trial.trial_pm_role == "nonfocal" and trial.pm_position_idx == pos_idx

        outer_circle = visual.Circle(
            win, radius=CUE_OUTER_RADIUS_DEG, pos=pos, fillColor=COLORS[color_name],
            lineColor=None if is_nonfocal else COLORS["white"],
            lineColorSpace=COLOR_SPACE if not is_nonfocal else None,
            lineWidth=0 if is_nonfocal else BORDER_LINE_WIDTH,
            fillColorSpace=COLOR_SPACE, edges=CIRCLE_EDGES,
        )
        inner_circle = visual.Circle(
            win, radius=CUE_INNER_RADIUS_DEG, pos=pos, fillColor=COLORS["white"],
            lineColor=None, fillColorSpace=COLOR_SPACE, edges=CIRCLE_EDGES,
        )
        reward_text = visual.TextStim(
            win, text=str(reward_value) if reward_value > 0 else "", pos=pos,
            color=COLORS["black"], colorSpace=COLOR_SPACE, height=CUE_TEXT_HEIGHT_DEG,
            units=UNITS,
        )
        outer_circle.draw()
        if is_focal:
            draw_focal_pm_marker(pos)
        inner_circle.draw()
        reward_text.draw()
        if is_nonfocal:
            draw_nonfocal_dashed_outline(pos)

    if DISPLAY_PROFILE.show_color_map:
        for square, label in keymap_stims:
            square.draw()
            if label is not None:
                label.draw()


def _score_trial(trial: TrialPlan, pressed_key, timed_out: bool):
    rewards = [trial.position_to_reward.get(i) or 0 for i in range(3)]
    max_reward_ccrp = max(rewards) if rewards else 0
    actual_reward = 0

    if trial.is_pm_trial:
        max_reward = PM_REWARD
        if not timed_out and pressed_key == PM_KEY:
            actual_reward = PM_REWARD
        elif not timed_out and pressed_key in KEY_TO_COLOR_ID:
            color_id = KEY_TO_COLOR_ID[pressed_key]
            for i in range(3):
                if trial.position_to_color_id[i] == color_id:
                    actual_reward = rewards[i]
                    break
    else:
        max_reward = max_reward_ccrp
        if not timed_out and pressed_key == PM_KEY:
            actual_reward = 0
        elif not timed_out and pressed_key in KEY_TO_COLOR_ID:
            color_id = KEY_TO_COLOR_ID[pressed_key]
            for i in range(3):
                if trial.position_to_color_id[i] == color_id:
                    actual_reward = rewards[i]
                    break

    return actual_reward, max_reward


# =============================================================================
# START
# =============================================================================

if not _show_instruction_text(_load_instruction(instruction_file_for_session(SESSION, "welcome"))):
    win.close()
    core.quit()

if is_first_session_of_pm_phase(SESSION) and PHASE_CONFIG.session_phase == "focal_pm":
    if not _show_instruction_text(_load_instruction(instruction_file_for_session(SESSION, "focal_intro"))):
        win.close()
        core.quit()
elif is_first_session_of_pm_phase(SESSION) and PHASE_CONFIG.session_phase == "nonfocal_pm":
    if not _show_instruction_text(_load_instruction(instruction_file_for_session(SESSION, "nonfocal_intro"))):
        win.close()
        core.quit()

if should_include_burnin_block(SESSION, FIRST_SESSION_OF_DAY, PARTICIPATION_DAY):
    pass  # hook for future burn-in block

serial_response_box = None
if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE and not (
    DEBUG_MODE and DEBUG_CONFIG.get("simulate_response_box", True)
):
    serial_response_box = _open_self_made_response_box()
elif RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE:
    print("DEBUG MODE: self-made response box not opened (simulate_response_box).")

cum_reward = 0.0
prev_block = None
completed_normally = True
csv_rows: list[dict] = []

for trial in trial_data_list:
    if prev_block is not None and trial.block != prev_block:
        break_text = _load_instruction(instruction_file_for_session(SESSION, "block_break"))
        break_text = break_text.format(
            prev_block=prev_block,
            next_block=trial.block,
            n_blocks=N_BLOCKS_PER_SESSION,
        )
        if not _show_instruction_text(break_text):
            completed_normally = False
            break

    fixation.draw()
    win.flip()
    core.wait(FIXATION_TIME)

    event.clearEvents()
    _draw_trial_stimulus(trial)
    clock = core.Clock()
    if serial_response_box is not None:
        serial_response_box.reset_input_buffer()
    win.flip()
    clock.reset()
    if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE and serial_response_box is not None:
        serial_response_box.write(b"S")
        serial_response_box.flush()
        box_response = _wait_for_self_made_response_box(
            serial_response_box, clock, MAX_RESPONSE_TIME
        )
        keys = [box_response] if box_response else None
    else:
        keys = event.waitKeys(
            keyList=ALL_RESPONSE_KEYS, maxWait=MAX_RESPONSE_TIME, timeStamped=clock
        )

    timed_out = keys is None
    pressed_raw = None
    pressed_key = None
    rt_ms = None
    rt_device_ms = None
    rt_computer_ms = None
    if not timed_out:
        pressed_raw = keys[0][0]
        response_time = keys[0][1]
        rt_computer_ms = response_time * 1000
        if len(keys[0]) > 2 and keys[0][2] is not None:
            rt_device_ms = keys[0][2]
        rt_ms = rt_device_ms if rt_device_ms is not None else rt_computer_ms
        pressed_key = _logical_key_from_response(pressed_raw)

    if pressed_key == QUIT_KEY:
        if _confirm_exit_or_continue():
            completed_normally = False
            break
        prev_block = trial.block
        continue

    actual_reward, max_reward = _score_trial(trial, pressed_key, timed_out)
    if timed_out:
        rt_ms = MAX_RESPONSE_TIME * 1000
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
    feedback3.setText(("%5.0f" % rt_ms + " ms") if rt_ms is not None else "")
    _set_feedback4_text(trial)
    for stim in (feedback1, feedback2, feedback3, feedback4):
        stim.draw()
    fixation.draw()
    win.flip()
    core.wait(FEEDBACK_WAIT_TIME)
    win.flip()
    core.wait(ITI_TIME)

    row = trial_plan_to_log_dict(trial)
    row.update({
        "ExperimentName": EXPERIMENT_NAME,
        "CodeVersion": CODE_VERSION,
        "Participant": PARTICIPANT,
        "ParticipantParity": PARTICIPANT_PARITY,
        "PmPhaseOrderFirst": PM_PHASE_ORDER[0],
        "PmPhaseOrderSecond": PM_PHASE_ORDER[1],
        "ColorKeyMapping": COLOR_KEY_MAPPING,
        "ColorKeyMappingAssigned": COLOR_KEY_MAPPING_ASSIGNED,
        "ColorKeyMappingOverridden": int(COLOR_KEY_MAPPING_OVERRIDDEN),
        "Session": SESSION,
        "SessionPhase": PHASE_CONFIG.session_phase,
        "DebugMode": int(DEBUG_MODE),
        "ResponseDevice": RESPONSE_DEVICE,
        "PressedRaw": pressed_raw or "",
        "PressedKey": pressed_key or "",
        "RT_ms": rt_ms,
        "RTComputer_ms": rt_computer_ms if rt_computer_ms is not None else "",
        "RTDevice_ms": rt_device_ms if rt_device_ms is not None else "",
        "ActualReward": actual_reward,
        "MaxReward": max_reward,
        "CumReward": cum_reward,
        "TimedOut": int(timed_out),
    })
    csv_rows.append(row)
    prev_block = trial.block

if csv_rows:
    with open(csv_path, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

if completed_normally:
    instruction_stim.setText(_load_instruction(instruction_file_for_session(SESSION, "end_session")))
    instruction_stim.draw()
    win.flip()
    event.waitKeys()

if serial_response_box is not None:
    serial_response_box.close()

win.close()
core.quit()
