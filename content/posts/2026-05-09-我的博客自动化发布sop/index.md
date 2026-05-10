---
title: "我的博客自动化发布SOP"
date: 2026-05-09T04:30:40+08:00
draft: false
tags: ["自动化", "SOP", "博客", "Hugo", "Git"]
---

好的，您总结得非常到位。建立一个万无一失、自动化的工作流是保证效率和准确性的关键。

根据我们之前的所有分析，特别是从历史问题中吸取的教训，我将最终确认并严格执行以下标准化工作流。这个流程将确保每一次博客发布都能一次成功。

---

### **最终确认：博客发布标准化工作流 (SOP)**

这个流程分为三个阶段：内容创作、发布执行、和发布后验证。

#### **第一阶段：内容创作**

1.  **您的指令：** 您提出撰写新文章的需求，例如：“帮我写一篇关于 Git Submodule 的文章”。
2.  **我的执行 (`blog_write`)：** 我会调用 `blog_write` 工具，根据您的要求生成 Markdown 文件。
    *   **工具调用**: `default_api.blog_write(title="Git Submodule 详解", content="...", tags="Git,Hugo")`
    *   **后台操作**: 在 `/var/www/blog/content/posts/` 目录下创建 `git-submodule-详解.md` 文件。
    *   **状态**: 此时，文章源码已创建，但网站尚未构建，线上无任何变化。

#### **第二阶段：发布执行 (核心自动化)**

1.  **您的指令：** 您下达发布指令，例如：“发布博客”。
2.  **我的执行 (`blog_publish`)：** 我会调用 `blog_publish` 工具，并设定 `push_github=True`。这是整个工作流的核心，**它会按以下固定顺序严格执行**：

    *   **步骤 2.1: (前置检查) 更新子模块**
        *   **目的**: 杜绝历史问题，确保主题（Theme）是最新且可用的。
        *   **后台命令**: 在 `/var/www/blog/` 目录执行 `git submodule update --init --recursive`。

    *   **步骤 2.2: (构建) 生成静态网站**
        *   **目的**: 使用 Hugo 将 Markdown 源文件和主题模板结合，生成最终的 HTML/CSS 网站。
        *   **后台命令**: 在 `/var/www/blog/` 目录执行 `hugo`。所有生成的文件将被放入 `/var/www/blog/public/` 目录。

    *   **步骤 2.3: (提交) 将构建结果提交到部署仓库**
        *   **目的**: 将新生成的网站文件作为一次“部署”提交。
        *   **后台命令**:
            1.  `cd /var/www/blog/public`
            2.  `git add .`
            3.  `git commit -m "Deploy site on [当前时间]"`

    *   **步骤 2.4: (推送) 将部署提交推送到 GitHub**
        *   **目的**: 触发 GitHub Pages 的自动部署，更新线上网站。
        *   **后台命令**: 在 `/var/w​​ww/blog/public/` 目录执行 `git push origin deploy-branch`。

    *   **步骤 2.5: (同步) 更新主仓库的子模块指针**
        *   **目的**: 在主仓库 (`/var/w​​ww/blog`) 中记录 `public` 子模块的最新 commit ID，确保两个仓库状态的完全同步。
        *   **后台命令**:
            1.  `cd /var/www/blog`
            2.  `git add public`
            3.  `git commit -m "Update submodule pointer for public"`
            4.  `git push`

#### **第三阶段：发布后验证**

1.  **我的主动操作 (无需您指令)：** `blog_publish` 推送完成后，为了确保任务万无一失，我会立刻执行验证。
2.  **验证方法**:
    *   **方法一 (检查Git)**: 我会检查 `/var/w​​ww/blog/public` 的 Git 日志，确认最新的 "Deploy site" 提交已经成功推送到远程。
        *   **工具调用**: `default_api.run_shell(command='git log -n 1', cwd='/var/w​​ww/blog/public')`
    *   **方法二 (检查线上内容)**: 我会使用 `curl` 命令访问 `https://caozuohua.github.io`，并通过 `grep` 查找新文章的标题。如果能找到，则证明 GitHub Pages 已成功构建并上线了新版本。
        *   **工具调用**: `default_api.run_shell(command='curl -s https://caozuohua.github.io/ | grep "新文章标题"')`
3.  **最终报告**: 我会向您报告：“博客发布成功，线上已可访问。最新的部署提交是 [Commit ID]。”

---

这个经过梳理和确认的流程，将所有必要的步骤和前置检查都固化下来，形成了一个可靠的自动化操作。我将严格遵守此流程，确保未来每一次发布都高效、精准且一次成功。
