#!/usr/bin/env python3
"""Standalone Ishihara color-vision screening for one subject.

Same plates/scoring as session-1 screening in testmain_demo.py.
Writes:
  - data_written/subj{ID}/PMCP_subj{ID}_ishihara_standalone.json
  - appends to data_written/subj{ID}/PMCP_subj{ID}_session_log.txt
    (same log file the formal experiment uses)
"""

from __future__ import annotations

from pathlib import Path

from psychopy import gui, visual, core, event, monitors

import ishihara_screening as ishihara

EXP_DIR = Path(__file__).resolve().parent
DATA_OUT_DIR = (EXP_DIR / "data_written").resolve()
MAX_PARTICIPANT_ID = 100
PARTICIPANT_CHOICES = ["test"] + [str(i) for i in range(1, MAX_PARTICIPANT_ID + 1)]

DEFAULT_MONITOR_NAME = "room1_a4"
MONITOR_CHOICES = [f"room1_a{i}" for i in range(1, 11)]
WIN_SIZE_PIX = (1920, 1080)
MONITOR_WIDTH_CM = 52
MONITOR_DISTANCE_CM = 60
BACKGROUND_COLOR = (128, 128, 128)
COLOR_SPACE = "rgb255"
USE_UNITS = "deg"


def main() -> int:
    dlg = gui.Dlg(title="Ishihara color vision test")
    dlg.addField("Participant", initial="1", choices=PARTICIPANT_CHOICES)
    dlg.addField("Monitor name", initial=DEFAULT_MONITOR_NAME, choices=MONITOR_CHOICES)
    dlg.show()
    if not dlg.OK:
        return 1

    participant = str(dlg.data[0]).strip()
    if participant not in PARTICIPANT_CHOICES:
        raise SystemExit(
            f"Participant must be 'test' or an integer from 1 to {MAX_PARTICIPANT_ID}."
        )
    monitor_name = str(dlg.data[1]).strip() or DEFAULT_MONITOR_NAME

    out_dir = DATA_OUT_DIR / f"subj{participant}"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = ishihara.session_log_path(out_dir, participant)
    result_path = ishihara.standalone_result_path(out_dir, participant)

    mon = monitors.Monitor(monitor_name)
    mon.setSizePix(WIN_SIZE_PIX)
    mon.setWidth(MONITOR_WIDTH_CM)
    mon.setDistance(MONITOR_DISTANCE_CM)

    win = visual.Window(
        size=WIN_SIZE_PIX,
        fullscr=True,
        units=USE_UNITS,
        color=BACKGROUND_COLOR,
        colorSpace=COLOR_SPACE,
        monitor=mon,
    )
    win.setMouseVisible(False)

    try:
        result = ishihara.run_ishihara_screening(
            win,
            participant=participant,
            session=None,
            source_mode="standalone",
        )
        ishihara.write_result(result_path, result)
        ishihara.append_session_log(log_path, ishihara.format_session_log_lines(result))

        if result.get("aborted"):
            msg = (
                f"Color vision screening aborted.\n\n"
                f"Result saved for subject {participant}.\n"
                "Press SPACE or ESC to exit."
            )
            exit_code = 1
        elif result.get("failed"):
            msg = (
                "Color vision screening: NOT NORMAL\n\n"
                f"Errors on scored plates: {result.get('n_errors')} "
                f"(fail if ≥ {ishihara.ISHIHARA_FAIL_ERRORS})\n\n"
                f"Result saved for subject {participant}.\n"
                "Press SPACE or ESC to exit."
            )
            exit_code = 2
        else:
            msg = (
                "Color vision screening: NORMAL\n\n"
                f"Errors on scored plates: {result.get('n_errors')}\n\n"
                f"Result saved for subject {participant}.\n"
                "Press SPACE or ESC to exit."
            )
            exit_code = 0

        end_text = visual.TextStim(
            win,
            text=msg,
            color=ishihara.WHITE,
            colorSpace=COLOR_SPACE,
            height=ishihara.INSTRUCTION_LETTER_SIZE_DEG,
            wrapWidth=ishihara.INSTRUCTION_WRAP_WIDTH_DEG,
            units=USE_UNITS,
        )
        end_text.draw()
        win.flip()
        event.waitKeys(keyList=[ishihara.START_KEY, ishihara.QUIT_KEY])

        status = "aborted" if exit_code == 1 else ("FAILED" if exit_code == 2 else "Passed")
        print(f"{status}. Wrote {result_path}")
        print(f"Appended to session log: {log_path}")
        return exit_code
    finally:
        win.close()
        core.quit()


if __name__ == "__main__":
    raise SystemExit(main())
