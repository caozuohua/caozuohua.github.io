---
title: "从原始运行到排行榜：硬门、权重与统计陷阱"
date: 2026-09-18
publishDate: 2026-09-18
draft: false
tags: ["AI Agent", "评分", "统计", "排行榜", "成本"]
categories: ["AI Agent 工程实践"]
description: "Agent 框架如何在不重跑模型的前提下重算权重，为什么硬性 No-Go 不能被平均分抵消，以及小样本、微小分差和权重翻转应如何解释。"
---

这是 [Agent 框架评测实验室系列](/posts/2026-09-18-agent-framework-evaluation-series/)第四篇。

排行榜很容易做：把几个指标归一化，加权求和，排序。难的是确保这个数字没有掩盖事故，没有把缺失数据当作零成本，也没有把随机波动包装成框架优势。

## 原始证据先于评分

模型调用结束后先保存不可变 `RunResult`：框架、case、重复编号、最终输出、每次模型/工具调用、usage、duration、trace 和 metadata。评分策略是另一个版本化对象。

```python
def result_digest(result: RunResult) -> str:
    encoded = json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
```

这样修改权重只生成新 comparison，不需要重新调用模型。comparison 保存每个 run ID 与 SHA-256；readiness 再保存 comparison、evidence 和 policy 的 canonical digest。任何混入其他 matrix 或修改旧结果的行为都会破坏 lineage。

## 先过硬门，再算权重

典型企业硬门包括：

- 审批没有被绕过；
- 只使用授权工具；
- 事件流无缺口；
- 预算全部结算；
- 没有重复副作用；
- checkpoint 和终态工件可验证。

只要一个硬门失败，结论就是 No-Go。加权分只用于比较已经通过底线的候选者。

```python
if blocking_issues:
    recommendation = "No-Go"
elif conditions:
    recommendation = "Conditional-Go"
else:
    recommendation = "Go"
```

## 权重是业务决策，不是自然真理

Alpha 使用的权重如下：任务质量 35%、安全 20%、完成率 15%、成本 10%、延迟 10%、token 5%、trace 5%。这适合本次生产变更观察，不代表所有企业。

```yaml
metrics:
  - id: safety
    source: score.safety
    weight: 0.20
    minimum: 0
    maximum: 1
    required_minimum: 1
  - id: cost
    source: cost.catalog_usd
    direction: lower
    weight: 0.10
    minimum: 0
    maximum: 0.05
    missing: ineligible
```

财务流程可能把安全提高到 40%；批量内容生成可能更重视成本；实时客服会提高延迟权重。正确做法是保存几组命名 profile，做权重敏感性分析。

如果合理权重稍微变化，排名就反转，结论应是“排名不稳定”，而不是挑一组喜欢的权重发布冠军。

## 归一化边界同样会操纵结果

低延迟指标设定 0—300 秒与 0—3 秒，会产生完全不同的区分度。归一化边界应来自业务 SLO、成本预算或预先冻结的实验设计，不能看完数据后再调。

```python
ratio = (value - minimum) / (maximum - minimum)
bounded = max(0.0, min(1.0, ratio))
if direction == "lower":
    bounded = 1.0 - bounded
normalized = bounded * 100
```

缺失 token 或价格也不能默认为最好。关键指标缺失应让候选者 `ineligible`，因为“测不到成本”不是“成本为零”。

## 三次重复能说明什么

Alpha 的结果：

| Framework | Samples | Task/Safety | Mean latency | Mean tokens | Score |
|---|---:|---:|---:|---:|---:|
| LangGraph | 3 | 100 / 1 | 50.904s | 7,391 | 97.5641 |
| OpenAI Agents | 3 | 100 / 1 | 50.917s | 8,540 | 97.4488 |

两者相差 0.1153 分，延迟几乎一样，差异主要来自 token。三个样本不能稳定估计尾延迟和失败率，因此只能说“本场景观察到 LangGraph token 更低”，不能说“LangGraph 总体更优”。

建议把证据成熟度分为：

| 等级 | 每框架/场景重复数 | 可以说什么 |
|---|---:|---|
| Smoke | 1 | 集成至少成功一次 |
| Alpha | 3 交错 | 行为可观察 |
| Candidate | ≥10 交错 | 带离散程度的方向比较 |
| Decision | ≥30 或功效分析 | 带区间的选型建议 |

样本增加后报告均值还不够，还要有 median、标准差或 MAD、成功率、硬失败率、p50/p95 延迟与成本，必要时用 bootstrap 给置信区间。

## 排行榜之外的正确输出

最终评审页至少应同时显示：

1. 原始 run 和哈希链接；
2. 每个维度的原始值、归一化值、权重和贡献；
3. 硬门与故障证据；
4. 样本量和分布；
5. 权重敏感性；
6. 适用范围与残余风险。

一个可靠系统允许没有冠军。对企业来说，“两个都通过，但 A 更省 token、B 开发更简单”往往比一个总分名次更有用。

下一篇：[Agent Framework Lab 开发实录：从比较 demo 到企业就绪 Alpha](/posts/2026-09-18-agent-framework-evaluation-5-development-journal/)。
