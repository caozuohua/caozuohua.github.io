---
title: "一次由 can't evaluate field locale 引发的 Hugo 构建“血案”"
date: 2026-05-10T00:32:08+08:00
draft: false
tags: ["Hugo", "Debugging", "Troubleshooting"]
---

本文是一篇详细的故障排查实录。作者记录了一次解决 Hugo 博客构建过程中遇到的 `can't evaluate field locale` 错误的完整过程。从错误的表象出发，一步步深入排查，涉及 Hugo 的版本、主题的兼容性、以及 Hugo Modules 的工作机制等多个方面。最终，通过隔离变量、大胆假设、小心求证，定位并解决了问题。文章不仅提供了解决方案，更展示了一种科学的问题排查思路，对于所有 Hugo 用户来说都有很高的参考价值。