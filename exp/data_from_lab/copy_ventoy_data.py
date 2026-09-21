#!/usr/bin/env python3
"""
Copy prospective-memory lab data from the Ventoy drive into raw_data, then
distribute into subject folders.

USB layout (checked on Ventoy):
    /media/lea/Ventoy/datapm/{a1,a3,a5}/subjN/PMCP_subjN_sesK_*.{csv,json}

Step 1 — copy from datapm into raw_data/ (flat filenames).
         If the same session filename appears on multiple lab computers,
         each copy is saved with a computer tag before the extension
         (e.g. _a1, _a3). Tagged files are never overwritten on later runs.
Step 2 — copy each PMCP session file from raw_data into data_from_lab/sub{N}/.
         Always run this second pass even when destinations already mirror
         the USB subject layout.

If a destination file with the same name already exists, skip it. Never overwrite.

Run from this directory (exp/data_from_lab):
    python copy_ventoy_data.py
"""

from __future__ import annotations

import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_SOURCE = Path("/media/lea/Ventoy/datapm")
LAB_DATA_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = LAB_DATA_DIR / "raw_data"

RE_PMCP = re.compile(
    r"^PMCP_subj(.+?)_ses\d+(?:\([^)]+\))?_(?:trials|metadata)\.(?:csv|json)$",
    re.IGNORECASE,
)
RE_PMCP_DEST = re.compile(
    r"^PMCP_subj(.+?)_ses\d+(?:\([^)]+\))?_(?:trials|metadata)"
    r"(?:_(?:a\d+))?\.(?:csv|json)$",
    re.IGNORECASE,
)


def computer_tag(folder_name: str) -> str:
    """Map USB top-level folder to a short tag (a1, a3, ...)."""
    if folder_name.startswith("computer"):
        return "a" + folder_name.removeprefix("computer")
    return folder_name


def tagged_filename(filename: str, tag: str) -> str:
    stem, ext = filename.rsplit(".", 1)
    return f"{stem}_{tag}.{ext}"


def is_session_file(name: str) -> bool:
    return bool(RE_PMCP.match(name))


def collect_session_files(source_root: Path) -> list[tuple[str, Path]]:
    """Collect (computer_folder, path) for every PMCP session file under datapm."""
    if not source_root.is_dir():
        raise FileNotFoundError(f"Source not found: {source_root}")

    files: list[tuple[str, Path]] = []
    for computer_dir in sorted(source_root.iterdir()):
        if not computer_dir.is_dir():
            continue
        for path in computer_dir.rglob("*"):
            if path.is_file() and is_session_file(path.name):
                files.append((computer_dir.name, path))
    return files


def run_copy(source_root: Path, dest_dir: Path) -> int:
    try:
        files = collect_session_files(source_root)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    if not files:
        print(f"No session files found under {source_root}", file=sys.stderr)
        return 1

    dest_dir.mkdir(parents=True, exist_ok=True)
    by_name: dict[str, list[tuple[str, Path]]] = defaultdict(list)
    for computer, path in files:
        by_name[path.name].append((computer, path))

    copied = 0
    skipped = 0

    print("=== Copy Ventoy/datapm -> raw_data ===")
    print(f"Source: {source_root}")
    print(f"Destination: {dest_dir}")
    print(f"Session files found: {len(files)}")
    print(f"Unique filenames: {len(by_name)}")
    print()

    for name in sorted(by_name):
        sources = sorted(by_name[name], key=lambda item: item[0])
        if len(sources) == 1:
            computer, source_file = sources[0]
            dest_path = dest_dir / name
            if dest_path.exists():
                print(f"SKIP   {computer}/{name} -> {dest_path.name} (exists)")
                skipped += 1
                continue
            print(f"COPY   {computer}/{name} -> {dest_path.name}")
            shutil.copy2(source_file, dest_path)
            copied += 1
            continue

        print(f"DUP    {name} on {[c for c, _ in sources]}")
        for computer, source_file in sources:
            tag = computer_tag(computer)
            dest_name = tagged_filename(name, tag)
            dest_path = dest_dir / dest_name
            if dest_path.exists():
                print(f"SKIP   {computer}/{name} -> {dest_name} (exists)")
                skipped += 1
                continue
            print(f"COPY   {computer}/{name} -> {dest_name}")
            shutil.copy2(source_file, dest_path)
            copied += 1

    print()
    print(f"Ventoy copy: {copied} copied | {skipped} skipped")
    return 0


def pmcp_target(name: str) -> tuple[str, str] | None:
    match = RE_PMCP_DEST.match(name)
    if not match:
        return None
    subj_token = match.group(1)
    return f"sub{subj_token}", name


def run_distribute(raw_dir: Path, lab_dir: Path) -> int:
    if not raw_dir.is_dir():
        print(f"raw_data not found: {raw_dir}", file=sys.stderr)
        return 1

    copied = 0
    skipped = 0
    ignored = 0

    print()
    print("=== Distribute raw_data -> data_from_lab/subN/ ===")
    print(f"Source: {raw_dir}")
    print(f"Destination root: {lab_dir}")
    print()

    for source_file in sorted(raw_dir.iterdir()):
        if not source_file.is_file():
            continue

        parsed = pmcp_target(source_file.name)
        if parsed is None:
            ignored += 1
            continue

        sub_dir_name, dest_name = parsed
        dest_dir = lab_dir / sub_dir_name
        dest_path = dest_dir / dest_name
        rel_dest = f"{sub_dir_name}/{dest_name}"

        if dest_path.exists():
            print(f"SKIP   {source_file.name} -> {rel_dest} (exists)")
            skipped += 1
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)
        print(f"COPY   {source_file.name} -> {rel_dest}")
        shutil.copy2(source_file, dest_path)
        copied += 1

    print()
    print(
        f"Distribute: {copied} copied | {skipped} skipped | "
        f"{ignored} ignored (not PMCP session data)"
    )
    return 0


def main() -> int:
    code = run_copy(DEFAULT_SOURCE.resolve(), RAW_DATA_DIR.resolve())
    if code != 0:
        return code
    return run_distribute(RAW_DATA_DIR.resolve(), LAB_DATA_DIR.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
