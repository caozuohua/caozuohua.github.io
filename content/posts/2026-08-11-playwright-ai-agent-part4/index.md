# 第四篇：AI 代理与浏览器控制 (MCP)

在现代自动化中，浏览器不仅是测试工具，更是 AI 代理（Agent）的“视觉与肢体”。本篇重点讲解如何利用 Playwright 作为 AI 的执行引擎，并结合 MCP (Model Context Protocol) 让 LLM 实现对网页的自主决策。

## 1. 核心架构：LLM + 浏览器
AI 代理控制浏览器的核心流程通常为：
1. **视觉分析**：获取 DOM 或页面截图。
2. **决策循环**：LLM 分析页面信息并下达命令（如“点击搜索按钮”）。
3. **执行与反馈**：Playwright 执行指令并返回 DOM 变化。

## 2. Playwright MCP 服务器实现
要让 LLM 能够控制浏览器，最优雅的方式是通过 MCP 服务器。以下是一个基础的浏览器交互层示例：

```python
# playwright_agent_exec.py
from playwright.sync_api import sync_playwright

def run_agent_task(url: str, action: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        
        # 简化版：AI 代理决策逻辑映射
        if action == "search_and_click":
            page.get_by_placeholder("搜索").fill("Hermes Agent")
            page.get_by_role("button", name="搜索").click()
            
        # 获取当前页面上下文供 LLM 分析
        content = page.content()
        print(f"Action Completed. Page Title: {page.title()}")
        browser.close()
        return content

# 示例：让 AI 代理自动搜索
# run_agent_task("https://www.google.com", "search_and_click")
```

## 3. 让 Agent 具备“观察”能力
AI 不仅要“做”，更要“看”。我们可以通过解析 DOM 结构，将其转化为 LLM 可理解的简要文本：

```python
def extract_actionable_dom(page):
    # 只提取交互元素
    links = page.locator("a").all_text_contents()
    buttons = page.locator("button").all_text_contents()
    return {"links": links[:10], "buttons": buttons[:10]}
```

## 4. 实战：登录与 MFA 自动处理
真正的挑战在于登录。AI 代理结合 Playwright 可以轻松应对：
* **自动定位**：利用 `getByLabel` 识别输入框。
* **延迟等待**：利用 `page.wait_for_selector` 自动等待加载。
* **异常注入**：当检测到 MFA 页面时，AI 介入解析短信验证码或 TOTP，回填并提交。

## 5. 局限性与防御
* **抗 Bot 防御**：网站会检测 WebDriver 标志。需使用 `playwright-stealth` 插件隐藏自动化特征。
* **可靠性**：LLM 可能下达错误的 CSS 选择器。建议在执行前，让 Agent 先通过 MCP 获取页面快照（Snapshot）。

---

**下一阶段建议**：
如果您的目标是打造一个真正的 Agent，可以从配置一个能够自动处理页面交互的 Playwright MCP 服务器开始。是否需要我为您编写一个更详细的 MCP 服务端集成示例？
