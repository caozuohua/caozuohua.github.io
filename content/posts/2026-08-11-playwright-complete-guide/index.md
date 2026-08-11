---
title: "Playwright 完全指南：从入门到精通的浏览器自动化实战"
date: 2026-08-11
publishDate: 2026-08-11
description: "一篇面向新手的 Playwright 完整教程，涵盖环境搭建、核心 API、定位策略、网络拦截、CI/CD 集成等实用主题，帮助你快速上手并写出稳定的自动化脚本。"
tags: ["Playwright", "Python", "Browser Automation", "E2E Testing", "Web Scraping"]
categories: ["技术教程"]
draft: false
aliases: ["/posts/playwright-complete-guide"]
---

## 一、为什么选择 Playwright？

Playwright 是微软于 2020 年开源的新一代浏览器自动化工具，如今已成为 E2E 测试和浏览器自动化领域的主流选择。与 Selenium 等传统工具相比，它有三个核心优势：

- **统一 API 跨浏览器**：Chromium、Firefox、WebKit 三套引擎通过一致的 Python API 操作，无需切换语法。
- **原生异步 + 自动等待**：底层基于 WebSocket 维持浏览器连接，元素操作自带重试和等待，避免了 Selenium 常见的 `time.sleep` 毒瘤。
- **开箱即用的工具链**：代码录制器（CodeGen）、Trace Viewer、截图对比、拦截 Mock 等能力均内置，不必再拼装第三方库。

如果你的需求是稳定地模拟用户操作、跑端到端测试，或者抓取强 JS 渲染页面，Playwright 的学习成本远低于 Selenium 全家桶。

## 二、环境搭建

### 2.1 前置条件

- **Python**：官方推荐 Python 3.9 及以上版本（3.7-3.8 也能运行，但部分特性受限）。
- **操作系统**：macOS、Windows、Linux（包括 Docker 容器）均支持。

### 2.2 安装步骤

```bash
# 1. 创建并激活虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate  # Windows PowerShell

# 2. 安装 Playwright 库
pip install playwright

# 3. 下载浏览器驱动（Chromium、Firefox、WebKit）
playwright install

# 4. 安装 pytest 插件（测试场景必备）
pip install pytest-playwright
```

> 💡 **国内加速**：如果下载浏览器慢，可使用清华镜像：
> ```bash
> playwright install --driver-path https://mirrors.tuna.tsinghua.edu.cn/github-release/microsoft/playwright-cli/latest/
> ```

验证安装：

```bash
python3 -c "from playwright.sync_api import sync_playwright; print('✅ OK')"
playwright --version
```

## 三、两种使用模式：同步 vs 异步

同步模式代码更直观，适合新手；异步模式适合批量、并发场景。

```python
# 同步模式（推荐新手）
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
    browser.close()
```

```python
# 异步模式（高并发场景）
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://example.com")
        print(await page.title())
        await browser.close()

asyncio.run(main())
```

> `headless=True` 表示无头模式（不弹窗）。开发调试时改为 `False` 可实时看到浏览器动作。

## 四、核心交互 API 速查

下表列出高频使用的 12 个 API，可作为速查手册。

**导航与页面属性**
- `page.goto(url)`：打开页面（自动等待加载）
- `page.title()`：获取页面标题
- `page.url`：当前页面 URL（属性，非方法）
- `page.go_back()` / `page.go_forward()`：后退 / 前进

**元素交互**
- `page.get_by_role(name="...").click()`：按 ARIA 角色点击
- `page.get_by_text("...").click()`：按可见文本点击
- `page.get_by_placeholder("...").fill(value)`：按 placeholder 填写输入框
- `page.get_by_label("用户名").fill("admin")`：按 label 关联填写
- `page.get_by_test_id("submit-btn").click()`：按 data-testid 点击

**断言与验证**
- `expect(page).to_have_title("...")`：断言页面标题
- `expect(locator).to_be_visible()`：断言元素可见
- `expect(locator).to_contain_text("...")`：断言包含文本

## 五、定位器（Locator）最佳实践

定位器是 Playwright 中最核心的概念，也是写出稳定脚本的关键。

**推荐优先级（从上到下）**

1. **`get_by_role`**：基于 ARIA role，最贴近真实用户交互，最稳定。例如 `page.get_by_role("button", name="Submit")`
2. **`get_by_label`**：基于表单 label 文本，适合输入框。例如 `page.get_by_label("Email")`
3. **`get_by_text`**：基于可见文本，适合按钮和链接。例如 `page.get_by_text("登录")`
4. **`get_by_placeholder`**：基于输入框 placeholder 提示
5. **`get_by_test_id`**：基于 `data-testid` 属性（需前端配合）
6. **CSS 选择器**：作为兜底方案。例如 `page.locator(".btn-primary")`

**需要避免的做法**
- 避免使用 XPath（可维护性差、性能低）
- 避免依赖动态生成的 ID（如 Vue 的 `data-v-xxxx`）
- 避免用 `nth(0)` 选择第一项，优先描述元素之间的关系
- 避免过度精确的 CSS 路径（如 `div > div > div > button`）

**定位器优先级的实际示例**

```python
# ✅ 推荐：基于角色和可见文本
page.get_by_role("button", name="提交订单").click()

# 也可以链式定位缩小范围
page.get_by_text("购物车").get_by_role("button", name="结算").click()

# ⚠️ 可接受但不够稳健：CSS 选择器
page.locator(".cart-summary .checkout-btn").click()

# ❌ 避免：XPath
page.locator("//button[contains(text(),'提交')]").click()
```

## 六、网络拦截与 Mock 数据

Playwright 原生支持拦截和修改网络请求，无需浏览器插件，非常适合需要模拟 API 响应的测试场景。

```python
# 拦截特定 URL 并返回自定义响应
page.route("**/api/user", lambda route: route.fulfill(
    status=200,
    content_type="application/json",
    body='{"id": 1, "name": "测试用户", "role": "admin"}'
))

# 监控所有请求
page.on("request", lambda req: print(f"→ {req.method} {req.url}"))
page.on("response", lambda res: print(f"← {res.status} {res.url}"))
```

实战场景：在测试环境不方便调用真实后端时，用 Mock 数据隔离前端测试。

## 七、自动化测试最佳实践

如果你用 Playwright 写 E2E 测试，推荐结合 **pytest** 框架，并遵循以下约定。

```python
# tests/test_login.py
import pytest
from playwright.sync_api import Page, expect

def test_login_success(page: Page):
    page.goto("https://example.com/login")
    page.get_by_label("邮箱").fill("user@test.com")
    page.get_by_label("密码").fill("password123")
    page.get_by_role("button", name="登录").click()
    expect(page).to_have_url("https://example.com/dashboard")
    expect(page.get_by_text("欢迎回来")).to_be_visible()

def test_login_fail_wrong_password(page: Page):
    page.goto("https://example.com/login")
    page.get_by_label("邮箱").fill("user@test.com")
    page.get_by_label("密码").fill("wrongpass")
    page.get_by_role("button", name="登录").click()
    expect(page.get_by_text("密码错误")).to_be_visible()
```

**约定建议**
- 测试文件放 `tests/` 目录，命名 `test_*.py`
- 用 `page` fixture（pytest-playwright 自动提供）而非手动创建 browser
- 每个测试独立上下文，互不依赖状态
- 断言写在交互之后，覆盖关键用户路径

运行测试：

```bash
# 全量运行
pytest

# 指定浏览器
pytest --browser=firefox

# 单文件运行
pytest tests/test_login.py

# 查看失败时的 Trace
playwright show-trace trace.zip
```

## 八、Trace Viewer 与调试

Playwright 的 Trace Viewer 能录制并回放测试的全过程（DOM 快照、Console、网络、操作日志），是定位问题的最强工具。

```python
# 录制 Trace（需安装 playwright 内置依赖）
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    # 启动追踪
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto("https://example.com")
    # ... 你的操作
    context.tracing.stop(path="trace.zip")
    browser.close()

# 查看 Trace
playwright show-trace trace.zip
```

在 pytest 中集成 Trace：

```python
# conftest.py
import pytest
from playwright.sync_api import BrowserContext

@pytest.fixture(scope="function")
def context(browser):
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    yield context
    context.tracing.stop(path=f"traces/{pytest.currentTest().name}.zip")
    context.close()
```

## 九、CI/CD 集成（GitHub Actions 示例）

Playwright 官方提供了 Docker 镜像和 GitHub Actions，适合在 CI 中稳定跑测试。

```yaml
# .github/workflows/playwright.yml
name: Playwright Tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - uses: actions/setup-java@v4
        with:
          distribution: "temurin"
          java-version: "17"
      - uses: microsoft/playwright-github-action@v1
      - run: pytest --browser=chromium
```

Docker 镜像方案（适合本地或私有 CI）：

```dockerfile
# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["pytest", "--browser=chromium"]
```

## 十、常见问题排查

1. **浏览器下载慢**：换清华镜像源（见第二节加速命令）。
2. **`webkit` 安装失败**：某些 Linux 发行版缺少系统依赖，可以用 `playwright install-deps` 自动补齐。
3. **元素找不到**：优先检查定位策略是否合理；确认元素是否在 iframe 中（需 `page.frame_locator()` 进入）。
4. **测试偶发失败**：加入 `expect(locator).to_be_visible()` 显式等待，避免隐式等待时间不足。
5. **Trace 录不到内容**：确认 `tracing.start()` 在创建 page 之前调用。

## 十一、进阶资源

- **官方文档**：[playwright.dev/python](https://playwright.dev/python)（最权威的一手资料）
- **API 参考**：[playwright.dev/python/docs/api/class-page](https://playwright.dev/python/docs/api/class-page)
- **GitHub 仓库**：[github.com/microsoft/playwright](https://github.com/microsoft/playwright)
- **Python 示例集**：[playwright.python](https://github.com/microsoft/playwright-python)