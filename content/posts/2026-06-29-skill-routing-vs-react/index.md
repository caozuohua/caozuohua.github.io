---
title: "Agent 系列日记 5：为什么 Skill 路由比 ReAct 控制器更适合个人助理"
date: 2026-06-29
publishDate: 2026-06-29
description: "从 luck-agent 到 Hermes-lite，我花了两年时间才想清楚这个问题：80% 的请求不需要'思考'，只需要'路由'。"
tags: ["Agent", "Skill", "Architecture", "LLM", "Hermes"]
categories: ["AI Agent", "个人助理智能体"]
draft: false
aliases: ["/posts/skill-routing-vs-react"]
---

> 从 luck-agent 到 Hermes-lite，我花了两年时间才想清楚这个问题：80% 的请求不需要"思考"，只需要"路由"。

## 回顾：ReAct 控制器模式的困境

2024 年做 luck-agent 的时候，我采用的是经典的 **ReAct 模式**（Reasoning + Acting）：

```
用户输入 → 大模型推理（意图识别 → 规划 → 工具选择 → 执行）→ 输出
```

所有请求，不管简单还是复杂，都走同一个推理链。一个"查 QPC 里有没有 VPS 相关的记录"的请求，也要经过：

1. 理解自然语言
2. 判断意图类别
3. 选择工具（search_qpc）
4. 构造查询参数
5. 执行并解释结果

**问题很明显**：

- **Token 消耗大**：每次推理要带上完整的 system prompt + 工具定义，光上下文就吃掉 3000-5000 token
- **延迟高**：一个简单查询要等模型完成完整推理链，响应时间 3-8 秒
- **上下文窗口压力**：随着工具数量增加（现在 Hermes-lite 有 20+ 个工具），system prompt 越来越大

我当时就在知识库里记了一条：

> "对于个人助理场景，相比最初的 ReAct 控制器模式，Skill 技能路由更适合当前 luckagent：80% 请求是固定模式，不需要复杂推理，技能比 Agent 更稳定，成本更低，响应更快。"

## Skill 路由的核心思想

**一句话**：预定义技能映射，轻量分类先路由，只加载需要的工具和 prompt。

```
用户输入 → 轻量路由（关键词/意图 → 技能）→ 加载专用 prompt + 工具 → 执行
```

### 路由表设计

```python
# 简化版路由逻辑
ROUTING_RULES = {
    "qpc": {
        "keywords": ["QPC", "知识库", "记一下", "记录"],
        "skill": "qpc",
        "tools": ["feishu_bitable_read", "feishu_bitable_write"],
        "prompt": "qpc_skill_prompt"  # 只加载 QPC 相关的 prompt
    },
    "vps": {
        "keywords": ["VPS", "服务器", "防火墙", "Docker"],
        "skill": "gcp-vps-ops",
        "tools": ["terminal", "read_file"],
        "prompt": "vps_skill_prompt"
    },
    "blog": {
        "keywords": ["博客", "文章", "Hugo", "发布"],
        "skill": "hugo-blog",
        "tools": ["terminal", "read_file", "write_file"],
        "prompt": "blog_skill_prompt"
    }
}
```

### 对比：同样"查 QPC"操作

| 指标 | ReAct 模式 | Skill 路由 |
|------|-----------|-----------|
| 上下文 token | ~4000（全量工具定义） | ~800（仅 QPC 相关） |
| 首次响应延迟 | 3-8s | 0.5-1.5s |
| 工具调用次数 | 2-3 次（推理+执行） | 1 次（直接执行） |
| 准确率 | 92%（模型可能选错工具） | 98%（路由确定性高） |

## Hermes-lite 的 Skill 实现

Hermes-lite 的 skill 系统是这样工作的：

### 1. Skill 按需加载

```python
# 不是启动时加载所有 skill
# 而是匹配到时才加载
if skill_match(user_input):
    skill_def = skill_view(name="qpc")  # 此时才读 SKILL.md
    # 加载 skill 的 prompt、工具列表、pitfalls
```

对比传统 agent 预加载全部 system prompt：

```
传统：启动时加载 20 个工具定义 = 固定消耗 4000 token
Hermes-lite：只加载匹配的 1 个 skill = 消耗 600 token
```

### 2. Skill 的 trigger 条件

每个 skill 在 SKILL.md 的 frontmatter 里定义触发条件：

```yaml
---
name: qpc
description: "Read, write, and manage the user's QPC..."
triggers:
  - "记一下"
  - "QPC"
  - "知识库"
  - "search records"
---
```

**什么时候激活**：用户输入匹配 trigger 关键词，或语义相似度 > 阈值。

**什么时候跳过**：输入明显是创作类任务（写小说、设计架构），即使包含关键词也不路由。

### 3. 实际 token 对比

我用同样的操作"搜索 QPC 里 VPS 相关的记录"做了实测：

```
ReAct 模式：
  - System prompt: 3,200 tokens
  - 推理过程: 1,500 tokens
  - 工具调用: 800 tokens
  - 总计: ~5,500 tokens

Skill 路由：
  - Skill prompt: 600 tokens
  - 直接执行: 200 tokens
  - 总计: ~800 tokens

节省: 85%
```

## 什么时候 ReAct 模式仍然有用

Skill 路由不是万能的。以下场景仍然需要完整的推理链：

### 1. 开放式创作任务

"帮我设计一个新的 Agent 记忆系统，要结合 git 的概念"——这种任务没有固定模式，需要模型发散思维、多步推理、迭代优化。

### 2. 需要多步推理的复杂问题

"分析我 QPC 里所有 Agent 相关记录，找出知识缺口，并给出补充建议"——需要理解全局、做判断、生成新内容。

### 3. 混合策略：路由优先 + fallback 推理

```python
def handle_input(user_input):
    # 先尝试路由
    skill = route(user_input)
    if skill and skill.confidence > 0.8:
        return skill.execute(user_input)

    # 路由不确定，fallback 到完整推理
    return react_mode(user_input)
```

**实际效果**：Hermes-lite 日常操作中，约 70-80% 的请求走 Skill 路由，20-30% 走完整推理。

## 从 luck-agent 到 Hermes-lite 的架构演进

回顾这两年，我的 Agent 架构经历了三个阶段：

### 2024：全 ReAct 控制器

```
用户 → luck-agent → 大模型推理 → 工具调用 → 输出
```

- 所有请求走同一个推理链
- 工具数量少（5-8 个），问题不明显
- 痛点：简单操作也慢，token 浪费

### 2025：引入 Skill 路由 + Memory 分层

```
用户 → 路由层 → Skill（70%）→ 快速执行
                → ReAct（30%）→ 完整推理
```

- 引入 Skill 路由层
- Memory 分层：短期（当前对话）→ 中期（memory.db）→ 长期（QPC）
- 痛点：Skill 之间切换不流畅，路由准确率不够

### 2026：Skill 生态 + QPC 第二大脑 + 分层记忆

```
用户 → Hermes-lite → Skill 路由（80%）→ 按需加载 skill_view
                            → ReAct（20%）→ 完整推理
                    → Memory 分层：
                       - 当前对话（context window）
                       - memory.db（跨 session）
                       - QPC bitable（永久知识）
```

- Skill 生态：20+ 个 skill，按需加载
- QPC 作为永久知识层，跨机器、跨 session
- 分层记忆：不同生命周期的知识存在不同地方

## 总结：个人助理架构选型建议

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 高频简单操作（查记录、查状态、发消息） | Skill 路由 | 快、省、稳 |
| 低频复杂推理（设计架构、分析问题） | ReAct 模式 | 需要完整推理链 |
| 不确定 | 混合策略 | 路由优先，fallback 推理 |

**不要迷信一个模式能解决所有问题。** 个人助理的核心不是"多智能"，而是在对的场景用对的方式。80% 的时候，一个 if-else 路由比大模型推理更好用。
