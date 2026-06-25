---
title: "Agent 日记系列（三）：揭秘 Agent 的自我进化：动态工具创建与管理"
date: 2024-04-12T00:31:35+08:00
draft: false
tags: ["Agent", "Self-evolution", "Tool Creation"]
---

传统 Agent 的能力在诞生时就固定了——给什么工具就用什么工具。真正的自进化 Agent 应该能在运行时识别能力缺口，自主扩展工具集。

## 何时需要动态工具

典型场景：

1. **批量文件重命名**：没有 rename 工具，但 Agent 可以写一个 Python 脚本
2. **API 数据聚合**：需要组合多个接口的结果，现成工具不支持
3. **格式转换**：CSV → JSON、Markdown → HTML，临时需要
4. **测试辅助**：需要一个 mock 服务或数据生成器

## 工具创建流程

```
识别缺口 → 编写代码 → 安全审查 → 注册到 Tool Registry → 可用
```

### 识别缺口

Agent 在以下情况触发工具创建：
- 工具调用连续失败（"没有这个工具"）
- 用户明确请求不存在的功能
- 任务需要多步组合但无现成路径

### 编写代码

Agent 根据需求生成工具脚本，关键约束：
- 输入输出必须有明确 schema
- 必须包含错误处理
- 不能访问超出工作目录的路径

### 安全审查

这是最关键的一步。Agent 生成的代码必须经过：
- **语法检查**：确保可执行
- **沙箱试运行**：用测试数据验证
- **权限边界**：不读取敏感文件、不发起外部网络请求
- **用户确认**（可选）：高风险操作需人工批准

### 注册与生命周期

```python
# 工具注册伪代码
tool_registry.register(
    name="batch_rename",
    description="批量重命名文件，支持正则匹配",
    parameters={
        "pattern": {"type": "string", "description": "正则匹配模式"},
        "replacement": {"type": "string", "description": "替换字符串"},
        "directory": {"type": "string", "description": "目标目录"}
    },
    handler="tools/batch_rename.py",
    scope="session"  # session / persistent
)
```

工具作用域：
- **session**：当前会话有效，会话结束自动清理
- **persistent**：持久化到磁盘，跨会话可用

## 失败案例与教训

1. **无限循环**：Agent 创建了一个调用自己的工具 → 死循环。解决：禁止工具递归调用创建器。
2. **功能重复**：Agent 不知道已有 `run_shell` 可以完成同样工作。解决：创建前先检查现有工具覆盖度。
3. **安全越界**：生成的脚本尝试读取 `~/.ssh/id_rsa`。解决：沙箱白名单 + 路径限制。

## 进化方向

下一步是**工具组合**——Agent 不创建新工具，而是自动编排现有工具形成新流水线。这比"造轮子"更高效，也更可控。

> 自进化的核心不是"创造"，是"知道什么时候该创造、什么时候该组合"。
