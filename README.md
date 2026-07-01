# 🖋️ CAO ZUOHUA 技术博客

> 分享技术、思考与生活 — Hugo 静态博客，部署在 https://caozuohua.github.io/

[![Built with Hugo](https://img.shields.io/badge/Hugo-Ananke-ff4088)](https://gohugo.io)
[![GitHub Pages](https://img.shields.io/badge/deploy-Pages-2ea44f)](https://caozuohua.github.io/)
[![GitHub last commit](https://img.shields.io/github/last-commit/caozuohua/caozuohua.github.io)](https://github.com/caozuohua/caozuohua.github.io/commits/main)

🌐 在线访问：https://caozuohua.github.io/

## 关于

个人技术博客，聚焦 **AI Agent 实践与研究**、**技术探索**、**效率工具** 三大方向。截至 2026 年 7 月，共 21 篇文章。

### 热门主题

- 🤖 **AI Agent** — Agent 架构、记忆系统、多智能体协调、幻觉治理、工具调用
- 🛠️ **技术实践** — Hermes Lite 调试、VPS 安全加固、搭建博客框架对比
- 🏦 **投资与财经** — 基金组合分析、AI 驱动投资研究

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
├── content/posts/                      # 所有文章
│   └── YYYY-MM-DD-slug/               # 每篇文章一个目录（目录型 bundle）
│       └── index.md                   # 文章内容 + frontmatter
├── layouts/                           # 自定义模板（覆盖主题）
│   └── baseof.html
├── themes/ananke/                     # 主题（git submodule）
└── hugo.toml                          # 站点配置
```

### Frontmatter 模板

```yaml
---
title: "文章标题（可中文）"
date: YYYY-MM-DDTHH:MM:SS+08:00
draft: false
tags: ["标签1", "标签2"]
categories: ["分类"]
---
```

## 本地预览

```bash
hugo server -D
# 访问 http://localhost:1313
```

## 部署

推送到 `main` 分支后，GitHub Actions 自动构建并部署到 GitHub Pages。

```bash
git add .
git commit -m "feat: Add new post: <标题>"
git push origin main
```

构建流程：`hugo --minify` → 产物上传 → 部署到 Pages

## License

MIT