"""
Simple PsychoPy version of the multiple-cue prospective memory experiment.

This is intentionally kept small and readable:
- 10 total trials
- 2 focal PM trials: one circle turns orange
- 2 nonfocal PM trials: one circle has a dashed outline
- keyboard only
"""

import math
import random
from psychopy import visual, core, event


# =============================================================================
# CONFIG: CHANGE THESE VALUES FIRST
# =============================================================================

WINDOW_SIZE = (1000, 700)
FULL_SCREEN = False
BACKGROUND_COLOR = "black"
COLOR_SPACE = "rgb255"

N_TRIALS = 10
FIXATION_TIME = 0.5
MAX_RESPONSE_TIME = 3.0
FEEDBACK_TIME = 0.7
ITI_TIME = 0.3

# Use PsychoPy "height" units so coordinates scale with the window height.
UNITS = "height"

CIRCLE_RADIUS = 0.08
INNER_CIRCLE_RADIUS = 0.045
REWARD_TEXT_HEIGHT = 0.055
DASHED_OUTLINE_RADIUS = 0.095
DASHED_OUTLINE_LINE_WIDTH = 3

POSITIONS = {
    "top": (0.0, 0.16),
    "bottom_left": (-0.18, -0.13),
    "bottom_right": (0.18, -0.13),
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

PM_KEY = "space"
QUIT_KEY = "escape"
ALL_RESPONSE_KEYS = list(COLOR_KEYS.values()) + [PM_KEY, QUIT_KEY]

PM_REWARD = 5


# =============================================================================
# TRIAL LIST: 10 SIMPLE TRIALS
# =============================================================================

# reward_values uses 0 for "empty inner circle" and 1/2/3 for displayed values.
# pm_type can be None, "focal", or "nonfocal".
trials = [
    {"reward_values": [1, 0, 0], "pm_type": None, "pm_position": None},
    {"reward_values": [0, 2, 0], "pm_type": None, "pm_position": None},
    {"reward_values": [0, 0, 3], "pm_type": "focal", "pm_position": "bottom_right"},
    {"reward_values": [2, 1, 0], "pm_type": None, "pm_position": None},
    {"reward_values": [3, 0, 1], "pm_type": "nonfocal", "pm_position": "top"},
    {"reward_values": [0, 3, 2], "pm_type": None, "pm_position": None},
    {"reward_values": [1, 0, 3], "pm_type": "focal", "pm_position": "bottom_left"},
    {"reward_values": [0, 1, 2], "pm_type": None, "pm_position": None},
    {"reward_values": [2, 0, 3], "pm_type": "nonfocal", "pm_position": "bottom_right"},
    {"reward_values": [0, 3, 0], "pm_type": None, "pm_position": None},
]

random.shuffle(trials)


# =============================================================================
# WINDOW AND STIMULI
# =============================================================================

win = visual.Window(
    size=WINDOW_SIZE,
    fullscr=FULL_SCREEN,
    units=UNITS,
    color=BACKGROUND_COLOR,
    colorSpace=COLOR_SPACE,
)

fixation = visual.TextStim(win, text="+", color=COLORS["white"], colorSpace=COLOR_SPACE, height=0.06)

instructions = visual.TextStim(
    win,
    text=(
        "Choose the color circle with the highest reward value.\n\n"
        "Red = N     Blue = J     Green = K\n\n"
        "PM rule: if one circle is ORANGE, or if one circle has a DASHED outline,\n"
        "press SPACE instead of the color key.\n\n"
        "Press SPACE to start."
    ),
    color=COLORS["white"],
    colorSpace=COLOR_SPACE,
    height=0.035,
    wrapWidth=0.8,
)

feedback = visual.TextStim(win, text="", color=COLORS["white"], colorSpace=COLOR_SPACE, height=0.045)


# =============================================================================
# EXPERIMENT START
# =============================================================================

instructions.draw()
win.flip()
event.waitKeys(keyList=[PM_KEY])

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

        # Focal PM cue: replace the normal task color with orange.
        circle_color = normal_color
        if trial["pm_type"] == "focal" and position_name == trial["pm_position"]:
            circle_color = "orange"

        outer_circle = visual.Circle(
            win,
            radius=CIRCLE_RADIUS,
            pos=pos,
            fillColor=COLORS[circle_color],
            lineColor=None,
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
        inner_circle.draw()
        reward_text.draw()

        # Nonfocal PM cue: draw a dashed white outline around one normal circle.
        # PsychoPy does not have a dashed-circle option, so each dash is a short
        # white line between two nearby points on an invisible circle.
        if trial["pm_type"] == "nonfocal" and position_name == trial["pm_position"]:
            for dash_start in range(0, 360, 24):
                angle1 = math.radians(dash_start)
                angle2 = math.radians(dash_start + 12)
                x1 = pos[0] + DASHED_OUTLINE_RADIUS * math.cos(angle1)
                y1 = pos[1] + DASHED_OUTLINE_RADIUS * math.sin(angle1)
                x2 = pos[0] + DASHED_OUTLINE_RADIUS * math.cos(angle2)
                y2 = pos[1] + DASHED_OUTLINE_RADIUS * math.sin(angle2)
                visual.Line(
                    win,
                    start=(x1, y1),
                    end=(x2, y2),
                    lineColor=COLORS["white"],
                    lineColorSpace=COLOR_SPACE,
                    lineWidth=DASHED_OUTLINE_LINE_WIDTH,
                ).draw()

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
