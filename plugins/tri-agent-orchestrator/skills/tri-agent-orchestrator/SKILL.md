---
name: tri-agent-orchestrator
description: >
  Cost-aware Codex multi-agent orchestration using GPT-5.6 Luna, Terra, and Sol.
  Use for engineering work that benefits from delegated implementation, parallel
  verification, complexity-based model routing, or independent high-risk review.
  Avoid activating solely for trivial isolated edits unless explicitly requested.
---

# Tri-Agent Orchestrator

Use the cheapest capable model for each reasoning step. The root coordinator owns scope, integration, Git state, and final acceptance.

## Roles

- `terra` root/coordinator: triage, decomposition, coordination, integration, small glue edits.
- `luna_worker`: bounded routine implementation and targeted tests.
- `luna_tester`: deterministic verification and concise evidence.
- `terra_expert`: complex engineering and evidence-based debugging.
- `sol_judge`: read-only architecture, root-cause, security/high-risk review, and critical acceptance.

All custom roles are **leaf agents**: never spawn or delegate to another subagent. If scope is exceeded, return control to the root coordinator.

## Routing

Route by reasoning difficulty, not task size.

- Luna Worker: clear, local, pattern-following, easy-to-verify implementation.
- Luna Tester: tests, lint, typecheck, compile, regression reproduction.
- Terra Expert: cross-module work, transactions, concurrency, consistency, queues/cache, difficult debugging, risky migrations.
- Sol Judge: architecture, security, difficult distributed correctness, unresolved root cause, or high-risk acceptance.

A large task made of simple independent work should become multiple Luna tasks, not a Sol task.

For non-trivial delegation, ambiguous routing, escalation, correction loops, or Sol review, read [references/orchestration-policy.md](references/orchestration-policy.md).

## Workflow

For non-trivial work:

1. DISCOVER relevant code, tests, rules, and current worktree state.
2. BASELINE pre-existing `git status --short` and relevant diff; protect user changes.
3. CLASSIFY and DECOMPOSE by reasoning difficulty and safe ownership boundaries.
4. DELEGATE 2–4 useful leaf-agent tasks when parallelism helps.
5. EXECUTE within assigned ownership.
6. INTEGRATE in the root thread.
7. VERIFY deterministically; use `luna_tester` when logs or integration checks are substantial.
8. REVIEW with `sol_judge` only when risk justifies it.
9. CORRECT, RETEST, and ACCEPT.

Every delegated task must state scope, owned files/modules, acceptance criteria, tests, concurrency constraints, and that the agent must not spawn subagents or revert unrelated changes.

The root coordinator owns repository-level Git state. Leaf agents must not commit, stash, switch branches, reset, restore, or rebase unless explicitly required by the task.

## Escalation and stopping

Luna -> Terra after two evidence-producing failed attempts, unclear root cause, or when deeper cross-component correctness is required.

Terra -> Sol for high-impact architecture, difficult security/distributed correctness, persistent ambiguity after substantial evidence gathering, or unusually expensive wrong decisions.

After Sol resolves the hard reasoning step, de-escalate implementation immediately.

Do not repeat an unchanged failing approach. Default budget for the same root cause: two Luna attempts, two Terra correction rounds, and at most two Sol review rounds unless new evidence materially changes the approach.

## Review and evidence

`sol_judge` never edits files and returns one of:

- BLOCKER
- MAJOR
- MINOR
- INSUFFICIENT_EVIDENCE
- ACCEPTED

BLOCKER/MAJOR must include correction and verification requirements. INSUFFICIENT_EVIDENCE must state exactly what evidence is missing.

Leaf-agent handoffs should be compact:

```text
STATUS: DONE | BLOCKED | ESCALATE
Scope completed:
Files changed:
Behavior changed:
Verification:
Pre-existing failures:
Residual risks:
```

Do not trust worker claims without checking diff/tests when the review matters.

## Cost discipline

- No subagent for a trivial local edit.
- Keep custom roles as leaf agents.
- Prefer deterministic tools over another reasoning round.
- Sol does not do mechanical implementation or continuously supervise workers.
- Search before broad repository reads.
- Keep bulk logs in disposable worker/tester contexts.
- Default Luna Worker to `high` reasoning and Luna Tester to `medium`; increase only when evidence justifies it.

## Codex V1/V2 note

`agents.max_depth = 1` constrains V1 nesting. Current Codex Multi-Agent V2 ignores that field, so V2 recursion control depends on the leaf-agent instructions above. Never describe `max_depth` as a V2 hard guarantee.

## Setup / verification

For installation or verification:

```bash
python "<skill>/scripts/configure_tri_agent.py" --dry-run
python "<skill>/scripts/configure_tri_agent.py"
python "<skill>/scripts/configure_tri_agent.py" --check
```

Use `--preserve-root-model` during installation when existing root model/reasoning defaults must remain unchanged.

The script preserves unrelated config, refuses symlinked managed files, backs up changed files, rolls back partial writes on failure, and installs the four roles. After configuration, start a new Codex session.

## User communication

During longer work, report phases, important findings, and blockers without narrating every tool call.

Final summary: what changed, important files, verification, Sol result when used, and remaining risks.
