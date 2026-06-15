"""
Trial schedule generation for the PM prospective-memory experiment.

Builds a full session list before run: per-block cue allocation, PM assignment
within each cue bucket, shuffle within block, last block absorbs count remainders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import permutations
import random
from typing import Literal, Optional

SessionPhase = Literal["practice", "baseline", "focal_pm", "nonfocal_pm"]
TrialPmRole = Literal["ongoing", "focal", "nonfocal"]

NUM_POSITIONS = 3
N_CUE_CONDITIONS = 6

N_PRACTICE_SESSIONS = 5
N_BASELINE_SESSIONS = 7
N_PM_SESSIONS_PER_PHASE = 7
TOTAL_SESSIONS = N_PRACTICE_SESSIONS + N_BASELINE_SESSIONS + 2 * N_PM_SESSIONS_PER_PHASE

PRACTICE_TRIALS_PER_SESSION = 400
MAIN_TRIALS_PER_SESSION = 402
PM_TRIALS_PER_SESSION = 60

N_BLOCKS_PER_SESSION = 6

CUE_CONDITIONS = [
    {"values": (1,), "label": "(1)"},
    {"values": (2,), "label": "(2)"},
    {"values": (3,), "label": "(3)"},
    {"values": (2, 1), "label": "(2,1)"},
    {"values": (3, 1), "label": "(3,1)"},
    {"values": (3, 2), "label": "(3,2)"},
]


@dataclass(frozen=True)
class SessionPhaseConfig:
    session_number: int
    session_phase: SessionPhase
    trials_per_session: int
    pm_trials_per_session: int

    @property
    def pm_trial_role(self) -> Optional[TrialPmRole]:
        if self.session_phase == "focal_pm":
            return "focal"
        if self.session_phase == "nonfocal_pm":
            return "nonfocal"
        return None


@dataclass
class TrialPlan:
    session_phase: SessionPhase
    trial_pm_role: TrialPmRole
    cue_condition_label: str
    reward_values: tuple[int, ...]
    pm_position_idx: Optional[int] = None
    pm_on_rewarded: Optional[bool] = None
    trial_in_session: int = 0
    block: int = 0
    trial_in_block: int = 0
    warm_up: int = 0
    burn_in_block: int = 0
    position_to_color_id: dict[int, Optional[int]] = field(default_factory=dict)
    position_to_reward: dict[int, Optional[int]] = field(default_factory=dict)

    @property
    def is_pm_trial(self) -> bool:
        return self.trial_pm_role != "ongoing"


@dataclass(frozen=True)
class SessionDisplayProfile:
    layout: str = "triangle"
    show_color_map: bool = True
    num_positions: int = 3


def trials_per_cue_condition(session_trials: int) -> int:
    return session_trials // N_CUE_CONDITIONS


def pm_trials_per_cue_condition(pm_trials_session: int) -> int:
    return pm_trials_session // N_CUE_CONDITIONS


def split_with_remainder_to_last(total: int, n_parts: int) -> list[int]:
    """Split total into n_parts; any remainder goes to the last part only."""
    if n_parts <= 0:
        raise ValueError("n_parts must be positive")
    base = total // n_parts
    remainder = total % n_parts
    counts = [base] * n_parts
    counts[-1] += remainder
    return counts


def per_block_cue_counts_rotating(block_size: int, block_number: int) -> list[int]:
    """Split block trials across cue conditions; rotate which cues get +1 remainder."""
    base = block_size // N_CUE_CONDITIONS
    remainder = block_size % N_CUE_CONDITIONS
    counts = [base] * N_CUE_CONDITIONS
    for r in range(remainder):
        counts[(block_number - 1 + r) % N_CUE_CONDITIONS] += 1
    return counts


def block_sizes_for_session(total_trials: int, n_blocks: int = N_BLOCKS_PER_SESSION) -> list[int]:
    return split_with_remainder_to_last(total_trials, n_blocks)


def get_pm_phase_order(participant_id: int) -> list[SessionPhase]:
    first: SessionPhase = "focal_pm" if participant_id % 2 == 1 else "nonfocal_pm"
    second: SessionPhase = "nonfocal_pm" if first == "focal_pm" else "focal_pm"
    return [first, second]


def resolve_session_phase(session_number: int, participant_id: int) -> SessionPhaseConfig:
    if not 1 <= session_number <= TOTAL_SESSIONS:
        raise ValueError(f"Session number must be 1..{TOTAL_SESSIONS}, got {session_number}")

    if session_number <= N_PRACTICE_SESSIONS:
        return SessionPhaseConfig(
            session_number=session_number,
            session_phase="practice",
            trials_per_session=PRACTICE_TRIALS_PER_SESSION,
            pm_trials_per_session=0,
        )

    offset = session_number - N_PRACTICE_SESSIONS
    if offset <= N_BASELINE_SESSIONS:
        return SessionPhaseConfig(
            session_number=session_number,
            session_phase="baseline",
            trials_per_session=MAIN_TRIALS_PER_SESSION,
            pm_trials_per_session=0,
        )

    pm_offset = offset - N_BASELINE_SESSIONS
    pm_order = get_pm_phase_order(participant_id)
    phase = pm_order[0] if pm_offset <= N_PM_SESSIONS_PER_PHASE else pm_order[1]

    return SessionPhaseConfig(
        session_number=session_number,
        session_phase=phase,
        trials_per_session=MAIN_TRIALS_PER_SESSION,
        pm_trials_per_session=PM_TRIALS_PER_SESSION,
    )


def display_profile_for_session(session_number: int) -> SessionDisplayProfile:
    return SessionDisplayProfile()


def should_include_burnin_block(
    session_number: int,
    first_session_of_day: bool,
    participation_day: int,
) -> bool:
    return False


def _pool_for_cue_condition(cue_condition: dict) -> list[dict]:
    reward_values = tuple(cue_condition["values"])
    all_color_ids = list(range(1, NUM_POSITIONS + 1))

    def make_trial(position_to_color_id: dict, position_to_reward: dict) -> dict:
        return {
            "position_to_color_id": position_to_color_id,
            "position_to_reward": position_to_reward,
        }

    if len(reward_values) == 1:
        reward_value = reward_values[0]
        out = []
        for reward_pos in range(NUM_POSITIONS):
            for color_perm in permutations(all_color_ids):
                position_to_color_id = {i: color_perm[i] for i in range(NUM_POSITIONS)}
                position_to_reward = {i: None for i in range(NUM_POSITIONS)}
                position_to_reward[reward_pos] = reward_value
                out.append(make_trial(position_to_color_id, position_to_reward))
        return out

    reward_a, reward_b = reward_values
    out = []
    for pos_a, pos_b in permutations(range(NUM_POSITIONS), 2):
        for reward_at_a, reward_at_b in ((reward_a, reward_b), (reward_b, reward_a)):
            for color_perm in permutations(all_color_ids):
                position_to_color_id = {i: color_perm[i] for i in range(NUM_POSITIONS)}
                position_to_reward = {i: None for i in range(NUM_POSITIONS)}
                position_to_reward[pos_a] = reward_at_a
                position_to_reward[pos_b] = reward_at_b
                out.append(make_trial(position_to_color_id, position_to_reward))
    return out


_CUE_POOLS = {cond["label"]: _pool_for_cue_condition(cond) for cond in CUE_CONDITIONS}


def _position_is_rewarded(position_to_reward: dict[int, Optional[int]], pos_idx: int) -> bool:
    return position_to_reward.get(pos_idx) is not None


def _assign_pm_positions(pm_trials: list[TrialPlan], rng: random.Random) -> None:
    if not pm_trials:
        return

    slot_counts = [0, 0, 0]
    for trial in pm_trials:
        slot = min(range(NUM_POSITIONS), key=lambda s: slot_counts[s])
        trial.pm_position_idx = slot
        slot_counts[slot] += 1

    rewarded_target = len(pm_trials) // 2
    rewarded_count = sum(
        1
        for t in pm_trials
        if t.pm_position_idx is not None
        and _position_is_rewarded(t.position_to_reward, t.pm_position_idx)
    )
    for trial in pm_trials:
        if rewarded_count >= rewarded_target:
            break
        if trial.pm_position_idx is None:
            continue
        if _position_is_rewarded(trial.position_to_reward, trial.pm_position_idx):
            continue
        for other in pm_trials:
            if other is trial or other.pm_position_idx is None:
                continue
            if _position_is_rewarded(other.position_to_reward, other.pm_position_idx):
                trial.pm_position_idx, other.pm_position_idx = (
                    other.pm_position_idx,
                    trial.pm_position_idx,
                )
                rewarded_count += 1
                break

    for trial in pm_trials:
        if trial.pm_position_idx is None:
            trial.pm_on_rewarded = False
        else:
            trial.pm_on_rewarded = _position_is_rewarded(
                trial.position_to_reward, trial.pm_position_idx
            )


def _build_cue_bucket(
    *,
    session_phase: SessionPhase,
    cue_condition: dict,
    n_trials: int,
    n_pm_trials: int,
    pm_role: Optional[TrialPmRole],
    rng: random.Random,
) -> list[TrialPlan]:
    bucket: list[TrialPlan] = []
    pool = _CUE_POOLS[cue_condition["label"]]

    for _ in range(n_trials):
        layout = rng.choice(pool)
        bucket.append(
            TrialPlan(
                session_phase=session_phase,
                trial_pm_role="ongoing",
                cue_condition_label=cue_condition["label"],
                reward_values=tuple(cue_condition["values"]),
                position_to_color_id=dict(layout["position_to_color_id"]),
                position_to_reward=dict(layout["position_to_reward"]),
            )
        )

    if n_pm_trials > 0 and pm_role is not None:
        pm_indices = rng.sample(range(n_trials), n_pm_trials)
        for idx in pm_indices:
            bucket[idx].trial_pm_role = pm_role

    _assign_pm_positions([t for t in bucket if t.is_pm_trial], rng)
    return bucket


def assign_pm_positions(pm_trials: list[TrialPlan], rng: Optional[random.Random] = None) -> None:
    """Public wrapper for PM position / rewarded-circle balancing."""
    _assign_pm_positions(pm_trials, rng or random.Random())


def apply_debug_pm_to_first_n(
    trial_data_list: list[TrialPlan],
    phase_config: SessionPhaseConfig,
    n_trials: int = 10,
    rng: Optional[random.Random] = None,
) -> list[TrialPlan]:
    """
    Debug helper: first n trials are PM trials using the session's PM role
    (focal_pm -> focal, nonfocal_pm -> nonfocal). Baseline/practice use focal for preview.
    """
    rng = rng or random.Random()
    pm_role: TrialPmRole = phase_config.pm_trial_role or "focal"
    subset = trial_data_list[:n_trials]
    for trial in subset:
        trial.trial_pm_role = pm_role
        trial.pm_position_idx = None
        trial.pm_on_rewarded = None
    assign_pm_positions([t for t in subset if t.is_pm_trial], rng)
    for trial_in_session, trial in enumerate(subset, start=1):
        trial.trial_in_session = trial_in_session
    return subset


def interleave_from_buckets(cue_buckets: dict[str, list[TrialPlan]]) -> list[TrialPlan]:
    """Round-robin merge cue buckets so blocks get a mixed cue spread."""
    labels = [c["label"] for c in CUE_CONDITIONS]
    lists = [list(cue_buckets[label]) for label in labels]
    max_len = max(len(lst) for lst in lists)
    interleaved: list[TrialPlan] = []
    for i in range(max_len):
        for lst in lists:
            if i < len(lst):
                interleaved.append(lst[i])
    return interleaved


def build_session_schedule(
    phase_config: SessionPhaseConfig,
    rng: Optional[random.Random] = None,
    *,
    n_blocks: int = N_BLOCKS_PER_SESSION,
) -> list[TrialPlan]:
    rng = rng or random.Random()
    block_sizes = block_sizes_for_session(phase_config.trials_per_session, n_blocks)
    pm_role = phase_config.pm_trial_role

    session_cue_counts = split_with_remainder_to_last(
        phase_config.trials_per_session, N_CUE_CONDITIONS
    )
    session_pm_cue_counts = (
        split_with_remainder_to_last(phase_config.pm_trials_per_session, N_CUE_CONDITIONS)
        if phase_config.pm_trials_per_session > 0
        else [0] * N_CUE_CONDITIONS
    )

    cue_buckets: dict[str, list[TrialPlan]] = {}
    for cue_condition, n_trials, n_pm in zip(
        CUE_CONDITIONS, session_cue_counts, session_pm_cue_counts
    ):
        cue_buckets[cue_condition["label"]] = _build_cue_bucket(
            session_phase=phase_config.session_phase,
            cue_condition=cue_condition,
            n_trials=n_trials,
            n_pm_trials=n_pm,
            pm_role=pm_role,
            rng=rng,
        )

    pooled = interleave_from_buckets(cue_buckets)
    if len(pooled) != phase_config.trials_per_session:
        raise ValueError("Interleaved trial count does not match session size")

    session_trials: list[TrialPlan] = []
    idx = 0
    for block_number, block_size in enumerate(block_sizes, start=1):
        block_trials = pooled[idx : idx + block_size]
        idx += block_size
        rng.shuffle(block_trials)
        for trial_in_block, trial in enumerate(block_trials, start=1):
            trial.block = block_number
            trial.trial_in_block = trial_in_block
        session_trials.extend(block_trials)

    for trial_in_session, trial in enumerate(session_trials, start=1):
        trial.trial_in_session = trial_in_session
    return session_trials


def print_trial_schedule(trial_data_list: list[TrialPlan]) -> None:
    """Print all trial structures for debugging."""
    for trial in trial_data_list:
        print(
            f"{trial.trial_in_session:4d}  block={trial.block:2d}  "
            f"in_blk={trial.trial_in_block:3d}  cue={trial.cue_condition_label:6s}  "
            f"pm_role={trial.trial_pm_role:9s}  pm_pos={trial.pm_position_idx}  "
            f"rewards={list(trial.position_to_reward.values())}"
        )


def validate_session_schedule(
    trial_data_list: list[TrialPlan],
    phase_config: SessionPhaseConfig,
) -> None:
    expected_n = phase_config.trials_per_session
    if len(trial_data_list) != expected_n:
        raise ValueError(f"Expected {expected_n} trials, got {len(trial_data_list)}")

    pm_count = sum(1 for t in trial_data_list if t.is_pm_trial)
    if pm_count != phase_config.pm_trials_per_session:
        raise ValueError(
            f"Expected {phase_config.pm_trials_per_session} PM trials, got {pm_count}"
        )

    cue_totals: dict[str, int] = {c["label"]: 0 for c in CUE_CONDITIONS}
    pm_cue_totals: dict[str, int] = {c["label"]: 0 for c in CUE_CONDITIONS}
    for trial in trial_data_list:
        cue_totals[trial.cue_condition_label] += 1
        if trial.is_pm_trial:
            pm_cue_totals[trial.cue_condition_label] += 1

    expected_per_cue = split_with_remainder_to_last(expected_n, N_CUE_CONDITIONS)
    for cond, expected in zip(CUE_CONDITIONS, expected_per_cue):
        label = cond["label"]
        if cue_totals[label] != expected:
            raise ValueError(
                f"Cue {label}: expected {expected} trials, got {cue_totals[label]}"
            )

    if phase_config.pm_trials_per_session > 0:
        expected_pm_per_cue = split_with_remainder_to_last(
            phase_config.pm_trials_per_session, N_CUE_CONDITIONS
        )
        for cond, expected in zip(CUE_CONDITIONS, expected_pm_per_cue):
            label = cond["label"]
            if pm_cue_totals[label] != expected:
                raise ValueError(
                    f"Cue {label}: expected {expected} PM trials, got {pm_cue_totals[label]}"
                )

    for trial in trial_data_list:
        if phase_config.session_phase in ("practice", "baseline"):
            if trial.trial_pm_role != "ongoing":
                raise ValueError("Non-PM phase contains PM trial")
        elif phase_config.session_phase == "focal_pm":
            if trial.is_pm_trial and trial.trial_pm_role != "focal":
                raise ValueError("Focal session contains non-focal PM trial")
        elif phase_config.session_phase == "nonfocal_pm":
            if trial.is_pm_trial and trial.trial_pm_role != "nonfocal":
                raise ValueError("Nonfocal session contains non-nonfocal PM trial")


def trial_plan_to_log_dict(trial: TrialPlan) -> dict:
    row = asdict(trial)
    row["is_pm_trial"] = trial.is_pm_trial
    return row


if __name__ == "__main__":
    for session in (1, 6, 13, 20):
        cfg = resolve_session_phase(session, participant_id=1)
        schedule = build_session_schedule(cfg, random.Random(42))
        validate_session_schedule(schedule, cfg)
        print(f"Session {session} ({cfg.session_phase}): {len(schedule)} trials OK")
