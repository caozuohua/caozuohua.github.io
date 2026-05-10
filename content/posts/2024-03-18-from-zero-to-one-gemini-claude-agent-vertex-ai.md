---
title: "从零到一：基于 Gemini 和 Claude 的智能体开发实战（集成 Vertex AI）"
date: 2026-05-10T00:31:16+08:00
draft: false
tags: ["Agent", "Gemini", "Claude", "Vertex AI"]
---

本文记录了从零开始开发一个集成 Google Gemini 和 Anthropic Claude 模型的 AI 智能体的完整过程，并详细介绍了如何将其与 Google Cloud Vertex AI 对接，实现更强大的功能和扩展性。文章从环境准备、模型选型、核心逻辑实现、长短期记忆设计，到最终的部署和调试，提供了详尽的步骤和代码示例，旨在为希望构建自己 AI Agent 的开发者提供一份清晰的路线图。

### 核心要点

*   **双模型集成**: 同时利用 Gemini Pro 和 Claude 3 Sonnet 的优势。
*   **Vertex AI 对接**: 通过 Google Cloud 的 Vertex AI 平台进行统一的模型管理和调用。
*   **工具调用 (Tool/Function Calling)**: 实现 Agent 与外部世界（如 Shell、数据库）的交互能力。
*   **长期记忆**: 基于 Turso 分布式数据库构建 Agent 的持久化记忆系统。
*   **动态工具创建**: Agent 能够根据需求自我扩展，动态创建和加载新工具。
