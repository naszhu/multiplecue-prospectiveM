#!/usr/bin/env python3
"""
Aggregate session-end CumReward from lab trial CSVs and write pay.csv.

Data live in per-subject folders (sub17/, sub28/, ...). Test subjects
(subtest, subj id >= 100, names containing 'test') are skipped.

Run from this directory (exp/data_from_lab):
    python compute_pay.py
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
# Standard: PMCP_subj17_ses10_trials.csv
# Redo/variant session: PMCP_subj17_ses1(2)_trials.csv
RE_FILE = re.compile(
    r"^PMCP_subj(.+?)_ses(\d+)(?:\(([^)]+)\))?_trials\.csv$",
    re.IGNORECASE,
)
RE_STD = re.compile(r"^PMCP_subj(\d+)_ses(\d+)_trials\.csv$", re.IGNORECASE)
RE_LEAD_DIGITS = re.compile(r"^(\d+)")
REWARD_COL = "CumReward"
OUT_CSV = "pay.csv"

# Unusual session files that are reported but excluded from pay.csv and totals.
EXCLUDED_VARIANTS = frozenset({"eeee", "discard", "eeeee"})


@dataclass(frozen=True)
class TrialFile:
    path: Path
    subject_id: int
    session: int
    subj_token: str
    is_standard: bool
    variant: str  # empty for standard files; e.g. "(2)" for ses1(2)


def is_test_subj_token(subj_token: str) -> bool:
    token_lower = subj_token.lower()
    if token_lower.startswith("__"):
        return True
    if "test" in token_lower or "teset" in token_lower:
        return True
    lead = RE_LEAD_DIGITS.match(subj_token)
    if lead and int(lead.group(1)) >= 100:
        return True
    return False


def is_excluded_from_pay(entry: TrialFile) -> bool:
    return entry.variant.lower() in EXCLUDED_VARIANTS


def parse_trial_file(path: Path) -> TrialFile | None:
    match = RE_FILE.match(path.name)
    if not match:
        return None
    subj_token, session = match.group(1), int(match.group(2))
    session_paren = match.group(3)  # e.g. "2" from ses1(2)
    if is_test_subj_token(subj_token):
        return None
    lead = RE_LEAD_DIGITS.match(subj_token)
    if not lead:
        return None
    subject_id = int(lead.group(1))
    is_standard = bool(RE_STD.match(path.name))
    suffix = subj_token[lead.end() :].lstrip("_")
    if session_paren is not None:
        variant = f"({session_paren})"
    elif is_standard:
        variant = ""
    else:
        variant = suffix or subj_token
    return TrialFile(
        path=path,
        subject_id=subject_id,
        session=session,
        subj_token=subj_token,
        is_standard=is_standard,
        variant=variant,
    )


def last_cum_reward(path: Path) -> float | None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get(REWARD_COL, "").strip() != ""
        ]
    if not rows:
        return None
    return float(rows[-1][REWARD_COL])


def iter_trial_csv_paths(data_dir: Path):
    """Yield trial CSV paths from subject subfolders only (not raw_data/)."""
    seen: set[Path] = set()
    for path in sorted(data_dir.glob("sub*/PMCP_subj*_ses*_trials.csv")):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            yield path


def discover_trial_files(data_dir: Path) -> list[TrialFile]:
    files: list[TrialFile] = []
    for path in iter_trial_csv_paths(data_dir):
        parsed = parse_trial_file(path)
        if parsed is not None:
            files.append(parsed)
    return files


def report_unusual_naming(files: list[TrialFile]) -> None:
    by_subject: dict[int, list[TrialFile]] = {}
    for item in files:
        by_subject.setdefault(item.subject_id, []).append(item)

    any_unusual = False
    for subject_id in sorted(by_subject):
        unusual = [f for f in by_subject[subject_id] if not f.is_standard]
        if not unusual:
            continue
        any_unusual = True
        print(f"subj {subject_id}: unusual file name(s):")
        for entry in sorted(unusual, key=lambda f: (f.session, f.path.name)):
            label = entry.variant or entry.subj_token
            suffix = " [not counted]" if is_excluded_from_pay(entry) else ""
            print(f"  ses{entry.session} ({label}): {entry.path.name}{suffix}")

    if not any_unusual:
        print("No unusual subject or session file names found.")


def build_pay_table(
    files: list[TrialFile],
) -> tuple[list[str], list[list[str]], dict[int, float]]:
    """Return row labels, table rows (without header), and per-subject totals."""
    subjects = sorted({f.subject_id for f in files})
    col_names = [f"subj{s}" for s in subjects]

    # (session, variant) -> {subject_id: reward}
    rewards: dict[tuple[int, str], dict[int, float]] = {}
    for entry in files:
        value = last_cum_reward(entry.path)
        if value is None:
            print(
                f"Warning: no {REWARD_COL} in {entry.path.name}",
                file=sys.stderr,
            )
            continue
        key = (entry.session, entry.variant)
        bucket = rewards.setdefault(key, {})
        if entry.subject_id in bucket:
            print(
                f"Warning: duplicate key subj{entry.subject_id} "
                f"ses{entry.session} variant={entry.variant!r}; "
                f"keeping {entry.path.name}",
                file=sys.stderr,
            )
        bucket[entry.subject_id] = value

    def row_for_session(session: int, variant: str) -> list[str]:
        label = str(session) if not variant else f"{session}_{variant}"
        cells = [label]
        bucket = rewards.get((session, variant), {})
        for subject_id in subjects:
            val = bucket.get(subject_id)
            cells.append("" if val is None else f"{val:g}")
        return cells

    row_labels: list[str] = []
    table_rows: list[list[str]] = []

    standard_sessions = sorted(
        session for session, variant in rewards if variant == ""
    )
    for session in standard_sessions:
        row_labels.append(str(session))
        table_rows.append(row_for_session(session, ""))

    extra_keys = sorted(
        (session, variant)
        for session, variant in rewards
        if variant != ""
    )
    for session, variant in extra_keys:
        row_labels.append(f"{session}_{variant}")
        table_rows.append(row_for_session(session, variant))

    totals: dict[int, float] = {s: 0.0 for s in subjects}
    for bucket in rewards.values():
        for subject_id, value in bucket.items():
            totals[subject_id] += value

    total_row = ["total"] + [f"{totals[s]:g}" for s in subjects]
    row_labels.append("total")
    table_rows.append(total_row)

    return ["session", *col_names], table_rows, totals


def write_pay_csv(data_dir: Path, header: list[str], rows: list[list[str]]) -> Path:
    out_path = data_dir / OUT_CSV
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    return out_path


def main() -> int:
    data_dir = Path.cwd()
    if data_dir.resolve() != DATA_DIR.resolve():
        print(
            f"Note: cwd is {data_dir}; script lives in {DATA_DIR}. "
            "Using cwd for input/output.",
        )

    trial_files = discover_trial_files(data_dir)
    if not trial_files:
        print(f"No trial CSV files found in {data_dir}/sub*/", file=sys.stderr)
        return 1

    report_unusual_naming(trial_files)
    payable_files = [f for f in trial_files if not is_excluded_from_pay(f)]
    header, rows, totals = build_pay_table(payable_files)
    out_path = write_pay_csv(data_dir, header, rows)

    print()
    print(f"Wrote {out_path}")
    print("Per-subject total accumulated reward (sum of session-end CumReward):")
    for subject_id in sorted(totals):
        print(f"  subj{subject_id}: {totals[subject_id]:g}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
