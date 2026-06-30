---
title: "我的博客自动化发布SOP"
date: 2026-05-09T04:30:40+08:00
draft: false
tags: ["自动化", "SOP", "博客", "Hugo", "Git"]
description: "记录当前 Hugo 博客的发布 SOP：在源码仓库中写作、运行 Hugo 构建验证、提交并推送 main，由 GitHub Actions 部署到 GitHub Pages。"
lastmod: 2026-06-30
aliases:
  - /posts/2026-05-09-我的博客自动化发布sop/
---

这篇 SOP 记录当前博客的真实发布流程。早期我曾经用过 `public` 子模块和部署仓库分离的方案，但当前仓库已经改成更简单的方式：**Markdown 源码、Hugo 模板和 GitHub Actions workflow 都在 `caozuohua.github.io` 仓库内，push 到 `main` 后由 Actions 构建并部署 GitHub Pages。**

## 当前仓库结构

```
caozuohua.github.io/
├── content/posts/        # Markdown 文章源码
├── layouts/              # 站点模板覆盖
├── themes/ananke/        # Hugo 主题
├── hugo.toml             # 站点配置
└── .github/workflows/    # GitHub Pages 部署流程
```

当前生产地址是 `https://caozuohua.github.io/`。本地构建产物会生成到 `public/`，但它只是验证结果，不再作为单独部署仓库提交。

## 第一阶段：内容创作

新文章统一放在 `content/posts/` 下。推荐使用 page bundle 结构：

```bash
hugo new content/posts/YYYY-MM-DD-kebab-case-slug/index.md
```

Front matter 至少包含：

```yaml
---
title: "文章标题"
date: 2026-06-30
publishDate: 2026-06-30
description: "一句话 SEO 摘要"
tags: ["标签1", "标签2"]
categories: ["分类"]
draft: false
---
```

写作完成后先做三项检查：

1. 标题和 `description` 是否准确。
2. 代码围栏是否成对闭合。
3. 文中外链和命令是否仍符合当前仓库实际情况。

## 第二阶段：本地构建验证

提交前必须跑 Hugo 构建：

```bash
hugo --minify
```

构建通过后再检查生成页面：

```bash
python -m http.server 8080 --bind 127.0.0.1 --directory public
```

打开 `http://127.0.0.1:8080/`，确认首页、文章页、目录页都能正常访问。预览结束后停止本地服务器。

## 第三阶段：提交与推送

只提交源码、模板和配置，不提交临时预览进程或无关文件：

```bash
git status --short
git add content/posts layouts hugo.toml .github/workflows
git commit -m "feat: add <文章标题>"
git push origin main
```

`main` 分支 push 后，`.github/workflows/` 中的 Pages workflow 会自动：

1. checkout 仓库；
2. 安装 Hugo extended；
3. 运行 `hugo --minify`；
4. 上传 `public/` artifact；
5. 部署到 GitHub Pages。

## 第四阶段：发布后验证

推送后等待 GitHub Actions 完成，再验证线上页面：

```bash
curl -I https://caozuohua.github.io/
curl -s https://caozuohua.github.io/ | grep "文章标题"
```

如果是新文章，还要直接访问文章 URL：

```bash
curl -I https://caozuohua.github.io/posts/YYYY-MM-DD-kebab-case-slug/
```

返回 `200` 且页面中能找到标题，才算发布完成。

## 失败处理

常见问题按顺序排查：

1. **本地 `hugo --minify` 失败**：先修模板或 Markdown，不要推送。
2. **Actions 构建失败**：打开 GitHub Actions 日志，看 Hugo 版本、模板语法和资源路径。
3. **线上 404**：确认 `draft: false`、日期不是未来日期、slug 与实际 URL 一致。
4. **首页没更新**：等待 Pages 部署完成，必要时刷新 CDN 缓存。

这个流程的关键不是“自动化越多越好”，而是把边界收清楚：源码仓库负责写作和构建配置，GitHub Actions 负责生产部署，本地只做构建验证。
