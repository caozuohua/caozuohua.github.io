# Playwright 系列教程：从零到 AI 代理

> **目标**：打造一份“事无巨细”的 Playwright 进阶指南，涵盖从基础自动化到复杂 AI 代理工作流的完整技术栈。

## 目录
1. [第一篇：环境搭建与架构初探](#part1)
2. [第二篇：定位器与交互艺术](#part2)
3. [第三篇：异步测试与高级等待机制](#part3)
4. [第四篇：AI 代理与浏览器控制 (MCP)](#part4)
5. [第五篇：CI/CD 与多环境适配](#part5)

---

<a id="part1"></a>
### 第一篇：环境搭建与架构初探
*   **核心逻辑**：Playwright 并非 Selenium 的替代品，而是一个基于 WebKit/Chromium/Firefox 协议栈的高性能自动化框架。
*   **初始化**：`npm init playwright@latest`
*   **关键配置**：理解 `playwright.config.ts` 中的 `projects`（多浏览器并行）、`use`（全局断言/超时设置）。

<a id="part2"></a>
### 第二篇：定位器与交互艺术
*   **Web-First Locators**：拒绝 XPath。全面拥抱 `getByRole`, `getByLabel`, `getByPlaceholder`, `getByTestId`。
*   **操作逻辑**：`click`, `fill`, `press` 的原子性与 Playwright 的自动等待机制。

<a id="part3"></a>
### 第三篇：异步测试与高级等待机制
*   **Event-Driven**：`page.waitForEvent`, `page.waitForResponse`。
*   **状态断言**：`expect(locator).toBeVisible()`, `expect(locator).toHaveText()`。
*   **网络拦截**：使用 `page.route` 进行 API Mock 或异常注入。

<a id="part4"></a>
### 第四篇：AI 代理与浏览器控制 (MCP)
*   **LLM 整合**：将 Playwright 作为 AI 的“手臂”。
*   **MCP 服务器**：利用 Playwright MCP Server，使 LLM 能够直接浏览、分析 DOM、执行复杂交互。
*   **实战**：让 Agent 自动分析登录页并完成 MFA 验证。

<a id="part5"></a>
### 第五篇：CI/CD 与多环境适配
*   **Dockerize**：官方镜像运行环境标准化。
*   **GitHub Actions**：`playwright-action` 实现测试结果自动存档。
*   **多环境**：通过 `dotenv` 处理 Dev/Staging/Prod 配置切换。

---

**您希望我优先撰写哪一章的详细内容？**
我们可以直接根据您的选择，在本地工作区生成完整代码示例。
