# Codex Tri-Agent Orchestrator

[English](README.md) | **简体中文**

> 面向 Codex 的成本敏感型多 Agent 编排方案：Luna 主力编码、Terra 复杂工程、Sol 架构与验收。

Codex Tri-Agent Orchestrator 会把 Codex 组织成一个职责明确的小型工程团队：

```text
你
 └─ Terra Coordinator · medium
     ├─ Luna Worker    · xhigh   — 常规编码 + 定向测试
     ├─ Luna Tester    · high    — 测试、lint、回归验证
     ├─ Terra Expert   · high    — 复杂实现 / 疑难调试
     └─ Sol Judge      · high    — 只读架构与最终验收
```

## 为什么这样设计？

最贵的模型不应该全天候处在热路径里。Sol 只用于高价值判断，Luna 处理边界清晰的执行任务，Terra 负责常驻协调和真正复杂的工程实现。

模型路由规则：

```text
明确 + 局部 + 可验证          -> Luna
复杂实现 / 跨模块 / 难调试     -> Terra
架构 / 高风险决策 / 关键验收    -> Sol
```

**任务大不等于任务难。** 先拆分，再根据推理难度升级模型。

## Plugin 会安装什么

- `tri-agent-orchestrator` Skill
- `luna_worker` — GPT-5.6 Luna，xhigh
- `luna_tester` — GPT-5.6 Luna，high
- `terra_expert` — GPT-5.6 Terra，high
- `sol_judge` — GPT-5.6 Sol，high，read-only
- 安全的 Codex 默认配置：Terra 作为协调者、开启 agents、限制并发与递归深度
- Python 3.11+ 安装/校验脚本，支持 `--dry-run` 和 `--check`

安装脚本只修改本插件负责的配置项；已有文件发生变化前会创建带时间戳的备份，不会整份覆盖你的 Codex 配置。

## 作为 Codex Plugin 安装

```bash
codex plugin marketplace add abo1016/codex-tri-agent-orchestrator --ref main
codex plugin add tri-agent-orchestrator@codex-tri-agent-orchestrator
```

安装后**新开一个 Codex 会话**，执行 `/skills`，选择 **Tri-Agent Orchestrator**，然后说：

```text
使用 Tri-Agent Orchestrator 配置并验证我的 Codex 多 Agent 开发环境。
```

也可以只安装 Skill：

```text
$skill-installer Install the skill from https://github.com/abo1016/codex-tri-agent-orchestrator/tree/main/plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator
```

## 手动安装/校验

需要 Python 3.11+。

```bash
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --dry-run
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py
python plugins/tri-agent-orchestrator/skills/tri-agent-orchestrator/scripts/configure_tri_agent.py --check
codex doctor
```

安装后请重启 Codex。

## 日常怎么用

正常开发直接启动 Codex 即可，由 Terra Coordinator 判断是否值得派生 Subagent。

例如：

```text
使用 tri-agent 工作流实现用户通知偏好功能。
```

```text
排查这个 Kafka consumer 问题。复杂实现交给 Terra，Sol 只做根因和最终验收。
```

```text
用 Sol Judge review 当前 diff，不允许修改文件。
```

## 默认工作流

```text
DISCOVER
  -> DESIGN（需要时）
  -> DECOMPOSE
  -> ROUTE
  -> PARALLEL EXECUTION
  -> TEST
  -> SOL REVIEW（按风险触发）
  -> CORRECT
  -> RETEST
  -> ACCEPT
```

Sol Review 是**风险驱动**，不是每个 20 行修改都必须调用 Sol。普通改动经编译、测试、lint 等确定性验证后即可验收；架构、安全、并发、一致性、高风险迁移等任务应进入 Sol Judge。

## 成本纪律

- 简单修改不要派 Subagent。
- 优先 2～4 个真正能并行的 worker，而不是把并发开满。
- 递归深度保持 1，禁止 Agent 继续无限派 Agent。
- Sol 不做机械编码。
- 困难决策解决后，立即把实现降级给 Terra/Luna。
- 能用编译器、测试、lint、静态分析、运行证据验证的，不要再加一轮昂贵推理。
- Luna 连续两次“有证据的失败”后升级 Terra，不要无限重试 Luna。

## 角色职责

### Terra Coordinator

常驻主线程，默认 `medium`。负责：

- 理解需求
- 搜索关键代码
- 判断复杂度
- 拆任务
- 指定文件/模块 ownership
- 判断哪些任务值得并行
- 汇总 worker 结果
- 决定是否需要 Sol Judge

它可以处理非常小的修改，但不应吞掉本来适合 Luna 并行完成的实现工作。

### Luna Worker

默认执行者，负责边界明确、容易验证的编码：

- CRUD
- API Handler / Controller
- DTO / VO / Proto / Schema
- Repository / Service 的常规实现
- Validator / Mapper / Adapter
- 测试
- 小重构
- 已知根因的简单 Bug

### Luna Tester

专门隔离测试日志与验证上下文：

- 单元测试
- 集成测试
- lint
- typecheck / compile
- 回归测试
- 失败摘要

优先返回精炼证据，不把大量测试输出塞回主线程。

### Terra Expert

处理真正需要高级工程判断的实现：

- 跨模块改动
- 事务
- 数据一致性
- Redis / Cache consistency
- Kafka / 消息队列
- goroutine / channel / lock
- 复杂鉴权
- 性能敏感 SQL
- 复杂迁移
- 非显然根因 Debug

### Sol Judge

`read-only`。只负责高价值判断：

- 架构
- 重要 trade-off
- 高风险设计
- 安全
- 复杂并发/分布式正确性
- 疑难根因复核
- 最终关键 Review

输出应为：

```text
ACCEPTED
```

或者：

```text
BLOCKER
MAJOR
MINOR
```

发现 BLOCKER/MAJOR 后，由 Coordinator 再把修复任务路由给 Luna 或 Terra，修完重新验证。

## 并行策略

推荐默认：

```text
1 Terra Coordinator
+
2~3 Luna Workers
+
0~1 Terra Expert
```

多个 Agent 只有在工作流真正独立时才并行。若多个任务可能修改同一文件或同一强耦合模块，应明确 ownership 或顺序执行。

禁止把 `git reset --hard`、`git checkout .`、`git restore .` 当成并发冲突恢复手段。

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
```

## 安全设计

`sol_judge` 从配置层面就是只读角色。实现角色只使用 workspace-write。本插件不会默认打开 unrestricted sandbox、不会配置 force-push、生产部署或破坏性操作。

## 兼容性

Codex 的配置格式仍可能变化。因此本项目首版默认避免依赖仅实验版存在的 multi-agent 字段。若你的 Codex 已稳定支持 spawn 时的 model override，Skill 可以优先使用；否则通过具名 custom agents 完成模型路由。

## 灵感来源

本项目参考了社区中几种“按成本分层”的 Codex 多 Agent 思路，例如 `codex-chief`、`codex-skills-sol-luna-orchestrator` 以及 Codex parallel-subagent experiments，并在此基础上增加了 Luna / Terra / Sol 三层工程路由与独立测试角色。

本项目为非官方社区项目，与 OpenAI 无关联，也未获得 OpenAI 背书。

## License

MIT
