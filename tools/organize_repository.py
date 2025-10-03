#!/usr/bin/env python3
"""
Bulk repository organizer for Docs, Tests, and Services archives.

Features
- Move root-level docs (e.g., *.md, *.txt) into Docs/{Current,Archive}
- Move test scripts (test_*.py) into Tests/{Current,Archive}
- Archive service file variants (e.g., main_*.py) into services/<svc>/archive/
- Dry-run mode prints the plan without moving files
- Generates a manifest JSON for audit and undo
- Undo mode restores files from a given manifest

Usage examples
  Dry-run (no changes):
    python tools/organize_repository.py --dry-run --days-current 60

  Execute (requires --confirm):
    python tools/organize_repository.py --days-current 60 --confirm

  Undo using manifest:
    python tools/organize_repository.py --undo .manifests/organization_manifest_YYYYMMDD_HHMMSS.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


# -------------------------------
# Data models
# -------------------------------

@dataclass
class MoveRecord:
    source: str
    destination: str


@dataclass
class Manifest:
    created_at_iso: str
    repo_root: str
    moves: List[MoveRecord]

    def to_json(self) -> Dict:
        return {
            "created_at": self.created_at_iso,
            "repo_root": self.repo_root,
            "moves": [record.__dict__ for record in self.moves],
        }


# -------------------------------
# Helpers
# -------------------------------

def now_timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def file_modified_within_days(path: Path, days: int) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return True  # assume current if unknown
    return (datetime.utcnow() - mtime) <= timedelta(days=days)


def unique_destination(dest_dir: Path, file_name: str) -> Path:
    candidate = dest_dir / file_name
    if not candidate.exists():
        return candidate
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    idx = 1
    while True:
        new_name = f"{stem}__{idx}{suffix}"
        candidate = dest_dir / new_name
        if not candidate.exists():
            return candidate
        idx += 1


def safe_move(src: Path, dest_dir: Path, dry_run: bool, manifest: Manifest) -> Path:
    ensure_dir(dest_dir)
    dest = unique_destination(dest_dir, src.name)
    if dry_run:
        print(f"DRY-RUN: move {src} -> {dest}")
    else:
        print(f"MOVE:    {src} -> {dest}")
        shutil.move(str(src), str(dest))
    manifest.moves.append(MoveRecord(str(src), str(dest)))
    return dest


def write_manifest(manifest: Manifest, folder: Path) -> Path:
    ensure_dir(folder)
    out_path = folder / f"organization_manifest_{now_timestamp()}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_json(), f, indent=2)
    print(f"Manifest written to {out_path}")
    return out_path


def undo_from_manifest(manifest_path: Path) -> None:
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    moves: List[Dict[str, str]] = data.get("moves", [])
    # Replay in reverse order to avoid conflicts
    for rec in reversed(moves):
        src = Path(rec["destination"]).resolve()
        dst_dir = Path(rec["source"]).resolve().parent
        ensure_dir(dst_dir)
        dst = dst_dir / Path(rec["source"]).name
        # If destination exists, add suffix
        if dst.exists():
            dst = unique_destination(dst_dir, dst.name)
        print(f"UNDO:    {src} -> {dst}")
        shutil.move(str(src), str(dst))
    print("Undo completed.")


# -------------------------------
# Organizers
# -------------------------------

DOC_EXTENSIONS = {".md", ".markdown", ".mdx", ".txt"}
TEST_PATTERNS = (
    re.compile(r"^test_.*\.py$", re.IGNORECASE),
    re.compile(r".*_test\.py$", re.IGNORECASE),
)


def is_doc_file(path: Path) -> bool:
    return path.suffix.lower() in DOC_EXTENSIONS


def is_test_file(path: Path) -> bool:
    name = path.name
    return any(p.search(name) for p in TEST_PATTERNS)


def organize_docs(repo_root: Path, days_current: int, dry_run: bool, manifest: Manifest) -> None:
    docs_root = repo_root / "Docs"
    current_dir = docs_root / "Current"
    archive_dir = docs_root / "Archive"
    ensure_dir(current_dir)
    ensure_dir(archive_dir)

    # 1) Root-level doc files -> Docs/{Current|Archive}
    for p in repo_root.iterdir():
        if p.is_file() and is_doc_file(p):
            target_dir = current_dir if file_modified_within_days(p, days_current) else archive_dir
            safe_move(p, target_dir, dry_run, manifest)

    # 2) Existing docs inside Docs root
    for p in docs_root.rglob("*"):
        if p.is_file() and is_doc_file(p):
            # Skip if already in Current/Archive
            if current_dir in p.parents or archive_dir in p.parents:
                continue
            target_dir = current_dir if file_modified_within_days(p, days_current) else archive_dir
            safe_move(p, target_dir, dry_run, manifest)


def organize_tests(repo_root: Path, days_current: int, dry_run: bool, manifest: Manifest) -> None:
    tests_root = repo_root / "Tests"
    current_dir = tests_root / "Current"
    archive_dir = tests_root / "Archive"
    ensure_dir(current_dir)
    ensure_dir(archive_dir)

    # Move root-level test files
    for p in repo_root.iterdir():
        if p.is_file() and is_test_file(p):
            target_dir = current_dir if file_modified_within_days(p, days_current) else archive_dir
            safe_move(p, target_dir, dry_run, manifest)

    # If there is an existing tests directory, normalize its files
    legacy_tests_dirs = [repo_root / "tests", repo_root / "test", repo_root / "unit_tests"]
    for legacy in legacy_tests_dirs:
        if legacy.exists() and legacy.is_dir():
            for p in legacy.rglob("*.py"):
                if p.is_file() and is_test_file(p):
                    target_dir = current_dir if file_modified_within_days(p, days_current) else archive_dir
                    safe_move(p, target_dir, dry_run, manifest)


SERVICE_KEEP_DEFAULT = {"main.py"}
SERVICE_VARIANT_PATTERNS = (
    re.compile(r"^main_.*\.py$", re.IGNORECASE),
    re.compile(r"^.*_backup\.py$", re.IGNORECASE),
    re.compile(r"^.*_demo\.py$", re.IGNORECASE),
    re.compile(r"^.*_simple\.py$", re.IGNORECASE),
)


def is_service_variant(path: Path) -> bool:
    if path.suffix.lower() != ".py":
        return False
    if path.name in SERVICE_KEEP_DEFAULT:
        return False
    return any(p.search(path.name) for p in SERVICE_VARIANT_PATTERNS)


def organize_services(repo_root: Path, dry_run: bool, manifest: Manifest, keep_map: Dict[str, List[str]] | None = None) -> None:
    services_root = repo_root / "services"
    if not services_root.exists():
        return
    keep_map = keep_map or {}

    for svc_dir in sorted([p for p in services_root.iterdir() if p.is_dir()]):
        archive_dir = svc_dir / "archive"
        ensure_dir(archive_dir)

        keep_set = set(SERVICE_KEEP_DEFAULT)
        extra_keep = keep_map.get(svc_dir.name, [])
        keep_set.update(extra_keep)

        for py in svc_dir.glob("*.py"):
            if py.name in keep_set:
                continue
            if is_service_variant(py):
                safe_move(py, archive_dir, dry_run, manifest)


# -------------------------------
# CLI
# -------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Organize repository files into Docs/Tests and archive service variants.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]), help="Path to repository root (default: project root)")
    parser.add_argument("--days-current", type=int, default=60, help="Files modified within N days are considered Current (default: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without changing files")
    parser.add_argument("--confirm", action="store_true", help="Required to execute actual moves (ignored with --dry-run)")
    parser.add_argument("--manifest-dir", default=str(Path(".manifests")), help="Directory to write manifest JSON (default: .manifests)")
    parser.add_argument("--keep", action="append", default=[], help="Service keep rule 'service_name:file1.py,file2.py' (can repeat)")
    parser.add_argument("--undo", default=None, help="Path to manifest JSON to undo moves")
    return parser.parse_args()


def build_keep_map(keep_args: List[str]) -> Dict[str, List[str]]:
    keep_map: Dict[str, List[str]] = {}
    for rule in keep_args:
        if ":" not in rule:
            continue
        svc, files_str = rule.split(":", 1)
        files = [f.strip() for f in files_str.split(",") if f.strip()]
        keep_map[svc.strip()] = files
    return keep_map


def main() -> None:
    args = parse_args()

    if args.undo:
        undo_from_manifest(Path(args.undo).resolve())
        return

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise SystemExit(f"Repo root not found: {repo_root}")

    manifest = Manifest(created_at_iso=datetime.utcnow().isoformat(), repo_root=str(repo_root), moves=[])

    keep_map = build_keep_map(args.keep)

    print(f"Organizing repository at {repo_root}")
    print(f"- Docs threshold: {args.days_current} days")
    print(f"- Tests threshold: {args.days_current} days")
    print(f"- Dry-run: {args.dry_run}")

    # Perform organization
    organize_docs(repo_root, args.days_current, args.dry_run, manifest)
    organize_tests(repo_root, args.days_current, args.dry_run, manifest)
    organize_services(repo_root, args.dry_run, manifest, keep_map=keep_map)

    # Write manifest
    manifest_dir = Path(args.manifest_dir)
    write_manifest(manifest, manifest_dir)

    if not args.dry_run and not args.confirm:
        print("No changes executed: add --confirm to apply moves.")


if __name__ == "__main__":
    main()


