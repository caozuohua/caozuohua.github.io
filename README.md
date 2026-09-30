# 🖋️ CAO ZUOHUA 技术博客

> 分享技术、思考与生活 — Hugo 静态博客，部署在 https://caozuohua.github.io/

[![Built with Hugo](https://img.shields.io/badge/Hugo-Ananke-ff4088)](https://gohugo.io)
[![GitHub Pages](https://img.shields.io/badge/deploy-Pages-2ea44f)](https://caozuohua.github.io/)
[![GitHub last commit](https://img.shields.io/github/last-commit/caozuohua/caozuohua.github.io)](https://github.com/caozuohua/caozuohua.github.io/commits/main)

🌐 在线访问：https://caozuohua.github.io/

## 关于

个人技术博客，聚焦 **AI Agent 实践与研究**、**技术探索**、**效率工具** 三大方向。截至 2026 年 9 月 30 日，共 116 篇文章。

### 热门主题

- 🤖 **AI Agent** — Agent 架构、记忆系统、多智能体协调、幻觉治理、工具调用
- 🧠 **本地大模型** — llama.cpp + Qwen 部署、speculative decoding、LoRA 微调
- 🔌 **Dify 与低代码编排** — 部署选型、节点自定义、RAG、Agent + MCP 实战
- 🧩 **国产算力与 AI 芯片** — 昇腾生态、TileLang、算子与编译器层解读
- 🏭 **行业 AI 调研** — 电力（发输变配用）、厂商解决方案的核查式研究
- 🏦 **投资与财经** — 基金组合分析、AI 驱动投资研究
- 🐧 **Linux 原理系列** — 信号、权限、网络命名空间、systemd

## 文章格式规范

每篇文章是一个**目录型 bundle**，目录命名规则：

```
YYYY-MM-DD-english-slug
```

- 日期前缀（`YYYY-MM-DD`）— 用于排序，不强制要求是真实发布日期
- 英文短横线连接的 slug — 会成为 URL 的一部分
- **目录名不含中文**，避免 URL 编码

### 创建新文章

```bash
hugo new content/posts/YYYY-MM-DD-your-english-slug/index.md
```

### 目录结构

```
.
├── .github/workflows/deploy-hugo.yml   # GitHub Actions 自动构建部署
├── .github/scripts/                    # 构建产物断言门禁
├── archetypes/posts.md                 # hugo new 的文章模板（含署名字段）
├── content/posts/                      # 所有文章
│   └── YYYY-MM-DD-slug/                # 每篇文章一个目录（目录型 bundle）
│       └── index.md                    # 文章内容 + frontmatter
├── layouts/                            # 自定义模板（覆盖主题）
│   ├── baseof.html
│   ├── posts/single.html               # 文章页模板（含 AI 署名渲染）
│   ├── _partials/head-additions.html   # 站点样式（含署名样式与 CSS 变量定义）
│   └── _default/_markup/               # mermaid 代码块渲染钩子
├── themes/ananke/                      # 主题（非 submodule，文件直接纳入版本管理）
└── hugo.toml                           # 站点配置
```

### Frontmatter 模板

```yaml
---
title: "文章标题（可中文）"
date: 2026-09-30T22:00:00+08:00
publishDate: 2026-09-30T22:00:00+08:00
description: "列表页摘要，写足信息量"
tags: ["标签1", "标签2"]
categories: ["技术分享"]
draft: false

# 可选：AI 协作署名，详见下文「署名规范」
ai:
  agent: "WorkBuddy"
  model: "DeepSeek-V4.1-Flash"
  provider: "DeepSeek"
---
```

七个字段缺一不可：`title` / `date` / `publishDate` / `description` / `tags` / `categories` / `draft`。
正文第一行重复一次 H1（与 `title` 相同）。站内互链写 `/posts/<slug>/`。

> ⚠️ **日期绝不能晚于构建时刻。** workflow 只跑 `hugo --minify`（未加 `--buildFuture`），
> Hugo 默认 `buildFuture=false`，日期在未来者会被**静默排除**——Actions 显示 build/deploy 双成功，线上却 404。
> 发稿时取「当前时间或更早」，并**写显式时区** `+08:00`（纯日期如 `2026-09-30` 会被按 **UTC** 解析，仍可能踩坑）。
> 线上 404 的第一诊断命令是 `hugo list future`。

## 署名规范（人类作者 + AI 协作）

### 为什么署名

本站相当数量的文章由 AI 智能体参与撰写与整理。署名不是免责声明，而是**让读者知道自己在读什么**：

- 读者有权知道内容的产出方式，以决定投入多少信任；
- 记录底层模型型号与版本，便于日后回溯「某篇文章当时是什么模型写的」——模型迭代很快，
  **没有版本号的署名等于没有署名**；
- 对作者本人也是一种约束：署上名，就意味着内容经过了自己的确认。

### 字段约定

署名信息写在 frontmatter 的 `ai` 块中（**全部可选**，缺失时页面上不渲染任何署名元素，向后兼容存量文章）：

| 字段 | 必填 | 含义 | 示例 |
|---|---|---|---|
| `ai.agent` | ✅ **触发渲染** | 智能体名称。**只有该字段存在时，署名才会出现** | `WorkBuddy` / `Claude Code` / `Cursor` |
| `ai.model` | 建议填 | 底层模型型号与版本 | `DeepSeek-V4.1-Flash` |
| `ai.provider` | 可选 | 模型提供方 | `DeepSeek` / `Anthropic` |

人类作者**无需**在 frontmatter 重复声明——站点级 `params.author` 已统一为 `Cao Zuohua`，
模板会自动带上（见 `layouts/posts/single.html`）。

> **鼓励，不强制。** 人类独立撰写的文章不加 `ai` 块即可。
> 但若一篇原本没有 AI 参与的文章后来由 AI 大幅改写（整段重写、大量补充调研），
> **应当补上 `ai` 块**——署名反映的是「当前这一版是怎么来的」。

### 呈现位置

填了 `ai.agent` 后，模板会在两处自动渲染：

1. **页头元信息行**（日期 / 字数 / 分类 之后）——一行 `· AI 协作：<agent>`，让读者第一眼就知情；
2. **文末署名块**（标签之后、上下篇导航之前）——完整署名：人类作者 + 智能体 + 模型 + 提供方，
   并附一行说明「人类作者保留最终判断；事实性结论与性能数据请读者自行核验」。

两处均由 `layouts/posts/single.html` 统一渲染，**不要在正文里手写署名**——
手写会与模板输出重复，日后改动也容易漏改。

### 存量文章

2026-09-30 之前的文章**不做回溯补署名**。历史文章的产出过程已不可考，
补一个「当时大概用的什么模型」只会制造不准确的记录。本规范自该日之后的文章起生效。

## 图表规范

文章配图分两类，各有明确分工：

| 类型 | 用什么 | 适用 |
|---|---|---|
| 结构 / 流程 / 决策 | **mermaid 代码块** | 分层图、流程图、状态机 |
| 数据图表 | **内联 SVG** | 折线、柱状、散点等需要精确控制坐标的场合 |

**不要引入 Chart.js / ECharts 这类 CDN 图表库。** 静态博客引运行期第三方脚本，
读者侧多一次外网请求，也增加构建期不可控因素。

- **mermaid**：围栏标 ` ```mermaid `，渲染钩子在 `layouts/_default/_markup/render-codeblock-mermaid.html`。
- **内联 SVG**：依赖 `[markup.goldmark.renderer] unsafe = true`（已在 `hugo.toml` 开启）放行原始 HTML。
  用 `<div class="...">` 包住 `<svg>`，**这一整块内部不留空行**——HTML block 遇空行会被截断成多段。
- **配色**：站点是**浅色**主题（卡片底 `#f8f9fa`、正文 `#1a1a2e`），图表必须走浅色系。
  可直接引用站点 CSS 变量（`var(--color-primary)`、`var(--color-border)` 等，
  定义见 `layouts/_partials/head-additions.html`）。
- **类名**加站点前缀（如 `.ds-tl-`）避免与主题选择器冲突；
  `<style>` 块既可放在 frontmatter 之后、正文 H1 之前，也可直接嵌在对应 `<div>` 内部（推荐，样式与图表自包含）。

## 本地预览

构建与部署完全交给 GitHub Actions，**本地没有 Hugo 也能正常发稿**。
但改动 `layouts/` 下的模板、或做发布前自检时，本地构建能提前把问题暴露出来。

本机已有一份 extended 版可用：

```bash
export HUGO="D:/Geek/.tools/hugo/hugo.exe"   # 已存在，v0.164.0 extended

# 与 CI 同参数做一次全量构建 —— 会把 CI 会拦下的 WARNING 直接暴露出来
"$HUGO" --minify --printPathWarnings --panicOnWarning

# 顺带跑一遍产物断言门禁
python .github/scripts/check-published-artifacts.py

# 或起本地服务预览
"$HUGO" server -D        # http://localhost:1313
```

需要与 CI 完全同版本时，按 `hugo-version` 下载 extended 版到 `.workbuddy/binaries/hugo/`（已 gitignore）：

```bash
gh release download v0.166.0 --repo gohugoio/hugo \
  --pattern "hugo_extended_0.166.0_windows-amd64.zip" \
  --dir .workbuddy/binaries/hugo --clobber
```

> ⚠️ 版本以 `.github/workflows/deploy-hugo.yml` 的 `hugo-version`（当前 `0.166.0`）为准。
> 本地与 CI 版本不一致时，**本地过了不代表 CI 过**——`--panicOnWarning` 对版本尤其敏感。

## 部署

推送到 `main` 分支后，GitHub Actions 自动构建并部署到 GitHub Pages，约 1 分钟生效。

```bash
git add content/posts/YYYY-MM-DD-your-slug    # 只加目标目录，不要用 git add -A
git commit -m "<YYYY-MM-DD>: <中文标题>"
git push origin main
```

构建流程：`hugo --minify --printPathWarnings --panicOnWarning`
→ 产物断言门禁（`.github/scripts/check-published-artifacts.py`）
→ 上传产物 → 部署到 Pages

**两条硬约束：**

- **`--panicOnWarning`**：任何 WARNING 都会让构建红灯。这是有意的——它把「静默失败」转成「显式失败」。
  出现新告警请修根因，**不要**为了变绿而删掉这个 flag。
- **产物断言门禁**：生效日期已到的文章必须产出 `public/posts/<slug>/index.html`，否则 exit 1。
  这是唯一能抓住「CI 绿 + 线上 404」的手段。
  按设计不产出 HTML 的两种情况（`draft: true`、日期在未来）会被记为 SKIP，不算失败。

**发布后必须验证线上 200**，不能只看 CI 绿：

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://caozuohua.github.io/posts/<slug>/
```

## License

MIT
