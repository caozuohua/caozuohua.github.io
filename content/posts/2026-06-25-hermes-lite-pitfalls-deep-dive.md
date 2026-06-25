---
title: "Hermes-lite 裁剪实战：7 类典型坑与解法"
date: 2026-06-25
publishDate: 2026-06-25
description: "从完整版 Hermes Agent 裁剪到 Hermes-lite 过程中遇到的 7 类踩坑经验：路径迁移、技能裁剪、工具裁剪、模型 fallback、直连 provider、记忆容量、长会话。"
tags: ["hermes", "轻量化", "troubleshooting", "ai-agent", "架构"]
categories: ["技术复盘"]
draft: false
---

上一篇文章介绍了 Hermes-lite 的整体裁剪思路。这篇深入每一类实际踩过的坑，
把"为什么会遇到"和"怎么解"都说清楚。

---

## 一、路径迁移坑

从 `.hermes/` 迁到 `.hermes-lite/` 后，不是只改 `HERMES_HOME` 就完事。

### 踩到的点

- `.skills_prompt_snapshot.json` 里残留旧 `.hermes/` 路径
- `web_search/SKILL.md` 硬编码了旧路径
- 技能、工具、memory、config、sessions、workspace 各自缓存旧路径
- systemd 环境变量、进程环境、配置文件、技能正文需要一起排查

### 经验

1. 迁移后 `grep` 全目录旧路径：

```bash
grep -r "\.hermes/" /home/user/.hermes-lite/ --include="*.json" --include="*.md" --include="*.yaml" -l
```

2. 技能快照要清理重建，不能复用旧缓存
3. systemd 重启不是可选项 — 长进程内缓存会保留旧状态

```bash
systemctl restart hermes-lite
systemctl status hermes-lite  # 确认新 PID
```

---

## 二、技能裁剪坑

一开始容易只看磁盘上有多少 `SKILL.md`，但真正可用数量要看运行时过滤后的结果。

### 踩到的点

- 磁盘上 67 个 `SKILL.md`，实际 gateway/slash 可见 65 个
- `kanban-orchestrator/worker` 因为 `environments: [kanban]` 被过滤，这是预期不是坏了
- `_find_all_skills(skip_disabled=True)` 这个参数名容易误读，实际是返回全部技能，默认才过滤 disabled
- `web_search` 技能存在，但 Tavily key 缺失，会变成"看得到但用不了"

### 经验

判断技能可用性要看三层：

1. **磁盘** `SKILL.md` — 技能文件是否存在
2. **skills_list** — 运行时是否导入
3. **slash command resolver** — 最终是否作为 slash 命令暴露

可裁技能最好显式 disabled，而不是只删工具 — 删了对应的 runtime entry 可能
导致依赖它的其他技能报错。

没 key 的技能比没有技能更糟，模型会走错误调用路径白白消耗 token。

---

## 三、工具裁剪坑

工具不是看模块有没有导入，而是看最终给模型的 schema。

### 踩到的点

- `discover_builtin_tools()` 看到的是导入模块，不是模型可见工具
- 真正可见工具要通过 `get_tool_definitions(enabled_toolsets=config.toolsets)` 看
- 裁掉 `web/search` 后，还要确认 `web_search/web_extract` 不在最终 schema
- Feishu `drive/doc` 虽然模块存在，但只要不在 toolsets/schema 就不会暴露

### 经验

**统计工具数量只用最终 schema：**

```python
# 这样才能看到模型实际能调用的工具
tools = get_tool_definitions(enabled_toolsets=config.toolsets)
print(len(tools))
```

裁剪目标应写成"模型可见工具数"，不是"代码里有哪些工具"。

---

## 四、模型 fallback 坑

NewAPI 接入后，不能只看"能回复"和"能 tool call"，还要看上下文窗口和 TPM。

### 踩到的点

- `llama-3.3-70b-versatile` tool call 可用，但只有 8K context
- OpenRouter 临时 SSE 错后 fallback 到 70B，当前上下文 25K，直接 413
- compression 自动走 fallback 时发现 70B 只有 8K，被 Hermes 拒绝
- `gemini-2.5-flash-lite` 才适合做 NewAPI 侧 64K fallback/compression

### 经验

**fallback 模型必须满足"上下文足够"，不是只要便宜快：**

```yaml
fallback_model:
  provider: newapi-local
  model: gemini-2.5-flash-lite  # context_length=65536
```

70B/8B 模型可以作为短任务手动 `/model` 切换，不适合做默认 fallback。

compression 模型必须明确配置，不能依赖 auto 推断。
不建议关闭 compression；要给 compression 配一个 64K 模型。

---

## 五、直连 provider 坑

Google AI Studio 直连模型虽然配置成功，但免费额度很脆。

### 踩到的点

- `gemini-3.5-flash` 很快触发 429 free-tier
- 429 后会污染当前会话体验，看起来像 Hermes-lite 不稳定
- OpenRouter / NewAPI / Google AI Studio 混用时，模型 alias 必须解析到正确 provider 和 key

### 经验

Google AI Studio 直连只适合手动测试，不适合默认。

**稳定优先配置结构：**

- **默认**：OpenRouter `openrouter/owl-alpha` (1M context, 稳定付费)
- **fallback/compression**：NewAPI `gemini-2.5-flash-lite` (64K context)
- **手动备用**：NewAPI `llama-3.3-70b-versatile` (仅短上下文)

免费额度模型不要放在关键自动链路里。

---

## 六、记忆容量坑

Hermes-lite memory 上限小，频繁追加很快满。

### 踩到的点

- memory 接近 2200 字后，add 经常失败
- 应该 replace 合并旧条目，而不是继续 add
- 独立调用 memory tool 需要注入 MemoryStore，否则报 "Memory is not available"

### 经验

Hermes-lite 记忆只存运行关键事实（模型别名列表、provider 结构、项目路径等）。

每次配置变化同步 memory 时优先 replace：

```python
# 不是 add() 追加新条目
# 而是 replace 合并旧条目
memory(action="replace", target="memory",
       content="hermes-lite active skills=64...",
       old_text="hermes-lite active skills=63...")
```

状态信息压缩成一条，不要分散多条。

---

## 七、Gateway 长会话坑

报错不一定来自当前配置，也可能来自旧会话状态。

### 踩到的点

- 修改配置后，不重启 gateway，长进程仍可能使用旧缓存
- 旧会话上下文过长时，会触发 compression、fallback、iteration budget 等连锁问题
- `/reset` 或 `/new` 对坏掉的长会话有时比继续修上下文更实际

### 经验

**配置级修复后必做三件套：**

1. 清缓存（如有）
2. 重启服务
3. 看新 PID 日志

```bash
systemctl restart hermes-lite
journalctl -u hermes-lite -f -n 50 --no-pager
```

对已经压缩多次的会话，建议新开会话 — 不要把"旧会话坏了"误判为"新配置仍坏"。

---

## 当前稳的配置原则

| 角色 | 模型 | Context |
|------|------|---------|
| 默认 | OpenRouter `openrouter/owl-alpha` | 1M |
| fallback / compression | NewAPI `gemini-2.5-flash-lite` | 64K |
| 短任务备用 | NewAPI `llama-3.3-70b-versatile` | 8K |

- **技能**：64 个可见，`web_search` disabled
- **工具**：16 个模型可见，`web/search`/`feishu drive/doc` 不暴露
- **记忆**：少写、替换、合并
- **provider**：默认 OpenRouter + NewAPI，Google AI Studio 仅手动测试

---

## 核心教训

Hermes-lite 要稳，不是"模型越多、工具越多、技能越多"越好，
而是**每条自动链路都要有明确的上下文窗口、key 来源、运行时可见性和失败边界**。
