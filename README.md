# Codex Tri-Agent Orchestrator

[简体中文](README.zh-CN.md)

> Cost-aware multi-agent orchestration for Codex using GPT-5.6 Luna, Terra, and Sol.

Codex Tri-Agent Orchestrator turns Codex into a small engineering team with explicit model routing:

```text
You
 └─ Terra Coordinator · medium
     ├─ Luna Worker    · xhigh   — routine implementation + targeted tests
     ├─ Luna Tester    · high    — verification, lint, regression tests
     ├─ Terra Expert   · high    — complex implementation / debugging
     └─ Sol Judge      · high    — read-only architecture & final review
```

## Why this architecture?

The expensive model should not stay in the hot path all day. Sol is reserved for high-value judgment; Luna handles bounded work; Terra coordinates and takes the hard implementation cases.

Routing rule:

```text
clear + local + verifiable       -> Luna
complex implementation/debugging -> Terra
architecture / high-risk review  -> Sol
```

Large does not mean difficult. Decompose first, then escalate only when reasoning difficulty requires it.

## What the plugin installs

- `tri-agent-orchestrator` Skill
- `luna_worker` — GPT-5.6 Luna, xhigh
- `luna_tester` — GPT-5.6 Luna, high
- `terra_expert` — GPT-5.6 Terra, high
- `sol_judge` — GPT-5.6 Sol, high, read-only
- safe Codex config defaults: Terra coordinator, agents enabled, bounded concurrency/depth
- a Python installer with `--dry-run` and `--check`

The installer merges only the keys owned by this plugin and creates timestamped backups before changing existing files.

## Install as a Codex Plugin

```bash
codex plugin marketplace add abo1016/codex-tri-agent-orchestrator --ref main
codex plugin add tri-agent-orchestrator@codex-tri-agent-orchestrator
```

Start a **new Codex session**, open `/skills`, select **Tri-Agent Orchestrator**, then ask:

```text
Use Tri-Agent Orchestrator to configure and verify my Codex multi-agent setup.
```

You can also install the Skill directly:

```text
$skill-installer Install the skill from https://github.com/abo1016/codex-tri-agent-orchestrator/tree/main/plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator
```

## Manual installer

Requires Python 3.11+.

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --dry-run
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check
codex doctor
```

Restart Codex after installation.

## Daily usage

For normal development, just start Codex normally and ask for work. The coordinator should decide whether delegation adds value.

Examples:

```text
Implement user notification preferences using the tri-agent workflow.
```

```text
Investigate this Kafka consumer bug. Use Terra for the difficult implementation and Sol only for root-cause review.
```

```text
Review the current diff with Sol Judge. Do not modify files.
```

## Default workflow

```text
DISCOVER
  -> DESIGN (only when needed)
  -> DECOMPOSE
  -> ROUTE
  -> PARALLEL EXECUTION
  -> TEST
  -> SOL REVIEW (risk-based)
  -> CORRECT
  -> RETEST
  -> ACCEPT
```

Sol review is intentionally **risk-based**, not mandatory for every 20-line change. Routine work can be accepted after deterministic verification; architecture/security/concurrency/high-risk changes should go through Sol Judge.

## Cost discipline

- Do not spawn agents for trivial edits.
- Prefer 2–4 useful workers over maximum fan-out.
- Keep recursion depth at 1.
- Do not use Sol for mechanical coding.
- After a difficult decision is solved, immediately de-escalate implementation to Terra/Luna.
- Prefer compiler/tests/linters/runtime evidence over another reasoning round.
- Two evidence-producing Luna failures are a signal to escalate to Terra, not to keep retrying Luna.

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
```

## Safety

`sol_judge` is read-only by construction. Implementation roles use workspace-write. The plugin does not enable unrestricted sandbox access, force-push, production deployment, or destructive operations.

## Compatibility

Codex configuration evolves. This project intentionally avoids experimental-only multi-agent flags in its default install. If explicit per-spawn model overrides become stable in your Codex version, the Skill may use them when available; otherwise it delegates to named custom agents.

## Inspiration

This project is informed by community work around budget-aware Codex orchestration, including `codex-chief`, `codex-skills-sol-luna-orchestrator`, and experiments with parallel Codex subagents.

This project is unofficial and is not affiliated with or endorsed by OpenAI.

## License

MIT
