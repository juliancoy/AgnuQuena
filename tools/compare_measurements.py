#!/usr/bin/env python3
"""Extract AgnuQuena geometry and pitch measurements across git history."""

from __future__ import annotations

import argparse
import ast
import csv
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);")
TRANSLATE_RE = re.compile(
    r"translate\s*\(\s*\[\s*0\s*,\s*0\s*,\s*(?P<z>[^\]]+)\]\s*\)"
    r".*?cylinder\s*\([^;]*?\bd\s*=\s*(?P<d>[^,)]+(?:[+-]\s*[^,)]+)*)",
)
MEASURE_RE = re.compile(
    r"^\s*//\s*(?P<note>[A-G](?:#|b)?\d?)\s+"
    r"(?P<expected>[0-9]+(?:\.[0-9]+)?)\s+"
    r"(?P<actual>[0-9]+(?:\.[0-9]+)?)\s*$"
)
NOTE_COMMENT_RE = re.compile(r"//\s*(?P<note>[A-G](?:#|b)?)\s*$")


@dataclass
class Commit:
    sha: str
    date: str
    subject: str


def git(args: list[str], check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def commits_for(paths: list[str]) -> list[Commit]:
    out = git(["log", "--format=%H%x09%ad%x09%s", "--date=short", "--", *paths])
    commits = []
    for line in out.splitlines():
        sha, date, subject = line.split("\t", 2)
        commits.append(Commit(sha=sha, date=date, subject=subject))
    return commits


def strip_line_comment(expr: str) -> str:
    return expr.split("//", 1)[0].strip()


class ExprEval(ast.NodeVisitor):
    def __init__(self, names: dict[str, float]):
        self.names = names

    def visit_Expression(self, node: ast.Expression) -> float:
        return self.visit(node.body)

    def visit_Constant(self, node: ast.Constant) -> float:
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("non-numeric constant")

    def visit_Name(self, node: ast.Name) -> float:
        if node.id in self.names:
            return float(self.names[node.id])
        raise ValueError(f"unknown name {node.id}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> float:
        value = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
        raise ValueError("unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> float:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        raise ValueError("unsupported binary operator")

    def visit_Call(self, node: ast.Call) -> float:
        if not isinstance(node.func, ast.Name):
            raise ValueError("unsupported call")
        args = [self.visit(arg) for arg in node.args]
        if node.func.id == "pow":
            return math.pow(*args)
        if node.func.id == "tuned_length":
            return args[0] * self.names.get("length_tuning_scale", 1.0)
        raise ValueError(f"unsupported function {node.func.id}")

    def generic_visit(self, node: ast.AST) -> float:
        raise ValueError(f"unsupported expression {type(node).__name__}")


def eval_expr(expr: str, env: dict[str, float]) -> float | None:
    expr = strip_line_comment(expr).replace("^", "**")
    expr = re.sub(r"\btrue\b", "1", expr, flags=re.I)
    expr = re.sub(r"\bfalse\b", "0", expr, flags=re.I)
    if "[" in expr or "]" in expr:
        return None
    try:
        tree = ast.parse(expr, mode="eval")
        return ExprEval(env).visit(tree)
    except Exception:
        return None


def parse_scad(scad: str) -> tuple[dict[str, float], list[dict[str, object]], list[dict[str, object]]]:
    env: dict[str, float] = {}
    holes: list[dict[str, object]] = []
    measurements: list[dict[str, object]] = []

    for line in scad.splitlines():
        if line.lstrip().startswith("//"):
            measured = MEASURE_RE.match(line)
            if measured:
                expected = float(measured.group("expected"))
                actual = float(measured.group("actual"))
                measurements.append(
                    {
                        "note": measured.group("note"),
                        "expected_hz": expected,
                        "actual_hz": actual,
                        "cents": 1200 * math.log2(actual / expected),
                    }
                )
            continue

        assign = ASSIGN_RE.match(line)
        if assign:
            value = eval_expr(assign.group(2), env)
            if value is not None:
                env[assign.group(1)] = value

        translated = TRANSLATE_RE.search(line)
        if translated and "rotate" in line:
            z = eval_expr(translated.group("z"), env)
            d = eval_expr(translated.group("d"), env)
            note_match = NOTE_COMMENT_RE.search(line)
            if z is not None and d is not None:
                holes.append(
                    {
                        "note": note_match.group("note") if note_match else "",
                        "z_mm": z,
                        "diameter_mm": d,
                        "source": strip_line_comment(line),
                    }
                )

    return env, holes, measurements


def scad_at(commit: str) -> str | None:
    out = git(["show", f"{commit}:Quena.scad"], check=False)
    return out if out else None


def tuning_csv_at(commit: str) -> list[dict[str, object]]:
    out = git(["show", f"{commit}:Fife/tuning.csv"], check=False)
    if not out:
        return []
    rows: list[dict[str, object]] = []
    reader = csv.DictReader(out.splitlines())
    for row in reader:
        note = row.get("Expected_Note", "")
        expected_raw = row.get("Expected_Frequency", "")
        if not expected_raw:
            continue
        expected = float(expected_raw)
        for key, value in row.items():
            if key in {"Expected_Note", "Expected_Frequency"} or not value:
                continue
            actual = float(value)
            rows.append(
                {
                    "dataset": key,
                    "note": note,
                    "expected_hz": expected,
                    "actual_hz": actual,
                    "cents": 1200 * math.log2(actual / expected),
                }
            )
    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="measurements/history", help="directory for CSV output")
    parser.add_argument("--max-count", type=int, default=0, help="limit commits for quick checks")
    parser.add_argument(
        "--no-worktree",
        action="store_true",
        help="only inspect committed revisions; by default the current working tree is included first",
    )
    args = parser.parse_args()

    commits = commits_for(["Quena.scad", "Fife/tuning.csv"])
    if args.max_count:
        commits = commits[: args.max_count]

    geometry_rows: list[dict[str, object]] = []
    hole_rows: list[dict[str, object]] = []
    pitch_rows: list[dict[str, object]] = []
    comparison_rows: list[dict[str, object]] = []

    work_items: list[tuple[Commit, str | None, list[dict[str, object]]]]
    work_items = []
    if not args.no_worktree:
        work_items.append(
            (
                Commit(sha="WORKTREE", date="", subject="current working tree"),
                Path("Quena.scad").read_text(encoding="utf-8"),
                tuning_csv_at("HEAD"),
            )
        )
    work_items.extend((commit, scad_at(commit.sha), tuning_csv_at(commit.sha)) for commit in commits)

    for commit, scad, fife_measurements in work_items:
        short_sha = commit.sha if commit.sha == "WORKTREE" else commit.sha[:12]
        holes_by_note: dict[str, dict[str, object]] = {}
        if scad:
            env, holes, measurements = parse_scad(scad)
            geometry_rows.append(
                {
                    "commit": short_sha,
                    "date": commit.date,
                    "subject": commit.subject,
                    "id_mm": env.get("id", ""),
                    "od_mm": env.get("od", ""),
                    "taper_mm": env.get("taper", ""),
                    "total_height_mm": env.get("total_height", env.get("th", "")),
                    "acoustic_length_mm": env.get("acoustic_length", ""),
                    "zadj_mm": env.get("zadj", ""),
                    "hole_shift_mm": env.get("hole_shift", ""),
                    "pitch_raise_cents": env.get("pitch_raise_cents", ""),
                }
            )
            for index, hole in enumerate(holes, start=1):
                hole_rows.append(
                    {
                        "commit": short_sha,
                        "date": commit.date,
                        "subject": commit.subject,
                        "hole_index": index,
                        "note": hole["note"],
                        "z_mm": f"{hole['z_mm']:.4f}",
                        "diameter_mm": f"{hole['diameter_mm']:.4f}",
                        "source": hole["source"],
                    }
                )
                if hole["note"]:
                    holes_by_note[str(hole["note"])] = hole
            for measurement in measurements:
                pitch_rows.append(
                    {
                        "commit": short_sha,
                        "date": commit.date,
                        "subject": commit.subject,
                        "dataset": "Quena.scad comment",
                        "note": measurement["note"],
                        "expected_hz": measurement["expected_hz"],
                        "actual_hz": measurement["actual_hz"],
                        "cents": f"{measurement['cents']:.2f}",
                    }
                )
                hole = holes_by_note.get(str(measurement["note"]))
                comparison_rows.append(
                    {
                        "commit": short_sha,
                        "date": commit.date,
                        "subject": commit.subject,
                        "dataset": "Quena.scad comment",
                        "note": measurement["note"],
                        "expected_hz": measurement["expected_hz"],
                        "actual_hz": measurement["actual_hz"],
                        "cents": f"{measurement['cents']:.2f}",
                        "hole_z_mm": f"{hole['z_mm']:.4f}" if hole else "",
                        "hole_diameter_mm": f"{hole['diameter_mm']:.4f}" if hole else "",
                    }
                )

        for measurement in fife_measurements:
            pitch_rows.append(
                {
                    "commit": short_sha,
                    "date": commit.date,
                    "subject": commit.subject,
                    "dataset": measurement["dataset"],
                    "note": measurement["note"],
                    "expected_hz": measurement["expected_hz"],
                    "actual_hz": measurement["actual_hz"],
                    "cents": f"{measurement['cents']:.2f}",
                }
            )

    out_dir = Path(args.out_dir)
    write_rows(out_dir / "geometry_by_commit.csv", geometry_rows)
    write_rows(out_dir / "holes_by_commit.csv", hole_rows)
    write_rows(out_dir / "pitches_by_commit.csv", pitch_rows)
    write_rows(out_dir / "quena_pitch_hole_comparison.csv", comparison_rows)

    print(f"wrote {len(geometry_rows)} geometry rows")
    print(f"wrote {len(hole_rows)} hole rows")
    print(f"wrote {len(pitch_rows)} pitch rows")
    print(f"wrote {len(comparison_rows)} comparison rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
