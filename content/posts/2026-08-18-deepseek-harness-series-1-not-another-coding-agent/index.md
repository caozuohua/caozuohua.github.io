---
title: "DeepSeek Harness 解读（一）：它不是另一个 Codex"
date: 2026-08-18T10:00:00+08:00
publishDate: 2026-08-18T10:00:00+08:00
description: "从 Codex、Claude Code 与 DSH 的产品边界出发，判断 DeepSeek Harness 真正想解决什么问题，以及谁会选择它。"
tags: ["DeepSeek", "DSH", "Agent", "Codex", "Claude Code", "Architecture"]
categories: ["AI Agent", "技术判断"]
draft: false
---

> 这是一组关于 DeepSeek Harness（简称 DSH）的源码级解读。第一篇先回答一个很现实的问题：市场上已经有 Codex、Claude Code，为什么还需要 DSH？

## 先说结论

如果需求是“给我一个现在就能写代码的 Agent”，普通用户没有太多理由选择 DSH。Codex 和 Claude Code 的优势在于完整的产品体验：安装、权限、上下文、编辑、测试、恢复和日常交互都已经被包装好了。

DSH 的合理定位不是“另一个更好用的 Codex”，而是：

> 一个可编程、可替换、可嵌入、可自托管的 Agent Runtime，同时提供一个 DeepSeek 原生的 Coding Agent。

这两个定位看起来相近，实际上面对的是不同买家。

## 三种产品不是同一层

可以把 Agent 市场拆成三层：

```text
模型层：DeepSeek / OpenAI / Anthropic / 自建模型
运行时层：DSH / OpenAI Agents SDK / Google ADK / LangGraph / Pi
产品层：Codex / Claude Code / 企业内部 Agent 产品
```

Codex 和 Claude Code 的核心目标是让用户完成任务。它们当然也在开放 Skills、MCP、SDK 和企业部署能力，但用户不需要先理解运行时内部结构，就可以开始工作。[Codex 开发者主页](https://developers.openai.com/)、[Claude Code CLI 文档](https://docs.anthropic.com/en/docs/claude-code/cli-usage)

DSH 的重点则是把运行时本身暴露出来：模型适配器、工具注册表、Session Log、Agent Loop、沙箱和审批都可以通过插件和配置组合。官方架构文档甚至明确写道，产品中的这些部分都属于插件，而不是一个必须修改的特权核心。[DSH 架构文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)

## 普通用户为什么不一定需要 DSH

普通用户更关心：

- 能不能少配置就开始用；
- 修改代码的成功率高不高；
- 工具调用出错后能不能自己恢复；
- 权限提示是否清楚；
- 出问题时有没有稳定的产品和服务支持。

这些恰好是成熟 Agent 产品的长处。DSH 当前仍然是 developer preview，仓库也提示可能存在 breaking changes。对于只想完成编码任务的人，选择 DSH 很可能是在主动承担运行时配置和升级成本。

普通用户只有在这些条件下才会被 DSH 吸引：

- 想接入 DeepSeek、OpenAI、Anthropic 和自建 gateway；
- 想在本地或企业内部部署；
- 想自己调整工具、提示词、沙箱和 Agent Loop；
- 喜欢研究 Agent 的执行过程；
- 不希望被单一模型或单一产品锁定。

也就是说，选择 DSH 的理由不是“它默认比 Codex 更好用”，而是“它允许我控制更多东西”。

## 企业为什么可能需要它

企业平台团队关心的通常不是某一次对话体验，而是：

- 能不能接企业模型网关；
- 能不能替换模型和执行环境；
- 能不能接内部审批、知识库和工具；
- 能不能完整记录 Agent 做过什么；
- 能不能恢复、回放和比较一次执行；
- 能不能把 Agent Runtime 嵌入自己的产品。

DSH 的多 Provider 适配器支持 DeepSeek、OpenAI、Anthropic 和自定义 provider。[DSH Provider 指南](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/providers.md) 它还提供 Python SDK、JSON-RPC 和 ACP 接口，因而可以作为后台运行时被其他系统调用，而不必以 CLI 形式面对最终用户。

这就是 DSH 和 Codex/Claude Code 的关键错位：

```text
Codex / Claude Code：帮我把这件事做完
DSH：让我定义这类事情应该怎样被做完
```

## DeepSeek 发布 DSH 的意图：我的推断

下面是基于仓库结构的判断，不是 DeepSeek 已公开确认的战略。

### 从模型供应商向 Agent 平台上移

如果 DeepSeek 只提供模型，最终可能被其他公司的 Agent 产品吸收。发布 DSH，意味着它开始控制模型调用、工具执行、上下文组织、子 Agent 协作和轨迹记录这些上层环节。

### 用多模型兼容降低采用门槛

DSH 并没有把自己限制成 DeepSeek-only runtime，而是支持第三方模型和自定义 gateway。这样企业可以先把 DSH 当作中立的 Agent Runtime 接入，之后再根据成本、效果和策略选择默认模型。

### 把 Agent 轨迹变成基础设施

DSH 对 session、trajectory、replay、fork 和 context injection 的重视，说明它关注的不只是最终答案，还关注 Agent 为什么这样做、调用了什么工具、如何复现和评估。

这对于模型研究、Agent Benchmark 和企业审计都很重要。

## 一条实际的选型规则

| 需求 | 更合理的选择 |
| --- | --- |
| 我只想高质量改代码 | Codex / Claude Code |
| 我想要轻量、可扩展的 Coding CLI | Pi |
| 我想编排复杂的有状态流程 | LangGraph / Google ADK |
| 我想替换 Agent 的底层能力 | DSH |
| 我想把 Agent 嵌入自己的企业平台 | DSH 值得评估 |

所以，DSH 的机会不在于抢走所有 Coding Agent 用户，而在于成为企业和开发者构建自己 Agent 产品时的运行时底座。

下一篇会进一步拆解它的内核：为什么 DSH 把 Cordis、事件、Scope 和 Agent Loop 放在架构中心。

## 相关链接

- [DeepSeek Harness 官方仓库](https://github.com/deepseek-ai/deepseek-harness)
- [DeepSeek Harness 官方介绍](https://deepseek.com/harness/)
- [下一篇：DSH 的内核——Cordis、事件与能力组合](/posts/2026-08-18-deepseek-harness-series-2-kernel-cordis/)
