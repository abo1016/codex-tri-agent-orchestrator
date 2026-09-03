from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "configure_tri_agent.py"
SPEC = importlib.util.spec_from_file_location("configure_tri_agent", SCRIPT)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


class ConfigureTriAgentTests(unittest.TestCase):
    def test_multiline_strings_are_not_treated_as_config(self) -> None:
        original = '''developer_instructions = """
Example only:
model = "do-not-touch"
[agents]
enabled = false
"""
model = "old"
model_reasoning_effort = "low"
'''
        rendered = mod.render_config(original)
        self.assertIn('model = "do-not-touch"', rendered)
        self.assertIn("[agents]\nenabled = false", rendered)
        self.assertIn('model = "gpt-5.6-terra"', rendered)
        self.assertEqual(
            tomllib.loads(rendered)["developer_instructions"],
            tomllib.loads(original)["developer_instructions"],
        )

    def test_existing_agents_table_and_nested_roles_are_preserved(self) -> None:
        original = '''model = "old"

[agents]
enabled = false
custom_setting = "keep-me"

[agents.researcher]
description = "existing role"
config_file = "/tmp/researcher.toml"
'''
        rendered = mod.render_config(original)
        data = tomllib.loads(rendered)
        self.assertTrue(data["agents"]["enabled"])
        self.assertEqual(data["agents"]["custom_setting"], "keep-me")
        self.assertEqual(data["agents"]["researcher"]["description"], "existing role")

    def test_render_is_idempotent(self) -> None:
        first = mod.render_config("")
        second = mod.render_config(first)
        self.assertEqual(first, second)

    def test_preserve_root_model(self) -> None:
        original = '''model = "custom-model"
model_reasoning_effort = "low"
'''
        rendered = mod.render_config(original, preserve_root_model=True)
        data = tomllib.loads(rendered)
        self.assertEqual(data["model"], "custom-model")
        self.assertEqual(data["model_reasoning_effort"], "low")
        self.assertIn("agents", data)

    def test_verify_detects_role_drift(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            (home / "agents").mkdir()
            (home / "config.toml").write_text(mod.render_config(""), encoding="utf-8")
            for filename, content in mod.desired_agents().items():
                (home / "agents" / filename).write_text(content, encoding="utf-8")

            worker = home / "agents" / "luna-worker.toml"
            worker.write_text(
                worker.read_text(encoding="utf-8").replace(
                    'sandbox_mode = "workspace-write"',
                    'sandbox_mode = "danger-full-access"',
                ),
                encoding="utf-8",
            )
            failures, _warnings = mod.verify(home)
            self.assertTrue(any("sandbox_mode" in item for item in failures))

    def test_rollback_restores_existing_and_removes_new_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            existing = home / "config.toml"
            created = home / "agents" / "new.toml"
            existing.write_text("before\n", encoding="utf-8")
            created.parent.mkdir()

            mod.atomic_write(existing, "after\n", home)
            mod.atomic_write(created, "new\n", home)
            changes = [
                mod.Change(existing, True, "before\n", "after\n"),
                mod.Change(created, False, "", "new\n"),
            ]
            errors = mod.rollback(changes, home)
            self.assertEqual(errors, [])
            self.assertEqual(existing.read_text(encoding="utf-8"), "before\n")
            self.assertFalse(created.exists())


if __name__ == "__main__":
    unittest.main()
