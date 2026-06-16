"""
PsychoPy version of the multiple-cue prospective memory experiment.

Full session structure: 26 sessions (5 practice + 7 baseline + 7 focal PM + 7 nonfocal PM).
Trial design is fully pre-assigned before the experiment starts (no randomization in the trial loop).
Supports keyboard or self-made serial response box.
"""

import csv
import json
import math
import random
import re
import time
from datetime import datetime
from itertools import permutations
from pathlib import Path

from psychopy import gui, visual, core, event, monitors

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

RESPONSE_DEVICE_KEYBOARD = "keyboard"
RESPONSE_DEVICE_CEDRUS = "response_box_cedrus"
RESPONSE_DEVICE_SELF_MADE = "self-made-response-box"

# =============================================================================
# CONFIG: CHANGE THESE VALUES FIRST
# =============================================================================

EXP_DIR = Path(__file__).resolve().parent

DEVICE_NAME_CHOICES = ["KB", "RB", "SRB1", "SRB2", "SRB3", "SRB4", "SRB5", "SRB6"]
DEVICE_NAME_AUTO_CHOICE = "as assigned"
DEVICE_NAME_DIALOG_CHOICES = [DEVICE_NAME_AUTO_CHOICE] + DEVICE_NAME_CHOICES
############################# TO MODIFY BELOW
DEBUG_CONFIG = {
    "enabled": False,
    "trial_duration": 0.001,
    "auto_advance_instructions": False,
    "simulate_response_box": True,
    "full_screen": True,
}
DEFAULT_PARTICIPANT = "3"  # Subject number: 1–100, or "test" (dialog pre-fill; color mapping from CSV)
DEFAULT_MONITOR_NAME = "room1_a4"
DEFAULT_RESPONSE_DEVICE = RESPONSE_DEVICE_KEYBOARD
# Physical unit ID: KB=keyboard, RB=Cedrus response box, SRB1–SRB6=self-made boxes.
DEFAULT_DEVICE_NAME = "KB"
DEFAULT_COLOR_MAP_LAYOUT = "njk"
############################# TO MODIFY ABOVE

if DEFAULT_DEVICE_NAME not in DEVICE_NAME_CHOICES:
    raise ValueError(
        f"DEFAULT_DEVICE_NAME must be one of {DEVICE_NAME_CHOICES!r}; got {DEFAULT_DEVICE_NAME!r}."
    )


CODE_VERSION = "v1-2026-06-15"
EXPERIMENT_NAME = "PMCP"
EXPERIMENT_NUMBER = 1002
DATA_OUT_DIR = (EXP_DIR / "data_written").resolve()
PARTICIPANT_COLOR_KEY_MAPPING_PATH = EXP_DIR / "participant_color_key_mapping.csv"

ALL_COLOR_KEY_MAPPINGS = sorted({"".join(p) for p in permutations("rbg")})
_BOOTSTRAP_COLOR_KEY_MAPPING = ALL_COLOR_KEY_MAPPINGS[0]
COLOR_KEY_MAPPING_AUTO_CHOICE = "as assigned"
COLOR_KEY_MAPPING_DIALOG_CHOICES: list[str] = []
COLOR_KEY_MAPPING_CHOICE_TO_VALUE: dict[str, str] = {}
COLOR_MAP_LAYOUT_AUTO_CHOICE = "as assigned"
COLOR_MAP_LAYOUT_DIALOG_CHOICES = [COLOR_MAP_LAYOUT_AUTO_CHOICE, "njk"]

# Set after session dialog.
COLOR_KEY_MAPPING = _BOOTSTRAP_COLOR_KEY_MAPPING
COLOR_KEY_MAPPING_ASSIGNED = _BOOTSTRAP_COLOR_KEY_MAPPING
COLOR_KEY_MAPPING_OVERRIDDEN = False
COLOR_MAP_LAYOUT = DEFAULT_COLOR_MAP_LAYOUT
COLOR_MAP_LAYOUT_ASSIGNED = DEFAULT_COLOR_MAP_LAYOUT
COLOR_MAP_LAYOUT_OVERRIDDEN = False
RESPONSE_DEVICE = DEFAULT_RESPONSE_DEVICE
DEVICE_NAME = DEFAULT_DEVICE_NAME
DEVICE_NAME_ASSIGNED = DEFAULT_DEVICE_NAME
DEVICE_NAME_OVERRIDDEN = False
REPEAT_DATA_NOTE = ""
REPEAT_REASON = ""
DATA_FILE_STEM = ""
AGE = "NA"
GENDER = "NA"
PARTICIPATION_DAY = 1
FIRST_SESSION_OF_DAY = True

INSTRUCTION_DIR = EXP_DIR / "Instructions"
INSTRUCTION_FONT_CJK = EXP_DIR / "fonts" / "NotoSansCJKsc-Regular.otf"
INSTRUCTION_FONT_CJK_NAME = "Noto Sans CJK SC"
INSTRUCTION_LANGUAGE_SUFFIX = {"en": "", "zh": " zh", "da": " da"}
INSTRUCTION_LANGUAGE_SWITCHER = {
    "en": "If you want to change to 中文 press c; for dansk press d.\n\n",
    "zh": "如需切换为英文请按 e，如需切换为丹麦语（dansk）请按 d。\n\n",
    "da": "Hvis du vil skifte til 中文, tryk c; for engelsk tryk e.\n\n",
}
SESSION1_INSTRUCTION_LANGUAGE = "en"

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

RESPONSE_DEADLINE = 2.0

# Warm-up / burn-in hooks (not active in main sessions yet).
FIRST_WARMUP_TRIALS = 0
OTHER_WARMUP_TRIALS = 0
INCLUDE_BURNIN_BLOCK = False
BURNIN_TRIALS_PER_BLOCK = 20
BURNIN_BLOCK_NUMBER = 0
PM_PRACTICE_BLOCK_NUMBER = -1
# Session 13 = first PM session; session 20 = first session of second PM phase (5+7=12, +1=13, +7=20).
FIRST_PM_SESSION = N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS + 1
FIRST_SECOND_PM_PHASE_SESSION = FIRST_PM_SESSION + N_PM_SESSIONS_PER_KIND
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

def _validate_color_key_mapping(mapping: str) -> str:
    mapping = str(mapping).strip().lower()
    if mapping not in ALL_COLOR_KEY_MAPPINGS:
        raise SystemExit(f"Invalid color key mapping: {mapping!r}")
    return mapping


def _load_participant_color_key_mapping_table() -> dict[str, str]:
    """Read committed assignment table (read-only; never written by this program)."""
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
            mapping = _validate_color_key_mapping(row["color_key_mapping"])
            table[pid] = mapping
    return table


PARTICIPANT_COLOR_KEY_MAPPING = _load_participant_color_key_mapping_table()


def _color_key_mapping_dialog_label(mapping: str) -> str:
    """Human-readable dropdown label for one mapping code."""
    return (
        f"{mapping}  (N={COLOR_LETTER_TO_NAME[mapping[0]]}, "
        f"J={COLOR_LETTER_TO_NAME[mapping[1]]}, "
        f"K={COLOR_LETTER_TO_NAME[mapping[2]]})"
    )


def _build_color_key_mapping_dialog_choices() -> tuple[list[str], dict[str, str]]:
    labeled = [_color_key_mapping_dialog_label(mapping) for mapping in ALL_COLOR_KEY_MAPPINGS]
    choice_to_value = dict(zip(labeled, ALL_COLOR_KEY_MAPPINGS))
    return [COLOR_KEY_MAPPING_AUTO_CHOICE] + labeled, choice_to_value


def _parse_color_key_mapping_choice(choice: str) -> str | None:
    """Return mapping code, or None when the dialog left 'as assigned'."""
    choice = str(choice).strip()
    if choice.lower() == COLOR_KEY_MAPPING_AUTO_CHOICE.lower():
        return None
    if choice in COLOR_KEY_MAPPING_CHOICE_TO_VALUE:
        return COLOR_KEY_MAPPING_CHOICE_TO_VALUE[choice]
    return _validate_color_key_mapping(choice)


def _assigned_color_key_mapping(participant: str) -> str:
    if participant == "test":
        return random.choice(ALL_COLOR_KEY_MAPPINGS)
    if participant in PARTICIPANT_COLOR_KEY_MAPPING:
        return PARTICIPANT_COLOR_KEY_MAPPING[participant]
    return random.choice(ALL_COLOR_KEY_MAPPINGS)


def _resolve_color_key_mapping_from_dialog(
    participant: str, dialog_choice: str
) -> tuple[str, str, bool]:
    """Return (assigned_mapping, used_mapping, overridden)."""
    assigned = _assigned_color_key_mapping(participant)
    parsed = _parse_color_key_mapping_choice(dialog_choice)
    if parsed is None:
        return assigned, assigned, False
    return assigned, parsed, parsed != assigned


def _resolve_device_name_from_dialog(dialog_choice: str) -> tuple[str, str, bool]:
    """Return (assigned_name, used_name, overridden)."""
    assigned = DEFAULT_DEVICE_NAME
    choice = str(dialog_choice).strip()
    if choice.lower() == DEVICE_NAME_AUTO_CHOICE.lower():
        return assigned, assigned, False
    if choice not in DEVICE_NAME_CHOICES:
        raise SystemExit(
            f"Device name must be '{DEVICE_NAME_AUTO_CHOICE}' or one of {DEVICE_NAME_CHOICES!r}; "
            f"got {choice!r}."
        )
    return assigned, choice, choice != assigned


def _resolve_color_map_layout_from_dialog(dialog_choice: str) -> tuple[str, str, bool]:
    """Return (assigned_layout, used_layout, overridden)."""
    assigned = DEFAULT_COLOR_MAP_LAYOUT
    choice = str(dialog_choice).strip().lower()
    if choice == COLOR_MAP_LAYOUT_AUTO_CHOICE.lower():
        return assigned, assigned, False
    if choice not in COLOR_MAP_LAYOUT_DIALOG_CHOICES[1:]:
        raise SystemExit(
            f"Color map layout must be '{COLOR_MAP_LAYOUT_AUTO_CHOICE}' or one of "
            f"{COLOR_MAP_LAYOUT_DIALOG_CHOICES[1:]!r}; got {choice!r}."
        )
    return assigned, choice, choice != assigned


def _tk_yes_no(title: str, message: str) -> bool:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    answer = messagebox.askyesno(title, message, parent=root)
    root.destroy()
    return bool(answer)


def _tk_ask_string(title: str, message: str) -> str | None:
    """Text prompt via tkinter (avoids PsychoPy wx second-dialog crash)."""
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    value = simpledialog.askstring(title, message, parent=root)
    root.destroy()
    return value


def _participant_data_dir(participant: str) -> Path:
    return DATA_OUT_DIR / f"subj{participant}"


def _max_completed_session(participant: str, out_dir: Path) -> int | None:
    """Highest session number found for this participant, or None."""
    prefix = f"PMCP_subj{participant}_ses"
    max_session = None
    if not out_dir.is_dir():
        return None
    for path in out_dir.iterdir():
        if not path.is_file() or not path.name.startswith(prefix):
            continue
        match = re.match(r"^(\d+)", path.name[len(prefix):])
        if match:
            session_num = int(match.group(1))
            max_session = session_num if max_session is None else max(max_session, session_num)
    return max_session


def _suggested_next_session(participant: str, out_dir: Path) -> int:
    max_session = _max_completed_session(participant, out_dir)
    return 1 if max_session is None else max_session + 1


def _confirm_unexpected_session(participant: str, session: int, out_dir: Path) -> None:
    expected = _suggested_next_session(participant, out_dir)
    if session == expected:
        return
    if not _tk_yes_no(
        "Confirm session number",
        (
            f"From reading your data, it seems that your next session number is {expected}.\n\n"
            f"You entered session {session}. Are you sure you want to continue?"
        ),
    ):
        raise SystemExit("Session confirmation cancelled.")


def _resolve_data_output_paths(
    participant: str, session: int, out_dir: Path
) -> tuple[Path, Path, str, str, str]:
    """Return trials path, metadata path, file stem, repeat note, repeat reason (empty if not repeat)."""
    base_stem = f"PMCP_subj{participant}_ses{session}"
    trials_path = (out_dir / f"{base_stem}_trials.csv").resolve()
    metadata_path = (out_dir / f"{base_stem}_metadata.json").resolve()

    if not trials_path.exists() and not metadata_path.exists():
        return trials_path, metadata_path, base_stem, "", ""

    reason = _tk_ask_string(
        "Participant data already exists",
        (
            f"Data already exists for participant {participant}, session {session}.\n\n"
            f"This will be saved as a repeated run (e.g. {base_stem}(2)). "
            "To continue anyway, enter a reason below:"
        ),
    )
    if reason is None:
        raise SystemExit("Repeat run cancelled.")
    reason = reason.strip()
    if not reason:
        raise SystemExit("A reason is required to save repeated participant data.")

    suffix_n = 2
    while True:
        stem = f"{base_stem}({suffix_n})"
        candidate_trials = (out_dir / f"{stem}_trials.csv").resolve()
        candidate_meta = (out_dir / f"{stem}_metadata.json").resolve()
        if not candidate_trials.exists() and not candidate_meta.exists():
            note = f"this is a repeated data, reason is '{reason}'"
            return candidate_trials, candidate_meta, stem, note, reason
        suffix_n += 1


def _find_self_made_response_box_port() -> str:
    """Find the self-made box serial port (skip Cedrus FTDI devices)."""
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
    box = serial.Serial(port_name, baudrate=SELF_MADE_BAUDRATE, timeout=0.001)
    time.sleep(2.0)
    box.reset_input_buffer()
    print(f"Using {RESPONSE_DEVICE_SELF_MADE} on {port_name}.")
    return box


def _wait_for_self_made_response_box(box, clock, max_wait):
    """Wait for a pin press; return (pin_or_escape, computer_time, device_rt_ms) or None."""
    buffer = ""
    start = clock.getTime()

    while clock.getTime() - start < max_wait:
        escape_keys = event.getKeys(keyList=[QUIT_KEY], timeStamped=clock)
        if escape_keys:
            return (QUIT_KEY, escape_keys[0][1], 0.0)

        buffer += box.read(box.in_waiting or 1).decode("ascii", errors="ignore")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            parts = line.strip().split(",")
            if len(parts) != 2:
                continue

            pin, latency_us = parts
            if pin in SELF_MADE_PIN_TO_KEY:
                return (pin, clock.getTime(), float(latency_us) / 1000)

    return None


# Display / monitor (match multiplecue-responsebox/exp/testmain.py paradigm)
WIN_SIZE_PIX = (1920, 1080)
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60
MONITOR_CHOICES = [f"room1_a{i}" for i in range(1, 11)]
MONITOR_NAME = DEFAULT_MONITOR_NAME
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

COLORS = {
    "red": (220, 50, 50),
    "blue": (50, 100, 220),
    "green": (50, 180, 80),
    "orange": (240, 150, 30),
    "white": (255, 255, 255),
    "black": (0, 0, 0),
}

COLOR_LETTER_TO_NAME = {"r": "red", "b": "blue", "g": "green"}
STIMULUS_COLOR_NAMES = ["red", "blue", "green"]
# Fixed NJK key slots (left-to-right in mapping string = n, j, k).
KEY_SLOT_KEYS = ["n", "j", "k"]

PM_KEY = "c"
START_KEY = "space"
QUIT_KEY = "escape"

# Self-made box: pins are wired to physical keys; color assignment comes from COLOR_KEY_MAPPING.
SELF_MADE_PIN_TO_KEY = {
    "7": PM_KEY,
    "8": "n",
    "9": "j",
    "5": "k",
}

# Populated by apply_color_key_mapping() after the session dialog.
COLOR_KEYS: dict[str, str] = {}
key_to_color: dict[str, str] = {}
ALL_RESPONSE_KEYS: list[str] = []


def apply_color_key_mapping(mapping: str) -> None:
    """
    Apply a 3-letter mapping (permutation of r,b,g) to response keys.

    Slot order is KEY_SLOT_KEYS: mapping[0] -> n, mapping[1] -> j, mapping[2] -> k.
    Self-made pins stay on the same keys; only the color each key reports changes.
    """
    global COLOR_KEYS, key_to_color, ALL_RESPONSE_KEYS
    mapping = str(mapping).strip().lower()
    if len(mapping) != 3 or set(mapping) != set("rbg"):
        raise SystemExit(f"Invalid color key mapping: {mapping!r}")

    color_keys = {}
    slot_colors = {}
    for slot_i, letter in enumerate(mapping):
        color_name = COLOR_LETTER_TO_NAME[letter]
        key = KEY_SLOT_KEYS[slot_i]
        color_keys[color_name] = key
        slot_colors[key] = color_name

    COLOR_KEYS = color_keys
    key_to_color = slot_colors
    ALL_RESPONSE_KEYS = list(COLOR_KEYS.values()) + [PM_KEY, QUIT_KEY]


apply_color_key_mapping(_BOOTSTRAP_COLOR_KEY_MAPPING)

COLOR_KEY_MAPPING_DIALOG_CHOICES, COLOR_KEY_MAPPING_CHOICE_TO_VALUE = (
    _build_color_key_mapping_dialog_choices()
)

# Self-made response box serial settings.
CEDRUS_VID = 0x0403
CEDRUS_PID = 0x6001
SELF_MADE_BAUDRATE = 115200

PM_REWARD = 5

FEEDBACK_LETTER_SIZE_DEG = 50 * STIM_FACTOR
FEEDBACK1_POS_DEG = (0, 70 * STIM_FACTOR)
FEEDBACK2_POS_DEG = (0, -70 * STIM_FACTOR)
FEEDBACK3_POS_DEG = (0, -140 * STIM_FACTOR)
FEEDBACK4_POS_DEG = (0, -200 * STIM_FACTOR)
FEEDBACK_TEXT_COLOR = COLORS["white"]
TOO_SLOW_TEXT = "TOO SLOW!"

COLOR_NAME_TO_ID = {"red": 1, "blue": 2, "green": 3}
COLOR_ID_TO_DISPLAY = {1: "Red", 2: "Blue", 3: "Green"}
POSITION_NAME_TO_ID = {
    "top": 1,
    "bottom_left": 2,
    "bottom_right": 3,
    "center": 0,
}
POSITION_ID_TO_LABEL = {
    1: "top",
    2: "bottom_left",
    3: "bottom_right",
    0: "center",
}


def _color_to_key_mapping_metadata(response_device: str | None = None) -> dict[str, str]:
    device = response_device or RESPONSE_DEVICE
    if device == RESPONSE_DEVICE_SELF_MADE:
        meta = {}
        for pin, key in SELF_MADE_PIN_TO_KEY.items():
            if key == PM_KEY:
                meta["PM"] = f"pin_{pin} ({key.upper()})"
            else:
                color_name = key_to_color[key]
                display = COLOR_ID_TO_DISPLAY[COLOR_NAME_TO_ID[color_name]]
                meta[display] = f"pin_{pin} ({key.upper()})"
        return meta
    return {
        COLOR_ID_TO_DISPLAY[COLOR_NAME_TO_ID[color]]: key.upper()
        for color, key in COLOR_KEYS.items()
    }


def _self_made_pin_to_color_metadata() -> dict[str, str]:
    """Pin -> stimulus color name for the active mapping (for metadata sidecar)."""
    out = {}
    for pin, key in SELF_MADE_PIN_TO_KEY.items():
        if key == PM_KEY:
            out[pin] = "pm"
        else:
            out[pin] = key_to_color[key]
    return out


def _trial_design_maps(trial: dict) -> tuple[dict, dict]:
    position_to_reward = {
        i: trial["reward_values"][i] if i < len(trial["reward_values"]) else 0
        for i in range(N_POSITIONS)
    }
    position_to_color_id = {}
    for i in range(N_POSITIONS):
        color_name = trial["trial_colors"][i] if i < len(trial["trial_colors"]) else ""
        reward = position_to_reward[i]
        if color_name and reward > 0:
            position_to_color_id[i] = COLOR_NAME_TO_ID[color_name]
        else:
            position_to_color_id[i] = None
    return position_to_color_id, position_to_reward


def _build_trial_row(
    *,
    trial: dict,
    position_to_color_id: dict,
    position_to_reward: dict,
    pressed_key: str | None,
    rt_ms: float | None,
    rt_computer_clock_ms: float | None = None,
    cue_time: float,
    end_trial_time: float,
    actual_reward: int,
    max_reward: int,
    cum_reward: float,
    trial_index: int,
    trial_start_jitter_time_ms: float,
    trial_wall_clock_str: str,
    session_elapsed_sec: float,
    trial_note: str = "",
) -> dict:
    """Build one CSV row matching CCRP columns plus PM fields."""
    colors = [position_to_color_id[i] or 0 for i in range(N_POSITIONS)]
    reward_vals = [position_to_reward[i] or 0 for i in range(N_POSITIONS)]
    sorted_reward_values = sorted((value for value in reward_vals if value), reverse=True)
    reward_rank_by_value = {value: rank + 1 for rank, value in enumerate(sorted_reward_values)}
    reward_ranks = [reward_rank_by_value.get(value, 4) if value else 4 for value in reward_vals]
    num_cues = sum(1 for value in reward_vals if value > 0)

    is_pm_trial = bool(trial.get("is_pm_trial"))
    pm_kind = trial.get("pm_trial_kind") or ""
    pm_position = trial.get("pm_position") or ""
    pm_position_id = POSITION_NAME_TO_ID.get(pm_position, 0)
    pm_response = int(pressed_key == PM_KEY)
    pm_intrusion = int((not is_pm_trial) and pressed_key == PM_KEY)
    pm_acc = int(is_pm_trial and pressed_key == PM_KEY)

    selected_color = None
    selected_position = None
    if pressed_key in key_to_color:
        selected_color_name = key_to_color[pressed_key]
        selected_color = COLOR_NAME_TO_ID[selected_color_name]
        if trial.get("single_center", False):
            if trial["trial_colors"][0] == selected_color_name:
                selected_position = 0
        else:
            selected_position = trial["trial_colors"].index(selected_color_name)

    if rt_ms is None:
        rt_ms = MAX_RESPONSE_TIME * 1000
    if rt_computer_clock_ms is None:
        rt_computer_clock_ms = rt_ms
    rt_sec = rt_ms / 1000
    rt_difference = rt_computer_clock_ms - rt_ms
    late = rt_sec > RESPONSE_DEADLINE
    intr = 1 if (selected_position is not None and selected_color is None) else 0
    if pressed_key == PM_KEY:
        intr = 0
    acc = 1 if actual_reward == max_reward and max_reward > 0 else 0

    chosen_location_idx = selected_position
    resp_loc = (chosen_location_idx + 1) if chosen_location_idx is not None else 0
    point_target = (
        "".join("1" if i == chosen_location_idx else "0" for i in range(N_POSITIONS))
        if chosen_location_idx is not None
        else "0" * N_POSITIONS
    )
    cue_response_exp_value = (
        reward_vals[chosen_location_idx] if chosen_location_idx is not None else 0
    )
    cue_rank_response = (
        reward_ranks[chosen_location_idx] if chosen_location_idx is not None else 0
    )
    exp_reward = max((value for value in reward_vals if value), default=0)

    return {
        "ExperimentName": EXPERIMENT_NAME,
        "ExperimentNumber": EXPERIMENT_NUMBER,
        "CodeVersion": CODE_VERSION,
        "ColorMapLayout": COLOR_MAP_LAYOUT,
        "ColorKeyMapping": COLOR_KEY_MAPPING,
        "ResponseDevice": RESPONSE_DEVICE,
        "DeviceName": DEVICE_NAME,
        "Subject": PARTICIPANT,
        "Handedness": HANDEDNESS,
        "ColorVision": COLOR_VISION,
        "EyeVision": EYE_VISION,
        "Session": SESSION,
        "Block": trial["block"],
        "Trial": trial_index + 1,
        "WarmUpTrial": trial.get("warm_up", 0),
        "BurnInBlock": trial.get("burn_in_block", 0),
        "ParticipationDay": PARTICIPATION_DAY,
        "FirstSessionOfDay": 1 if FIRST_SESSION_OF_DAY else 0,
        "PMPracticeBlock": trial.get("pm_practice_block", 0),
        "SessionPhase": trial.get("session_phase", SESSION_PHASE),
        "CueCondition": trial.get("cue_condition", ""),
        "NumCues": num_cues,
        "TrialStartJitterTime": round(trial_start_jitter_time_ms, 2),
        "CueSOA": 0,
        "Cues": "".join(str(c) for c in colors),
        "CueValues": "".join(str(v) for v in reward_vals),
        "CueRanks": "".join(str(r) for r in reward_ranks),
        "Response": pressed_key or "timeout",
        "RespLoc": resp_loc,
        "PointTargetResponse": point_target,
        "RT": round(rt_ms, 2),
        "RTComputerClock": round(rt_computer_clock_ms, 2),
        "RTDifference": round(rt_difference, 2),
        "LateResponse": late,
        "ACC": acc,
        "INTR": intr,
        "CueResponseValue": actual_reward,
        "CueResponseExpValue": cue_response_exp_value,
        "CueRankResponse": cue_rank_response,
        "ExpectedReward": exp_reward,
        "Reward": actual_reward,
        "MaxReward": max_reward,
        "CumReward": cum_reward,
        "PMTrial": int(is_pm_trial),
        "PMKind": pm_kind,
        "PMPosition": pm_position,
        "PMPositionId": pm_position_id,
        "PMKey": PM_KEY,
        "PMResponse": pm_response,
        "PMACC": pm_acc,
        "PMIntrusion": pm_intrusion,
        "PMReward": PM_REWARD if is_pm_trial else 0,
        "FocalPMStyle": trial.get("focal_pm_style", FOCAL_PM_STYLE) if pm_kind == "focal" else "",
        "CueTime": round(cue_time * 1000, 2),
        "PointTargetTime": round((cue_time + rt_sec) * 1000, 2),
        "ColorTargetTime": round(cue_time * 1000, 2),
        "EndTrialTime": round(end_trial_time * 1000, 2),
        "TrialWallClockTime": trial_wall_clock_str,
        "SessionElapsedSec": round(session_elapsed_sec, 3),
        "Note": trial_note,
    }


DAT_COLUMN_DESCRIPTIONS = {
    "ExperimentName": "Short experiment label constant.",
    "ExperimentNumber": "Numeric experiment ID constant.",
    "CodeVersion": "Experiment code version configured at the top of the script.",
    "ColorMapLayout": "Color-key legend layout: NJK keyboard-matched triangle.",
    "ColorKeyMapping": "Three-character mapping for response colors: r=red, b=blue, g=green.",
    "ResponseDevice": "Response input device used for this run (keyboard only in this script).",
    "DeviceName": "Physical response unit ID (KB for keyboard).",
    "Subject": "Participant ID from the session dialog.",
    "Handedness": "Participant handedness from the session dialog.",
    "ColorVision": "Participant color vision status from the session dialog.",
    "EyeVision": "Participant eye vision status from the session dialog.",
    "Session": "Session number from the session dialog (1-based).",
    "Block": "Block number within the session; -1 = PM practice, 0 = burn-in when present.",
    "Trial": "Trial index within the session (1-based).",
    "WarmUpTrial": "1 if warmup trial, 0 if main trial.",
    "BurnInBlock": "1 if trial belongs to the optional burn-in block (block 0); 0 otherwise.",
    "ParticipationDay": "Participant's self-reported day of participation (1–4) from the session dialog.",
    "FirstSessionOfDay": "1 if participant reported this as their first session of the day; 0 otherwise.",
    "PMPracticeBlock": "1 if trial belongs to the PM practice block (block -1); 0 otherwise.",
    "SessionPhase": "practice, baseline, focal_pm, or nonfocal_pm.",
    "CueCondition": "Reward-value combination label among cued locations, e.g. (1), (2,3).",
    "NumCues": "Count of cued stimulus locations this trial.",
    "TrialStartJitterTime": "Duration of fixation before stimulus onset (ms).",
    "CueSOA": "Cue-target stimulus onset asynchrony (ms); 0 here.",
    "Cues": "Three digits: color ID 1-3 at each spatial slot; 0 = no stimulus at that slot.",
    "CueValues": "Three digits: reward digit at each slot; 0 = no reward at that slot.",
    "CueRanks": "Three digits: reward-value rank at each location; 4 = no reward at that location.",
    "Response": "Key pressed (lowercase) or timeout; escape not logged as a trial row.",
    "RespLoc": "Location id (1-3) of the participant's chosen cue; 0 if no valid chosen location.",
    "PointTargetResponse": "Three-digit one-hot vector of chosen cue location; all zeros if none.",
    "RT": "Reaction time (ms). For self-made-response-box, this uses the device timer; for keyboard, this matches RTComputerClock.",
    "RTComputerClock": "Reaction time (ms) using the PsychoPy computer clock.",
    "RTDifference": "RTComputerClock minus RT (ms). For keyboard this is 0; for self-made-response-box this shows computer-clock minus device-clock RT.",
    "LateResponse": "True if RT (seconds) exceeded RESPONSE_DEADLINE; False otherwise.",
    "ACC": "1 if obtained reward equals max possible reward on that trial and max > 0; else 0.",
    "INTR": "1 if participant responded with a key whose mapped color was absent on screen; else 0.",
    "CueResponseValue": "Reward points obtained from the chosen response (0 if wrong/absent).",
    "CueResponseExpValue": "Expected reward value at location chosen.",
    "CueRankResponse": "Rank of value at location chosen; 0 if no valid chosen location.",
    "ExpectedReward": "Highest possible ongoing-task reward in this trial.",
    "Reward": "Same as obtained points for this trial (CueResponseValue).",
    "MaxReward": "Maximum obtainable reward on this trial (PM bonus on PM trials).",
    "CumReward": "Cumulative monetary-style score (points x REWARD_MONEY_FACTOR), running total.",
    "PMTrial": "1 if this trial includes a prospective-memory cue; 0 otherwise.",
    "PMKind": "focal, nonfocal, or empty.",
    "PMPosition": "Stimulus location name of the PM cue (top, bottom_left, bottom_right, center).",
    "PMPositionId": "Numeric location id of the PM cue; 0 for center-only layout or none.",
    "PMKey": "Key assigned to PM responses.",
    "PMResponse": "1 if participant pressed the PM key on this trial; 0 otherwise.",
    "PMACC": "1 if PM trial and participant pressed the PM key; 0 otherwise.",
    "PMIntrusion": "1 if participant pressed the PM key on a non-PM trial; 0 otherwise.",
    "PMReward": "PM bonus points available when PMTrial=1; 0 on ongoing trials.",
    "FocalPMStyle": "Focal PM marker style when PMKind=focal; empty otherwise.",
    "CueTime": "Stimulus onset time from trial clock (ms).",
    "PointTargetTime": "Time of keypress from trial clock (ms), or cue time if no RT.",
    "ColorTargetTime": "Same as cue onset time here (ms).",
    "EndTrialTime": "Trial clock time (ms) at end of feedback phase.",
    "TrialWallClockTime": "Local wall-clock date and time when this trial row was logged.",
    "SessionElapsedSec": "Seconds since session timing start (monotonic clock).",
    "Note": "Free-text notes (e.g. repeat run reason on first trial); usually empty.",
}


def _build_metadata(
    *,
    exp_start_time_str: str,
    n_blocks: int,
    n_trials_total: int,
    n_trials_per_block: int,
    include_burnin_block: bool,
    include_pm_practice_block: bool,
    display_config: dict,
    dat_columns: list[str],
) -> dict:
    try:
        import psychopy

        psychopy_version = getattr(psychopy, "__version__", "unknown")
    except Exception:
        psychopy_version = "unknown"

    reward_labels = [cond["label"] for cond in get_session_generation_config(SESSION)["cue_conditions"]]
    n_reward_conds = len(reward_labels)
    reps_per_condition = (n_trials_per_block // n_reward_conds) if n_reward_conds else 0
    debug_on = bool(DEBUG_CONFIG.get("enabled"))

    return {
        "trial_timing_and_design": {
            "cue_soa_ms": 0,
            "fixation_duration_s": FIXATION_TIME,
            "response_key_wait_max_s": MAX_RESPONSE_TIME,
            "late_response_threshold_s": RESPONSE_DEADLINE,
            "feedback_duration_s": FEEDBACK_WAIT_TIME,
            "iti_duration_s": ITI_TIME,
            "warmup_trials_first_block": FIRST_WARMUP_TRIALS,
            "warmup_trials_other_blocks": OTHER_WARMUP_TRIALS,
            "burnin_block_included": include_burnin_block,
            "burnin_trials_per_block": BURNIN_TRIALS_PER_BLOCK if include_burnin_block else 0,
            "burnin_block_number": BURNIN_BLOCK_NUMBER if include_burnin_block else None,
            "pm_practice_block_included": include_pm_practice_block,
            "pm_practice_block_number": PM_PRACTICE_BLOCK_NUMBER if include_pm_practice_block else None,
            "pm_trials_per_block": PM_TRIALS_PER_BLOCK,
            "pm_reward_points": PM_REWARD,
            "pm_key": PM_KEY,
            "blocks": n_blocks,
            "main_trials_per_block": n_trials_per_block,
            "total_trials": n_trials_total,
            "single_stimulus_at_center": bool(display_config.get("single_center", False)),
            "color_key_legend_on_screen": bool(display_config.get("show_color_keymap", True)),
            "cue_condition_labels": reward_labels,
            "number_of_reward_conditions": n_reward_conds,
            "main_trials_per_reward_condition_per_block_balanced": reps_per_condition,
            "color_id_mapping_for_cues": {
                str(color_id): COLOR_ID_TO_DISPLAY[color_id] for color_id in sorted(COLOR_ID_TO_DISPLAY)
            },
            "color_to_key_mapping": _color_to_key_mapping_metadata(RESPONSE_DEVICE),
            "location_id_mapping": {
                str(position_id): {
                    "screen_location": POSITION_ID_TO_LABEL[position_id],
                    "position_deg_x_y": [
                        round(POSITIONS[name][0], 3),
                        round(POSITIONS[name][1], 3),
                    ],
                }
                for name, position_id in POSITION_NAME_TO_ID.items()
                if name != "center"
            },
            "location_id_mapping_note": (
                "Location ids are 1-based positions in Cues, CueValues, CueRanks, RespLoc, "
                "and PointTargetResponse. Center-only sessions log the cue in slot 1."
            ),
            "per_trial_logging_note": (
                "TrialWallClockTime is local wall time; SessionElapsedSec is monotonic elapsed "
                "seconds since pre-loop session start."
            ),
        },
        "run_and_display_metadata": {
            "psychopy_version": psychopy_version,
            "experimental_program": Path(__file__).name,
            "experiment_name": EXPERIMENT_NAME,
            "experiment_number": EXPERIMENT_NUMBER,
            "code_version": CODE_VERSION,
            "exp_start_time": exp_start_time_str,
            "debug_config_enabled": debug_on,
            "color_key_mapping": COLOR_KEY_MAPPING,
            "color_key_mapping_assigned": COLOR_KEY_MAPPING_ASSIGNED,
            "color_key_mapping_overridden": COLOR_KEY_MAPPING_OVERRIDDEN,
            "color_key_mapping_table_path": str(PARTICIPANT_COLOR_KEY_MAPPING_PATH),
            "color_key_mapping_description": (
                f"Mapping {COLOR_KEY_MAPPING}: "
                f"{KEY_SLOT_KEYS[0].upper()}={COLOR_LETTER_TO_NAME[COLOR_KEY_MAPPING[0]]}, "
                f"{KEY_SLOT_KEYS[1].upper()}={COLOR_LETTER_TO_NAME[COLOR_KEY_MAPPING[1]]}, "
                f"{KEY_SLOT_KEYS[2].upper()}={COLOR_LETTER_TO_NAME[COLOR_KEY_MAPPING[2]]}."
            ),
            "color_map_layout": COLOR_MAP_LAYOUT,
            "color_map_layout_assigned": COLOR_MAP_LAYOUT_ASSIGNED,
            "color_map_layout_overridden": COLOR_MAP_LAYOUT_OVERRIDDEN,
            "repeated_run": bool(REPEAT_DATA_NOTE),
            "repeat_reason": REPEAT_REASON,
            "data_file_stem": DATA_FILE_STEM,
            "participant_data_subdirectory": str(PARTICIPANT_DATA_DIR),
            "subject": PARTICIPANT,
            "age": AGE,
            "gender": GENDER,
            "handedness": HANDEDNESS,
            "color_vision": COLOR_VISION,
            "eye_vision": EYE_VISION,
            "participation_day": PARTICIPATION_DAY,
            "first_session_of_day": "Y" if FIRST_SESSION_OF_DAY else "N",
            "practice": "Y" if SESSION <= N_PRACTICE_SESSIONS else "N",
            "session": SESSION,
            "session_phase": SESSION_PHASE,
            "session1_instruction_language": SESSION1_INSTRUCTION_LANGUAGE if SESSION == 1 else None,
            "number_of_blocks": n_blocks,
            "total_number_of_trials": n_trials_total,
            "reward_money_factor": REWARD_MONEY_FACTOR,
            "full_screen": "Y" if DEBUG_CONFIG.get("full_screen", False) else "N",
            "response_device": RESPONSE_DEVICE,
            "device_name": DEVICE_NAME,
            "device_name_assigned": DEVICE_NAME_ASSIGNED,
            "device_name_overridden": DEVICE_NAME_OVERRIDDEN,
            "default_device_name_in_code": DEFAULT_DEVICE_NAME,
            "response_keys": [key.upper() for key in COLOR_KEYS.values()] + [PM_KEY.upper()],
            "self_made_response_box_pins": _self_made_pin_to_color_metadata(),
            "self_made_response_box_pin_to_key": dict(SELF_MADE_PIN_TO_KEY),
            "pm_key": PM_KEY,
            "response_deadline": RESPONSE_DEADLINE,
            "monitor_name": MONITOR_NAME,
            "monitor_set_size_pixels": list(WIN_SIZE_PIX),
            "monitor_width_cm": MONITOR_WIDTH_CM,
            "monitor_distance_cm": MONITOR_DISTANCE_CM,
            "background_color": list(BACKGROUND_COLOR),
            "stimulus_opacity": STIMULUS_OPACITY,
            "focal_pm_style": FOCAL_PM_STYLE,
        },
        "column_order": dat_columns,
        "column_definitions": {
            col: DAT_COLUMN_DESCRIPTIONS.get(col, "No description defined.")
            for col in dat_columns
        },
    }


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


def session_needs_pm_practice_block(session: int) -> bool:
    """One PM practice block at session 13 (baseline→PM A) and session 20 (PM A→PM B)."""
    return session in (FIRST_PM_SESSION, FIRST_SECOND_PM_PHASE_SESSION)


def pm_practice_kind_for_session(session: int, participant_id: str) -> str:
    """Return 'focal' or 'nonfocal' for the PM practice block on this session."""
    phase = session_phase_for(session, participant_id)
    return "focal" if phase == "focal_pm" else "nonfocal"


def _secondary_cue_label(session: int, participant_id: str) -> str:
    """Participant-facing cue description key: orange_ring or dashed."""
    return "orange ring" if session_phase_for(session, participant_id) == "focal_pm" else "dashed"


def get_session_display_config(session: int) -> dict:
    """Display options for a session; defaults unless overridden."""
    cfg = {**DEFAULT_DISPLAY, **SESSION_DISPLAY_OVERRIDES.get(session, {})}
    if session == 1:
        cfg.update(single_center=True, triangle_layout=False, show_color_keymap=True)
    elif session in (2, 3):
        cfg.update(single_center=False, triangle_layout=True, show_color_keymap=True)
    else:
        # Sessions 4+: triangle layout, no on-screen color-key legend.
        cfg.update(single_center=False, triangle_layout=True, show_color_keymap=False)
    return cfg


def get_session_generation_config(session: int) -> dict:
    """Trial-generation options per session (cue conditions, center layout)."""
    if session == 1:
        defaults = {
            "cue_conditions": SINGLE_CUE_CONDITIONS,
            "single_center": True,
            "n_cue_conditions": len(SINGLE_CUE_CONDITIONS),
        }
    elif session == 2:
        defaults = {
            "cue_conditions": SINGLE_CUE_CONDITIONS,
            "single_center": False,
            "n_cue_conditions": len(SINGLE_CUE_CONDITIONS),
        }
    elif session in (3, 4):
        defaults = {
            "cue_conditions": DUAL_CUE_CONDITIONS,
            "single_center": False,
            "n_cue_conditions": len(DUAL_CUE_CONDITIONS),
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
DUAL_CUE_CONDITIONS = CUE_CONDITIONS[3:]
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
    all_colors = STIMULUS_COLOR_NAMES[:]

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
    pm_practice_block: int = 0,
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
                "pm_practice_block": pm_practice_block,
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
                "pm_practice_block": pm_practice_block,
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
    include_pm_practice_block: bool = False,
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

    if include_pm_practice_block:
        practice_block = _make_block(
            rng,
            session_phase,
            session_number,
            burn_in_block=0,
            pm_practice_block=1,
        )
        for trial_in_block, trial in enumerate(practice_block, start=1):
            trial = dict(trial)
            trial.update(
                block=PM_PRACTICE_BLOCK_NUMBER,
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
        + (TRIALS_PER_BLOCK if include_pm_practice_block else 0)
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


def _load_session1_instruction(language: str = "en") -> str:
    """Load session-1 instruction text for the selected language."""
    if language not in INSTRUCTION_LANGUAGE_SUFFIX:
        raise SystemExit(f"Unsupported instruction language: {language!r}")
    path = INSTRUCTION_DIR / f"instruction ses 1{INSTRUCTION_LANGUAGE_SUFFIX[language]}.txt"
    if not path.exists():
        raise SystemExit(f"Instruction file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def _load_pm_practice_instruction(session: int, participant_id: str) -> str:
    """Instruction at session start when a practice block precedes the main session."""
    cue = _secondary_cue_label(session, participant_id)
    if session == FIRST_PM_SESSION:
        return _load_instruction(f"instruction practice after baseline {cue}.txt")
    return _load_instruction(f"instruction practice new cue {cue}.txt")


def _load_session_instruction(session: int, participant_id: str) -> str:
    """Load the main session instruction (shown at start, or after the practice block)."""
    if session == 1:
        return _load_session1_instruction(SESSION1_INSTRUCTION_LANGUAGE)
    if session == 2:
        return _load_instruction("instruction ses 2.txt")
    if session == 3:
        return _load_instruction("instruction ses 3.txt")
    if session == 4:
        return _load_instruction("instruction ses 4.txt")
    if session == 5:
        return _load_instruction("instruction ses 5.txt")
    if session <= N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS:
        return _load_instruction("instruction ses 6 onward.txt")
    cue = _secondary_cue_label(session, participant_id)
    if session == FIRST_PM_SESSION:
        return _load_instruction(f"instruction ses after baseline {cue}.txt")
    if session == FIRST_SECOND_PM_PHASE_SESSION:
        return _load_instruction(f"instruction ses new cue {cue}.txt")
    return _load_instruction(f"instruction ses continue {cue}.txt")


def _load_session_start_instruction(session: int, participant_id: str) -> str:
    """First instruction screen: PM practice intro on sessions 13 and 20, else normal session intro."""
    if session_needs_pm_practice_block(session):
        return _load_pm_practice_instruction(session, participant_id)
    return _load_session_instruction(session, participant_id)


# =============================================================================
# SESSION DIALOG
# =============================================================================

_dialog_default_participant = (
    DEFAULT_PARTICIPANT if DEFAULT_PARTICIPANT in PARTICIPANT_CHOICES else "1"
)
_dialog_default_session = _suggested_next_session(
    _dialog_default_participant,
    _participant_data_dir(_dialog_default_participant),
)
PARTICIPATION_DAY_LABEL_TO_NUM = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
session_dlg = gui.Dlg(title="Prospective MCP Session")
session_dlg.addField(
    "Participant",
    initial=_dialog_default_participant,
    choices=PARTICIPANT_CHOICES,
)
session_dlg.addText("— Participant: fill in the fields below —")
session_dlg.addField("Session", initial=_dialog_default_session)
session_dlg.addField(
    "First session of day?",
    initial="yes",
    choices=["yes", "no"],
)
session_dlg.addField(
    "Participation day",
    initial="1st",
    choices=["1st", "2nd", "3rd", "4th"],
    tip="Which day of participation is this?",
)
session_dlg.addField("Age", initial="")
session_dlg.addField("Gender", initial="NA")
session_dlg.addField(
    "Handedness",
    initial="right",
    choices=["right", "left", "ambidextrous", "other"],
)
session_dlg.addField(
    "Color vision",
    initial="normal",
    choices=["normal", "not normal", "unknown"],
)
session_dlg.addField(
    "Eye vision",
    initial="normal",
    choices=["normal", "corrected", "not normal", "unknown"],
)
session_dlg.addText("— Experimenter only: do not change unless instructed —")
session_dlg.addField(
    "Color key mapping",
    initial=COLOR_KEY_MAPPING_AUTO_CHOICE,
    choices=COLOR_KEY_MAPPING_DIALOG_CHOICES,
    tip=(
        "as assigned = mapping from participant_color_key_mapping.csv for this participant "
        "(random for test or if id is missing from the table). "
        "Or pick one of 6 mappings: each sets N/J/K -> red/blue/green."
    ),
)
session_dlg.addField(
    "Response device",
    initial=DEFAULT_RESPONSE_DEVICE,
    choices=[RESPONSE_DEVICE_KEYBOARD, RESPONSE_DEVICE_CEDRUS, RESPONSE_DEVICE_SELF_MADE],
)
session_dlg.addField(
    "Device name",
    initial=DEVICE_NAME_AUTO_CHOICE,
    choices=DEVICE_NAME_DIALOG_CHOICES,
    tip="Default uses DEFAULT_DEVICE_NAME from code. Pick KB/RB/SRB1–6 only to override.",
)
session_dlg.addField(
    "Color map layout",
    initial=COLOR_MAP_LAYOUT_AUTO_CHOICE,
    choices=COLOR_MAP_LAYOUT_DIALOG_CHOICES,
    tip="Only NJK layout is implemented; leave as assigned unless instructed.",
)
session_dlg.addField(
    "Monitor name",
    initial=DEFAULT_MONITOR_NAME,
    choices=MONITOR_CHOICES,
)
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

FIRST_SESSION_OF_DAY = str(session_dlg.data[2]).strip().lower() == "yes"
_participation_day_label = str(session_dlg.data[3]).strip().lower()
if _participation_day_label not in PARTICIPATION_DAY_LABEL_TO_NUM:
    raise SystemExit(
        f"Invalid participation day: {session_dlg.data[3]!r}. Choose 1st, 2nd, 3rd, or 4th."
    )
PARTICIPATION_DAY = PARTICIPATION_DAY_LABEL_TO_NUM[_participation_day_label]
AGE = str(session_dlg.data[4]).strip() or "NA"
GENDER = str(session_dlg.data[5]).strip() or "NA"
HANDEDNESS = str(session_dlg.data[6]).strip() or "NA"
COLOR_VISION = str(session_dlg.data[7]).strip() or "NA"
EYE_VISION = str(session_dlg.data[8]).strip() or "NA"
COLOR_KEY_MAPPING_ASSIGNED, COLOR_KEY_MAPPING, COLOR_KEY_MAPPING_OVERRIDDEN = (
    _resolve_color_key_mapping_from_dialog(PARTICIPANT, session_dlg.data[9])
)
apply_color_key_mapping(COLOR_KEY_MAPPING)
RESPONSE_DEVICE = session_dlg.data[10]
DEVICE_NAME_ASSIGNED, DEVICE_NAME, DEVICE_NAME_OVERRIDDEN = _resolve_device_name_from_dialog(
    session_dlg.data[11]
)
COLOR_MAP_LAYOUT_ASSIGNED, COLOR_MAP_LAYOUT, COLOR_MAP_LAYOUT_OVERRIDDEN = (
    _resolve_color_map_layout_from_dialog(session_dlg.data[12])
)
MONITOR_NAME = str(session_dlg.data[13]).strip() or DEFAULT_MONITOR_NAME

# Post-dialog checks (order matters):
# 1) unexpected session number, 2) repeated data for same participant+session
_confirm_unexpected_session(
    PARTICIPANT, SESSION, _participant_data_dir(PARTICIPANT)
)

PARTICIPANT_DATA_DIR = _participant_data_dir(PARTICIPANT)
(
    _out_trials_path,
    _out_metadata_path,
    DATA_FILE_STEM,
    REPEAT_DATA_NOTE,
    REPEAT_REASON,
) = _resolve_data_output_paths(PARTICIPANT, SESSION, PARTICIPANT_DATA_DIR)

SESSION_PHASE = session_phase_for(SESSION, PARTICIPANT)
DISPLAY_CONFIG = get_session_display_config(SESSION)
INCLUDE_BURNIN = INCLUDE_BURNIN_BLOCK  # hook for future session/day rules
INCLUDE_PM_PRACTICE = (
    session_needs_pm_practice_block(SESSION) and not DEBUG_CONFIG["enabled"]
)

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
        include_pm_practice_block=INCLUDE_PM_PRACTICE,
    )
N_TRIALS = len(trials)
SESSION_N_BLOCKS = max(t["block"] for t in trials) if trials else N_BLOCKS
_block_trial_counts = {}
for _t in trials:
    _block_trial_counts[_t["block"]] = _t["trial_in_block"]

# print(json.dumps(trials, indent=2))  # full pre-designed session structure

serial_response_box = None
simulate_response_box = (
    DEBUG_CONFIG["enabled"]
    and DEBUG_CONFIG.get("simulate_response_box", True)
    and RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE
)
if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE:
    if simulate_response_box:
        print(
            f"DEBUG: simulating {RESPONSE_DEVICE_SELF_MADE}; "
            "serial response box will not be opened."
        )
    else:
        serial_response_box = _open_self_made_response_box()


# =============================================================================
# WINDOW AND STIMULI
# =============================================================================

mon = monitors.Monitor(MONITOR_NAME)
mon.setSizePix(WIN_SIZE_PIX)
mon.setWidth(MONITOR_WIDTH_CM)
mon.setDistance(MONITOR_DISTANCE_CM)

win = visual.Window(
    size=WIN_SIZE_PIX,
    fullscr=DEBUG_CONFIG["full_screen"],
    units=USE_UNITS,
    color=BACKGROUND_COLOR,
    colorSpace=COLOR_SPACE,
    monitor=mon,
)
win.setMouseVisible(False)

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
    fontFiles=(
        [str(INSTRUCTION_FONT_CJK)] if INSTRUCTION_FONT_CJK.exists() else []
    ),
)
DEFAULT_INSTRUCTION_FONT = instructions.font

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
keymap_stims = []
for key in KEY_SLOT_KEYS:
    pos = keymap_positions[key]
    square = visual.Rect(
        win,
        width=RESPONSE_COLOR_SIZE_DEG,
        height=RESPONSE_COLOR_SIZE_DEG,
        pos=pos,
        fillColor=COLORS[key_to_color[key]],
        colorSpace=COLOR_SPACE,
        lineColor=None,
        units=USE_UNITS,
    )
    label = None
    if RESPONSE_DEVICE != RESPONSE_DEVICE_SELF_MADE:
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
            colorSpace=COLOR_SPACE,
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
            colorSpace=COLOR_SPACE,
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
            colorSpace=COLOR_SPACE,
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
            colorSpace=COLOR_SPACE,
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
            colorSpace=COLOR_SPACE,
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


def _set_instruction_display(
    text: str,
    *,
    language: str = "en",
    use_cjk_font: bool = False,
) -> None:
    instructions.setText(text)
    if use_cjk_font and INSTRUCTION_FONT_CJK.exists():
        instructions.font = INSTRUCTION_FONT_CJK_NAME
    else:
        instructions.font = DEFAULT_INSTRUCTION_FONT


def _show_instruction_text(text: str, *, use_cjk_font: bool = False, language: str = "en"):
    _set_instruction_display(text, language=language, use_cjk_font=use_cjk_font)
    instructions.draw()
    win.flip()
    return _wait_space_or_exit()


def _show_session1_first_instruction() -> bool:
    """Session 1 opening instruction with English / 中文 / dansk switching."""
    global SESSION1_INSTRUCTION_LANGUAGE
    language = "en"
    while True:
        body = _load_session1_instruction(language)
        _set_instruction_display(
            INSTRUCTION_LANGUAGE_SWITCHER[language] + body,
            language=language,
            use_cjk_font=True,
        )
        instructions.draw()
        win.flip()
        while True:
            keys = event.waitKeys(keyList=[START_KEY, QUIT_KEY, "c", "d", "e"])
            if not keys:
                continue
            key = keys[0]
            if key == "c" and language != "zh":
                language = "zh"
                break
            if key == "d" and language != "da":
                language = "da"
                break
            if key == "e" and language != "en":
                language = "en"
                break
            if key == START_KEY:
                SESSION1_INSTRUCTION_LANGUAGE = language
                return True
            if key == QUIT_KEY and _confirm_exit_or_continue():
                return False


def _trials_in_block(block_number):
    if block_number == BURNIN_BLOCK_NUMBER:
        return BURNIN_TRIALS_PER_BLOCK
    if block_number == PM_PRACTICE_BLOCK_NUMBER:
        return TRIALS_PER_BLOCK
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
    if trial.get("pm_practice_block"):
        feedback4.setText(
            "Practice     Trial  "
            + str(trial_in_block)
            + " / "
            + str(TRIALS_PER_BLOCK)
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

if SESSION == 1:
    if not _show_session1_first_instruction():
        win.close()
        core.quit()
elif not _show_instruction_text(_load_session_start_instruction(SESSION, PARTICIPANT)):
    win.close()
    core.quit()

if INCLUDE_BURNIN:
    if not _show_instruction_text(_load_instruction("instruction burnin intro.txt")):
        win.close()
        core.quit()

cum_reward = 0.0
prev_block = None
completed_normally = True
trial_index = 0
first_trial_save = True
csv_columns = None
exp_start_time_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
session_start_perf = time.perf_counter()
PARTICIPANT_DATA_DIR.mkdir(parents=True, exist_ok=True)
print(f"Trial data will be saved to: {_out_trials_path}")
print(f"Metadata will be saved to: {_out_metadata_path}")

for trial in trials:
    current_block = trial["block"]
    if prev_block is not None and current_block != prev_block:
        if prev_block == PM_PRACTICE_BLOCK_NUMBER and current_block == 1:
            if not _show_instruction_text(
                _load_session_instruction(SESSION, PARTICIPANT)
            ):
                completed_normally = False
                break
        elif prev_block == BURNIN_BLOCK_NUMBER and current_block == 1:
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
    trial_start_jitter_time_ms = FIXATION_TIME * 1000

    fixation.draw()
    win.flip()
    core.wait(FIXATION_TIME)

    event.clearEvents()
    trial_clock = core.Clock()
    trial_clock.reset()

    single_center = trial.get("single_center", DISPLAY_CONFIG.get("single_center", False))
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
            lineWidth=0 if is_nonfocal_pm_target else BORDER_LINE_WIDTH,
            colorSpace=COLOR_SPACE,
            edges=CIRCLE_EDGES,
        )
        inner_circle = visual.Circle(
            win,
            radius=INNER_CIRCLE_RADIUS,
            pos=pos,
            fillColor=COLORS["white"],
            lineColor=None,
            colorSpace=COLOR_SPACE,
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
                    colorSpace=COLOR_SPACE,
                    lineWidth=DASHED_OUTLINE_LINE_WIDTH,
                ).draw()

    show_keymap = (
        DISPLAY_CONFIG.get("show_color_keymap", True)
        and not trial.get("pm_practice_block")
    )
    if show_keymap:
        for square, label in keymap_stims:
            square.draw()
            if label is not None:
                label.draw()

    if serial_response_box is not None:
        serial_response_box.reset_input_buffer()

    trial_clock.reset()
    win.flip()
    cue_time = trial_clock.getTime()
    if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE and serial_response_box is not None:
        serial_response_box.write(b"S")
        serial_response_box.flush()

    if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE and serial_response_box is not None:
        self_made_response = _wait_for_self_made_response_box(
            serial_response_box, trial_clock, MAX_RESPONSE_TIME
        )
        keys = [self_made_response] if self_made_response else None
    else:
        keys = event.waitKeys(
            keyList=ALL_RESPONSE_KEYS,
            maxWait=MAX_RESPONSE_TIME,
            timeStamped=trial_clock,
        )

    max_reward_ccrp = max(trial["reward_values"]) if trial["reward_values"] else 0
    is_pm_trial = trial["is_pm_trial"]
    actual_reward = 0
    pressed_key = None
    rt = None
    rt_computer_clock_ms = None
    timed_out = keys is None

    if keys:
        pin_or_key = keys[0][0]
        response_time = keys[0][1]
        if pin_or_key == QUIT_KEY:
            if _confirm_exit_or_continue():
                completed_normally = False
                break
            prev_block = current_block
            trial_index += 1
            continue
        rt_computer_clock_ms = (response_time - cue_time) * 1000
        if RESPONSE_DEVICE == RESPONSE_DEVICE_SELF_MADE and serial_response_box is not None:
            rt = keys[0][2]
            pressed_key = SELF_MADE_PIN_TO_KEY.get(pin_or_key)
        else:
            pressed_key = pin_or_key
            rt = rt_computer_clock_ms
    else:
        rt = MAX_RESPONSE_TIME * 1000
        rt_computer_clock_ms = rt

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
    end_trial_time = trial_clock.getTime()

    now = datetime.now()
    trial_wall_clock_str = (
        now.strftime("%Y-%m-%d %H:%M:%S") + f".{now.microsecond // 1000:03d}"
    )
    session_elapsed_sec = time.perf_counter() - session_start_perf
    position_to_color_id, position_to_reward = _trial_design_maps(trial)
    row = _build_trial_row(
        trial=trial,
        position_to_color_id=position_to_color_id,
        position_to_reward=position_to_reward,
        pressed_key=pressed_key,
        rt_ms=rt,
        rt_computer_clock_ms=rt_computer_clock_ms,
        cue_time=cue_time,
        end_trial_time=end_trial_time,
        actual_reward=actual_reward,
        max_reward=max_reward,
        cum_reward=cum_reward,
        trial_index=trial_index,
        trial_start_jitter_time_ms=trial_start_jitter_time_ms,
        trial_wall_clock_str=trial_wall_clock_str,
        session_elapsed_sec=session_elapsed_sec,
        trial_note=REPEAT_DATA_NOTE if trial_index == 0 and REPEAT_DATA_NOTE else "",
    )

    if csv_columns is None:
        csv_columns = list(row.keys())
    with open(
        _out_trials_path,
        "w" if first_trial_save else "a",
        encoding="utf-8",
        newline="",
    ) as fp:
        writer = csv.DictWriter(fp, fieldnames=csv_columns)
        if first_trial_save:
            writer.writeheader()
            metadata = _build_metadata(
                exp_start_time_str=exp_start_time_str,
                n_blocks=SESSION_N_BLOCKS,
                n_trials_total=N_TRIALS,
                n_trials_per_block=TRIALS_PER_BLOCK,
                include_burnin_block=INCLUDE_BURNIN,
                include_pm_practice_block=INCLUDE_PM_PRACTICE,
                display_config=DISPLAY_CONFIG,
                dat_columns=csv_columns,
            )
            with open(_out_metadata_path, "w", encoding="utf-8") as meta_fp:
                json.dump(metadata, meta_fp, indent=2, ensure_ascii=False)
        writer.writerow(row)
    first_trial_save = False

    prev_block = current_block
    trial_index += 1


# =============================================================================
# END
# =============================================================================

if completed_normally:
    end_text.draw()
    win.flip()
    event.waitKeys()

win.close()
if serial_response_box is not None:
    serial_response_box.close()
core.quit()
