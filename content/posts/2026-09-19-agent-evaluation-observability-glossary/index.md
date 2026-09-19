---
title: "Agent 评测与可观测性术语地图：从 Eval、Trace 到 Replay"
date: 2026-09-19
publishDate: 2026-09-19
draft: false
tags: ["AI Agent", "Agent Eval", "可观测性", "Tracing", "可靠性"]
categories: ["AI Agent 工程实践"]
description: "用一条 Agent 运行与评测链路解释 Eval、Trace、Span、Replay、Workflow、Dataset、Evaluator、Ground Truth、Guardrail、HITL、Checkpoint 等常见术语及其边界。"
---

Agent 评测领域最容易造成误解的，不是某个指标怎么算，而是同一个词在不同框架里常常指向不同层级。

有人把一次模型调用叫 Run，有人把整个工作流叫 Run；有人说 Replay，实际只是重新发送 prompt；有人把 Trace 当日志，也有人把它当成一棵有父子关系、可以定位耗时与错误的执行树。术语没有先对齐，评测报告里的“成功率 95%”“支持恢复”“全链路可追踪”就很难验证。

这篇文章不按字母顺序背词典，而是沿着一条完整链路解释这些概念：Agent 怎样运行，怎样留下证据，怎样用数据集和评估器打分，又怎样把失败样本变成回归测试。

## 先看全局：一次运行如何变成一次评测

```text
Dataset 中的一条 Case
        │ 输入 + 可选 Ground Truth
        ▼
Workflow 启动一个 Run
        │
        ├── Span：模型调用
        ├── Span：Tool Call
        ├── Span：Guardrail 检查
        ├── Checkpoint：保存 State
        └── HITL：暂停并等待人工决定
        │
        ▼
Trace：串起本次执行的完整证据
        │
        ├── Evaluator 打分
        ├── Offline Eval 批量比较
        ├── Online Eval 生产监控
        └── Replay / Regression Eval 复现与防回退
```

这里可以先记住三句话：

1. **Workflow 描述应该怎么走，Run 记录这一次实际怎么走。**
2. **Trace 是一次运行的结构化证据，Span 是其中一个局部操作。**
3. **Eval 是判断过程，Evaluator 是执行判断的规则或程序。**

## 运行层：Workflow、Run、State、Checkpoint

### Workflow：工作流

Workflow 是 Agent 的控制结构：有哪些步骤，步骤之间如何转移，什么时候重试、并行、暂停、终止或请求审批。

它可以是显式状态机，也可以是代码中的循环。下面两种都属于 Workflow：

```text
研究 → 汇总 → 审核 → 发布
```

```text
观察 → 决策 → 调工具 → 更新状态 → 再观察
```

Workflow 不是某次执行产生的数据，而是可重复执行的流程定义。企业评测不仅要看最终答案，还要验证流程是否遵守了审批、权限、超时、重试和终止条件。

### Run：一次运行

Run 是 Workflow 或 Agent 在一组具体输入和配置下的一次执行实例。例如，同一条测试样本分别运行 30 次，就会产生 30 个 Run。

一个 Run 通常至少需要这些身份信息：

- `run_id`；
- dataset 与 case 版本；
- workflow、prompt、model、tool 和 evaluator 版本；
- 开始/结束时间与最终状态；
- 对应的 trace、输出和产物。

不同平台对 Run 的层级定义并不完全相同。有的平台把单次模型调用也叫 Run。因此跨平台分析时，不要只对词，要对齐它代表的是“整个任务”还是“一个步骤”。

### State：状态

State 是某一时刻继续执行任务所需的业务数据与控制数据，例如用户目标、已收集证据、当前步骤、剩余预算、审批结果、工具返回和重试次数。

State 不等于聊天记录。聊天记录可能是 State 的一部分，但复杂 Agent 还需要保存结构化字段：

```json
{
  "task_id": "change-1042",
  "phase": "awaiting_approval",
  "evidence_ids": ["artifact-7", "artifact-9"],
  "approved": false,
  "retry_count": 1,
  "budget_remaining": 0.62
}
```

状态结构越明确，越容易检查非法状态转移，也越容易恢复和回放。

### Checkpoint：检查点

Checkpoint 是在特定时刻持久化的 State 快照，通常还会包含版本、序号、时间戳和恢复游标。它让长流程在进程退出、机器重启或等待人工审批后继续执行。

Checkpoint 解决的是“从哪里继续”，但不自动保证“继续后一定正确”。可靠恢复还需要：

- 工具操作具有幂等键，避免重复扣款或重复发布；
- checkpoint 与外部副作用的提交顺序明确；
- 恢复时校验 workflow 与 schema 版本；
- 能识别已经完成但结果尚未写回的工具调用。

## 证据层：Trace、Span、Tool Call、Observability

### Trace：追踪

Trace 是一次端到端任务的结构化执行记录。它通常用同一个 `trace_id` 串起输入、模型调用、工具调用、状态转移、审批、错误和最终输出。

一个好的 Trace 不是几千行平铺日志，而是可以回答：

- 这次任务经过了哪些步骤？
- 哪一步最慢、最贵或失败了？
- 某个工具调用由哪个决策触发？
- 最终答案使用了哪些证据？
- 谁在什么时候批准了有副作用的操作？

需要特别强调：**隐藏 thinking 不应被当作可靠的决策审计轨迹。** 它可能不可获得、不稳定，也不等于严格的真实因果链。更适合审计的是可观测的决策摘要、输入引用、状态转移、工具参数、工具结果、审批与产物哈希。

### Span：追踪片段

Span 是 Trace 中一个有开始和结束时间的操作单元。一个 Trace 可以包含多个父子 Span：

```text
trace: 客户退款处理
└── span: 读取订单
    └── span: tool_call / get_order
└── span: 判断退款资格
    └── span: model_call
└── span: 人工审批
└── span: 执行退款
    └── span: tool_call / issue_refund
```

Span 通常记录名称、类型、父 Span、开始/结束时间、状态、属性、事件和错误。它适合计算局部延迟、失败率、token 和成本，并定位问题集中在哪一段。

### Tool Call：工具调用

Tool Call 是 Agent 请求外部能力执行操作的结构化事件，例如查询数据库、搜索网页、创建工单或发起退款。至少应记录：

- 工具名称和版本；
- 输入参数及 schema 版本；
- 调用者、权限与策略判断；
- 开始/结束时间、重试与超时；
- 返回值、错误和外部操作标识；
- 幂等键，以及敏感字段的脱敏状态。

只记录“调用成功”不够。企业回溯往往需要知道 Agent 为什么有权调用、调用了什么对象、外部系统是否真正提交，以及重试有没有造成重复副作用。

### Observability：可观测性

Observability 是通过外部可见信号理解系统内部状态的能力。对 Agent 来说，它不只是日志，而是多种证据的组合：

- Trace：一次任务的因果与时序结构；
- Metrics：成功率、延迟、token、成本、拒绝率等聚合指标；
- Logs：具体事件和错误文本；
- State / Checkpoint：某一时刻的执行现场；
- Artifacts：报告、代码、截图、检索证据等任务产物；
- Eval Results：质量、安全和业务规则的评分结果。

Tracing 是可观测性的一部分，不是全部。能看到调用链，也不等于已经具备告警、评测、数据治理和审计能力。

## 评测层：Eval、Dataset、Evaluator、Ground Truth

### Eval：评测

Eval 是用明确的输入集合、评价标准和统计口径，判断 Agent 的输出、过程或系统行为是否满足目标。

Agent Eval 往往要同时评三层：

| 层级 | 典型问题 | 典型指标 |
|---|---|---|
| 结果 | 任务是否完成、答案是否正确 | 正确率、任务完成率、rubric 分 |
| 过程 | 是否选对工具、遵守顺序与策略 | 工具选择、参数正确率、步骤合规率 |
| 系统 | 是否稳定、可恢复、成本可接受 | p95 延迟、失败率、恢复率、成本 |

Eval 不是单个分数的同义词。一个完整 Eval 还应说明样本范围、版本、重复次数、评估器、失败处理、统计方法和适用边界。

### Dataset：评测数据集

Dataset 是一组版本化测试样本。每个 Case 通常包含输入、上下文、预期约束，以及可选的参考答案或评分标签。

高质量数据集不应只包含“正常问题”，还要覆盖：

- 典型业务任务；
- 边界条件和歧义输入；
- 工具超时、空结果、权限不足等故障；
- 提示注入、越权请求和敏感数据；
- 历史线上事故与高价值长尾样本。

Dataset 需要版本化。若样本、ground truth 或 rubric 变了却沿用同一版本号，前后分数就不可比较。

### Evaluator：评估器

Evaluator 是对 Run 或 Trace 执行判断的规则、程序或人工流程。常见类型包括：

- 确定性检查：JSON schema、单元测试、字符串或数值匹配；
- 业务规则：金额、权限、步骤顺序、SQL 结果对账；
- 轨迹检查：是否调用必需工具、是否绕过审批；
- 模型评审：按 rubric 评价相关性、完整性和表达；
- 人工评审：专家判断、盲测和成对比较。

能用确定性规则的地方，应优先使用确定性规则。LLM-as-a-Judge 适合评价开放式内容，但需要固定 rubric、记录 judge 模型版本、校准偏差，并用人工样本检查一致性。

### Ground Truth：真值或参考标准

Ground Truth 是用于判断结果是否正确的参考事实、标签、答案或可执行预期。它可以是唯一答案，也可以是约束集合。

例如，“订单余额为 120 元”可以有精确真值；“给客户写一封合适的解释信”通常没有唯一文本，此时 ground truth 更适合写成 rubric：必须说明原因、不得承诺未批准补偿、语气礼貌。

不要把一份模型生成的参考答案自动视为真值。真值需要可追溯来源、审核和版本；现实变化后还要更新，否则评测测到的可能是数据过期，而不是 Agent 退化。

## 控制层：Guardrail 与 HITL

### Guardrail：护栏

Guardrail 是在输入、输出、工具使用或状态转移处执行的约束与检查。它可以检测提示注入、敏感信息、越权工具、危险参数、输出格式或业务政策违规。

Guardrail 的动作不只“通过/拒绝”，还可能是脱敏、修正、降级、请求补充信息、转人工或终止任务。

Guardrail 与 Evaluator 可能使用相似规则，但职责不同：**Guardrail 在运行路径上实施控制，Evaluator 在评测路径上产生判断。** 前者通常要求低延迟和保守失败策略，后者更强调可重复、可解释和统计有效性。

### HITL：Human in the Loop，人在回路中

HITL 指人在关键节点参与判断、审批、纠正或接管。它不是简单地“界面上有确认按钮”，而是一套可验证的控制机制：

- 暂停点绑定具体 Run、State 和待执行动作；
- 审批人身份与权限可验证；
- 审批内容不可在确认后被 Agent 静默替换；
- 批准、拒绝、修改、超时和撤回都有明确语义；
- 决策被记录，并能从 checkpoint 安全恢复。

对高风险操作，HITL 是权限边界；对低置信度任务，它也是质量兜底和新增评测样本的来源。

## 重现与防回退：Replay、Offline/Online Eval、Regression Eval

### Replay：回放

Replay 是使用历史 Run 的输入、配置、事件或工具结果重新执行全部或部分流程，以复现问题或比较新版本。

Replay 至少有三种不同强度：

1. **输入重跑**：只复用用户输入，模型和外部系统都重新调用。最接近一次新运行，但不保证复现原结果。
2. **工具结果回放**：固定历史 Tool Result，重新运行决策逻辑。适合隔离模型、prompt 或 workflow 变化。
3. **事件级回放**：按事件账本恢复 State 和状态转移。适合检查恢复、幂等和审计逻辑。

因此，“支持 Replay”必须继续追问：回放的是什么、哪些依赖被固定、外部副作用是否被禁用、能否从任意 checkpoint 开始。

### Offline Eval：离线评测

Offline Eval 在开发、测试或发布前，对固定 Dataset 批量运行并评分。它适合：

- 比较 prompt、model、workflow 或框架版本；
- 做发布门禁；
- 复现历史问题；
- 进行故障注入和安全红队测试。

它的优点是可控、可重复；缺点是数据可能与真实流量脱节，也难覆盖生产环境中的时序和依赖变化。

### Online Eval：在线评测

Online Eval 对生产或近生产流量持续抽样、评分和监控。它可以使用真实反馈、业务结果、规则检查或异步模型评审，发现分布漂移和离线数据集没覆盖的新问题。

在线评测不应默认把所有原始内容送去评审。需要处理用户授权、隐私、脱敏、采样率、成本和反馈延迟。高风险指标还应配合实时 guardrail，而不是等异步评分发现事故。

Offline 与 Online 不是替代关系：离线评测负责发布前的可重复门禁，在线评测负责发布后的真实世界反馈；线上失败样本再经过清洗和审核，回流到离线 Dataset。

### Regression Eval：回归评测

Regression Eval 用固定基线验证新版本是否让已有能力退化。它关注的不是“新版本绝对分数高不高”，而是相对基线在哪些切片上变差。

一次可信的回归评测应固定或记录：

- Dataset、evaluator、model/provider 和工具版本；
- 随机性设置与重复次数；
- 基线 commit 或发布版本；
- 总体指标和关键切片；
- 允许波动范围与阻断门槛。

平均分不下降仍可能发生严重回退：高频简单样本的提升，会掩盖安全审批样本的失败。因此企业门禁通常要同时使用总体统计、关键切片和硬性 No-Go 条件。

## 把这些词落到同一份事件模型里

一个最小但可用的记录可以长这样：

```json
{
  "run_id": "run_20260919_001",
  "trace_id": "trace_8f31",
  "workflow_version": "refund-flow@2.3.0",
  "dataset_case": "refund-policy/over-limit@7",
  "state_version": 12,
  "events": [
    {
      "span_id": "span_tool_04",
      "type": "tool_call",
      "tool": "issue_refund@1.4",
      "idempotency_key": "order-918/refund-v1",
      "status": "blocked_by_guardrail"
    },
    {
      "span_id": "span_hitl_05",
      "type": "human_approval",
      "checkpoint_id": "cp_12",
      "decision": "approved",
      "actor": "role:refund_manager"
    }
  ],
  "eval_results": [
    {
      "evaluator": "refund-policy-check@3",
      "score": 1,
      "label": "pass"
    }
  ]
}
```

重点不在字段名，而在关联关系：Case 触发 Run，Run 产生 Trace，Trace 由 Span 和事件组成，State 在 Checkpoint 被持久化，Guardrail 与 HITL 控制执行，Evaluator 最终对结果和过程评分。

## 最容易混淆的六组边界

| 容易混淆 | 实际区别 |
|---|---|
| Workflow vs Run | 前者是流程定义，后者是一次执行实例 |
| Trace vs Log | Trace 强调端到端关联与父子关系，Log 更像单条事件记录 |
| Trace vs Span | Trace 是整条链路，Span 是其中一个操作单元 |
| State vs Checkpoint | State 是当前数据，Checkpoint 是其持久化版本 |
| Guardrail vs Evaluator | 前者在运行时控制，后者在评测时判断 |
| Replay vs Regression Eval | Replay 是重现执行的方法，Regression Eval 是防止能力回退的评测目的 |

## 一套可落地的最小闭环

如果从零开始建设 Agent 评测与可观测性，不必一次搭完所有平台能力。可以先做六件事：

1. 给 Workflow、prompt、model、tool、dataset 和 evaluator 全部加版本。
2. 为每次任务生成 `run_id` 与 `trace_id`，为关键操作生成 `span_id`。
3. 结构化记录 Tool Call、State Transition、Guardrail、HITL 和 Checkpoint。
4. 建立一小套包含正常、边界、安全和历史事故样本的 Dataset。
5. 用确定性 Evaluator 做发布门禁，再为开放式质量补充人工或模型评审。
6. 将线上失败样本审核后加入 Regression Eval，形成持续更新的离线基线。

最终，企业真正需要的不是一条看似聪明的 thinking，而是一条可以回答“输入是什么、系统做了什么、依据是什么、谁批准了什么、结果是否合格、能否安全重现”的证据链。

这条证据链，才是可信、可控、可追踪的 Agent 工程基础。

