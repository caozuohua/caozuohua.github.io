---
title: "Hermes-lite 裁剪指南：在 1GB VPS 上跑轻量 AI Agent"
date: 2026-06-24T23:58:52Z
draft: false
tags: ["Hermes", "AI Agent", "GCP", "轻量化", "LLM", "系统运维"]
description: "将完整版 Hermes Agent 裁剪部署到 1GB 内存的 GCP e2-micro VPS 上的完整实践记录。涵盖裁剪思路、内存优化、模型配置、工具链选择和踩坑经验。"
aliases:
  - /posts/2026-06-24-hermes-lite-trimming-guide/
---

## 为什么要裁剪

完整版 Hermes Agent（Nous Research）功能丰富：多平台网关、浏览器自动化、语音 TTS/STTS、多 Agent 协作、Kanban 看板等。但这些功能对资源要求不低——官方文档建议至少 2GB 内存。

我有一台 GCP e2-micro（2 vCPU / 954MB RAM），想用它跑一个 24/7 在线的 AI Agent 接入飞书。完整版装不下，于是有了这个裁剪实践。

## 裁剪目标

- **保留**：核心 Agent 能力（工具调用、技能系统、记忆、会话搜索、终端/文件操作）
- **去掉**：浏览器、语音 TTS/STTS、图片生成、多 Agent 协作、Kanban 等重功能
- **约束**：内存占用控制在 500MB 以内，能稳定运行在 e2-micro 上

## 环境概况

| 项目 | 值 |
|------|-----|
| 机型 | GCP e2-micro |
| CPU | 2 vCPU (Intel Xeon @ 2.20GHz) |
| 内存 | 954MB |
| 磁盘 | 28GB (36% 使用) |
| 系统 | Ubuntu 24.04 LTS (kernel 6.17) |
| Hugo | v0.161.1 extended |

## 裁剪步骤

### 1. 安装完整版 Hermes

先用官方脚本安装完整版，确认能跑起来，再逐步裁剪：

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

这一步会安装到 `~/.hermes/`，包含所有功能。

### 2. 识别可裁剪项

完整版安装后检查：

- **Toolsets**：`hermes tools list` — 列出所有可用工具集
- **Skills**：`ls ~/.hermes/skills/` — 已安装技能
- **Config**：`cat ~/.hermes/config.yaml` — 完整配置

### 3. 配置裁剪

在 `config.yaml` 中禁用不需要的功能：

```yaml
# 禁用非核心 toolsets
disabled_toolsets:
  - browser
  - image_gen
  - tts
  - cronjob

# 关闭语音
tts:
  enabled: false
stt:
  enabled: false

# 关闭多 Agent 协作
delegation:
  model: ""  # 禁用子代理

# 关闭 Kanban
kanban:
  enabled: false

# 关闭 Curator（技能自动维护）
curator:
  enabled: false
```

### 4. 内存优化

关键配置：

```yaml
# 限制上下文长度
model:
  context_length: 65536  # 默认 131072，减半

# 启用压缩
compression:
  enabled: true
  threshold: 0.35       # 上下文 35% 时触发压缩
  target_ratio: 0.15    # 压缩到 15%

# 限制工具输出
tool_output:
  max_bytes: 20000
  max_lines: 800
```

### 5. 模型选择

默认模型走 OpenRouter（owl-alpha），辅助任务（压缩、视觉等）走本地 NewAPI：

```yaml
auxiliary:
  compression:
    provider: newapi-local
    model: gemini-2.5-flash-lite
    context_length: 65536
```

**注意**：NewAPI 的 Groq 70B/8B 模型只有 8K 上下文，不适合做压缩。选 `gemini-2.5-flash-lite`（65K ctx）。

## 实际运行效果

裁剪后稳定运行一周，内存占用：

| 组件 | 内存占用 |
|------|----------|
| Hermes Gateway | ~280MB |
| NewAPI (Docker) | ~120MB |
| Nginx + SSH | ~30MB |
| **总计** | **~430MB** |

剩余 500MB+ 余量，系统无压力。

## 踩坑记录

### 1. fallback_providers 为空

配置了 `fallback_providers: []` 意味着主模型不可用时**没有后备**。不要像文档里说的那样配一个 Groq 70B 当 fallback——8K 上下文会导致压缩任务失败。

### 2. 技能数量影响启动速度

每增加一个技能，gateway 启动时解析时间增加。24 个技能约 3 秒，64 个技能约 8 秒。按需安装，不要贪多。

### 3. 记忆文件宁少勿多

MEMORY.md 和 USER.md 每轮都会注入系统提示。内容越多，token 消耗越大。保持精简——只记"下次还需要知道"的事实，不记过程记录。

### 4. systemd 环境变量

Hermes 通过 systemd 运行时，环境变量需要显式配置：

```ini
[Service]
Environment=HERMES_HOME=/home/user/.hermes-lite
```

否则可能出现"找不到配置"或"回退到 fallback 回复"的问题。

### 5. 红截断（Redactor）

Hermes 默认开启 `security.redact_secrets: true`，工具输出中的 token 字符串会被 `***` 替换。这意味着你**不能**在对话中打印或构造 API key——即使部分片段也会被截断。写脚本时用文件读取 key，不要内联。

## 裁剪前后对比

| 特性 | 完整版 | Hermes-lite |
|------|--------|-------------|
| 内存占用 | 1.5-2GB | ~430MB |
| 启动时间 | ~12s | ~4s |
| 技能数量 | 64+ | 24 |
| 浏览器 | ✅ | ❌ |
| 语音 TTS | ✅ | ❌ |
| 子代理 | ✅ | ❌ |
| Kanban | ✅ | ❌ |
| 核心工具 | ✅ | ✅ |
| 记忆系统 | ✅ | ✅ |
| 会话搜索 | ✅ | ✅ |
| 技能系统 | ✅ | ✅ |

## 总结

裁剪的核心思路：**明确需求，砍掉不需要的**。

完整版 Hermes 是为多平台、多 Agent、全能场景设计的。如果你的场景是"单 VPS + 单平台 + 单 Agent + 文本交互"，裁剪后完全够用，而且更稳定、更省资源。

轻量化不是降级，是适配。
