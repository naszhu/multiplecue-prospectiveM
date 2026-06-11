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
FEEDBACK_TIME = 0.7
ITI_TIME = 0.3

# Use the same "deg + StimFactor-like" sizing style as the example file.
UNITS = "deg"
BASE_STIM_FACTOR = 0.04
STIM_SCALE = 1.55
STIM_FACTOR = BASE_STIM_FACTOR * STIM_SCALE
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

feedback = visual.TextStim(
    win,
    text="",
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=0.7,
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


# =============================================================================
# EXPERIMENT START
# =============================================================================

instructions.draw()
win.flip()
event.waitKeys(keyList=[START_KEY])

total_points = 0
position_names = list(POSITIONS.keys())
color_names = list(COLOR_KEYS.keys())

for trial_number, trial in enumerate(trials, start=1):
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
    if keys is None:
        pressed_key = None
        rt = None
    else:
        pressed_key, rt = keys[0]

    if pressed_key == QUIT_KEY:
        break

    is_pm_trial = trial["pm_type"] is not None
    correct_pm_response = is_pm_trial and pressed_key == PM_KEY
    false_alarm = (not is_pm_trial) and pressed_key == PM_KEY

    if correct_pm_response:
        points = PM_REWARD
        feedback.text = f"PM CUE CAUGHT! +{points} points"
    elif is_pm_trial and pressed_key != PM_KEY:
        points = 0
        feedback.text = "MISSED PM CUE"
    elif false_alarm:
        points = 0
        feedback.text = "No PM cue present"
    elif pressed_key is None:
        points = 0
        feedback.text = "TOO SLOW"
    else:
        best_reward = max(trial["reward_values"])
        best_position_index = trial["reward_values"].index(best_reward)
        best_color = trial_colors[best_position_index]
        correct_key = COLOR_KEYS[best_color]

        if pressed_key == correct_key:
            points = best_reward
            feedback.text = f"+{points} points"
        else:
            points = 0
            feedback.text = f"Wrong key. Correct key was {correct_key.upper()}"

    total_points += points
    feedback.text += f"\nTotal points: {total_points}\nTrial {trial_number} / {N_TRIALS}"

    # -------------------------------------------------------------------------
    # FEEDBACK AND ITI
    # -------------------------------------------------------------------------
    feedback.draw()
    win.flip()
    core.wait(FEEDBACK_TIME)

    win.flip()
    core.wait(ITI_TIME)


# =============================================================================
# END
# =============================================================================

feedback.text = f"End of experiment.\n\nTotal points: {total_points}\n\nPress any key to close."
feedback.draw()
win.flip()
event.waitKeys()

win.close()
core.quit()
