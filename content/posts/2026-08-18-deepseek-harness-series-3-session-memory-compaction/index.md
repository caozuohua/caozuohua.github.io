---
title: "DeepSeek Harness 解读（三）：会话、记忆与上下文压缩"
date: 2026-08-18T10:20:00+08:00
publishDate: 2026-08-18T10:20:00+08:00
description: "拆解 DSH 的 Session Persistence、事件溯源、Compaction、Goal 和 MCP 长期记忆，理解它为什么不内置万能 Memory 模块。"
tags: ["DeepSeek", "DSH", "Agent Memory", "Compaction", "Persistence", "MCP"]
categories: ["AI Agent", "记忆系统"]
draft: false
---

> 这是 DSH 系列的第三篇。很多 Agent 都声称支持“记忆”，但这个词往往同时指会话保存、上下文压缩、跨会话召回和目标续跑。DSH 的有趣之处，是把这些问题明确拆开了。

## 先把“记忆”拆成五件事

```text
Session Persistence   保存发生过什么
Context History       决定模型当前看到什么
Compaction            压缩当前可见历史
Long-term Memory      跨会话主动召回知识
Goal State            Agent 还要继续完成什么
```

DSH 内置支持前四项中的一部分：它强内置会话事件日志和上下文压缩，Goal 是持久任务状态；真正的语义长期记忆则通过外部 Provider 或 MCP 接入。

## 1. Session Persistence：日志才是事实来源

DSH 不把 `messages[]` 当作唯一状态，而是将一次交互保存为 append-only 的类型化事件：

```text
turn/start
user/message
assistant/chunk
assistant/message
tool/call
tool/result
step/end
turn/end
```

模型的历史消息由这些事件重新派生。这样可以让 UI、Replay、Fork、Telemetry 和恢复逻辑共享同一份事实来源。[Session 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/session.md)

持久化层通过 `ctx.sessionPersistence` 抽象出来，目前支持 JSONL 和 SQLite 后端。写入采用批处理和 flush checkpoint；崩溃恢复时，DSH 会识别没有关闭的 turn，并以 `interrupted` 结束它，而不是粗暴截断日志。[Persistence 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/persistence.md)

这是一种“事实优先”的设计：

```text
原始日志尽量完整
模型上下文可以变化
历史投影可以重新计算
```

## 2. Compaction：压缩可见表面，不删除原始历史

上下文接近模型窗口时，DSH 不直接删除旧事件，而是选择一段旧的 surface，调用 summarizer 生成摘要，然后追加一个 checkpoint：

```text
compaction/start
    ↓
选择旧历史范围
    ↓
摘要模型或其他 backend
    ↓
compaction/summary
    ↓
user/message + surfaceOp: replace
    ↓
compaction/end
```

最终模型看到的是：

```text
历史摘要 + 最近的原始上下文
```

但旧事件仍然保留在 Session Log 中，方便审计和回放。摘要事件还会记录被 shadow 的 seq、估算 token 数、provider、model 和 usage。

DSH 把 `compaction` 做成独立的 capability seam，而不是 Agent Loop 的硬编码逻辑。抽象接口只定义 `compactIfNeeded()`、`compactNow()` 和 `compactRegion()`，阈值、保留尾部、摘要方式和失败处理由具体 backend 决定。[Compaction 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/compaction.md)

## 3. 压缩触发与结构保护

当前设计中，压缩有三条路径：

- `pressure`：上下文接近阈值；
- `context-overflow`：Provider 明确返回上下文超限；
- `manual`：用户执行 `/compact`。

自动压缩通常在 `agent/pre-step` 发生，也就是上一个 step 的回答和工具结果已经持久化、下一次请求尚未生成之前。这样不会基于一个临时的、尚未落盘的请求做压缩。

DSH 还会避免把工具调用和工具结果拆开：

```text
assistant: call bash
tool: bash result
```

这是一个结构单元，压缩边界不能落在中间。对于特别大的 `tool/result`，还可以先使用独立的 tool-result pruner 做结构化裁剪，再重新测量上下文，必要时才调用摘要模型。

这个顺序很有启发：

> 先做便宜、确定、低损的裁剪，再做昂贵、有损的语义摘要。

## 4. 跨会话长期记忆：DSH 有意留在外面

DSH 当前没有一个默认开启的“自动记住用户偏好和项目事实”的 Memory 模块。仓库提供的是三个默认关闭的 MCP 参考配置：

- Memorix；
- MCP Reference Memory；
- Engram。

DSH 只负责解析 Cordis overlay、启动或连接 MCP Server、发现工具，然后把工具暴露给模型。存储、embedding、召回、冲突解决和遗忘策略由外部 Provider 负责。[第三方记忆 MCP 示例](https://github.com/deepseek-ai/deepseek-harness/tree/master/examples/mcp-memory)

所以跨会话记忆路径是：

```text
Session A：模型调用 memory_write
    ↓
外部 Memory Provider：保存事实、关系或项目记忆
    ↓
Session B：模型调用 memory_search
    ↓
当前上下文：注入召回结果
```

这和 Hermes-Lite 的集成式记忆架构形成了对比。Hermes-Lite 把持久记忆、压缩、会话检索、Nudge 和原子写入作为一个个人助理系统共同设计；DSH 则把“通用运行时”和“记忆产品”分开。可以参考我之前写的 [Agent 的记忆：Hermes-Lite 如何用 5 层结构解决「鱼的难题」](/posts/2026-07-01-agent-memory-5-layer-architecture/)。

## 5. Goal：持久任务状态，而不是语义记忆

DSH 的 Goal 子系统保存的是：

```text
objective
phase: active / paused / blocked / complete
roundsStarted
maxGoalRounds
revision
```

Goal 的每次变更都会形成 `goal/change` 事件。Agent 重启后可以继续知道任务目标、当前阶段、阻塞原因和剩余轮次，但 Goal 不负责召回用户偏好或历史知识。[Goal 文档](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/goal.md)

可以这样理解：

```text
Session Log：我做过什么
Goal：我还要做什么
Memory Provider：我需要回忆什么
```

## 这种设计的核心理念

### 持久化和召回是两回事

保存所有事件，不代表系统知道哪些事件值得在未来召回。DSH 把“忠实保存”交给 Persistence，把“语义选择”交给 Memory Provider。

### 压缩是投影，不是事实改写

上下文窗口是一个有限的工作表面。DSH 允许 surface 被替换，但不要求原始事件消失。这让压缩可以是有损的，而审计和回放仍然保留依据。

### 记忆策略属于领域

代码 Agent 记住项目约定，客服 Agent 记住客户关系，个人助理记住用户偏好。用一个通用向量数据库覆盖所有场景，往往比提供一个稳定的 Provider 接口更容易失控。

### 失败也必须可解释

压缩何时开始、压缩了哪些范围、摘要用什么模型、是否失败，都进入日志。这样 Agent 不会在某次压缩后悄悄丢掉上下文而无人知晓。

## 我的判断

DSH 的记忆设计不是“功能最全”，而是“边界最清楚”：

> Runtime 负责事实、生命周期和可重放性；Memory Provider 负责知识选择和召回。

这很适合企业平台，因为企业往往已经有自己的数据库、权限模型、知识库和合规边界。但它不适合期待开箱即用个人记忆的普通用户。

下一篇讨论 DSH 的 minimal preset：它到底是不是最小 Agent，以及它对 Agent Framework Benchmark 有什么启发。

## 系列导航

- [上一篇：内核不是 Agent，而是 Cordis 运行时](/posts/2026-08-18-deepseek-harness-series-2-kernel-cordis/)
- [下一篇：minimal preset 与框架契约](/posts/2026-08-18-deepseek-harness-series-4-minimal-agent-framework-contracts/)
