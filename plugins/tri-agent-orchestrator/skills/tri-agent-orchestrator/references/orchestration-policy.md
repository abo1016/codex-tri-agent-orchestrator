# Orchestration Policy

Read this reference for non-trivial delegation, ambiguous routing, escalation, correction loops, or Sol review.

## Decision rule

Choose models by reasoning difficulty, not task size.

| Work | Route |
|---|---|
| Clear, local, pattern-following, easy to verify | Luna Worker |
| Test/lint/typecheck/compile/regression verification | Luna Tester |
| Cross-module, concurrency, consistency, complex debugging | Terra Expert |
| Architecture, security, difficult correctness, high-risk acceptance | Sol Judge |

## Cost boundaries

1. Keep the root coordinator on Terra Medium unless the user chooses otherwise.
2. Custom roles are leaf agents and must not spawn more agents.
3. Prefer 2–4 useful parallel workers.
4. Do not invoke Sol merely because a task is large.
5. Do not keep Sol continuously supervising workers.
6. Once hard reasoning is resolved, de-escalate implementation.
7. Prefer deterministic verification over another reasoning turn.
8. Default Luna Worker to High and Luna Tester to Medium reasoning.

## Codex V1/V2 recursion

`agents.max_depth = 1` is a V1 constraint. Current Multi-Agent V2 ignores `max_depth` and allows child agents to spawn by capability, so recursion is prevented by role instructions:

- `luna_worker`, `luna_tester`, `terra_expert`, and `sol_judge` are leaf roles.
- Leaf roles must never spawn, delegate to, or create another subagent.
- When scope is exceeded, return an escalation handoff to the root coordinator.
- The coordinator must not instruct a leaf role to bypass this rule.

## Worktree and ownership safety

Before delegation, the root coordinator captures the current `git status --short` and relevant diff. Pre-existing user changes are protected state.

A delegated task states:

- exact scope and expected outcome
- files/modules owned
- dependencies and concurrency constraints
- acceptance criteria
- tests/checks to run
- other agents may work concurrently
- inspect current file state before edits
- never revert unrelated changes
- never spawn additional subagents

The root coordinator owns repository-level Git state. Unless explicitly required by the task, leaf roles must not:

- commit or amend commits
- stash
- switch/create/delete branches
- reset or restore files
- rebase or merge
- force-update refs

If ownership overlaps materially, sequence work rather than racing edits.

## Evidence contract

Implementation/expert handoff:

```text
STATUS: DONE | BLOCKED | ESCALATE
Scope completed:
Files changed:
Behavior changed:
Verification:
Pre-existing failures:
Residual risks:
```

Tester handoff:

```text
STATUS: DONE | BLOCKED
PASS:
FAIL:
SKIPPED:
First actionable failure:
Likely owner:
Pre-existing failures:
Residual risks:
```

Escalation handoff:

```text
STATUS: ESCALATE
Known facts:
Unknowns:
Evidence / attempts:
Why current scope is exceeded:
Recommended next step:
```

Claims are not evidence. For material review, inspect the actual diff, tests, compiler/typecheck/lint output, and relevant runtime evidence.

## Review thresholds

Sol review SHOULD be used for:

- new subsystem architecture
- security-sensitive changes
- concurrency or distributed-system correctness
- data-loss or migration risk
- significant compatibility risk
- unresolved root-cause disputes
- material changes where wrong judgment is expensive

Sol review MAY be skipped for routine low-risk work with strong deterministic verification.

Sol returns one of:

- `BLOCKER` — correctness/security/data-loss risk; cannot accept.
- `MAJOR` — important defect/regression/risk to fix before acceptance.
- `MINOR` — legitimate non-blocking improvement.
- `INSUFFICIENT_EVIDENCE` — acceptance cannot be determined from available evidence.
- `ACCEPTED` — no blocking issue remains.

For BLOCKER/MAJOR, include file/symbol, impact, expected behavior, correction direction, and required verification. For INSUFFICIENT_EVIDENCE, identify the exact missing checks or runtime evidence.

## Correction and stopping

```text
worker/expert -> tests -> review
                      |-> ACCEPTED
                      |-> INSUFFICIENT_EVIDENCE -> tester/evidence collection
                      |-> BLOCKER/MAJOR -> coordinator -> Luna/Terra fix -> retest -> review
```

A failed attempt counts only if it produces new evidence.

Default limits for the same root cause:

- Luna implementation attempts: 2
- Terra correction rounds: 2
- Sol review rounds: 2
- unchanged deterministic failure: no blind retry
- transient infrastructure failure: retry once when evidence indicates transience

Exceed a limit only when new evidence materially changes the hypothesis or approach. Otherwise return the unresolved evidence to the root coordinator/user instead of looping.
