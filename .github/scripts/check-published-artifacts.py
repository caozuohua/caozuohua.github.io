#!/usr/bin/env python3
"""构建产物断言：每一篇「按语义应当公开」的文章，都必须真的产出 HTML。

背景
----
本仓库历史上多次出现「CI 构建绿色 + 部署绿色，但线上 404」。根因是 Hugo 默认
buildFuture=false：date / publishDate 晚于构建时刻的文章会被**静默排除**，
既不报错也不警告。构建成功因此不等于内容上线。

这个脚本把那种静默失败显式化：
  - 对每篇内容，取其生效日期（优先 publishDate，否则 date）
  - 若生效日期 <= 当前时刻，则该文**应当**已发布 → 断言 public/posts/<slug>/index.html 存在
  - 若生效日期 > 当前时刻，则按设计被排除 → 记为 SKIP，不算失败
  - 任一「应当发布却缺产物」→ 打印清单并 exit 1，构建即红灯

用法（在 Hugo 构建之后执行）：
    python3 .github/scripts/check-published-artifacts.py
"""
import datetime
import os
import re
import sys

CONTENT_DIR = "content/posts"
PUBLIC_DIR = os.path.join("public", "posts")


def read_front_matter(path):
    """返回 front matter 文本；文件不以 --- 开头则返回 None。"""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("  ! 无法读取 %s: %s" % (path, exc))
        return None
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    return m.group(1) if m else None


def get_effective_date(fm, slug):
    """取生效日期，模拟 Hugo 的日期解析链。

    顺序与 Hugo 默认 frontmatter 配置一致：date → publishDate → 文件名。
    注意最后一项不可省：本站存在 `2026-08-11-playwright-ai-agent-part4`
    这类**没有 front matter**、日期只写在文件名里的文章，而 Hugo 会从
    文件名提取日期并正常发布。漏掉这条回退会误报为构建失败。
    返回 (datetime 或 None, 原因说明)。
    """
    if fm is not None:
        for key in ("publishDate", "date"):
            m = re.search(r"^%s:\s*(.+)$" % key, fm, re.M)
            if not m:
                continue
            raw = m.group(1).strip().strip("\"'")
            dt = parse_datetime(raw)
            if dt is None:
                return None, "%s 无法解析: %s" % (key, raw)
            return dt, "%s=%s" % (key, raw)

    # 回退：从文件名/slug 前导的 YYYY-MM-DD 取日期
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", slug)
    if m:
        dt = parse_datetime(m.group(1))
        if dt is not None:
            return dt, "文件名=%s" % m.group(1)

    return None, "无可用日期（front matter 与文件名均未提供）"


def parse_datetime(raw):
    """解析 ISO 日期或日期时间；纯日期按 UTC 处理（与 Hugo 行为一致）。"""
    try:
        if "T" in raw:
            dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.datetime.fromisoformat(raw + "T00:00:00+00:00")
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def collect_articles():
    """遍历 content/posts，产出 (slug, front_matter_path)。

    同时支持两种约定：
      - 目录型 bundle：content/posts/<slug>/index.md
      - 散落单文件：  content/posts/<slug>.md
    """
    if not os.path.isdir(CONTENT_DIR):
        print("! 找不到内容目录 %s" % CONTENT_DIR)
        sys.exit(1)
    for entry in sorted(os.listdir(CONTENT_DIR)):
        path = os.path.join(CONTENT_DIR, entry)
        if entry.endswith(".md"):
            yield entry[:-3], path
        elif os.path.isdir(path):
            index = os.path.join(path, "index.md")
            if os.path.exists(index):
                yield entry, index


def main():
    if not os.path.isdir(PUBLIC_DIR):
        print("! 找不到产物目录 %s —— 构建步骤可能失败了" % PUBLIC_DIR)
        sys.exit(1)

    now = datetime.datetime.now(datetime.timezone.utc)
    print("构建产物断言 @ %s" % now.isoformat())

    published, skipped, missing, unparsable = [], [], [], []

    for slug, md_path in collect_articles():
        fm = read_front_matter(md_path)
        dt, raw = get_effective_date(fm, slug)
        if dt is None:
            unparsable.append((slug, raw))
            continue
        if dt > now:
            skipped.append((slug, raw))
            continue
        published.append(slug)
        out = os.path.join(PUBLIC_DIR, slug, "index.html")
        if not os.path.exists(out):
            missing.append((slug, raw))

    for slug, raw in skipped:
        print("  SKIP (未到生效时间)  %-52s %s" % (slug, raw))
    print("  应当发布: %d 篇 | 按设计跳过: %d 篇" % (len(published), len(skipped)))

    if unparsable:
        print("\n无法判定生效日期（需人工确认，按失败处理）:")
        for slug, why in unparsable:
            print("  ? %-52s %s" % (slug, why))

    if missing or unparsable:
        print("\n断言失败：以下文章应当已发布，但产物不存在")
        for slug, raw in missing:
            print("  FAIL %-52s %s" % (slug, raw))
        print("\n排查提示：CI 绿色但此处失败，最可能是日期陷阱；")
        print("本地可跑 `hugo list future` 列出被日期排除的页面。")
        sys.exit(1)

    print("OK: 全部应当发布的文章均已产出 index.html")


if __name__ == "__main__":
    main()
