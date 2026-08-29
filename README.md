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

## Version tags (pilot releases)

GitHub’s **Tags** tab lists refs by version number (highest first), not by commit date or when the tag was added. Chronological order of the experiment code:

| Tag | Commit | When run / notes |
| --- | ------ | ---------------- |
| [v1-pilot](https://github.com/naszhu/multiplecue-prospectiveM/releases/tag/v1-pilot) | `881c58a` | Jun 17 2026 — first pilot |
| [v1.1-pilot](https://github.com/naszhu/multiplecue-prospectiveM/releases/tag/v1.1-pilot) | `788327e` | Jun 18 2026 — 23 sessions (6 baseline + 6 PM per phase) |
| [v1.3-pilot](https://github.com/naszhu/multiplecue-prospectiveM/releases/tag/v1.3-pilot) | `5e629b7` | Jun 2026 line — 26 sessions (7+7), CCRP practice blocks; **no v1.2 tag** (see tag message) |
| [v2.0-pilot](https://github.com/naszhu/multiplecue-prospectiveM/releases/tag/v2.0-pilot) | `e45fff8` | Aug 2026 — dialog, Ishihara, survey, burn-in, SRB auto-detect |
| [v2.1-pilot](https://github.com/naszhu/multiplecue-prospectiveM/releases/tag/v2.1-pilot) | `6ea286c` | Aug 2026 — SRB reconnect/resilience + session log |

Current development: `exp/testmain_demo.py` (`CODE_VERSION` in file).

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
