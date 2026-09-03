#!/usr/bin/env python3
"""Safely configure Codex for the Tri-Agent orchestration workflow."""
from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone

try:
    import tomllib
except ModuleNotFoundError as exc:
    raise SystemExit("Python 3.11 or newer is required.") from exc

ROOT_VALUES = {
    "model": '"gpt-5.6-terra"',
    "model_reasoning_effort": '"medium"',
}
AGENT_VALUES = {
    "enabled": "true",
    "max_concurrent_threads_per_session": "4",
    "max_depth": "1",
    "default_subagent_model": '"gpt-5.6-luna"',
    "default_subagent_reasoning_effort": '"high"',
}
AGENT_FILES = [
    "luna-worker.toml",
    "luna-tester.toml",
    "terra-expert.toml",
    "sol-judge.toml",
]


@dataclass
class Change:
    path: Path
    existed: bool
    before: str
    after: str
    backup_path: Path | None = None


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Configure Codex Tri-Agent orchestration.")
    p.add_argument("--codex-home", type=Path, default=codex_home())
    p.add_argument(
        "--preserve-root-model",
        action="store_true",
        help="Do not change or verify the root model/model_reasoning_effort.",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true")
    return p.parse_args()


def ensure_safe_path(path: Path, home: Path) -> None:
    """Refuse symlinked managed paths or directories below CODEX_HOME."""
    try:
        path.relative_to(home)
    except ValueError as exc:
        raise RuntimeError(f"Managed path escapes CODEX_HOME: {path}") from exc

    current = path
    while True:
        if current.is_symlink():
            raise RuntimeError(f"Refusing symlinked managed path: {current}")
        if current == home:
            break
        current = current.parent


def read(path: Path, home: Path | None = None) -> str:
    if home is not None:
        ensure_safe_path(path, home)
    if not path.exists():
        return ""
    if not path.is_file():
        raise RuntimeError(f"Expected file: {path}")
    return path.read_text(encoding="utf-8-sig")


def atomic_write(path: Path, content: str, home: Path) -> None:
    ensure_safe_path(path, home)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_safe_path(path.parent, home)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        if path.exists():
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def backup(path: Path, home: Path) -> Path | None:
    ensure_safe_path(path, home)
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(f"{path.name}.backup-{stamp}")
    n = 2
    while dst.exists():
        dst = path.with_name(f"{path.name}.backup-{stamp}-{n}")
        n += 1
    ensure_safe_path(dst, home)
    shutil.copy2(path, dst)
    return dst


def structural_lines(lines: list[str]) -> list[str]:
    """Return TOML lines with strings/comments blanked while preserving positions."""
    state = "normal"
    result: list[str] = []
    triple_double = '"' * 3
    triple_single = "'" * 3

    for line in lines:
        out: list[str] = []
        i = 0
        while i < len(line):
            if state == "ml_basic":
                if line.startswith(triple_double, i):
                    out.extend("   ")
                    i += 3
                    state = "normal"
                elif line[i] == "\\" and i + 1 < len(line):
                    out.extend("  ")
                    i += 2
                else:
                    out.append(" ")
                    i += 1
                continue

            if state == "ml_literal":
                if line.startswith(triple_single, i):
                    out.extend("   ")
                    i += 3
                    state = "normal"
                else:
                    out.append(" ")
                    i += 1
                continue

            if state == "basic":
                if line[i] == "\\" and i + 1 < len(line):
                    out.extend("  ")
                    i += 2
                elif line[i] == '"':
                    out.append(" ")
                    i += 1
                    state = "normal"
                else:
                    out.append(" ")
                    i += 1
                continue

            if state == "literal":
                if line[i] == "'":
                    out.append(" ")
                    i += 1
                    state = "normal"
                else:
                    out.append(" ")
                    i += 1
                continue

            if line.startswith(triple_double, i):
                out.extend("   ")
                i += 3
                state = "ml_basic"
            elif line.startswith(triple_single, i):
                out.extend("   ")
                i += 3
                state = "ml_literal"
            elif line[i] == '"':
                out.append(" ")
                i += 1
                state = "basic"
            elif line[i] == "'":
                out.append(" ")
                i += 1
                state = "literal"
            elif line[i] == "#":
                out.extend(" " * (len(line) - i))
                i = len(line)
            else:
                out.append(line[i])
                i += 1

        if state in {"basic", "literal"}:
            state = "normal"
        result.append("".join(out))

    return result


def table_name(structural_line: str) -> str | None:
    s = structural_line.strip()
    if s.startswith("[") and s.endswith("]") and not s.startswith("[["):
        return s[1:-1].strip()
    return None


def key_name(structural_line: str) -> str | None:
    s = structural_line.strip()
    if not s or s.startswith("[") or "=" not in s:
        return None
    return s.split("=", 1)[0].strip()


def rewrite_region(
    lines: list[str],
    structural: list[str],
    values: dict[str, str],
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line, structure in zip(lines, structural, strict=True):
        k = key_name(structure)
        if k in values:
            if k in seen:
                continue
            out.append(f"{k} = {values[k]}")
            seen.add(k)
        else:
            out.append(line)

    while out and out[-1] == "":
        out.pop()
    for k, v in values.items():
        if k not in seen:
            out.append(f"{k} = {v}")
    return out


def render_config(original: str, preserve_root_model: bool = False) -> str:
    if original.strip():
        tomllib.loads(original)

    lines = original.splitlines()
    structural = structural_lines(lines)

    if not preserve_root_model:
        first_table = next(
            (i for i, line in enumerate(structural) if table_name(line)),
            len(lines),
        )
        root_lines = rewrite_region(
            lines[:first_table],
            structural[:first_table],
            ROOT_VALUES,
        )
        if first_table < len(lines):
            root_lines.append("")
        lines = root_lines + lines[first_table:]

    structural = structural_lines(lines)
    starts = [i for i, line in enumerate(structural) if table_name(line) == "agents"]
    if len(starts) > 1:
        raise RuntimeError("Duplicate [agents] tables; resolve manually before installing.")

    if not starts:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[agents]")
        lines.extend(f"{k} = {v}" for k, v in AGENT_VALUES.items())
    else:
        start = starts[0]
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if table_name(structural[i])
            ),
            len(lines),
        )
        agent_lines = rewrite_region(
            lines[start + 1 : end],
            structural[start + 1 : end],
            AGENT_VALUES,
        )
        if end < len(lines):
            agent_lines.append("")
        lines = lines[: start + 1] + agent_lines + lines[end:]

    rendered = "\n".join(lines).rstrip() + "\n"
    tomllib.loads(rendered)
    return rendered


def asset_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets"


def desired_agents() -> dict[str, str]:
    result = {}
    for name in AGENT_FILES:
        content = (asset_dir() / name).read_text(encoding="utf-8")
        tomllib.loads(content)
        result[name] = content.rstrip() + "\n"
    return result


def diff(path: Path, before: str, after: str) -> None:
    if before == after:
        print(f"[UNCHANGED] {path}")
        return
    print(
        "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile=str(path),
                tofile=str(path),
                lineterm="",
            )
        )
    )


def multi_agent_v2_enabled(data: dict) -> bool:
    features = data.get("features")
    if not isinstance(features, dict):
        return False
    value = features.get("multi_agent_v2")
    if value is True:
        return True
    return isinstance(value, dict) and value.get("enabled") is True


def verify(
    home: Path,
    preserve_root_model: bool = False,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    cfg = home / "config.toml"

    try:
        ensure_safe_path(cfg, home)
    except Exception as exc:
        return [str(exc)], warnings

    if not cfg.is_file():
        return [f"Missing config: {cfg}"], warnings

    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return [f"Invalid config: {exc}"], warnings

    if not preserve_root_model:
        expected_root = {
            "model": "gpt-5.6-terra",
            "model_reasoning_effort": "medium",
        }
        for k, v in expected_root.items():
            if data.get(k) != v:
                failures.append(f"{k}={data.get(k)!r}; expected {v!r}")

    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        failures.append("[agents] must be a TOML table")
        agents = {}

    expected_agents = {
        "enabled": True,
        "max_concurrent_threads_per_session": 4,
        "max_depth": 1,
        "default_subagent_model": "gpt-5.6-luna",
        "default_subagent_reasoning_effort": "high",
    }
    for k, v in expected_agents.items():
        if agents.get(k) != v:
            failures.append(f"agents.{k}={agents.get(k)!r}; expected {v!r}")

    try:
        expected_role_contents = desired_agents()
    except Exception as exc:
        failures.append(f"Invalid bundled agent assets: {exc}")
        expected_role_contents = {}

    for filename in AGENT_FILES:
        path = home / "agents" / filename
        try:
            ensure_safe_path(path, home)
        except Exception as exc:
            failures.append(str(exc))
            continue
        if not path.is_file():
            failures.append(f"Missing agent: {path}")
            continue

        try:
            actual_text = path.read_text(encoding="utf-8-sig").rstrip() + "\n"
            actual = tomllib.loads(actual_text)
        except Exception as exc:
            failures.append(f"Invalid {filename}: {exc}")
            continue

        expected_text = expected_role_contents.get(filename)
        if expected_text is None:
            continue
        expected = tomllib.loads(expected_text)

        for key in ("name", "model", "model_reasoning_effort", "sandbox_mode"):
            if actual.get(key) != expected.get(key):
                failures.append(
                    f"{filename}.{key}={actual.get(key)!r}; "
                    f"expected {expected.get(key)!r}"
                )

        if actual.get("developer_instructions") != expected.get("developer_instructions"):
            failures.append(f"{filename}.developer_instructions drifted from bundled role")

        if set(actual) != set(expected):
            failures.append(f"{filename} has unexpected/missing top-level keys")

    if multi_agent_v2_enabled(data):
        warnings.append(
            "Multi-Agent V2 ignores agents.max_depth; leaf role instructions "
            "provide the no-recursion policy."
        )

    return failures, warnings


def rollback(changes: list[Change], home: Path) -> list[str]:
    errors: list[str] = []
    for change in reversed(changes):
        try:
            if change.existed:
                atomic_write(change.path, change.before, home)
            elif change.path.exists():
                ensure_safe_path(change.path, home)
                change.path.unlink()
        except Exception as exc:
            errors.append(f"{change.path}: {exc}")
    return errors


def main() -> int:
    args = parse_args()
    home = args.codex_home.expanduser().resolve()
    if home == Path(home.anchor):
        print("[FAIL] Refusing filesystem root as CODEX_HOME")
        return 2

    if args.check:
        failures, warnings = verify(home, args.preserve_root_model)
        for warning in warnings:
            print(f"[WARN] {warning}")
        if failures:
            for item in failures:
                print(f"[FAIL] {item}")
            return 1
        if args.preserve_root_model:
            print("[OK] Root model preserved (not verified by request)")
        else:
            print("[OK] Terra coordinator: gpt-5.6-terra (medium)")
        print("[OK] Luna worker(high)/tester(medium), Terra expert, Sol judge installed")
        print("[OK] Sol judge is read-only; concurrency=4; V1 max_depth=1")
        return 0

    cfg_path = home / "config.toml"
    try:
        before_cfg = read(cfg_path, home)
        after_cfg = render_config(before_cfg, args.preserve_root_model)
        agent_contents = desired_agents()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 2

    changes = [
        Change(
            path=cfg_path,
            existed=cfg_path.exists(),
            before=before_cfg,
            after=after_cfg,
        )
    ]
    for filename, content in agent_contents.items():
        path = home / "agents" / filename
        try:
            before = read(path, home)
        except Exception as exc:
            print(f"[FAIL] {exc}")
            return 2
        changes.append(
            Change(
                path=path,
                existed=path.exists(),
                before=before,
                after=content,
            )
        )

    if args.dry_run:
        for change in changes:
            diff(change.path, change.before, change.after)
        return 0

    pending = [change for change in changes if change.before != change.after]
    if not pending:
        print("[UNCHANGED] Tri-Agent configuration already matches desired state.")
        failures, warnings = verify(home, args.preserve_root_model)
        for warning in warnings:
            print(f"[WARN] {warning}")
        if failures:
            for item in failures:
                print(f"[FAIL] {item}")
            return 1
        return 0

    applied: list[Change] = []
    try:
        for change in pending:
            ensure_safe_path(change.path, home)
        for change in pending:
            change.backup_path = backup(change.path, home)
        for change in pending:
            atomic_write(change.path, change.after, home)
            applied.append(change)
            print(f"[UPDATED] {change.path}")
            if change.backup_path:
                print(f"[BACKUP] {change.backup_path}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        rollback_errors = rollback(applied, home)
        if rollback_errors:
            for item in rollback_errors:
                print(f"[ROLLBACK-FAIL] {item}")
        else:
            print("[ROLLED BACK] Partial writes reverted.")
        return 2

    failures, warnings = verify(home, args.preserve_root_model)
    for warning in warnings:
        print(f"[WARN] {warning}")
    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        rollback_errors = rollback(applied, home)
        if rollback_errors:
            for item in rollback_errors:
                print(f"[ROLLBACK-FAIL] {item}")
        else:
            print("[ROLLED BACK] Verification failed; installed files restored.")
        return 1

    print("[OK] Tri-Agent configuration verified. Restart Codex to reload roles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
