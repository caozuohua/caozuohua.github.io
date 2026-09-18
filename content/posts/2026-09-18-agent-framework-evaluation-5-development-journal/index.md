---
title: "Agent Framework Lab 开发实录：从比较 demo 到企业就绪 Alpha"
date: 2026-09-18
publishDate: 2026-09-18
draft: false
tags: ["AI Agent", "开发复盘", "Agent Framework Lab", "LangGraph", "OpenAI Agents"]
categories: ["AI Agent 工程实践"]
description: "记录 Agent Framework Lab 从多框架跑通、runtime-v1、恢复审计、RC2 到企业生产变更 Alpha 的演进过程，以及每个阶段改变了什么判断。"
---

这是 [Agent 框架评测实验室系列](/posts/2026-09-18-agent-framework-evaluation-series/)第五篇，也是阶段开发记录。

## 起点：先让不同框架完成同一任务

Lab 最早解决的是兼容性：统一 stdin/stdout 的请求与结果契约，让不同 Python/Node 框架可以在各自隔离环境运行。这个阶段最直观的产物是 matrix 和报告，但也很快暴露问题：

- 每个 adapter 对 usage 的理解不同；
- 有的框架隐藏模型重试；
- MCP SDK 与 CLI 协议不同；
- 同名模型可能被 gateway 路由到不同后端；
- prompt、工具包装稍有不同，分数就不可比。

因此第一条经验是：**先统一证据格式，再谈统一排行榜。**

## V2.0—V2.1：运行时从附属代码变成核心边界

普通 runner 只关心子进程退出码。企业 Agent 还需要 job、attempt、lease、事件 revision、预算 reservation、checkpoint 和 immutable artifact。

runtime-v1 采用 SQLite WAL 和 append-only event/reducer：

```text
command -> validate current snapshot -> append events
        -> reduce new snapshot -> transactionally persist both
```

这个阶段没有急着做远程服务，而是坚持单机、一次命令、可验证状态。事实证明这是正确取舍：并发和网络还没加入时，就已经发现事件序列、预算结算和终态工件之间有大量边界条件。

## V2.2：恢复不是“再跑一次”

接下来加入 host crash、SQLite reopen、orphan attempt 回收和 checkpoint resume。LangGraph composed 与 OpenAI Agents native 都通过了“researcher 已完成后恢复，只继续 analyst/reviewer”的测试。

这一阶段最重要的认识是：checkpoint 是协议状态，不是消息缓存；幂等是持久收据，不是进程内字典；恢复必须先验证工件，再清理 reservation，最后申请新 lease。

## V2.3—V2.4：能运行还要能操作和审计

Lab 增加 runtime CLI 的 health、list、get、events、audit、export、work、decide 和 cancel。MCP 只开放只读观察，A2A 保持 loopback。RC 验收覆盖审批、取消、崩溃、恢复和备份还原。

一次真实 audit 的判断依据不是“状态 succeeded”四个字，而是：

```json
{
  "status": "succeeded",
  "gap_free": true,
  "active_attempt_id": null,
  "pending_approval_ids": [],
  "outstanding_reservations": 0,
  "terminal_artifact_verified": true,
  "checkpoint_verified": true
}
```

这让“成功”从一个声明变成可检查的不变量集合。

## RC2：让任务、模型、价格和评分真正可注入

为了从开发 runtime 转向评测框架，RC2 把外部任务、模型配置、价格目录和 ScoreProfile 都做成严格契约。任意 Python evaluator 和任意工具插件仍然被禁止；外部任务只能组合预置工具。

这个阶段还踩到一个典型坑：库存题的 ground truth 写错，框架正确调用工具却被扣分。我们保留错误运行，发布新任务版本，而不是覆盖结果。这决定了后来所有 comparison 都保存 raw result hash。

## V2.5：从“有能力”变成一次企业决策

生产变更 Alpha 冻结了一个完整场景：代码修复、测试、任务依赖、750 美元审批、pending 停止和禁用提交。LangGraph 与 OpenAI Agents 用 `glm-4.5-air` 各交错运行三次。

六次结果全部完成，任务分 100、安全分 1。固定探针覆盖审批通过/拒绝、取消、工具失败、worker crash、进程重启和重复副作用。六个硬门通过，最终 readiness 为 Go。

```text
LangGraph      97.5641
OpenAI Agents  97.4488
```

我们没有宣布 winner：样本只有三个，0.1153 分主要来自 token。这次 Alpha 的真正成果是把“为什么 Go”追溯到六个 raw run、结果摘要、探针日志和 policy，而不是这两个小数。

## 独立核验器带来的最后一课

如果报告只能由生成它的代码验证，就仍有共同缺陷风险。Lab 增加了一个不导入 `agent_framework_lab` 的独立脚本，重新计算 manifest、canonical digest、run lineage、工具顺序、审批参数、硬门和 probe log hash。

开发过程中第一次导出也暴露了两个真实问题：裸 Python 环境缺少未声明的 PyYAML；live 证据 commit 与后来增加的 exporter commit 被混写为一个 source commit。修复后，包分别记录 evidence commit 与 exporter commit，并携带固定依赖。

随后在临时副本中只改 `results.json` 的一个空格，核验器立即非零退出：

```text
manifest digest mismatch: evidence/results.json
```

这类负控比“验证通过”更能说明验证器真的在工作。

## 项目过程中形成的十条方法

1. 运行状态、任务质量、治理门槛和排名策略必须分层。
2. 原始结果先落盘，评分和可视化后计算。
3. 一轮实验只改变一个主要变量。
4. 重复按框架交错，减少时间与网关偏差。
5. 共享 runtime 能力不能冒充框架原生能力。
6. 高风险失败使用硬 No-Go，不能被平均分抵消。
7. checkpoint、审批和幂等都必须绑定精确身份与摘要。
8. 缺失 usage 或价格意味着不可比较，不意味着免费。
9. ground truth 和 harness 也需要版本、测试和审计。
10. 一个可信实验可以不产生 winner。

## 下一阶段：真正服务框架选型

现在 Lab 能证明一个企业垂直切片，但还不能判断框架的普遍优劣。下一阶段应同时保留“受控公共赛道”和“原生上限赛道”，增加证据型研究、长流程恢复和多角色协作场景，把重复数提高到至少十次，并输出分布和权重敏感性。

框架数量暂时不是瓶颈。更重要的是让每一个新增场景都能改变或加深选型判断。

完整代码见 [agent-framework-lab](https://github.com/caozuohua/agent-framework-lab)，方法论见 [framework-evaluation-methodology.md](https://github.com/caozuohua/agent-framework-lab/blob/agent/deep-dive-v1/docs/framework-evaluation-methodology.md)。
