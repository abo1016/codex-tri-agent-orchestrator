# Codex Tri-Agent Orchestrator

[English](README.md) | **简体中文**

> 面向 Codex 的成本敏感型多 Agent 编排方案：Luna 主力执行，Terra 负责协调与复杂工程，Sol 负责高价值判断与关键验收。

```text
你
 └─ Terra Coordinator · medium
     ├─ Luna Worker    · high    — 常规实现 + 定向测试
     ├─ Luna Tester    · medium  — 测试、lint、回归验证
     ├─ Terra Expert   · high    — 复杂实现 / 疑难调试
     └─ Sol Judge      · high    — 只读架构与关键验收
```

所有自定义角色都是 **leaf agent（叶子 Agent）**：不会继续派生子 Agent。当前 Codex Multi-Agent V2 会忽略 `agents.max_depth`，因此 `max_depth = 1` 只作为 V1 限制；V2 下通过角色指令禁止继续 spawn。

## 为什么这样设计？

最贵的模型不应该长期待在热路径里。Sol 只处理高价值判断；Luna 承担边界清晰的实现与确定性验证；Terra 负责常驻协调和真正复杂的工程问题。

```text
明确 + 局部 + 可验证          -> Luna Worker
测试 / lint / 回归验证        -> Luna Tester
复杂实现 / 跨模块 / 难调试     -> Terra Expert
架构 / 高风险决策 / 关键验收    -> Sol Judge
```

**任务大不等于任务难。** 先拆分，再按推理难度升级模型。

## Plugin 会安装什么

- `tri-agent-orchestrator` Skill
- `luna_worker` — GPT-5.6 Luna，high
- `luna_tester` — GPT-5.6 Luna，medium
- `terra_expert` — GPT-5.6 Terra，high
- `sol_judge` — GPT-5.6 Sol，high，read-only
- Codex Agent 默认配置：限制并发、V1 `max_depth = 1`、默认子 Agent 使用 Luna
- Python 3.11+ 安装器，支持 `--dry-run`、`--check`、`--preserve-root-model`

安装器现在会：识别 TOML 多行字符串、创建时间戳备份、拒绝覆盖 symlink、检查角色配置漂移，并在部分写入或验证失败时自动回滚。

## 安装

```bash
codex plugin marketplace add abo1016/codex-tri-agent-orchestrator --ref main
codex plugin add tri-agent-orchestrator@codex-tri-agent-orchestrator
```

安装后新开 Codex 会话，执行 `/skills`，选择 **Tri-Agent Orchestrator**。

手动安装/校验：

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --dry-run
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check
```

如果希望保留现有 root `model` 和 `model_reasoning_effort`：

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --preserve-root-model
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check --preserve-root-model
```

## 默认工作流

```text
DISCOVER + WORKTREE BASELINE
  -> CLASSIFY / DECOMPOSE
  -> PARALLEL LEAF EXECUTION
  -> INTEGRATE
  -> DETERMINISTIC VERIFY
  -> SOL REVIEW（风险驱动）
  -> CORRECT
  -> RETEST
  -> ACCEPT
```

派发任务前，Root Coordinator 记录当前 `git status --short` 和必要 diff，把用户已有改动视为受保护状态。Root Coordinator 负责仓库级 Git 状态；Leaf Agent 默认不能执行 commit、stash、切分支、reset、restore、rebase 等操作，除非任务明确要求。

## 升级与停止条件

- Luna 连续两次有新证据的失败后，通常升级 Terra。
- Terra 在高影响架构、安全/分布式正确性或充分调查后仍存在根因歧义时升级 Sol。
- 同一根因默认预算：Luna 最多 2 次、Terra 修正最多 2 轮、Sol Review 最多 2 轮。
- 确定性失败且方法没变化时禁止盲目重试。
- Sol 解决困难判断后，机械实现立即降级回 Terra/Luna。

Sol Judge 的结果：

```text
BLOCKER
MAJOR
MINOR
INSUFFICIENT_EVIDENCE
ACCEPTED
```

## 成本纪律

- 简单局部修改不要派 Subagent。
- 优先 2～4 个真正能并行的 worker。
- 所有自定义角色保持 leaf agent。
- 能用编译器、测试、lint、静态分析、运行证据验证的，不增加额外推理轮次。
- Sol 不做机械编码，也不持续监督 worker。
- Luna Worker 默认 `high`，Luna Tester 默认 `medium`。

## 目录结构

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

CI 会在 Python 3.11～3.13 上验证安装器，并覆盖多行 TOML、幂等性、已有角色保留、root model 保留、rollback 和角色安全配置漂移检测。

本项目为非官方社区项目，与 OpenAI 无关联，也未获得 OpenAI 背书。

## License

MIT
