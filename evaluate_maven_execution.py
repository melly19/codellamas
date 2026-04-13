#!/usr/bin/env python3
"""Evaluate Maven execution for generated exercises and update the CSV incrementally.

Workflow per exercise:
1) Run `mvn clean install` on current (smelly) project.
2) Replace `src` with `answers/src`.
3) Run `mvn clean install` again (solution).
4) Restore original `src`.
5) Save CSV after each exercise.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


ROOT_DIR = Path(__file__).resolve().parent
EXERCISES_DIR = ROOT_DIR / "backend" / "src" / "codellamas_backend" / "generated_exercises"
CSV_PATH = EXERCISES_DIR / "Evaluation - Sheet5.csv"


@dataclass
class BuildResult:
    success: bool
    return_code: int
    output_tail: str


def read_csv_with_title(path: Path) -> tuple[str, List[Dict[str, str]], List[str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    if not lines:
        raise ValueError("CSV is empty")

    title_line = lines[0].rstrip("\r\n")

    header_index = -1
    for i, line in enumerate(lines):
        if line.lstrip().startswith("Name,"):
            header_index = i
            break

    if header_index < 0:
        raise ValueError("Could not find CSV header row starting with 'Name,'")

    content = "".join(lines[header_index:])

    reader = csv.DictReader(content.splitlines())
    rows = list(reader)
    fieldnames = list(reader.fieldnames or [])

    if not fieldnames:
        raise ValueError("CSV has no header row")

    return title_line, rows, fieldnames


def write_csv_with_title(path: Path, title: str, rows: List[Dict[str, str]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(f"{title}\n")
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_maven_build(project_dir: Path, timeout_seconds: int) -> BuildResult:
    cmd = ["mvn", "clean", "install"]
    try:
        completed = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\n" + (exc.stderr or "")
        tail = "\n".join(output.splitlines()[-25:])
        return BuildResult(False, -1, f"TIMEOUT after {timeout_seconds}s\n{tail}")

    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    tail = "\n".join(combined.splitlines()[-25:])
    success = completed.returncode == 0 and "BUILD SUCCESS" in combined
    return BuildResult(success, completed.returncode, tail)


def evaluate_exercise(exercise_dir: Path, timeout_seconds: int) -> tuple[bool, bool, str]:
    src_dir = exercise_dir / "src"
    answers_src_dir = exercise_dir / "answers" / "src"

    if not exercise_dir.exists():
        return False, False, "Exercise directory missing"
    if not (exercise_dir / "pom.xml").exists():
        return False, False, "pom.xml missing"

    smelly_result = run_maven_build(exercise_dir, timeout_seconds)
    smelly_ok = smelly_result.success

    if not src_dir.exists() or not answers_src_dir.exists():
        return smelly_ok, False, "src or answers/src missing"

    note = ""
    solution_ok = False
    with tempfile.TemporaryDirectory(prefix="src_backup_") as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        src_backup = tmp_dir / "src_backup"
        src_swapped = False

        shutil.copytree(src_dir, src_backup)
        shutil.rmtree(src_dir)
        shutil.copytree(answers_src_dir, src_dir)
        src_swapped = True

        try:
            solution_result = run_maven_build(exercise_dir, timeout_seconds)
            solution_ok = solution_result.success
        finally:
            # Restore original src even if Maven run is interrupted.
            if src_swapped and src_backup.exists():
                if src_dir.exists():
                    shutil.rmtree(src_dir)
                shutil.copytree(src_backup, src_dir)

        if not smelly_ok:
            note += f"Smelly build failed (code={smelly_result.return_code}). "
        if not solution_ok:
            note += f"Solution build failed (code={solution_result.return_code})."
        if not note:
            note = "Both builds succeeded"

        return smelly_ok, solution_ok, note.strip()


def main() -> int:
    timeout_seconds = 300
    if len(sys.argv) > 1:
        try:
            timeout_seconds = int(sys.argv[1])
        except ValueError:
            print(f"Invalid timeout value: {sys.argv[1]}")
            return 2

    title, rows, fieldnames = read_csv_with_title(CSV_PATH)
    total = len(rows)

    print(f"Evaluating {total} exercises from {CSV_PATH}")
    print(f"Per-build timeout: {timeout_seconds}s")

    for idx, row in enumerate(rows, start=1):
        name = (row.get("Name") or "").strip()
        if not name:
            continue

        exercise_dir = EXERCISES_DIR / name
        print(f"\n[{idx}/{total}] {name}")

        # If CSV name does not map to a real directory, skip updates for this row.
        if not exercise_dir.exists() or not exercise_dir.is_dir():
            print("  Skipped: no matching exercise directory (row left unchanged)")
            continue

        try:
            smelly_ok, solution_ok, note = evaluate_exercise(exercise_dir, timeout_seconds)
        except KeyboardInterrupt:
            print("\nInterrupted by user. Stopping cleanly; progress already saved for previous rows.")
            break
        except Exception as exc:  # Keep going even if one exercise crashes.
            smelly_ok, solution_ok = False, False
            note = f"Unhandled error: {exc}"

        row["Smelly Code Execution"] = "TRUE" if smelly_ok else "FALSE"
        row["Solution Execution"] = "TRUE" if solution_ok else "FALSE"

        write_csv_with_title(CSV_PATH, title, rows, fieldnames)

        print(f"  Smelly Code Execution: {row['Smelly Code Execution']}")
        print(f"  Solution Execution: {row['Solution Execution']}")
        print(f"  Note: {note}")

    print("\nDone. CSV updated incrementally after each exercise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())