# Orchestration Policy

## Decision rule

Choose models by reasoning difficulty, not task size.

| Work | Route |
|---|---|
| Clear, local, pattern-following, easy to verify | Luna Worker |
| Test/lint/typecheck/regression verification | Luna Tester |
| Cross-module, concurrency, consistency, complex debugging | Terra Expert |
| Architecture, security, difficult correctness, high-risk acceptance | Sol Judge |

## Cost boundaries

1. Keep the root coordinator on Terra Medium.
2. Keep recursion depth at 1.
3. Prefer 2–4 useful parallel workers.
4. Do not invoke Sol merely because a task is large.
5. Do not keep Sol continuously supervising workers.
6. Once the hard reasoning is resolved, de-escalate implementation.
7. Prefer deterministic verification over another reasoning turn.

## Review thresholds

Sol review SHOULD be used for:

- new subsystem architecture
- security-sensitive changes
- concurrency or distributed-system correctness
- data-loss or migration risk
- significant compatibility risk
- unresolved root-cause disputes
- material changes where wrong judgment is expensive

Sol review MAY be skipped for routine low-risk work that has strong deterministic verification.

## Parallel ownership

A delegated task must specify scope, file/module ownership, dependencies, acceptance criteria, tests, and concurrency constraints. If ownership overlaps materially, sequence work rather than racing edits.

## Correction loop

```text
worker/expert -> tests -> review
                      |-> ACCEPTED
                      |-> BLOCKER/MAJOR -> coordinator -> Luna/Terra fix -> retest -> review
```

A failed attempt only counts as useful if it produces new evidence. Two evidence-producing Luna failures should normally trigger Terra escalation.
