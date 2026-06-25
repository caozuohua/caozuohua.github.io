---
title: "从零到一：基于 Gemini 和 Claude 的智能体开发实战（集成 Vertex AI）"
date: 2024-03-18T00:31:16+08:00
draft: false
tags: ["Agent", "Gemini", "Claude", "Vertex AI"]
---

构建一个真正能用的 AI Agent，不是调 API 写段对话就完事。你需要的是：能接工具、能记忆、能扩展、能上线的完整系统。

## 技术选型

### 模型选择

| 模型 | 优势 | 适用场景 |
|------|------|----------|
| Gemini 3.5 Flash | 1M 上下文、多模态、性价比高 | 长文档分析、多轮对话 |
| Claude 3.5 Sonnet | 代码能力强、指令遵循严格 | 代码生成、复杂推理 |
| Gemini + Claude 双模型 | 互补优势 | 主模型决策 + 辅助验证 |

### 部署平台

**Vertex AI**（推荐 GCP 用户）：
- 统一接口管理多个模型
- VPC 内调用，安全可控
- ADC 认证，无需手动管理 key

**Gemini Developer API**（快速原型）：
- 免费额度够日常用
- API Key 简单直接
- 适合单机开发阶段

## 核心架构

```
用户输入
    ↓
主控制器（LLM 决策）
    ├── 工具调用 → Shell / File / Web / API
    ├── 记忆读写 → 持久化存储
    └── 子代理 → 并行任务
    ↓
输出生成
```

### 1. 工具层

基础工具集：
- `run_shell`：执行任意 Shell 命令
- `read_file` / `write_file`：文件操作
- `web_search` / `web_extract`：网络搜索
- `memory`：记忆读写

扩展工具：
- 根据任务动态创建（见 Agent 日记系列三）

### 2. 记忆层

三层记忆：
- **身份记忆**：用户偏好、项目上下文（每轮注入）
- **经验记忆**：踩坑记录、最佳实践（按需检索）
- **会话状态**：当前任务进度（对话历史）

### 3. 安全层

- 权限最小化：不用 root 运行
- 命令白名单：高危命令需确认
- 输出截断：防止工具输出打爆上下文

## 实战代码：Vertex AI 调用

```python
from google import genai

client = genai.Client(vertexai=True, project="your-project", location="global")

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="分析这段代码的性能问题并给出优化建议",
    config=types.GenerateContentConfig(
        temperature=0.3,
        max_output_tokens=4096,
    ),
)
print(response.text)
```

## 踩坑记录

### 1. 上下文溢出

问题：对话过长，超过模型 context_length。
解决：启用 compression，压缩到 15%，阈值 35%。

### 2. 工具输出过大

问题：`run_shell` 执行 `cat` 大文件，返回打爆上下文。
解决：限制工具输出 max_bytes=20000，超出截断。

### 3. 多轮 tool call 的 thought_signature

问题：Gemini 3.x 多轮 tool call 报 400。
解决：用 Interactions API 自动管理，或在 Proxy 层缓存回放。

### 4. 模型 fallback 配置

问题：主模型 429 后 fallback 到 8K 上下文模型，长对话直接 413。
解决：fallback 模型必须满足 context_length ≥ 64K。

## 上线清单

- [ ] systemd 服务配置（自动重启）
- [ ] 环境变量隔离（key 不硬编码）
- [ ] 日志轮转（journalctl）
- [ ] 监控告警（内存、token 消耗）
- [ ] 备份策略（Git 仓库 + 记忆文件）

> Agent 不是 demo，是工程系统。从能跑到能稳，中间隔的是运维思维。
