# blog-source

Hugo 静态博客源码，部署在 https://caozuohua.github.io/

## 目录结构

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

## 文章格式规范

每篇文章是一个**目录型 bundle**，目录命名规则：

```
YYYY-MM-DD-english-slug
```

- 日期前缀（`YYYY-MM-DD`）— 用于排序，不强制要求是真实发布日期
- 英文短横线连接的 slug — 会成为 URL 的一部分
- **目录名不含中文**，避免 URL 编码后出现 `%XX`

示例：`content/posts/2026-05-10-deep-dive-agent-shell-tool/index.md`

## 创建新文章

**正确方式：**

```bash
hugo new content/posts/YYYY-MM-DD-your-english-slug/index.md
```

Hugo 会自动创建目录和 `index.md`，并根据 `themes/ananke/archetypes/default.md` 生成 frontmatter 模板。

**手动创建时务必遵守：**

1. 创建目录，不是单个 `.md` 文件
2. 目录名 = 日期 + 英文 slug，全小写，短横线分隔
3. 文章写在 `index.md` 里
4. frontmatter 中 `title` 可以是中文（显示用），但 `slug` 必须是英文

**错误示例（不要这样做）：**

```bash
# ❌ 直接创建 .md 文件，没有目录
touch content/posts/my-article.md

# ❌ 目录名含中文
mkdir content/posts/我的文章/
```

## Frontmatter 模板

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
```

访问 http://localhost:1313

## 部署

推送到 `main` 分支后，GitHub Actions 自动构建并部署到 GitHub Pages。

```bash
git add .
git commit -m "feat: Add new post: <标题>"
git push origin main
```

构建流程：`hugo --minify` → 产物上传 → 部署到 Pages
