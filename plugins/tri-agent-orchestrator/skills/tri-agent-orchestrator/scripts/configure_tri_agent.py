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
    "default_subagent_reasoning_effort": '"xhigh"',
}
AGENT_FILES = [
    "luna-worker.toml",
    "luna-tester.toml",
    "terra-expert.toml",
    "sol-judge.toml",
]


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Configure Codex Tri-Agent orchestration.")
    p.add_argument("--codex-home", type=Path, default=codex_home())
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--check", action="store_true")
    return p.parse_args()


def read(path: Path) -> str:
    if not path.exists():
        return ""
    if not path.is_file():
        raise RuntimeError(f"Expected file: {path}")
    return path.read_text(encoding="utf-8-sig")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dst = path.with_name(f"{path.name}.backup-{stamp}")
    n = 2
    while dst.exists():
        dst = path.with_name(f"{path.name}.backup-{stamp}-{n}")
        n += 1
    shutil.copy2(path, dst)
    return dst


def table_name(line: str) -> str | None:
    s = line.split("#", 1)[0].strip()
    if s.startswith("[") and s.endswith("]") and not s.startswith("[["):
        return s[1:-1].strip()
    return None


def key_name(line: str) -> str | None:
    s = line.split("#", 1)[0].strip()
    if not s or s.startswith("[") or "=" not in s:
        return None
    return s.split("=", 1)[0].strip()


def rewrite_region(lines: list[str], values: dict[str, str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        k = key_name(line)
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


def render_config(original: str) -> str:
    if original.strip():
        tomllib.loads(original)
    lines = original.splitlines()
    first_table = next((i for i, line in enumerate(lines) if table_name(line)), len(lines))
    lines = rewrite_region(lines[:first_table], ROOT_VALUES) + lines[first_table:]

    starts = [i for i, line in enumerate(lines) if table_name(line) == "agents"]
    if len(starts) > 1:
        raise RuntimeError("Duplicate [agents] tables; resolve manually before installing.")
    if not starts:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[agents]")
        lines.extend(f"{k} = {v}" for k, v in AGENT_VALUES.items())
    else:
        start = starts[0]
        end = next((i for i in range(start + 1, len(lines)) if table_name(lines[i])), len(lines))
        lines = lines[: start + 1] + rewrite_region(lines[start + 1:end], AGENT_VALUES) + lines[end:]

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
    print("\n".join(difflib.unified_diff(
        before.splitlines(), after.splitlines(),
        fromfile=str(path), tofile=str(path), lineterm=""
    )))


def verify(home: Path) -> list[str]:
    failures: list[str] = []
    cfg = home / "config.toml"
    if not cfg.is_file():
        return [f"Missing config: {cfg}"]
    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return [f"Invalid config: {exc}"]
    expected_root = {"model": "gpt-5.6-terra", "model_reasoning_effort": "medium"}
    for k, v in expected_root.items():
        if data.get(k) != v:
            failures.append(f"{k}={data.get(k)!r}; expected {v!r}")
    agents = data.get("agents", {})
    expected_agents = {
        "enabled": True,
        "max_concurrent_threads_per_session": 4,
        "max_depth": 1,
        "default_subagent_model": "gpt-5.6-luna",
        "default_subagent_reasoning_effort": "xhigh",
    }
    for k, v in expected_agents.items():
        if agents.get(k) != v:
            failures.append(f"agents.{k}={agents.get(k)!r}; expected {v!r}")

    expected_roles = {
        "luna-worker.toml": ("luna_worker", "gpt-5.6-luna", "xhigh"),
        "luna-tester.toml": ("luna_tester", "gpt-5.6-luna", "high"),
        "terra-expert.toml": ("terra_expert", "gpt-5.6-terra", "high"),
        "sol-judge.toml": ("sol_judge", "gpt-5.6-sol", "high"),
    }
    for filename, expected in expected_roles.items():
        path = home / "agents" / filename
        if not path.is_file():
            failures.append(f"Missing agent: {path}")
            continue
        try:
            a = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            failures.append(f"Invalid {filename}: {exc}")
            continue
        actual = (a.get("name"), a.get("model"), a.get("model_reasoning_effort"))
        if actual != expected:
            failures.append(f"{filename}: {actual!r}; expected {expected!r}")
        if filename == "sol-judge.toml" and a.get("sandbox_mode") != "read-only":
            failures.append("sol_judge must use sandbox_mode=read-only")
    return failures


def main() -> int:
    args = parse_args()
    home = args.codex_home.expanduser().resolve()
    if home == Path(home.anchor):
        print("[FAIL] Refusing filesystem root as CODEX_HOME")
        return 2

    if args.check:
        failures = verify(home)
        if failures:
            for item in failures:
                print(f"[FAIL] {item}")
            return 1
        print("[OK] Terra coordinator: gpt-5.6-terra (medium)")
        print("[OK] Luna worker/tester, Terra expert, Sol judge installed")
        print("[OK] Sol judge is read-only; concurrency=4; depth=1")
        return 0

    cfg_path = home / "config.toml"
    before_cfg = read(cfg_path)
    try:
        after_cfg = render_config(before_cfg)
        agent_contents = desired_agents()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 2

    if args.dry_run:
        diff(cfg_path, before_cfg, after_cfg)
        for filename, content in agent_contents.items():
            path = home / "agents" / filename
            diff(path, read(path), content)
        return 0

    try:
        if before_cfg != after_cfg:
            b = backup(cfg_path)
            atomic_write(cfg_path, after_cfg)
            print(f"[UPDATED] {cfg_path}")
            if b: print(f"[BACKUP] {b}")
        else:
            print(f"[UNCHANGED] {cfg_path}")

        for filename, content in agent_contents.items():
            path = home / "agents" / filename
            before = read(path)
            if before == content:
                print(f"[UNCHANGED] {path}")
                continue
            b = backup(path)
            atomic_write(path, content)
            print(f"[UPDATED] {path}")
            if b: print(f"[BACKUP] {b}")
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 2

    failures = verify(home)
    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        return 1
    print("[OK] Tri-Agent configuration verified. Restart Codex to reload roles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
