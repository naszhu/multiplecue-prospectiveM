#!/usr/bin/env python3
"""Shared Ishihara color-vision screening (plates 1–9).

Used by:
  - testmain_demo.py (session-1 gate)
  - test_ishihara_color_vision.py (standalone subject screening)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from psychopy import visual, core, event

EXP_DIR = Path(__file__).resolve().parent
ISHIHARA_DIR = EXP_DIR / "stimuli" / "ishihara"
ISHIHARA_PLATES_JSON = ISHIHARA_DIR / "plates.json"
ISHIHARA_FAIL_ERRORS = 3
ISHIHARA_PLATE_SIZE_DEG = 12.0
ISHIHARA_SOURCE_CITATION = (
    "Martin Krzywinski Ishihara's Tests for Colour Deficiency lowres v1.0.0 "
    "(https://mk.bcgsc.ca/ishihara-tests-for-colour-deficiency/)"
)

START_KEY = "space"
QUIT_KEY = "escape"
_EXPERIMENTER_SKIP_KEY = "p"
COLOR_SPACE = "rgb255"
USE_UNITS = "deg"
WHITE = (255, 255, 255)
INSTRUCTION_LETTER_SIZE_DEG = 0.6
INSTRUCTION_WRAP_WIDTH_DEG = 32.0  # 800 * 0.04


def load_plate_defs() -> list[dict]:
    if not ISHIHARA_PLATES_JSON.is_file():
        raise SystemExit(f"Missing Ishihara plate key file: {ISHIHARA_PLATES_JSON}")
    with ISHIHARA_PLATES_JSON.open(encoding="utf-8") as fp:
        payload = json.load(fp)
    plates = payload.get("plates")
    if not isinstance(plates, list) or not plates:
        raise SystemExit(f"Invalid Ishihara plate key file: {ISHIHARA_PLATES_JSON}")
    return plates


def standalone_result_path(out_dir: Path, participant: str) -> Path:
    return out_dir / f"PMCP_subj{participant}_ishihara_standalone.json"


def session_log_path(out_dir: Path, participant: str) -> Path:
    return out_dir / f"PMCP_subj{participant}_session_log.txt"


def append_session_log(log_path: Path, lines: list[str]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fp:
        for line in lines:
            fp.write(line + "\n")


def write_result(path: Path, result: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fp:
        json.dump(result, fp, indent=2, ensure_ascii=False)
    return path


def load_standalone_result(out_dir: Path, participant: str) -> dict | None:
    path = standalone_result_path(out_dir, participant)
    if not path.is_file():
        return None
    try:
        with path.open(encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return None


def _experimenter_skip_confirm(win) -> bool:
    """Experimenter-only two-step skip confirm (second P confirms)."""
    confirm = visual.TextStim(
        win,
        text="Skip color vision screening?\n\nPress SPACE to continue the test.",
        color=WHITE,
        colorSpace=COLOR_SPACE,
        height=INSTRUCTION_LETTER_SIZE_DEG,
        wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
        units=USE_UNITS,
    )
    while True:
        confirm.draw()
        win.flip()
        keys = event.waitKeys(
            keyList=[_EXPERIMENTER_SKIP_KEY, START_KEY, QUIT_KEY],
            maxWait=0.5,
        )
        if not keys:
            continue
        key = keys[0]
        if key == _EXPERIMENTER_SKIP_KEY:
            return True
        if key in (START_KEY, QUIT_KEY):
            return False


def _confirm_exit(win) -> bool:
    confirm = visual.TextStim(
        win,
        text="Exit color vision test?\n\nESC = yes, exit\nSPACE = no, continue",
        color=WHITE,
        colorSpace=COLOR_SPACE,
        height=INSTRUCTION_LETTER_SIZE_DEG,
        wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
        units=USE_UNITS,
    )
    while True:
        confirm.draw()
        win.flip()
        keys = event.waitKeys(keyList=[QUIT_KEY, START_KEY], maxWait=0.5)
        if not keys:
            continue
        return keys[0] == QUIT_KEY


def _wait_space_or_exit(win, redraw_stim) -> str:
    """Return 'start', 'exit', or 'skip'."""
    while True:
        redraw_stim.draw()
        win.flip()
        keys = event.waitKeys(
            keyList=[START_KEY, QUIT_KEY, _EXPERIMENTER_SKIP_KEY],
            maxWait=0.5,
        )
        if not keys:
            continue
        key = keys[0]
        if key == START_KEY:
            return "start"
        if key == _EXPERIMENTER_SKIP_KEY:
            if _experimenter_skip_confirm(win):
                return "skip"
            continue
        if key == QUIT_KEY and _confirm_exit(win):
            return "exit"


def _collect_digit_response(
    win,
    *,
    plate_stim: visual.ImageStim,
    prompt_stim: visual.TextStim,
    answer_stim: visual.TextStim,
) -> str | None:
    typed = ""
    digit_keys = [str(d) for d in range(10)] + [f"num_{d}" for d in range(10)]
    key_list = digit_keys + ["backspace", "return", "enter", QUIT_KEY, _EXPERIMENTER_SKIP_KEY]

    while True:
        plate_stim.draw()
        prompt_stim.draw()
        answer_stim.setText(typed if typed else "_")
        answer_stim.draw()
        win.flip()

        keys = event.waitKeys(keyList=key_list, maxWait=0.5)
        if not keys:
            continue
        key = keys[0]
        if key == _EXPERIMENTER_SKIP_KEY:
            if _experimenter_skip_confirm(win):
                return "__SKIP__"
            continue
        if key == QUIT_KEY:
            if _confirm_exit(win):
                return None
            continue
        if key in ("return", "enter"):
            return typed
        if key == "backspace":
            typed = typed[:-1]
            continue
        if key.startswith("num_") and len(key) == 5 and key[-1].isdigit():
            typed += key[-1]
        elif key.isdigit():
            typed += key


def run_ishihara_screening(
    win,
    *,
    participant: str,
    session: int | None = None,
    source_mode: str = "standalone",
) -> dict:
    """Show demo plate 1 then scored plates 2–9; return result dict."""
    plate_defs = load_plate_defs()
    base = {
        "skipped": False,
        "aborted": False,
        "passed": None,
        "failed": None,
        "n_errors": None,
        "fail_threshold": ISHIHARA_FAIL_ERRORS,
        "plates": [],
        "source": ISHIHARA_SOURCE_CITATION,
        "source_mode": source_mode,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "participant": participant,
        "session": session,
    }

    intro = visual.TextStim(
        win,
        text=(
            "Color vision screening\n\n"
            "You will see several colored plates.\n"
            "Type the number you see, then press ENTER.\n"
            "If you see nothing, press ENTER with an empty answer.\n\n"
            "Press SPACE to begin."
        ),
        color=WHITE,
        colorSpace=COLOR_SPACE,
        height=INSTRUCTION_LETTER_SIZE_DEG,
        wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
        units=USE_UNITS,
    )
    intro_action = _wait_space_or_exit(win, intro)
    if intro_action == "exit":
        base["aborted"] = True
        return base
    if intro_action == "skip":
        base["skipped"] = True
        return base

    prompt_stim = visual.TextStim(
        win,
        text="Type the number you see, then ENTER (blank ENTER if none)",
        pos=(0, -8.5),
        color=WHITE,
        colorSpace=COLOR_SPACE,
        height=0.45,
        wrapWidth=INSTRUCTION_WRAP_WIDTH_DEG,
        units=USE_UNITS,
    )
    answer_stim = visual.TextStim(
        win,
        text="_",
        pos=(0, -9.5),
        color=WHITE,
        colorSpace=COLOR_SPACE,
        height=0.7,
        units=USE_UNITS,
    )

    plate_rows: list[dict] = []
    n_errors = 0
    for plate in plate_defs:
        plate_id = int(plate["id"])
        expected = str(plate["expected"]).strip()
        scored = bool(plate.get("scored", True))
        image_path = ISHIHARA_DIR / str(plate["file"])
        if not image_path.is_file():
            raise SystemExit(f"Missing Ishihara plate image: {image_path}")

        plate_stim = visual.ImageStim(
            win,
            image=str(image_path),
            size=(ISHIHARA_PLATE_SIZE_DEG, ISHIHARA_PLATE_SIZE_DEG),
            units=USE_UNITS,
            pos=(0, 0.5),
        )
        response = _collect_digit_response(
            win,
            plate_stim=plate_stim,
            prompt_stim=prompt_stim,
            answer_stim=answer_stim,
        )
        if response is None:
            base["aborted"] = True
            base["n_errors"] = n_errors
            base["plates"] = plate_rows
            return base
        if response == "__SKIP__":
            base["skipped"] = True
            base["n_errors"] = n_errors
            base["plates"] = plate_rows
            return base

        response_norm = response.strip()
        correct = response_norm == expected
        if scored and not correct:
            n_errors += 1
        plate_rows.append(
            {
                "plate_id": plate_id,
                "file": plate["file"],
                "expected": expected,
                "response": response_norm,
                "correct": correct,
                "scored": scored,
            }
        )
        win.flip()
        core.wait(0.25)

    failed = n_errors >= ISHIHARA_FAIL_ERRORS
    base.update(
        {
            "passed": not failed,
            "failed": failed,
            "n_errors": n_errors,
            "plates_scored": sum(1 for p in plate_defs if p.get("scored", True)),
            "plates": plate_rows,
            "color_vision": "not normal" if failed else "normal",
        }
    )
    return base


def format_session_log_lines(result: dict, *, label: str = "Ishihara") -> list[str]:
    """Lines to append to PMCP_subj*_session_log.txt."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mode = result.get("source_mode", "unknown")
    if result.get("skipped"):
        return [f"{ts}  {label} ({mode}): skipped; ColorVision={result.get('color_vision')!r}"]
    if result.get("aborted"):
        return [f"{ts}  {label} ({mode}): aborted"]
    if result.get("failed"):
        return [
            f"{ts}  {label} ({mode}): FAILED; "
            f"n_errors={result.get('n_errors')}; fail_threshold={result.get('fail_threshold')}; "
            f"ColorVision={result.get('color_vision')!r}"
        ]
    if result.get("passed"):
        return [
            f"{ts}  {label} ({mode}): passed; "
            f"n_errors={result.get('n_errors')}; ColorVision={result.get('color_vision')!r}"
        ]
    return [f"{ts}  {label} ({mode}): finished with unrecognized status"]
