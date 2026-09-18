---
title: "Agent 框架评测实验室系列：如何测出企业场景中的真实强弱"
date: 2026-09-18
publishDate: 2026-09-18
draft: false
tags: ["AI Agent", "Agent Framework", "评测", "企业级", "可靠性"]
categories: ["AI Agent 工程实践"]
description: "Agent Framework Lab 系列总览：从公平比较、企业任务契约、故障注入、可重算评分到开发实录，解释怎样用证据判断框架优劣，而不是凭 demo 和印象选型。"
---

“LangGraph、OpenAI Agents、PydanticAI、Google ADK，到底哪个更强？”

这句话听起来像一个排行榜问题，实际上至少藏着六个不同问题：谁更容易写出第一个 demo，谁在同一模型下更省 token，谁能安全暂停审批，谁能在进程崩溃后恢复，谁的原生抽象更适合复杂工作流，谁的运行证据足以通过企业审计。

如果不先限定业务场景和风险边界，“最强框架”没有可验证的含义。

我在开发 [Agent Framework Lab](https://github.com/caozuohua/agent-framework-lab) 的过程中，逐步把框架测验从“同一个 prompt 跑一遍”改造成一条证据链：冻结任务、提示词、工具、模型和价格；交错重复执行；注入审批、取消、工具故障、worker 崩溃和进程重启；保存不可变原始结果；最后才按自定义权重生成比较结果。

这个系列整理 Lab 的核心理念、方法、代码、失败经验和阶段记录。它既是项目复盘，也是未来开发其他 Agent 测验项目时可以复用的设计手册。

## 系列文章

1. [别急着问哪个 Agent 框架最好：先把比较问题定义对](/posts/2026-09-18-agent-framework-evaluation-1-define-the-question/)
2. [把企业需求写成可执行的 Agent 评测契约](/posts/2026-09-18-agent-framework-evaluation-2-enterprise-contracts/)
3. [不注入故障，就测不出 Agent 框架的生产能力](/posts/2026-09-18-agent-framework-evaluation-3-failure-evidence/)
4. [从原始运行到排行榜：硬门、权重与统计陷阱](/posts/2026-09-18-agent-framework-evaluation-4-scoring-and-statistics/)
5. [Agent Framework Lab 开发实录：从比较 demo 到企业就绪 Alpha](/posts/2026-09-18-agent-framework-evaluation-5-development-journal/)

此前发布的[《Agent 框架开发与评测踩坑实录》](/posts/2026-09-17-agent-framework-lab-pitfalls/)是本系列的代码型伴读，集中记录事件账本、审批绑定、幂等键、价格表和 ground truth 等十二类工程坑。

## 一张图理解 Lab

```text
场景 / Prompt / 工具 / 模型 / 价格 / 限额
                  │ 冻结并版本化
                  ▼
        Framework Adapter Matrix
       ┌──────────┴──────────┐
       │ 公平公共赛道        │ 原生上限赛道
       │ 同输入、同工具      │ 原生图、handoff、checkpoint
       └──────────┬──────────┘
                  ▼
       正常运行 + 固定故障注入
                  ▼
      Raw Result / Events / Artifacts
                  ▼
       硬性 No-Go → 加权能力画像
                  ▼
        Go / Conditional-Go / No-Go
```

这套方法最重要的变化，是不再把框架看成一个只负责“调用模型”的 SDK。企业应用真正关心的是一整组能力：任务质量、安全治理、故障恢复、审计、成本、延迟、可运维性、开发体验和迁移成本。

## 当前能下什么结论

2026-09-17 的生产变更 Alpha 使用同一个 `glm-4.5-air`、同一任务和工具，让 LangGraph 与 OpenAI Agents 各交错运行三次。六次任务分都是 100，安全分都是 1，所有硬门和故障探针通过。加权分分别为 97.5641 和 97.4488。

这并不证明 LangGraph “普遍更强”。0.1153 分主要来自 token 用量，而且每个框架只有三个样本。它能证明的是：在这个受限生产变更场景中，两者都达到 Alpha 观察门槛，LangGraph 的本次 token 开销略低。

一个可信的评测系统，不是每次都必须宣布冠军。它应该允许“都合格”“都不合格”“各有适用场景”和“证据不足”成为正式结论。

## 未来要测什么

生产变更只是第一个场景。要真正支持企业框架选型，至少还需要证据型研究/合规审查、可取消的长流程、带访问边界的数据处理、多角色调查与交接、具有真实外部副作用的幂等与对账。

Lab 接下来的重点不是继续堆框架数量，而是扩展这组企业场景，并把三次 Alpha 观察提升为至少十次交错的方向性比较，再加入分布、置信区间和权重敏感性分析。

评测的最终产品不是排行榜，而是一个有范围、有证据、有失效条件的选型判断。
