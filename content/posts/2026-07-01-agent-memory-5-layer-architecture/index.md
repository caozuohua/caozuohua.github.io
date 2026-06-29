---
title: "Agent 的记忆：Hermes-Lite 如何用 5 层结构解决「鱼的难题」"
date: 2026-06-28
publishDate: 2026-06-28
description: "一篇源码级拆解：Agent 的记忆系统怎么同时做到持久化、低成本、不丢上下文？Hermes-Lite 用 5 层架构给出了一个答案。"
tags: ["Agent", "Memory", "Hermes-Lite", "LLM", "Architecture"]
categories: ["Agent"]
draft: false
aliases: ["/posts/agent-memory-5-layer-architecture"]
---

> 人类 chatbot 最尴尬的瞬间：第二次见面完全不认识你。Agent 的记忆系统怎么同时做到持久化、低成本、不丢上下文？我深入 Hermes-Lite 源码写了一个月，拆解出 5 层架构。

## 从「鱼的难题」开始

用过 ChatGPT 的人都知道一个痛：**下次打开，它完全不记得你了**。

对一次性聊天这没问题。但对个人助理——帮你管理 200 条知识库、追踪几个项目的进度、记住你的偏好——这等于每次都要把整段友情重来。

我做 QPC（个人知识库）时就被这个问题卡过。后来折腾 Hermes-Lite、nanobot，逐步摸到一条可行的路。这篇文章从 Hermes-Lite 的实际源码出发，拆解它的 5 层记忆架构，看看一个 Agent 是怎么解决「鱼的难题」的。

## 总览：5 层架构

```
┌─────────────────────────────────────────────┐
│  Layer 1: 持久记忆 (MEMORY.md / USER.md)     │  ← 跨会话，纯文本
├─────────────────────────────────────────────�
│  Layer 2: 会话压缩 (ContextCompressor)       │  ← 长对话不爆
├─────────────────────────────────────────────┤
│  Layer 3: 会话检索 (session_search + FTS5)   │  ← 历史不丢
├─────────────────────────────────────────────�
│  Layer 4: 增量写入门控 (Nudge 机制)           │  ← 该记就记
├─────────────────────────────────────────────�
│  Layer 5: 原子性保障 (fcntl + 临时文件)       │  ← 不丢不坏
└─────────────────────────────────────────────┘
```

每一层解决一个独立问题，层与层之间不耦合。下面逐层拆解。

## Layer 1：持久记忆——两个纯文本文件

最底层，也是最简单的：**两个 § 分隔的纯文本文件**。

- `MEMORY.md`：Agent 自己的笔记（环境事实、项目约定、工具坑点）
- `USER.md`：关于你的信息（偏好、沟通风格、工作流习惯）

```python
# 源码：tools/memory_tool.py
ENTRY_DELIMITER = "\n§\n"

class MemoryStore:
    def __init__(self, memory_char_limit=2200, user_char_limit=1375):
        self.memory_entries: List[str] = []
        self.user_entries: List[str] = []
```

**关键设计：冻结快照（Frozen Snapshot）**

```python
# 加载时拍一次快照，注入系统提示
self._system_prompt_snapshot = {
    "memory": self._render_block("memory", sanitized_memory),
    "user": self._render_block("user", sanitized_user),
}
```

会话中途的写入**只改磁盘文件，不改系统提示**。为什么？因为改系统提示会破坏 KV 缓存（prefix cache），让每一轮推理都重新处理整个提示词。冻结快照 = 缓存友好。

**字符上限而非 token 上限**：memory 2200 字符（~800 tokens），user 1375 字符（~500 tokens）。用字符数是因为它模型无关——换模型不用重新调。

**防漂移检测**（issue #26045）：写入前检查磁盘文件是否被外部修改过（patch 工具、shell 追加、手动编辑）。如果检测到漂移，拒绝写入并生成 `.bak` 快照，防止静默数据丢失。

## Layer 2：会话压缩——对话再长也不爆

65K 上下文窗口听起来很大，但一个复杂任务跑 50 轮工具调用就满了。怎么办？

**答案：像 zip 一样压缩旧对话，但保留关键信息。**

```python
# 源码：agent/context_compressor.py
class ContextCompressor(ContextEngine):
    def __init__(self, model, threshold_percent=0.50, protect_first_n=3,
                 protect_last_n=20, summary_target_ratio=0.20):
```

**压缩算法 5 步**：

1. **剪枝旧工具结果**（便宜，不调 LLM）：把 `[terminal] ran npm test -> exit 0, 47 lines output` 这种大段输出替换成一行摘要
2. **保护头部**（前 3 条消息：系统提示 + 首轮对话）
3. **保护尾部**（最近 ~20K tokens 的消息原样保留）
4. **LLM 摘要中间部分**：用便宜模型（auxiliary model）生成结构化摘要
5. **迭代更新**：再次压缩时，基于上次的摘要继续压缩，信息不丢失

**摘要模板**（这是我见过最精巧的部分）：

```
## Historical Task Snapshot     ← 历史任务快照
## Historical In-Progress State  ← 历史进行状态
## Historical Pending User Asks  ← 历史待答问题
## Historical Remaining Work     ← 历史剩余工作
```

注意标题里的 **"Historical"** 和 **"Reference Only"**。这不是随便写的——早期版本用 "Active Task"、"Next Steps" 这类标题，弱模型会把摘要当成新指令去执行（issue #11475）。改成 "Historical" 后，模型明确知道这是背景参考，不是当前任务。

**防抖机制**：如果连续 2 次压缩都只省了不到 10%，就跳过压缩，避免无限循环（每次只删 1-2 条消息的无效压缩）。

## Layer 3：会话检索——历史不丢

压缩解决了「对话太长」的问题，但压缩后的摘要信息密度再高，也不如原始对话细节丰富。怎么办？

**答案：SQLite FTS5 全文检索。**

```python
# 源码：tools/session_search_tool.py
# 三种调用模式：
# 1. DISCOVERY — 传 query，FTS5 搜索，返回 top N 会话
# 2. SCROLL — 传 session_id + around_message_id，返回 ±N 条消息窗口
# 3. BROWSE — 无参数，按时间倒序列出最近会话
```

**零 LLM 成本**：所有模式都直接查 SQLite，不调 LLM。FTS5 支持 AND/OR/NOT、前缀匹配、短语搜索。

**会话血缘去重**：压缩产生的子会话通过 `parent_session_id` 链回查根会话，避免同一个话题的多个压缩版本重复出现。

**跨 profile 读取**：`@session:work/abc123` 这种链接可以读取另一个 profile 的会话历史，只读模式打开 SQLite，安全无锁。

## Layer 4：Nudge 机制——该记就记

记忆系统最大的敌人不是技术，是**遗忘**。Agent 聊着聊着就忘了该把信息存起来。

```python
# 源码：agent/turn_context.py
# 每轮检查：
if agent._turns_since_memory >= agent._memory_nudge_interval:
    should_review_memory = True
    agent._turns_since_memory = 0
```

**Nudge 不是强制写入**，而是在系统提示里注入一段提醒：

> 💡 你已经 10 轮没检查记忆了。如果有值得长期保存的信息，现在是用 memory 工具的好时机。

默认间隔：memory 每 10 轮，skill 每 15 轮。

**为什么不用自动提取？** 因为自动提取 = 不可控的信息膨胀。Nudge 让 Agent 自己判断什么值得记，保持记忆的「策展」性质——不是所有对话都值得记住，只有用户纠正你、表达偏好、分享个人信息时才值得。

## Layer 5：原子性保障——不丢不坏

最后一层是工程保障：**写入不能半途而废**。

```python
# 源码：tools/memory_tool.py
# fcntl 文件锁 + 临时文件原子替换
from utils import atomic_replace
```

**防漂移检测**（issue #26045）：

写入前检查磁盘文件的哈希。如果文件在外部被修改过（patch 工具、shell 追加、并发会话写入），拒绝本次写入并生成 `.bak.<ts>` 快照。这防止了：
- 你用 `echo >> MEMORY.md` 追加内容，Agent 不知道，下次写入覆盖掉了
- 两个会话同时写同一个文件，互相覆盖

**威胁扫描**（supply chain 防护）：

```python
from tools.threat_patterns import first_threat_message as _first_threat_message

def _scan_memory_content(content: str) -> Optional[str]:
    return _first_threat_message(content, scope="strict")
```

每条记忆写入时扫描 prompt injection 模式。命中则在系统提示快照里替换为 `[BLOCKED: ...]`，但保留原文在 live state 里让你查看和删除。

## 实测数据

在我自己的 Hermes-Lite 实例上（运行 3 个月，60+ 会话）：

- **MEMORY.md**：2057/2200 字符（93% 满）— 接近上限，需要清理
- **USER.md**：1238/1375 字符（90% 满）— 同上
- **state.db**：包含 60+ 会话的完整消息历史
- **压缩触发**：平均每 3-4 个长会话触发 1 次
- **Nudge 触发**：每 10 轮提醒一次，实际写入率约 30%（70% 的提醒被 Agent 判断为"不值得记"）

## 和其他方案对比

**vs ChatGPT Memory**：
- ChatGPT 是黑盒自动提取，你不知道它记了什么
- Hermes-Lite 是策展式，每条记忆都是 Agent 主动决策的结果
- 你可以直接编辑 MEMORY.md，完全可控

**vs LangChain Memory**：
- LangChain 的 Memory 类通常是内存变量，会话结束就丢
- Hermes-Lite 的文件持久化 + FTS5 检索 = 真正的跨会话

**vs QPC（我的知识库）**：
- QPC 是面向人类的知识管理（4 字段极简设计）
- Hermes-Lite 记忆是面向 Agent 的（自动注入系统提示）
- 两者互补：QPC 存「我知道什么」，Agent 记忆存「我怎么工作」

## 设计哲学：为什么是这 5 层？

看完源码，我觉得核心哲学是三个词：

1. **分层**：每层解决一个问题，不互相耦合。压缩坏了不影响持久记忆，检索坏了不影响 Nudge
2. **策展**：不是所有信息都自动保存，Agent 自己判断什么值得记。这比自动提取更可控
3. **工程诚实**：冻结快照、防漂移、防抖、威胁扫描——这些脏活保证系统在真实长期运行中不崩

## 如果你也想搭一个

最小可行版本只需要 Layer 1：

```python
# 伪代码：最简 Agent 记忆
MEMORY_FILE = "memory.txt"

def remember(text):
    with open(MEMORY_FILE, "a") as f:
        f.write(f"§\n{text}\n")

def recall():
    with open(MEMORY_FILE) as f:
        return f.read()

# 系统提示里注入：
system_prompt += f"\n## 你的记忆：\n{recall()}"
```

加上 Layer 2（压缩）和 Layer 3（检索）就是生产级。Layer 4 和 Layer 5 是锦上添花。

## 结语

Agent 的记忆不是「把对话存起来」这么简单。它需要在**持久性、成本、上下文完整性、写入控制、数据安全**五个维度同时做好。

Hermes-Lite 的 5 层架构不一定是最好的方案，但它是一个经过实战检验的方案——在我每天的使用中，它确实记住了我的偏好、我的项目、我的习惯。

下次你打开对话，Agent 说「上次你说的那个 VPS 安全方案，我查了一下日志……」——背后就是这套系统在运作。

---

*源码基于 Hermes Agent 开源项目（Nous Research），截至 2026 年 6 月。*
