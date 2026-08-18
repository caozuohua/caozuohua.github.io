---
title: "DeepSeek Harness 解读（二）：内核不是 Agent，而是 Cordis 运行时"
date: 2026-08-18T10:10:00+08:00
publishDate: 2026-08-18T10:10:00+08:00
description: "拆解 DSH 的 Cordis、Context、Typed Events、可撤销 Effects、Capability Seams 和 Agent Loop，理解它为什么拒绝单体式 Agent。"
tags: ["DeepSeek", "DSH", "Cordis", "Agent", "Runtime", "Plugin"]
categories: ["AI Agent", "架构拆解"]
draft: false
---

> 上一篇讨论了 DSH 为什么不应该被简单看成“另一个 Codex”。这一篇进入源码架构：DSH 的真正内核不是一个大而全的 Agent 类，而是一套用来组装 Agent 的插件运行时。

## 先给一个简化模型

```text
Runtime = Profile + Bundle + Patch + Plugin
Agent   = Scoped Context + Session + Agent Driver
Turn    = LLM Request + Tool Pipeline + Durable Events
```

DSH 官方文档对自己的描述很直接：模型适配器、工具注册表、会话日志和 Agent Loop 都是插件；没有一个需要被所有扩展修改的 privileged core。[DSH Architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md)

这里的“没有核心”不是说系统没有基础代码，而是说：基础服务存在，但业务能力没有被绑死在一个不可替换的中心对象里。

## Cordis：Context 是服务仓库

Cordis 是 DSH 底层的插件框架。每个插件可以向共享 Context 注册服务：

```text
ctx.llm          模型适配器
ctx.sessions     会话存储
ctx.tools        工具注册表
ctx.systemPrompt Prompt 组装
ctx.fs           文件系统能力
ctx.sandbox      沙箱能力
ctx.agents       Agent 注册表
```

插件不直接依赖具体实现，而是通过 `ctx.<key>` 找到能力；依赖通过 `inject` 声明，加载顺序由服务依赖关系决定。插件注册的工具、Prompt、Provider 和事件监听器都会通过 effect 安装，并在插件卸载时撤销。[Cordis Primer](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/cordis-primer.md)

这套机制解决的是一个很现实的问题：Agent 运行时经常需要热更新、替换 Provider、按会话隔离能力，甚至在同一进程中运行多个不同配置的 Agent。

## Typed Event：事件才是控制流扩展点

DSH 不要求每个功能都去修改 Agent Loop，而是把关键流程暴露为类型化事件：

```text
user/message
    ↓
agent/pre-step
    ↓
agent/request → llm/stream → assistant/message
    ↓
tool/call → tools/pre-execute
          → tools/execute
          → tools/post-execute
          → tool/result
    ↓
step/end → next step or turn/end
```

事件有不同的派发语义：

- `emit`：观察事件，不改变结果；
- `parallel`：并行通知多个消费者；
- `serial`：按顺序处理；
- `waterfall`：类似 middleware，可以继续、改写或短路。

例如，一个审批插件可以在 `tools/pre-execute` 阶段把调用变成 `ask`；一个安全策略插件可以直接 `deny`；一个上下文插件可以在 `agent/pre-step` 阶段注入文件变化、项目规则或记忆结果。

这样，策略插件不需要 import Agent Loop，也不需要维护自己的 fork。

## Capability Seam：把能力拆成接口、Provider 和 Consumer

DSH 反复使用一个概念：capability seam。

一个能力通常包含三部分：

```text
Service Definition  定义接口和事件契约
Service Provider    提供具体实现
Consumer             使用该能力的工具或 Agent
```

例如文件系统不是一个固定的 `local_fs()` 函数，而是 `ctx.fs` 能力。换成本地文件系统、远程文件系统或受限沙箱后，Bash、PTY 和 LSP 可以共享同一个执行世界。子 Agent 也可以通过同一接口接入不同的子进程 Agent 或远程 Agent。

这和传统“工具函数集合”的设计区别很大：工具只是能力的一个消费者，权限、执行环境和工具展示可以分别替换。

## Agent Loop 只是默认实现

DSH 有一个默认的 `agent-loop`，负责：

- 从 inbox 领取输入；
- 开启 turn；
- 组装 Prompt 和工具 Schema；
- 发起模型请求；
- 执行工具；
- 判断是否继续下一 step；
- 关闭 turn。

但 DSH 将 `Agent` 抽象和 `agent-loop` 实现分开。扩展插件依赖 Agent 的契约，而不是直接依赖默认 Loop。这使得未来可以替换成不同的 ReAct、计划-执行、PTC 或多 Agent 驱动器。[Core Subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/core.md)

因此 DSH 的中心抽象不是“一个 Agent 怎么思考”，而是“一个 Agent 如何被创建、拥有、暂停、恢复、观察和销毁”。

## Profile、Bundle、Patch：配置就是运行时组合

一次 DSH 启动不是读取一个巨大配置文件，而是从多层组合出一棵插件树：

```text
dsh-base
  → profile bundles
    → profile patch
      → home-level patch
        → command-line overlay
```

每层都可以替换既有配置行或插入新的插件。一个 preset 也不只是 Prompt 模板，而是一个 Agent Scope：它可以为某个 Agent 挂载特定的工具、Prompt、模型、文件系统和策略。

这解释了为什么 DSH 可以同时运行：

```text
Agent A：bash + editor
Agent B：bash + editor + web
Agent C：PTC + subagent + sandbox
```

而不需要为每一种 Agent 维护一套独立程序。

## 和其他框架的区别

| 框架/产品 | 最核心的抽象 |
| --- | --- |
| Codex / Claude Code | 面向用户的完整 Agent 产品 |
| OpenAI / Google SDK | 让开发者组合 Agent 的基础原语 |
| LangGraph | 图结构和状态转移 |
| Pi | 轻量、可扩展的 Coding Harness |
| DSH | 插件运行时、事件契约、会话轨迹和能力作用域 |

DSH 和 LangGraph 并不是完全同一层。LangGraph 更适合显式设计流程图；DSH 更像一个持续运行的 Agent 容器，让能力在事件和 Scope 中动态组合。

## 这种内核的收益和代价

收益很明确：

- 可以替换模型、工具、沙箱和 Loop；
- 可以为不同 Agent 组合不同能力；
- 策略可以通过事件拦截而不侵入主循环；
- 插件卸载和热更新有生命周期基础；
- Session、Replay 和 UI 可以共同消费同一条事件流。

代价也同样明显：

- 配置层次比普通 Agent 更复杂；
- 事件契约一旦设计不好，会造成隐式耦合；
- 插件的生命周期和 Scope 传播难以调试；
- “没有特权核心”意味着团队必须严格维护接口和事件地图。

我的判断是：DSH 的内核更像 Agent 领域的操作系统，而不是一个业务应用。它牺牲了开箱即用的简单性，换取了运行时的可组合性。

下一篇讨论这套架构如何处理持久会话、上下文压缩和跨会话长期记忆。

## 系列导航

- [上一篇：它不是另一个 Codex](/posts/2026-08-18-deepseek-harness-series-1-not-another-coding-agent/)
- [下一篇：Session、记忆与压缩](/posts/2026-08-18-deepseek-harness-series-3-session-memory-compaction/)
