#!/usr/bin/env python3
"""
Generate session_phase_schedule.csv for PMCP v3 four-day design.

Day 1 (ses 1–8): practice 1–5, baseline 6, then focal/nonfocal on 7–8
  (odd participant_id → focal first; even → nonfocal first; "test" → odd/focal first).

Days 2–4 (ses 9–14, 15–20, 21–26): each day is two consecutive sessions of each
phase, as one of 6 block orders of {BB, FF, NN}, e.g.
  BB FF NN, BB NN FF, FF BB NN, FF NN BB, NN BB FF, NN FF BB.

Each subject gets 3 distinct block orders (one per day), assigned without
replacement from the 6. After all P(6,3)=120 ordered triples are used,
reshuffle with a new seeded pass and continue.

Fixed seed so every computer regenerates the identical CSV.
"""

from __future__ import annotations

import csv
from itertools import permutations
from pathlib import Path

SEED = 20260921
MAX_PARTICIPANT_ID = 100
OUT_PATH = Path(__file__).resolve().parent / "session_phase_schedule.csv"

PHASE_B = "baseline"
PHASE_F = "focal_pm"
PHASE_N = "nonfocal_pm"
PHASE_BLOCKS = {
    "B": (PHASE_B, PHASE_B),
    "F": (PHASE_F, PHASE_F),
    "N": (PHASE_N, PHASE_N),
}

DAY2_SESSIONS = list(range(9, 15))
DAY3_SESSIONS = list(range(15, 21))
DAY4_SESSIONS = list(range(21, 27))


def _unique_day_combinations() -> list[tuple[str, ...]]:
    """All 6 block orders: two consecutive sessions of each phase."""
    ordered: list[tuple[str, ...]] = []
    for perm in permutations("BFN"):
        seq: list[str] = []
        for letter in perm:
            seq.extend(PHASE_BLOCKS[letter])
        ordered.append(tuple(seq))
    assert len(ordered) == 6, len(ordered)
    return ordered


def _seeded_shuffle(items: list, seed: int) -> list:
    """Deterministic Fisher–Yates using a simple LCG (no random.Random state drift)."""
    out = list(items)
    state = seed % (2**31 - 1)
    if state == 0:
        state = 1
    n = len(out)
    for i in range(n - 1, 0, -1):
        state = (1103515245 * state + 12345) % (2**31)
        j = state % (i + 1)
        out[i], out[j] = out[j], out[i]
    return out


def _triple_pool_iterator(combos: list[tuple[str, ...]], base_seed: int):
    """Yield (day2, day3, day4) triples of distinct combos; reshuffle when depleted."""
    indices = list(permutations(range(len(combos)), 3))
    pass_idx = 0
    while True:
        pool = _seeded_shuffle(indices, base_seed + pass_idx * 9973)
        for i2, i3, i4 in pool:
            yield combos[i2], combos[i3], combos[i4], pass_idx, i2, i3, i4
        pass_idx += 1


def _day1_pm_order(participant_id: str) -> str:
    if participant_id == "test":
        return "focal_first"
    n = int(participant_id)
    return "focal_first" if n % 2 == 1 else "nonfocal_first"


def _day1_phases(pm_order: str) -> dict[int, str]:
    if pm_order == "focal_first":
        return {7: PHASE_F, 8: PHASE_N}
    return {7: PHASE_N, 8: PHASE_F}


def _assert_paired_blocks(seq: tuple[str, ...]) -> None:
    assert len(seq) == 6
    assert seq[0] == seq[1] and seq[2] == seq[3] and seq[4] == seq[5]
    assert sorted(seq) == sorted([PHASE_B, PHASE_B, PHASE_F, PHASE_F, PHASE_N, PHASE_N])


def build_rows() -> list[dict]:
    combos = _unique_day_combinations()
    pool = _triple_pool_iterator(combos, SEED)
    participant_ids = ["test"] + [str(i) for i in range(1, MAX_PARTICIPANT_ID + 1)]
    rows = []
    for pid in participant_ids:
        pm_order = _day1_pm_order(pid)
        day1 = _day1_phases(pm_order)
        d2, d3, d4, pass_i, i2, i3, i4 = next(pool)
        row = {
            "participant_id": pid,
            "day1_pm_order": pm_order,
            "day2_combo_id": f"p{pass_i}_{i2}",
            "day3_combo_id": f"p{pass_i}_{i3}",
            "day4_combo_id": f"p{pass_i}_{i4}",
        }
        for ses in range(1, 6):
            row[f"ses{ses:02d}"] = "practice"
        row["ses06"] = PHASE_B
        row["ses07"] = day1[7]
        row["ses08"] = day1[8]
        for ses, phase in zip(DAY2_SESSIONS, d2):
            row[f"ses{ses:02d}"] = phase
        for ses, phase in zip(DAY3_SESSIONS, d3):
            row[f"ses{ses:02d}"] = phase
        for ses, phase in zip(DAY4_SESSIONS, d4):
            row[f"ses{ses:02d}"] = phase
        for label, seq in (("day2", d2), ("day3", d3), ("day4", d4)):
            _assert_paired_blocks(seq)
        assert len({d2, d3, d4}) == 3, (pid, d2, d3, d4)
        rows.append(row)
    return rows


def main() -> None:
    rows = build_rows()
    fieldnames = (
        ["participant_id", "day1_pm_order", "day2_combo_id", "day3_combo_id", "day4_combo_id"]
        + [f"ses{i:02d}" for i in range(1, 27)]
    )
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
