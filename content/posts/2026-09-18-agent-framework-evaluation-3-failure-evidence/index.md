---
title: "不注入故障，就测不出 Agent 框架的生产能力"
date: 2026-09-18
publishDate: 2026-09-18
draft: false
tags: ["AI Agent", "故障注入", "崩溃恢复", "幂等", "审计"]
categories: ["AI Agent 工程实践"]
description: "为什么正常成功路径不足以评估企业 Agent，以及如何测试审批通过/拒绝、取消、工具故障、worker 崩溃、进程重启和重复副作用防护。"
---

这是 [Agent 框架评测实验室系列](/posts/2026-09-18-agent-framework-evaluation-series/)第三篇。

一个 Agent 在 demo 中完成任务，最能说明的是：这次模型、网络和工具刚好都没有出大问题。企业系统真正区分框架能力的地方，往往发生在错误之后。

## 七类最低故障矩阵

生产变更 Alpha 固定测试七类场景：

| 场景 | 要证明什么 |
|---|---|
| 审批通过 | 精确意图获批后才可继续 |
| 审批拒绝 | 拒绝不能通过新 ID 或重试绕过 |
| 取消 | 正在执行的 attempt 中断，预算结算 |
| 工具失败 | 错误可见，重试有界，不伪装成功 |
| worker 崩溃 | lease 和 reservation 可回收 |
| 进程重启 | 从已提交 checkpoint 恢复，不重跑完成阶段 |
| 重复副作用 | 同一外部操作最多生效一次 |

这些测试不能只检查“最后还是成功了”。还要检查事件顺序、预算余额、checkpoint 哈希、工具调用次数和幂等收据。

## 审批不是一个布尔值

如果审批只保存 `approved=true`，就无法确认批准的是哪次操作。安全审批至少绑定：

```python
class ApprovalDecision(BaseModel):
    approval_id: UUID
    job_id: UUID
    attempt_id: UUID
    operation_id: UUID
    action: str
    arguments_sha256: str
    decision: Literal["approved", "rejected"]
    approver_id: str
    revision: int
```

恢复时重新计算参数摘要。job、operation、action、参数或 revision 任一不一致，都不能复用原批准。测试不仅要覆盖正确批准，还要专门提交“看起来很像”的错误批准。

## checkpoint 保存协议状态，不只是聊天历史

只保存 messages，恢复后模型可能重新决定调用一次付款或发布工具。一个可靠 checkpoint 需要明确：执行到哪个协议阶段、哪些角色已经完成、哪些副作用已经获得 durable receipt、还有哪些 reservation 未结算。

```python
checkpoint = {
    "completed_roles": ["researcher"],
    "next_role": "analyst",
    "research_artifact_sha256": digest,
    "settled_operations": ["search", "read-alpha", "read-beta"],
}
```

Lab 的框架原生探针先完成 researcher，再模拟恢复。恢复后的 LangGraph 和 OpenAI Agents 都只能执行 analyst/reviewer；如果检索工具再次出现，就说明恢复只是“重新运行”。

## 幂等键必须绑定请求摘要

同一个 idempotency key 被不同参数复用，比完全没有幂等更危险，因为系统会产生错误的安全感。

```python
request = json.dumps(
    {"tool": tool_name, "arguments": arguments},
    sort_keys=True, separators=(",", ":"), ensure_ascii=False,
)
request_sha256 = sha256(request.encode()).hexdigest()

receipt = store.get(idempotency_key)
if receipt and receipt.request_sha256 != request_sha256:
    raise IdempotencyConflict()
if receipt:
    return receipt.output, True
```

测试必须跨 runtime 重启。只在同一个进程的内存字典里命中一次，不叫生产级幂等。

## append-only 事件为什么重要

普通日志可以丢失、乱序或被覆盖。运行时账本要能证明：

```text
job.submitted
job.started
attempt.started
budget.reserved
tool.requested
tool.succeeded
budget.debited
checkpoint.committed
attempt.completed
job.succeeded
```

每个事件有全局递增 sequence，写入使用 optimistic revision；事件和快照在同一事务提交。审计器才能判断 `gap_free=true`、`outstanding_reservations=0`，并验证终态工件与 checkpoint。

## 共享运行时证据与框架证据要分开

审批、取消、预算和 durable receipt 如果由 Lab 的共同 runtime 负责，就不应该谎称是 LangGraph 或 OpenAI Agents 各自实现的能力。Alpha 报告把这类探针标记为 `shared-runtime`，再按评审需要展开到两个框架。

工具故障恢复和 checkpoint resume 则走各自 native adapter，属于框架相关证据。

这一区分很重要：否则排行榜会把 harness 的能力算到框架头上。反过来，如果生产架构本来就规定所有框架必须运行在共同 runtime 上，那么共享能力又确实是最终系统能力。报告必须同时说清“框架本体”和“部署组合”。

## 固定探针，而不是配置任意 shell

为了自动收集故障证据，最简单的办法是让 YAML 配一段 command。但这会把评测平台变成远程命令执行器。

Lab 使用代码内白名单：

```python
PROBE_GROUPS = (
    ProbeGroup("shared-cancelled", (
        "tests/test_runtime_execution.py::"
        "test_external_cancel_interrupts_attempt_and_settles_reservation",
    )),
    ProbeGroup("langgraph-adapter", ("tests/test_langgraph_composed.py",)),
    ProbeGroup("openai-agents-adapter", ("tests/test_openai_agents_native.py",)),
)
```

外部 campaign 只能提供 ID 和输出目录，不能注入命令。每份日志计算 SHA-256，再进入 readiness evidence。

## 失败应该怎样影响结论

审批绕过、未授权工具、事件缺口、预算未结算、重复副作用、不可验证工件，不应只是扣几分。这些是硬性 No-Go。否则一个框架可以靠任务答案很漂亮，抵消一次生产事故。

企业评测最重要的原则不是“失败越少越好”，而是“失败必须可见、可归因，并在高风险边界上 fail closed”。

下一篇：[从原始运行到排行榜：硬门、权重与统计陷阱](/posts/2026-09-18-agent-framework-evaluation-4-scoring-and-statistics/)。
