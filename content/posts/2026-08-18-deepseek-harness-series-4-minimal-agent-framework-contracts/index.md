---
title: "DeepSeek Harness 解读（四）：minimal 真的是最小 Agent 吗？"
date: 2026-08-18T10:30:00+08:00
publishDate: 2026-08-18T10:30:00+08:00
description: "从 DSH 的 minimal preset、四种能力组合和框架层次出发，讨论什么叫最小 Agent，以及如何设计 Agent Framework Benchmark。"
tags: ["DeepSeek", "DSH", "Minimal Agent", "Agent Framework", "Benchmark", "Runtime"]
categories: ["AI Agent", "架构判断"]
draft: false
---

> 这是 DSH 系列的最后一篇。我们之前问过：minimal preset 只有两个工具，它是否已经是最小化 Agent？答案是：对模型可见能力来说接近最小，对真实运行时来说并不是。

## DSH 的四种 preset 不是四个产品

DSH 当前把 Agent 能力组合成几类 preset：

```text
standard   完整 Coding Agent
ptc        TypeScript Code Mode / PTC
minimal    persistent bash + str_replace_editor
creator    运行时检查和插件实验
```

它们不是四个独立程序，而是同一个 Cordis Runtime 上的不同能力组合。

这一区分很重要：preset 决定的是某个 Agent Scope 可以看到和使用哪些能力，而不是重新启动一套完全不同的 Agent 实现。

## minimal 为什么看起来很小

DSH 的 minimal 配置对模型暴露的主要能力只有：

```text
1. persistent bash
2. str_replace_editor
```

同时它关闭或抑制了很多额外上下文：

- 不加载完整 Coding Agent 的复杂工具集；
- 不注入运行时上下文；
- 不使用默认的复杂压缩能力；
- 使用固定、短的系统提示；
- 让 Bash 在多个 step 之间保持状态。

相关实现可以直接看 [minimal agent preset](https://github.com/deepseek-ai/deepseek-harness/blob/master/apps/cli/config/agent-presets/minimal/agent.cordis.yml) 和 [minimal runtime 设计记录](https://github.com/deepseek-ai/deepseek-harness/blob/master/.agents/notes/implemented/feature/2026-08-11-minimal-profiles-bare-two-tool-runtime.md)。

从模型的视角看，它确实已经非常接近“能修改代码的最小 Agent”：

```text
理解任务
  ↓
bash 查看和验证
  ↓
editor 修改文件
  ↓
bash 运行测试
  ↓
完成
```

## 但它不是最小 Runtime

minimal 仍然依赖很多模型不可见的基础设施：

- Cordis Context；
- Agent Loop；
- Session Log；
- 文件系统 Provider；
- subprocess/PTY；
- sandbox 和 approval 服务；
- tool pipeline；
- persistence；
- workspace 和生命周期管理。

这些服务可能不全部直接暴露给模型，但它们决定了 Bash、编辑器、会话恢复和安全策略能否正常工作。

因此必须区分两个问题：

```text
模型可见最小性：模型需要几个工具才能完成任务？
运行时最小性：完成任务必须启动哪些服务和边界？
```

minimal 的答案是：

```text
模型可见最小性：很接近
运行时最小性：不是
```

如果进一步把 sandbox、approval、session 和 persistence 都拿掉，得到的可能只是一个能调用 shell 的模型，而不是一个可恢复、可控制、可审计的 Agent。

## 最小 Agent 的正确判断标准

一个 Agent 是否“最小”，不能只数工具数量。我更愿意用五个维度判断：

### 1. Model Surface

模型看到了多少工具、Prompt 和上下文？minimal 在这一项非常克制。

### 2. Execution Surface

工具实际能触碰哪些文件、进程、网络和环境变量？两个工具也可能拥有很大的执行权限。

### 3. State Surface

Agent 是否拥有持久会话、终端状态、任务目标和跨 step 上下文？persistent Bash 就已经引入了状态。

### 4. Policy Surface

谁决定一次工具调用能否执行？approval、sandbox、guard 和 tool pipeline 都属于这一层。

### 5. Recovery Surface

失败、取消、崩溃和上下文超限后能否恢复？没有 Session Log 和持久化，系统可能更小，但也不再是可靠 Agent。

所以“最小 Agent”不是：

```text
工具数量最少
```

而是：

```text
在目标任务和安全边界下，所需能力的最小闭包
```

## 这对框架选型有什么启发

之前把 DSH 和 Codex、Claude Code、Pi、LangGraph、OpenAI/Google SDK 放在一起比较，容易产生一个问题：它们其实不完全处在同一层。

| 对象 | 主要合同 |
| --- | --- |
| Codex / Claude Code | 面向用户的任务完成合同 |
| OpenAI / Google SDK | Agent 构造原语合同 |
| LangGraph | 状态图和流程编排合同 |
| Pi | 轻量 Coding Harness 合同 |
| DSH | Runtime 能力、事件、会话和 Scope 合同 |

所谓“合同”，可以理解为框架向上层保证的稳定边界：

- 产品保证“任务最终完成”；
- SDK 保证“你可以创建 Agent、工具和 handoff”；
- 图框架保证“状态按节点和边推进”；
- Harness 保证“编码循环、终端和编辑器可用”；
- DSH 保证“能力可以组合、事件可以拦截、状态可以持久化和重放”。

这也是为什么 DSH 的价值不应该只用 Coding Benchmark 的最终成功率衡量。

## 对 agent-framework-lab 的启发

在我的框架实验项目里，DSH 更适合被放进两条赛道，而不是和所有产品共用一张排行榜。

### Product Track

评价用户是否能快速完成任务：

- 安装和首次运行时间；
- 真实代码任务成功率；
- 工具调用次数；
- 上下文成本；
- 权限体验；
- 失败后的恢复能力。

这一条更适合 Codex、Claude Code、Pi 等 Coding Agent 产品。

### Runtime Track

评价一个框架能否作为 Agent 基础设施：

- 更换模型 Provider 的成本；
- 修改工具和策略的成本；
- 是否支持 per-agent capability scope；
- 是否能够审计和回放完整轨迹；
- 是否支持 Session resume/fork；
- 是否能嵌入 SDK、ACP 或 JSON-RPC；
- 是否能替换 sandbox、filesystem 和 persistence。

这一条才是 DSH 的主场。

## DSH 最值得借鉴的几条原则

### 不要把“工具定义”和“工具权限”混在一起

模型能看到某个工具，不代表宿主一定允许它执行。Schema、Policy 和 Execution 应该是三层。

### 不要把“会话历史”和“模型上下文”混在一起

完整日志是事实，当前上下文只是投影。压缩可以改变投影，但不应该抹掉事实来源。

### 不要把“长期记忆”硬编码进通用 Runtime

记住什么属于业务领域。通用 Runtime 更应该提供稳定的 Provider 和注入边界。

### 不要把所有行为都写进 Agent Loop

压缩、审批、工具策略、遥测、上下文注入都可以通过事件和 capability seam 接入。

### “最小”应该按任务边界定义

minimal 不是把所有服务删除，而是把模型可见能力压缩到刚好能完成目标，同时保留必要的执行、安全、状态和恢复闭包。

## 结语：DSH 的真正赌注

DSH 的真正赌注不是“DeepSeek 能不能做出一个比 Codex 更好的 CLI”。它赌的是另一件事：

> Agent 未来会像数据库、容器或浏览器内核一样，需要一个可组合的运行时，而不只是一个聊天界面。

如果这个判断成立，DSH 的 Cordis、事件日志、能力作用域和可替换 Provider 会变得很有价值。

如果用户永远只需要一个开箱即用的 Coding Agent，那么 Codex 和 Claude Code 仍然是更自然的选择。

这大概就是 DSH 最值得研究的地方：它不一定是当前最好的 Agent 产品，但它很可能是在尝试定义下一层 Agent 基础设施。

## 系列导航

- [上一篇：会话、记忆与上下文压缩](/posts/2026-08-18-deepseek-harness-series-3-session-memory-compaction/)
- [第一篇：它不是另一个 Codex](/posts/2026-08-18-deepseek-harness-series-1-not-another-coding-agent/)
