---
name: tri-agent-orchestrator
description: >
  Cost-aware Codex multi-agent orchestration using GPT-5.6 Luna, Terra, and Sol.
  Use for feature development, bug fixing, refactoring, architecture, testing,
  and review when work can benefit from model-specialized delegation.
---

# Tri-Agent Orchestrator

Use the cheapest capable model for each reasoning step.

## Roles

- `terra` root/coordinator (current main thread): triage, decomposition, coordination, small glue edits.
- `luna_worker`: routine implementation and targeted tests.
- `luna_tester`: testing, lint, typecheck, regression verification; return concise evidence.
- `terra_expert`: complex engineering and debugging.
- `sol_judge`: read-only architecture, root-cause judgment, security/high-risk review, final critical acceptance.

## Routing

Route by reasoning difficulty, not by task size.

Use `luna_worker` for clear, bounded, verifiable work following known project patterns.

Use `terra_expert` for cross-module implementation, transactions, concurrency, consistency, Kafka/queues, cache behavior, difficult debugging, performance-sensitive work, or risky migrations.

Use `sol_judge` only when high-value judgment is justified: architecture, meaningful trade-offs, security, difficult concurrency/distributed correctness, unresolved root cause, or high-risk final review.

A large task made of simple independent work should become multiple Luna tasks, not a Sol task.

## Workflow

For non-trivial work:

1. DISCOVER — inspect only relevant code, tests, and project rules.
2. CLASSIFY — determine routine vs complex vs judgment-heavy work.
3. DESIGN — only when a real design decision exists. Invoke `sol_judge` when the decision is high impact.
4. DECOMPOSE — define independent tasks with scope, ownership, dependencies, acceptance criteria, and tests.
5. DELEGATE — spawn named custom agents. Prefer 2–4 useful parallel tasks, not maximum fan-out.
6. EXECUTE — workers implement and test within scope.
7. INTEGRATE — root coordinator reconciles interfaces and performs small glue edits if necessary.
8. VERIFY — use `luna_tester` when verification output would pollute the root context or when integration testing is substantial.
9. REVIEW — invoke `sol_judge` for architecture/security/concurrency/high-risk changes. Routine low-risk work may be accepted after deterministic verification.
10. CORRECT — route BLOCKER/MAJOR findings back to Luna or Terra according to complexity.
11. RETEST and ACCEPT.

## Parallel safety

Every delegated implementation task must state:

- exact scope and expected outcome
- files/modules owned
- acceptance criteria
- tests to run
- other agents may work concurrently
- do not revert unrelated changes
- inspect current file state before edits

Never use `git reset --hard`, `git checkout .`, or `git restore .` as routine conflict recovery.

If tasks may edit the same tightly coupled code, sequence them unless ownership boundaries are explicit and safe.

## Escalation

Luna -> Terra when:

- two meaningful attempts produced evidence but did not solve the problem; or
- the root cause remains unclear; or
- cross-component correctness, transactions, concurrency, or consistency require deeper engineering judgment.

Before escalation, return a compact handoff:

```text
Known facts:
Unknowns:
Evidence / attempts:
Why Luna scope is exceeded:
Recommended next step:
```

Terra -> Sol when:

- a fundamental architecture decision has significant long-term trade-offs;
- correctness depends on difficult security/concurrency/distributed reasoning;
- substantial evidence-based investigation still leaves the root cause ambiguous;
- the cost of a wrong decision is unusually high.

After Sol resolves the hard reasoning step, de-escalate implementation immediately to Terra or Luna.

## Review contract

`sol_judge` never edits files. It should verify actual evidence and classify findings as:

- BLOCKER — cannot accept; correctness/security/data-loss risk.
- MAJOR — important defect/regression/risk that should be fixed before acceptance.
- MINOR — legitimate non-blocking improvement.

If no blocking issue remains, return `ACCEPTED` and a short evidence summary.

Do not trust worker claims without checking diff/tests when the review matters.

## Cost discipline

- Do not spawn a subagent for a trivial local edit.
- Keep agent recursion depth at 1.
- Prefer deterministic tools over another reasoning round.
- Sol must not do mechanical implementation.
- Do not keep Sol watching workers continuously; invoke it at decision/review boundaries.
- Use search before broad repository reads.
- Keep bulk logs/tests inside disposable tester/worker contexts and return summaries.

## Setup / verification

When asked to install, configure, update, or verify this workflow, run:

```bash
python "<skill>/scripts/configure_tri_agent.py" --dry-run
python "<skill>/scripts/configure_tri_agent.py"
python "<skill>/scripts/configure_tri_agent.py" --check
```

Use the actual installed Skill path for `<skill>`. The script preserves unrelated Codex config, creates timestamped backups for changed files, and installs the four custom roles.

After successful configuration, tell the user to start a new Codex session so the roles/config are reloaded.

## User communication

Do not narrate every spawn or tool call. During longer work, report phases, delegated workstreams, important findings, and blockers concisely.

Final summary should include:

- what changed
- important modules/files
- verification performed
- review result when Sol was used
- remaining known risks
