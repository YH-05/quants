#!/usr/bin/env python3
"""Claude Config Sync - .claude/ 設定ファイルをプロジェクト間で同期

Usage:
    python3 sync.py              # 全同期（差分のみコピー）
    python3 sync.py --dry-run    # 差分確認のみ
    python3 sync.py --auto       # 自動モード（差分検出→サイレント同期）
    python3 sync.py --status     # 同期ステータス表示
    python3 sync.py --list       # 同期対象一覧
"""

from __future__ import annotations

import argparse
import contextlib
import filecmp
import re
import shutil
import sys
from fnmatch import fnmatch
from pathlib import Path

CONFIG_FILENAME = "sync-config.yaml"
CATEGORIES = ("skills", "agents", "commands", "rules")


# ── Minimal YAML Parser (stdlib only) ────────────────────────
# Supports: nested dicts, lists of strings, lists of dicts, comments
# Does NOT support: anchors, aliases, multiline strings, flow style


def load_yaml(path: Path) -> dict:
    """Load a simple YAML file."""
    with open(path) as f:
        return _parse_yaml(f.read())


def _parse_yaml(text: str) -> dict:
    lines = text.split("\n")
    result, _ = _parse_mapping(lines, 0, 0)
    return result


def _skip(lines: list[str], i: int) -> int:
    """Skip empty lines and full-line comments."""
    while i < len(lines):
        s = lines[i].strip()
        if s and not s.startswith("#"):
            return i
        i += 1
    return i


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _split_key_value(line: str) -> tuple[str, str] | None:
    """Split 'key: value' handling URLs with colons."""
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)", line)
    if m:
        return m.group(1), m.group(2).strip()
    return None


def _parse_mapping(lines: list[str], i: int, min_indent: int) -> tuple[dict, int]:
    result: dict = {}
    while True:
        i = _skip(lines, i)
        if i >= len(lines):
            break
        line = lines[i]
        ind = _indent(line)
        if ind < min_indent:
            break
        stripped = line.strip()
        if stripped.startswith("-"):
            break

        kv = _split_key_value(stripped)
        if not kv:
            i += 1
            continue

        key, rest = kv
        # Strip inline comment (but not in URLs)
        if " #" in rest and "://" not in rest:
            rest = rest[: rest.index(" #")].strip()

        if rest:
            result[key] = _strip_quotes(rest)
            i += 1
        else:
            i = _skip(lines, i + 1)
            if i >= len(lines):
                result[key] = {}
                break
            next_ind = _indent(lines[i])
            if next_ind <= ind:
                result[key] = {}
                continue
            if lines[i].strip().startswith("-"):
                result[key], i = _parse_sequence(lines, i, next_ind)
            else:
                result[key], i = _parse_mapping(lines, i, next_ind)
    return result, i


def _parse_sequence(lines: list[str], i: int, min_indent: int) -> tuple[list, int]:
    result: list = []
    while True:
        i = _skip(lines, i)
        if i >= len(lines):
            break
        line = lines[i]
        ind = _indent(line)
        if ind < min_indent:
            break
        stripped = line.strip()
        if not stripped.startswith("-"):
            break

        item_text = stripped[1:].strip()

        kv = _split_key_value(item_text)
        if kv:
            # Dict item: - key: value
            item: dict = {}
            k, v = kv
            item[k] = _strip_quotes(v)
            i += 1
            # Read continuation keys at deeper indent
            while True:
                j = _skip(lines, i)
                if j >= len(lines):
                    i = j
                    break
                nl = lines[j]
                ni = _indent(nl)
                ns = nl.strip()
                if ni <= ind or ns.startswith("-"):
                    i = j
                    break
                nkv = _split_key_value(ns)
                if nkv:
                    nk, nv = nkv
                    item[nk] = _strip_quotes(nv)
                i = j + 1
            result.append(item)
        else:
            # String item: - value
            result.append(_strip_quotes(item_text))
            i += 1
    return result, i


# ── Path Resolution ──────────────────────────────────────────


def find_project_root() -> Path:
    """Find project root containing .claude/sync-config.yaml."""
    # Try script location first
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".claude" / CONFIG_FILENAME).exists():
            return current
        current = current.parent
    # Fallback: cwd
    cwd = Path.cwd()
    if (cwd / ".claude" / CONFIG_FILENAME).exists():
        return cwd
    msg = f".claude/{CONFIG_FILENAME} not found"
    raise FileNotFoundError(msg)


def resolve_target_path(target: dict) -> Path | None:
    """Resolve local filesystem path for a sync target."""
    if "local_path" in target:
        path = Path(target["local_path"])
        if path.exists() and (path / ".claude").exists():
            return path

    github_url = target.get("github_url", "")
    if github_url:
        repo_name = github_url.rstrip("/").split("/")[-1].removesuffix(".git")
        for parent in [Path.home() / "Desktop", Path.home() / "Projects", Path.home()]:
            candidate = parent / repo_name
            if candidate.exists() and (candidate / ".claude").is_dir():
                return candidate
    return None


# ── Item Discovery & Filtering ───────────────────────────────


def get_items(claude_dir: Path, category: str) -> list[tuple[str, Path]]:
    """Get all items in a category as (name, source_path) tuples.

    For .md files, name is the stem (without extension).
    For directories, name is the directory name.
    """
    cat_dir = claude_dir / category
    if not cat_dir.exists():
        return []

    items = []
    for entry in sorted(cat_dir.iterdir()):
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        if entry.is_file() and entry.suffix == ".md":
            items.append((entry.stem, entry))
        elif entry.is_dir():
            items.append((entry.name, entry))
        else:
            # Non-.md files (e.g., .py, .json) - use full name
            items.append((entry.name, entry))
    return items


def filter_items(
    items: list[tuple[str, Path]],
    include: str | list,
    exclude: list | None = None,
) -> list[tuple[str, Path]]:
    """Filter items based on include/exclude rules.

    include: "*" for all, or list of specific names
    exclude: list of glob patterns to exclude (only used with "*")
    """
    if isinstance(include, str) and include == "*":
        result = list(items)
    elif isinstance(include, list):
        include_set = set(include)
        result = [(n, p) for n, p in items if n in include_set]
    else:
        return []

    if exclude:
        result = [
            (n, p) for n, p in result if not any(fnmatch(n, pat) for pat in exclude)
        ]
    return result


# ── Sync Logic ───────────────────────────────────────────────


def needs_sync(src: Path, dst: Path) -> bool:
    """Check if source and destination differ."""
    if not dst.exists():
        return True
    if src.is_file() and dst.is_file():
        return not filecmp.cmp(src, dst, shallow=False)
    if src.is_dir() and dst.is_dir():
        return _dir_differs(src, dst)
    return True  # type mismatch


def _dir_differs(src: Path, dst: Path) -> bool:
    """Recursively check if two directories differ."""
    src_files = {
        p.relative_to(src)
        for p in src.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    }
    dst_files = {
        p.relative_to(dst)
        for p in dst.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    }

    if src_files != dst_files:
        return True

    return any(
        not filecmp.cmp(src / rel, dst / rel, shallow=False) for rel in src_files
    )


def sync_item(src: Path, dst: Path) -> None:
    """Copy a single item (file or directory)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


# ── Main Operations ─────────────────────────────────────────


def load_config() -> dict:
    root = find_project_root()
    return load_yaml(root / ".claude" / CONFIG_FILENAME)


def run_sync(
    *,
    dry_run: bool = False,
    quiet: bool = False,
) -> list[str]:
    """Run sync operation. Returns list of result messages."""
    root = find_project_root()
    config = load_config()
    claude_dir = root / ".claude"
    sync_conf = config.get("sync", {})
    results: list[str] = []

    for target in config.get("targets", []):
        target_path = resolve_target_path(target)
        target_name = target.get("name", "unknown")

        if not target_path:
            if not quiet:
                results.append(f"WARNING: {target_name}: local path not found")
            continue

        target_claude = target_path / ".claude"
        synced_count = 0

        for category in CATEGORIES:
            include = sync_conf.get(category, [])
            if not include:
                continue
            exclude = sync_conf.get(f"{category}_exclude", [])

            all_items = get_items(claude_dir, category)
            filtered = filter_items(all_items, include, exclude)

            for name, src_path in filtered:
                dst_path = target_claude / category / src_path.name

                if not needs_sync(src_path, dst_path):
                    continue

                if dry_run:
                    status = "NEW" if not dst_path.exists() else "MODIFIED"
                    results.append(f"  [{status}] {category}/{name} -> {target_name}")
                else:
                    sync_item(src_path, dst_path)
                    if not quiet:
                        results.append(f"  SYNCED: {category}/{name} -> {target_name}")
                synced_count += 1

        if synced_count == 0 and not quiet:
            results.append(f"  {target_name}: all in sync")

    return results


def run_auto() -> None:
    """Auto mode: compare and sync all items silently."""
    with contextlib.suppress(Exception):
        run_sync(quiet=True)


def show_status() -> list[str]:
    """Show detailed sync status for all configured items."""
    root = find_project_root()
    config = load_config()
    claude_dir = root / ".claude"
    sync_conf = config.get("sync", {})
    results: list[str] = []

    for target in config.get("targets", []):
        target_path = resolve_target_path(target)
        target_name = target.get("name", "unknown")

        if not target_path:
            results.append(f"[{target_name}] local path not found")
            continue

        target_claude = target_path / ".claude"
        results.append(f"[{target_name}] {target_path}")

        out_of_sync = 0
        total = 0

        for category in CATEGORIES:
            include = sync_conf.get(category, [])
            if not include:
                continue
            exclude = sync_conf.get(f"{category}_exclude", [])

            all_items = get_items(claude_dir, category)
            filtered = filter_items(all_items, include, exclude)

            for name, src_path in filtered:
                dst_path = target_claude / category / src_path.name
                total += 1
                if needs_sync(src_path, dst_path):
                    out_of_sync += 1
                    if not dst_path.exists():
                        results.append(f"  MISSING: {category}/{name}")
                    else:
                        results.append(f"  MODIFIED: {category}/{name}")

        if out_of_sync == 0:
            results.append(f"  All {total} items in sync")
        else:
            results.append(f"  {out_of_sync}/{total} items out of sync")

    return results


def list_targets() -> list[str]:
    """List all resolved sync targets."""
    config = load_config()
    root = find_project_root()
    claude_dir = root / ".claude"
    sync_conf = config.get("sync", {})
    results: list[str] = []

    for category in CATEGORIES:
        include = sync_conf.get(category, [])
        if not include:
            continue
        exclude = sync_conf.get(f"{category}_exclude", [])

        all_items = get_items(claude_dir, category)
        filtered = filter_items(all_items, include, exclude)

        results.append(f"\n[{category}] ({len(filtered)} items)")
        for name, _ in filtered:
            results.append(f"  - {name}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Claude Config Sync")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without copying"
    )
    parser.add_argument("--auto", action="store_true", help="Auto mode (silent sync)")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--list", action="store_true", help="List sync targets")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress output")
    args = parser.parse_args()

    if args.auto:
        run_auto()
        return

    if args.status:
        for line in show_status():
            print(line)
        return

    if args.list:
        for line in list_targets():
            print(line)
        return

    results = run_sync(dry_run=args.dry_run, quiet=args.quiet)
    if results:
        for line in results:
            print(line)
    elif not args.quiet:
        print("All items in sync.")


if __name__ == "__main__":
    main()
