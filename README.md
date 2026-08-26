# multiplecue-prospectiveM (PMCP)

Prospective-memory extension of the multiple-cue reward selection task (CCRP). Participants choose among rewarded colors; on some trials they must instead make a left-hand PM response to a special cue (focal: orange ring; nonfocal: dashed outline).

**Question:** are PM costs better explained by shared capacity inside MIS, threshold/control adjustments, or a hybrid?

## Design (short)

| Phase | Sessions | Notes |
| ----- | -------- | ----- |
| Practice | 1–5 | Ongoing task only |
| Baseline | 6–12 | No PM |
| Focal / nonfocal PM | 13–19 and 20–26 | Order counterbalanced by subject ID |

Details: `exp/design.md`, `exp/trial_number_design.md`.

## Run

```bash
cd exp
python testmain_demo.py
```

Main entry point: **`exp/testmain_demo.py`** (PsychoPy; keyboard or self-made serial response box). Session, device, and language are set in the startup dialog / script defaults.

## Layout

- `exp/` — experiment code, instructions, stimuli, design notes
- `exp/Instructions/` — EN / ZH / DA instruction texts
- `exp/data_written/` — local session output (usually gitignored)
- Ethics materials at repo root

## Related repos

- [multiplecue-responsebox](https://github.com/naszhu/multiplecue-responsebox) — base CCRP ongoing task (no PM)
- [multiplecue-RTfit](https://github.com/naszhu/multiplecue-RTfit) — MIS+LBA model fitting (mainly on CCRP data)
