"""
Simple PsychoPy version of the multiple-cue prospective memory experiment.

This is intentionally kept small and readable:
- 10 total trials
- 2 focal PM trials: circle keeps its task color; an orange in-channel marker is added
- 2 nonfocal PM trials: one circle has a dashed outline
- keyboard only
"""

import math
import random
from psychopy import visual, core, event, monitors


# =============================================================================
# CONFIG: CHANGE THESE VALUES FIRST
# =============================================================================

# Keep the normal window ratio, but allow easy scaling for high-res displays.
BASE_WINDOW_SIZE = (1000, 700)
WINDOW_SCALE = 1.35
WINDOW_SIZE = (
    int(BASE_WINDOW_SIZE[0] * WINDOW_SCALE),
    int(BASE_WINDOW_SIZE[1] * WINDOW_SCALE),
)
FULL_SCREEN = False
# Gray background (non-black).
BACKGROUND_COLOR = (128, 128, 128)
COLOR_SPACE = "rgb255"

N_TRIALS = 10
FIXATION_TIME = 0.5
MAX_RESPONSE_TIME = 3.0
FEEDBACK_WAIT_TIME = 1.5
ITI_TIME = 0.3
REWARD_MONEY_FACTOR = 0.05
STIMULUS_OPACITY = 1.0

# Pseudo block structure (placeholder until full session blocks are wired up).
N_BLOCKS = 2
TRIALS_PER_BLOCK_MAIN = 3
FIRST_WARMUP_TRIALS = 1
OTHER_WARMUP_TRIALS = 1
INCLUDE_BURNIN_BLOCK = True
BURNIN_TRIALS_PER_BLOCK = 2
BURNIN_BLOCK_NUMBER = 0
INSTRUCTION_LETTER_SIZE_DEG = 0.6

# Use the same "deg + StimFactor-like" sizing style as the example file.
UNITS = "deg"
BASE_STIM_FACTOR = 0.04
STIM_SCALE = 1.55
STIM_FACTOR = BASE_STIM_FACTOR * STIM_SCALE
INSTRUCTION_WRAP_WIDTH_DEG = 800 * STIM_FACTOR
# Keep disk placement independent from STIM_SCALE so the triangle geometry
# stays like before (only disk size changes, not disk-to-disk distance).
POSITION_SCALE = 1.0
POSITION_FACTOR = BASE_STIM_FACTOR * POSITION_SCALE
MONITOR_NAME = "testmain_demo_monitor"
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60

# Circle and number size assignments match the example style.
CIRCLE_RADIUS = 20 * STIM_FACTOR       # 0.8
INNER_CIRCLE_RADIUS = 8.75 * STIM_FACTOR  # 0.35
REWARD_TEXT_HEIGHT = 14 * STIM_FACTOR  # 0.56
BORDER_LINE_WIDTH = 4
DASHED_OUTLINE_LINE_WIDTH = 5

# Focal PM markers are orange features added inside/on the task-colored circle.
# Supported styles: inner_dot, center_ring, small_patch, halo, marker_bg
FOCAL_PM_INNER_DOT_RADIUS = 3.5 * STIM_FACTOR
FOCAL_PM_RING_RADIUS = (CIRCLE_RADIUS + INNER_CIRCLE_RADIUS) / 2
FOCAL_PM_RING_LINE_WIDTH = 5
FOCAL_PM_PATCH_RADIUS = 5 * STIM_FACTOR
FOCAL_PM_PATCH_OFFSET = 0.55 * CIRCLE_RADIUS
FOCAL_PM_HALO_RADIUS = CIRCLE_RADIUS * 1.08
FOCAL_PM_HALO_LINE_WIDTH = 7
FOCAL_PM_MARKER_BG_RADIUS = INNER_CIRCLE_RADIUS * 0.72

# Isosceles triangle layout:
# - top is centered on x=0
# - bottom points are symmetric at x=±BOTTOM_X
# - both bottom points share the same y
# This keeps equal left/right side lengths and makes bottom disks less crowded.
TOP_Y = 60 * POSITION_FACTOR
BOTTOM_Y = -50 * POSITION_FACTOR
BOTTOM_X = 60 * POSITION_FACTOR
POSITIONS = {
    "top": (0.0, TOP_Y),
    "bottom_left": (-BOTTOM_X, BOTTOM_Y),
    "bottom_right": (BOTTOM_X, BOTTOM_Y),
}

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

PM_KEY = "d"
START_KEY = "space"
QUIT_KEY = "escape"
ALL_RESPONSE_KEYS = list(COLOR_KEYS.values()) + [PM_KEY, QUIT_KEY]

PM_REWARD = 5

# Feedback (match multiplecue-responsebox/exp/testmain.py: Feedback1-4 layout)
FEEDBACK_LETTER_SIZE_DEG = 50 * STIM_FACTOR
FEEDBACK1_POS_DEG = (0, 70 * STIM_FACTOR)
FEEDBACK2_POS_DEG = (0, -70 * STIM_FACTOR)
FEEDBACK3_POS_DEG = (0, -140 * STIM_FACTOR)
FEEDBACK4_POS_DEG = (0, -200 * STIM_FACTOR)
FEEDBACK_TEXT_COLOR = COLORS["white"]
TOO_SLOW_TEXT = "TOO SLOW!"

# Color-key mapping legend (NJK keyboard-style arrangement).
# These are directly aligned with the example file style.
KEYMAP_SQUARE_SIZE = 30 * STIM_FACTOR       # same as ResponseColorSize
KEYMAP_TEXT_HEIGHT = 0.55 * KEYMAP_SQUARE_SIZE
KEYMAP_DISTANCE = 50 * STIM_FACTOR          # same as ResponseColorDistance
KEYMAP_EXTRA_DOWN = 0.75 * KEYMAP_DISTANCE
KEYMAP_BASE_Y = (-150 * STIM_FACTOR) - KEYMAP_EXTRA_DOWN
KEYMAP_ROW_OFFSET = 0.6 * KEYMAP_DISTANCE   # same row spacing style as example


# =============================================================================
# TRIAL LIST: 10 SIMPLE TRIALS
# =============================================================================

# reward_values uses 0 for "empty inner circle" and 1/2/3 for displayed values.
# pm_type can be None, "focal", or "nonfocal".
# focal_pm_style applies only on focal trials (see FOCAL_PM_* constants above).
trials = [
    {"reward_values": [1, 0, 0], "pm_type": None, "pm_position": None},
    {"reward_values": [0, 2, 0], "pm_type": None, "pm_position": None},
    {
        "reward_values": [0, 0, 3],
        "pm_type": "focal",
        "pm_position": "bottom_right",
        "focal_pm_style": "inner_dot",
    },
    {"reward_values": [2, 1, 0], "pm_type": None, "pm_position": None},
    {"reward_values": [3, 0, 1], "pm_type": "nonfocal", "pm_position": "top"},
    {"reward_values": [0, 3, 2], "pm_type": None, "pm_position": None},
    {
        "reward_values": [1, 0, 3],
        "pm_type": "focal",
        "pm_position": "bottom_left",
        "focal_pm_style": "center_ring",
    },
    {"reward_values": [0, 1, 2], "pm_type": None, "pm_position": None},
    {"reward_values": [2, 0, 3], "pm_type": "nonfocal", "pm_position": "bottom_right"},
    {"reward_values": [0, 3, 0], "pm_type": None, "pm_position": None},
]

random.shuffle(trials)

# Manually force PM placement:
# - Trial 2 (index 1) is nonfocal
# - Trial 4 (index 3) is focal
# - Trial 6 (index 5) is nonfocal
# - Trial 8 (index 7) is focal
# - All other trials are normal (no PM cue)
nonfocal_trials = [t for t in trials if t["pm_type"] == "nonfocal"]
focal_trials = [t for t in trials if t["pm_type"] == "focal"]
normal_trials = [t for t in trials if t["pm_type"] is None]

forced_trials = []
for i in range(len(trials)):
    if i in (1, 5):
        forced_trials.append(nonfocal_trials.pop(0))
    elif i in (3, 7):
        forced_trials.append(focal_trials.pop(0))
    else:
        forced_trials.append(normal_trials.pop(0))

trials = forced_trials


def annotate_trials_with_pseudo_blocks(trial_list):
    """Add block metadata fields used by testmain.py feedback and block breaks."""
    annotated = []
    trial_index = 0

    if INCLUDE_BURNIN_BLOCK:
        for trial_in_block in range(1, BURNIN_TRIALS_PER_BLOCK + 1):
            trial = dict(trial_list[trial_index])
            trial_index += 1
            trial.update(
                block=BURNIN_BLOCK_NUMBER,
                trial_in_block=trial_in_block,
                warm_up=0,
                burn_in_block=1,
            )
            annotated.append(trial)

    trials_remaining = len(trial_list) - trial_index
    trials_per_block = trials_remaining // N_BLOCKS
    # Any remainder goes into the final block.
    for block_number in range(1, N_BLOCKS + 1):
        if block_number == N_BLOCKS:
            block_size = len(trial_list) - trial_index
        else:
            block_size = trials_per_block
        warmup_trials = FIRST_WARMUP_TRIALS if block_number == 1 else OTHER_WARMUP_TRIALS
        for trial_in_block in range(1, block_size + 1):
            trial = dict(trial_list[trial_index])
            trial_index += 1
            trial.update(
                block=block_number,
                trial_in_block=trial_in_block,
                warm_up=1 if trial_in_block <= warmup_trials else 0,
                burn_in_block=0,
            )
            annotated.append(trial)

    if trial_index != len(trial_list):
        raise ValueError("Pseudo block layout does not cover all demo trials.")

    return annotated


trials = annotate_trials_with_pseudo_blocks(trials)
N_TRIALS = len(trials)


# =============================================================================
# WINDOW AND STIMULI
# =============================================================================
# With units="deg", PsychoPy needs a monitor with known pixel size.
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
    text=(
        "Choose the color circle with the highest reward value.\n\n"
        "Red = N     Blue = J     Green = K\n\n"
        "PM rule: if one circle has an ORANGE marker (dot/ring/patch), or a DASHED outline,\n"
        "press D instead of the color key. Circle colors stay red/blue/green.\n\n"
        "Press SPACE to start."
    ),
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=0.6,
    wrapWidth=24,
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
    text="End of session!\n\n\nContact the Experimenter",
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
burnin_instruction_text = visual.TextStim(
    win,
    text=(
        "Burn-in block complete.\n\n"
        "This is a placeholder transition screen matching the full experiment.\n\n"
        "Press SPACE to continue to Block 1."
    ),
    color=FEEDBACK_TEXT_COLOR,
    colorSpace=COLOR_SPACE,
    height=INSTRUCTION_LETTER_SIZE_DEG,
    wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
    units=UNITS,
)

# -------------------------------------------------------------------------
# KEY MAPPING STIMULI (NJK keyboard arrangement)
# -------------------------------------------------------------------------
# 1) Compute a bottom-center anchor for the 3-key legend
# 2) Define raw NJK offsets (N lower row, J/K upper row and shifted right)
# 3) Re-center offsets so the 3-key cluster is truly centered at the anchor
keymap_center = (0.0, KEYMAP_BASE_Y)

top_row_y = KEYMAP_ROW_OFFSET
bottom_row_y = -KEYMAP_ROW_OFFSET

raw_key_offsets = {
    # N is on lower row; J/K are on upper row and shifted right.
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
    """After ESC: return True if user confirms exit (second ESC), False to continue."""
    esc_confirm_text.draw()
    win.flip()
    keys = event.waitKeys(keyList=[QUIT_KEY, START_KEY])
    return bool(keys and keys[0] == QUIT_KEY)


def _wait_space_or_exit():
    """Wait for space to continue. Return False if user exits via double ESC."""
    while True:
        keys = event.waitKeys(keyList=[START_KEY, QUIT_KEY])
        if not keys:
            continue
        if keys[0] == START_KEY:
            return True
        if keys[0] == QUIT_KEY and _confirm_exit_or_continue():
            return False


def _show_instruction_screen(instruction_stim):
    """Draw an instruction screen and wait for SPACE (or double-ESC exit)."""
    instruction_stim.draw()
    win.flip()
    return _wait_space_or_exit()


def _trials_in_block(block_number):
    """Total trials expected in a pseudo block, including warm-up trials."""
    if block_number == BURNIN_BLOCK_NUMBER:
        return BURNIN_TRIALS_PER_BLOCK
    warmup_trials = FIRST_WARMUP_TRIALS if block_number == 1 else OTHER_WARMUP_TRIALS
    return warmup_trials + TRIALS_PER_BLOCK_MAIN


def _set_feedback4_text(trial):
    """Match multiplecue-responsebox feedback4 formatting."""
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
        + str(N_BLOCKS)
        + "     Trial  "
        + str(trial_in_block)
        + " / "
        + str(n_in_block)
    )


# =============================================================================
# EXPERIMENT START
# =============================================================================

instructions.draw()
win.flip()
if not _wait_space_or_exit():
    win.close()
    core.quit()

if INCLUDE_BURNIN_BLOCK:
    # Placeholder burn-in preamble, matching the full experiment's extra instruction screen.
    burnin_intro_text = visual.TextStim(
        win,
        text=(
            "Pseudo burn-in block.\n\n"
            "This placeholder block mirrors the burn-in transition used in the full task.\n\n"
            "Press SPACE to begin."
        ),
        color=FEEDBACK_TEXT_COLOR,
        colorSpace=COLOR_SPACE,
        height=INSTRUCTION_LETTER_SIZE_DEG,
        wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
        units=UNITS,
    )
    if not _show_instruction_screen(burnin_intro_text):
        win.close()
        core.quit()

cum_reward = 0.0
position_names = list(POSITIONS.keys())
color_names = list(COLOR_KEYS.keys())
prev_block = None
completed_normally = True

for trial_number, trial in enumerate(trials, start=1):
    current_block = trial["block"]
    if prev_block is not None and current_block != prev_block:
        if prev_block == BURNIN_BLOCK_NUMBER and current_block == 1:
            if not _show_instruction_screen(burnin_instruction_text):
                completed_normally = False
                break
        else:
            block_break_text.setText(
                f"End of Block {prev_block}.\n\n"
                f"Next: Block {current_block} of {N_BLOCKS}.\n\n"
                "Press SPACE to continue."
            )
            block_break_text.draw()
            win.flip()
            if not _wait_space_or_exit():
                completed_normally = False
                break

    # Randomize which color appears at each position, so location does not predict response.
    trial_colors = color_names[:]
    random.shuffle(trial_colors)

    # -------------------------------------------------------------------------
    # FIXATION
    # -------------------------------------------------------------------------
    fixation.draw()
    win.flip()
    core.wait(FIXATION_TIME)

    # -------------------------------------------------------------------------
    # STIMULUS DISPLAY
    # -------------------------------------------------------------------------
    event.clearEvents()

    for i, position_name in enumerate(position_names):
        pos = POSITIONS[position_name]
        normal_color = trial_colors[i]
        reward_value = trial["reward_values"][i]
        is_focal_pm_target = (
            trial["pm_type"] == "focal" and position_name == trial["pm_position"]
        )
        is_nonfocal_pm_target = (
            trial["pm_type"] == "nonfocal" and position_name == trial["pm_position"]
        )
        focal_pm_style = trial.get("focal_pm_style", "inner_dot")

        # Focal PM keeps the task color; an orange marker is added later.
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

        # Nonfocal PM cue: draw a dashed white outline on the same border radius
        # as the original circle border (not a bigger outside circle).
        # PsychoPy does not have a dashed-circle option, so each dash is a short
        # white line between two nearby points on an invisible circle.
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

    # Draw color-key mapping on every trial.
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

    # -------------------------------------------------------------------------
    # RESPONSE SCORING
    # -------------------------------------------------------------------------
    max_reward_ccrp = max(trial["reward_values"]) if trial["reward_values"] else 0
    is_pm_trial = trial["pm_type"] is not None
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

    # -------------------------------------------------------------------------
    # FEEDBACK SCREEN (match multiplecue-responsebox/exp/testmain.py)
    # -------------------------------------------------------------------------
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
