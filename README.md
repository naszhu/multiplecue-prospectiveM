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

## Experiment program designs

- **Design 1:** `exp/testmain_demo.py` is the original Design 1 program. The
  crash-resume work described below does not modify this file.
- **Design 2:** `exp/testmain_design2-1.py` is the current Design 2 program and
  the active target for crash recovery, cumulative resume files, and manual
  block overrides. See [Issue #8](https://github.com/naszhu/multiplecue-prospectiveM/issues/8).

The Design 2 recovery policy keeps every source file unchanged:

- An automatically detected incomplete block creates `..._resumeN_trials.csv`.
  The new file copies all strictly complete earlier blocks, omits the partial
  block, and records the restarted block and all later data. The latest safe
  `resumeN` file is therefore self-contained for analysis.
- A manually selected block that differs from the detected block requires an
  override reason and creates `..._overrideN_trials.csv`. It copies no prior
  trial rows and records the detected block, selected block, and reason in
  metadata and the session log.
- Choosing `0, i.e., not skip any block` for an existing session remains a
  full-session repeat. It keeps the existing reason dialog and `(2)`, `(3)`,
  etc. filename convention.
- A block is safe to copy only when its task-row count exactly equals the
  expected count. Too few rows identify the block to restart; too many rows
  require the manual override path.

Current development: `exp/testmain_design2-1.py` (`CODE_VERSION` in file).

## Run

```bash
cd exp
python testmain_design2-1.py
```

Current Design 2 entry point: **`exp/testmain_design2-1.py`** (PsychoPy;
keyboard or self-made serial response box). Session, device, and language are
set in the startup dialog / script defaults. Use `exp/testmain_demo.py` only
when intentionally running the original Design 1 program.

## Layout

- `exp/` — experiment code, instructions, stimuli, design notes
- `exp/Instructions/` — EN / ZH / DA instruction texts
- `exp/data_written/` — local session output (usually gitignored)
- Ethics materials at repo root

## Related repos

- [multiplecue-responsebox](https://github.com/naszhu/multiplecue-responsebox) — base CCRP ongoing task (no PM)
- [multiplecue-RTfit](https://github.com/naszhu/multiplecue-RTfit) — MIS+LBA model fitting (mainly on CCRP data)
