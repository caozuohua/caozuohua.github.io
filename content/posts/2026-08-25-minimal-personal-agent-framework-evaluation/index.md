---
title: "轻量个人助理 Agent 选型：Hermes、OpenClaw、nanobot 与开发框架怎么选"
date: 2026-08-25T11:35:00+08:00
publishDate: 2026-08-25T11:35:00+08:00
description: "以 Lark、MCP、记忆、定时任务、安全审批和低资源部署为标准，评估 2026 年适合个人自托管的成熟 Agent 与框架。"
tags: ["AI Agent", "Hermes Agent", "OpenClaw", "nanobot", "PydanticAI", "MCP"]
categories: ["个人助理智能体", "技术选型"]
draft: false
---

我曾经把个人助理的每一层都自己实现：Lark WebSocket、卡片、Agent Loop、Goal Runtime、记忆、定时任务、多模型 fallback、工具审批和多云 VPS 运维。

这样做最大的收益是理解了边界，最大的代价也是边界——一旦通用 Agent 能力持续扩张，维护一个个人助手就会逐渐变成维护一个框架。

更合理的方向是：

```text
成熟 Agent 负责通用助理能力
标准 MCP 负责专业工具
服务端策略负责最终安全边界
```

但“成熟”和“轻量”不能只看项目介绍。这篇文章使用同一组需求评估 2026 年几类主流选择。

## 我的真实需求

这不是通用 Agent 排行榜。目标环境是一台低资源 VPS，主要服务一个人：

- 通过 Lark 私聊和群聊使用；
- 处理问答、翻译、摘要、Idea、纪要和博客；
- 保存少量长期偏好与会话历史；
- 支持定时提醒和主动推送；
- 通过 MCP 接入 GitHub、知识库和多云运维；
- 模型不可用时，核心运维控制面仍然可查询；
- 重启、备份、恢复和发布等动作必须人工批准；
- 使用远程模型，不在小 VPS 上运行本地大模型。

基于这些约束，我把候选分成两类：

```text
成品助理：Hermes Agent / OpenClaw / nanobot
开发框架：OpenAI Agents SDK / PydanticAI / Agno / LangGraph
```

成品助理的优势是少造渠道、记忆和调度；框架的优势是运行时可控，但应用外壳仍要自己写。

## 先定义“成熟”

一个仓库更新频繁、Star 很多，不等于适合长期运行。我更关心：

1. 配置和升级有没有稳定入口；
2. 会话和任务能否在重启后恢复；
3. 渠道是否处理去重、重连和用户隔离；
4. MCP 是否支持过滤、超时和失败降级；
5. 高风险工具是否有确定性权限边界；
6. 日志、健康检查、备份和回滚是否可操作；
7. 安全修复是否持续发布；
8. 能否关闭不需要的工具，而不是默认把整台主机交给模型。

个人助理生态仍然变化很快。这里的“成熟”是相对成熟，不等于 systemd、SQLite 或 Ansible 那样经过多年稳定周期。

## 结论总表

| 方案 | Lark | MCP | 记忆/定时 | 运行形态 | 结论 |
|---|---|---|---|---|---|
| Hermes Agent | 原生 | 原生 | 完整 | Python Gateway，可裁剪 | 当前环境最合适 |
| OpenClaw | 原生插件 | 原生 | 很完整 | Node Gateway，插件丰富 | 功能完整度最高 |
| nanobot | 原生 | 原生 | 完整 | 单 Python Gateway | 最轻，但安全成熟度较弱 |
| OpenAI Agents SDK | 自建 | 很强 | Session 有，Cron 自建 | Python 库 | 最小定制核心 |
| PydanticAI | 自建 | 很强 | 持久执行可选 | Python 库 | 类型安全、适合严谨开发 |
| Agno AgentOS | 自建 | 原生 | 完整 | FastAPI Runtime + 控制面 | 单用户偏重 |
| LangGraph | 自建 | 可接 | 编排与持久化强 | 低层图运行时 | 已在用，但不能减少外壳代码 |
| Letta | 自建 | 可集成 | 记忆最强 | 状态型 Agent 平台 | 适合记忆，不适合做 Lark 主入口 |

## Hermes Agent：最适合现有环境

Hermes 已经覆盖最关键的助理外壳：Lark/Feishu WebSocket 和 webhook、私聊与群聊、媒体、Cron 回推、用户 allowlist 和会话隔离。危险命令可以直接在 Lark 里通过交互卡片批准或拒绝。[Hermes Lark 文档](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/feishu)

它的 MCP 客户端支持本地 stdio 和远程 HTTP、自动发现、按服务器过滤工具，以及资源和 Prompt 接入。[Hermes MCP 文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)

对低资源部署尤其有价值的是 Blank Slate：安装时可以关闭浏览器、委派、Cron、外部记忆、技能和大部分工具，再逐项启用。这样新版本也不会悄悄加载未选择的能力。[Hermes Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart/)

我会采用这样的最小配置：

```text
保留：Lark、基础记忆、Cron、Web Search、luck-ops MCP
关闭：Host Terminal、任意文件写、自我修改、浏览器、多 Agent
```

需要注意：Hermes 安装器会准备 Python、Node、ffmpeg 等依赖，磁盘占用并非极小；同时它要求主模型至少有 64K 上下文。如果使用远程模型，这主要影响模型选择和 token 成本，不会把推理内存压到 VPS 上。

还有一个现实优势：我的 GCP 和 Azure 主机已经运行 Hermes Gateway/A2A。选择它不是从零押注，而是复用已有运维经验。

## OpenClaw：个人助理完成度最高

OpenClaw 更像一个完整的个人 Agent 操作系统。它提供多渠道 Gateway、长期会话、记忆、Skills、后台任务、MCP、权限模式和命令审批。

它的 Feishu/Lark 插件支持流式卡片、群聊/话题隔离，以及 Doc、Wiki、Drive、Bitable 和 Chat 工具。对于希望直接把 Lark 当个人工作台的人，这一层比多数框架完整得多。[OpenClaw Feishu/Lark 文档](https://docs.openclaw.ai/channels/feishu)

执行权限支持 `deny`、`allowlist`、`ask`、`auto` 和 `full`。如果把运维能力放进独立 MCP，就应该禁用宿主机 exec，不能因为框架提供审批就保留一条泛化 Shell 后门。[OpenClaw Exec 权限](https://docs.openclaw.ai/tools/exec)

它的不足不是功能，而是范围：Node Gateway、插件系统、多个工具族和管理能力意味着更大的安装、升级和攻击表面。OpenClaw 适合“尽量停止自研通用助理”的选择，不一定是空闲 RSS 最低的选择。当前版本需要较新的 Node，官方推荐 Node 26。[OpenClaw 安装文档](https://docs.openclaw.ai/install)

## nanobot：最轻的成品候选

nanobot 是一个单 Python Gateway，已经集成 Feishu、MCP、Cron、长任务、会话、长期记忆、OpenAI-compatible API 和多模型 Provider。它的架构比完整平台容易阅读和修改。[nanobot 仓库](https://github.com/HKUDS/nanobot)

如果目标是尽可能压低常驻资源，同时不想从 SDK 开始写 Lark、Cron 和 Memory，nanobot 很有吸引力。

但它仍处于快速演进阶段。近期发布持续修复路径越界、Shell 注入、认证、会话损坏和 MCP 超时等问题；社区深度审计也集中提出过认证绕过、资源泄漏和并发方面的风险。[nanobot 安全审计记录](https://github.com/HKUDS/nanobot/issues/4815)

因此我的边界是：nanobot 可以负责聊天、记忆、搜索、调度和调用 MCP，但不能直接持有 root、生产 SSH key、Docker socket 或任意宿主机 Shell。真正的运维授权必须由 `luck-ops-mcp` 服务端重新验证。

## OpenAI Agents SDK：最小的成熟开发核心

如果愿意继续维护应用外壳，OpenAI Agents SDK 是一个很紧凑的 Agent 核心。它支持 SQLite Session、本地和远程 MCP、工具过滤、结构化输出、Guardrail，以及工具调用的暂停、批准、拒绝和恢复。

HITL 状态可以序列化，之后用同一个 Session 恢复；MCP 工具也可以声明强制审批。[Agents SDK HITL](https://openai.github.io/openai-agents-python/human_in_the_loop/)、[Agents SDK MCP](https://openai.github.io/openai-agents-python/mcp/)

问题是它不是个人助理产品。仍需自己实现：

- Lark 收发和卡片；
- Cron 和主动通知；
- 消息去重与断线恢复；
- 长期记忆策略；
- 服务健康、升级和备份。

运行时可以很轻，但维护量不会比当前 luck-agent 少太多。

## PydanticAI：严谨的类型化框架

PydanticAI 的优势是类型明确、依赖注入自然，MCP 可以通过精简安装接入 stdio、SSE 和 Streamable HTTP。[PydanticAI MCP Client](https://pydantic.dev/docs/ai/mcp/client/)

它支持工具审批；需要可靠长任务时，还可以接 Temporal、DBOS、Prefect 或 Restate。[PydanticAI Durable Execution](https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/)

但一旦引入这些持久执行平台，部署就不再极简。不引入时，调度、Lark、记忆和恢复又需要自己实现。它适合构建严谨的定制 Agent，不是最快获得个人助理的方案。

## Agno、LangGraph 和 Letta 为什么没有进入前三

Agno AgentOS 已有 API、Session、Memory、Knowledge、Scheduler、审批、RBAC、Tracing 和 MCP，也可以把整个 AgentOS 暴露为 MCP。[Agno AgentOS](https://docs.agno.com/agent-os/introduction)

这些能力对团队平台很有价值，但 FastAPI Runtime、50 多个 API 和控制面对于单用户 VPS 是额外负担。

LangGraph 的持久化、长任务和 Human-in-the-Loop 很成熟，但它是低层编排框架。Lark、个人记忆、工具目录、Cron、卡片和升级依然要自己组装。[LangGraph 参考](https://langchain-ai.github.io/langgraph/reference/)

Letta 的长处是持续记忆和状态型 Agent，不是 Lark 渠道和低资源运维。它更适合作为记忆后端候选，而不是个人助理主入口。

## 最终选择

我会按三种目标做选择：

```text
现有环境迁移成本最低：Hermes Agent
个人助理功能最完整：OpenClaw
常驻资源尽可能低：nanobot
完全自主定制：OpenAI Agents SDK / PydanticAI
```

当前方案优先采用：

```text
Lark
  ↓
Hermes Agent（Blank Slate）
  ├─ 对话、搜索、记忆、Cron
  └─ MCP Client
         ↓
     luck-ops-mcp
     权限、审批、审计、固定操作
```

Agent 不是权限边界。无论最后选择 Hermes、OpenClaw 还是 nanobot，都应该关闭泛化宿主机 Shell，并让 `luck-ops-mcp` 独立校验身份、目标、服务、操作和审批快照。

此外，项目宣传中的“轻量”不能替代测量。下一步应该让 Hermes 和 OpenClaw 使用同一个模型、同一个 Lark 场景和同一个 MCP，执行上一篇的[极简 Agent 实用测试基准](/posts/2026-08-25-minimal-agent-practical-benchmark/)，用空闲内存、任务峰值、重启恢复和 72 小时稳定性做最终决策。

专业运维工具如何从 Agent 中拆出来，见下一篇：[Luck Ops MCP：把 Lark 多云运维做成标准工具](/posts/2026-08-25-luck-ops-mcp-design/)。
