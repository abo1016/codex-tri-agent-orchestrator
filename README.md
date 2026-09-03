# Codex Tri-Agent Orchestrator

[简体中文](README.zh-CN.md)

> Cost-aware multi-agent orchestration for Codex using GPT-5.6 Luna, Terra, and Sol.

```text
You
 └─ Terra Coordinator · medium
     ├─ Luna Worker    · high    — routine implementation + targeted tests
     ├─ Luna Tester    · medium  — verification, lint, regression tests
     ├─ Terra Expert   · high    — complex implementation / debugging
     └─ Sol Judge      · high    — read-only architecture & critical review
```

All custom roles are **leaf agents** and never spawn additional subagents. Current Codex Multi-Agent V2 ignores `agents.max_depth`, so `max_depth = 1` is treated as a V1 constraint; V2 recursion is prevented by role instructions.

## Why this architecture?

Sol is reserved for high-value judgment, Luna handles bounded implementation and deterministic verification, and Terra coordinates and handles hard engineering work.

```text
clear + local + verifiable       -> Luna Worker
verification / regression        -> Luna Tester
complex implementation/debugging -> Terra Expert
architecture / high-risk review  -> Sol Judge
```

Large does not mean difficult. Decompose first, then escalate only when reasoning difficulty requires it.

## What the plugin installs

- `tri-agent-orchestrator` Skill
- `luna_worker` — GPT-5.6 Luna, high
- `luna_tester` — GPT-5.6 Luna, medium
- `terra_expert` — GPT-5.6 Terra, high
- `sol_judge` — GPT-5.6 Sol, high, read-only
- bounded Codex agent defaults, including V1 `max_depth = 1`
- a Python 3.11+ installer with `--dry-run`, `--check`, and `--preserve-root-model`

Installer safety now includes multiline-aware TOML editing, timestamped backups, symlink refusal for managed paths, role-drift verification, and rollback after partial writes or failed verification.

## Install

```bash
codex plugin marketplace add abo1016/codex-tri-agent-orchestrator --ref main
codex plugin add tri-agent-orchestrator@codex-tri-agent-orchestrator
```

Start a new Codex session, open `/skills`, and select **Tri-Agent Orchestrator**.

Manual install/verification:

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --dry-run
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check
```

To preserve an existing root `model` and `model_reasoning_effort`:

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --preserve-root-model
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check --preserve-root-model
```

## Default workflow

```text
DISCOVER + WORKTREE BASELINE
  -> CLASSIFY / DECOMPOSE
  -> PARALLEL LEAF EXECUTION
  -> INTEGRATE
  -> DETERMINISTIC VERIFY
  -> SOL REVIEW (risk-based)
  -> CORRECT
  -> RETEST
  -> ACCEPT
```

Before delegation, the root coordinator records the current worktree state and protects pre-existing user changes. The root owns repository-level Git state; leaf agents should not commit, stash, switch branches, reset, restore, or rebase unless explicitly assigned.

## Escalation and stopping

- Two evidence-producing Luna failures normally escalate to Terra.
- Terra escalates to Sol for high-impact architecture, difficult security/distributed correctness, or persistent ambiguity.
- Same-root-cause default budget: 2 Luna attempts, 2 Terra correction rounds, and 2 Sol review rounds.
- Do not blindly retry unchanged deterministic failures.
- After Sol resolves the hard reasoning step, implementation de-escalates immediately.

Sol Judge returns one of:

```text
BLOCKER
MAJOR
MINOR
INSUFFICIENT_EVIDENCE
ACCEPTED
```

## Cost discipline

- Do not spawn agents for trivial edits.
- Prefer 2–4 useful workers over maximum fan-out.
- Keep custom roles as leaf agents.
- Prefer compiler/tests/linters/runtime evidence over another reasoning round.
- Do not use Sol for mechanical coding or continuous supervision.
- Default Luna Worker to `high` and Luna Tester to `medium`.

## Files

```text
.agents/plugins/marketplace.json
plugins/tri-agent-orchestrator/
  .codex-plugin/plugin.json
  skills/tri-agent-orchestrator/
    SKILL.md
    agents/openai.yaml
    assets/
      luna-worker.toml
      luna-tester.toml
      terra-expert.toml
      sol-judge.toml
    references/orchestration-policy.md
    scripts/configure_tri_agent.py
    tests/test_configure_tri_agent.py
```

CI validates the installer on Python 3.11–3.13 and covers multiline TOML preservation, idempotency, existing role preservation, root model preservation, rollback, and role security drift.

This project is unofficial and is not affiliated with or endorsed by OpenAI.

## License

MIT
