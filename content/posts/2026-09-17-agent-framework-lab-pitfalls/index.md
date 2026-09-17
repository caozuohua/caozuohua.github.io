---
title: "Agent 框架开发与评测踩坑实录：从能跑到可审计、可比较"
date: 2026-09-17T18:00:00+08:00
draft: false
tags: ["AI Agent", "Agent Framework", "LangGraph", "OpenAI Agents", "评测", "可靠性"]
categories: ["AI Agent 工程实践"]
description: "Agent Framework Lab V2 RC 的工程复盘：耐久运行时、审批、崩溃恢复、工具幂等、模型成本、可注入任务和加权横向评测中，真正容易出错的地方，以及可以直接复用的代码。"
lastmod: 2026-09-17
---

很多 Agent demo 的成功标准是：“模型能调用工具，最后返回一个答案。”

但只要把它放进真实系统，问题马上变成另一组问题：任务执行到一半进程崩了怎么办？审批通过的到底是哪一次工具调用？工具重试会不会重复扣款？两个框架比较时，是否真的使用了同一份提示词和工具？模型价格变化后，旧实验的排名还能不能复算？

我在 Agent Framework Lab V2 RC 中把这些问题做成了一个可以运行、恢复、审计和比较的实验台。本文不讲“Agent 很有前景”，只记录实现过程中最容易被低估的坑、最终采用的设计，以及可以直接复制的代码片段。

## 先给结论：Agent 评测是一条证据链

可信的评测结果必须能回答：这次运行用了哪个框架、模型、provider、提示词和工具？模型调用、工具调用、审批、checkpoint 的顺序是什么？崩溃或重启后哪些动作被恢复，哪些动作绝不能重放？结果怎么评分？换一组权重后能否只重算排名？排名是否因为 ground truth 写错了？

因此数据流不是：

```text
prompt -> model -> score
```

而是：

```text
任务契约 + 模型契约 + 工具契约
                ↓
      append-only 运行事件
                ↓
     不可变 RunResult 原始证据
                ↓
       可重算的 ScoreProfile
                ↓
       排名、图表和审计报告
```

## 坑一：把“任务成功”和“评分高”混成一件事

一次运行可能在运行时层面成功完成，但答案质量只有 60 分；反过来，一个答案看起来不错，也不能掩盖未授权工具调用、预算超限或事件账本损坏。

Lab 将两者拆开：

```python
class RunResult(BaseModel):
    run_id: str
    matrix_id: str
    framework: str
    case_id: str
    status: Literal["completed", "failed", "blocked_gateway_contract", "unavailable"]
    final_output: str = ""
    tool_calls: list[ToolCallRecord] = []
    model_calls: list[ModelCallRecord] = []
    usage: Usage = Usage()
    score: Score | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = {}
```

`status == completed` 只表示执行器完成生命周期；`score.total` 是评测器对结果的判断。模型返回错误 JSON 时，运行可以成功但结构化输出为 0；预算结算失败时，即使模型输出正确，也必须判为运行时失败；评分规则改变时，可以重算分数，但不能重写原始执行状态。

## 坑二：普通日志不够，必须有可验证的事件账本

`print("tool called")` 不是可靠性设计。真实运行至少要持久化全局递增的 event sequence、job/attempt/lease 三层身份、预算 reservation 与 settlement、工具 operation ID、checkpoint 工件 SHA-256，以及最终输出工件 SHA-256。

一个最小的 append-only 约束：

```python
def append(self, job_id: UUID, expected_revision: int,
           events: list[RuntimeEvent]) -> Snapshot:
    current = self.snapshot(job_id)
    if current.revision != expected_revision:
        raise StateConflict("revision mismatch")

    for event in events:
        event.sequence = current.revision + 1
        self._validate_transition(current, event)
        current = reduce_snapshot(current, event)

    self._write_transactionally(job_id, events, current)
    return current
```

三个不变量：revision 不匹配时拒绝写入；状态先经 reducer 验证；事件和快照在同一事务中落盘。RC 观察期的 14 个历史 Job 全部通过审计：事件流无缺口、预算 reservation 为 0，所有存在的 checkpoint 和终态工件均通过哈希验证。

## 坑三：崩溃恢复最怕重复副作用

假设 Agent 已调用“提交订单”，刚好在返回结果前崩溃。恢复时从上一个 prompt 重新跑，可能再次提交订单。

```text
可重放：模型推理、只读检索、纯计算
不可盲目重放：写文件、更新任务板、付款、提交订单
```

checkpoint 不能只保存最后一条消息，而要保存能继续执行的协议状态：

```python
checkpoint = {
    "stage": "before-protected-submit",
    "pending_operation_id": str(operation_id),
    "tool_name": "protected_submit",
    "arguments_sha256": arguments_digest,
}
```

恢复流程是：验证 checkpoint 工件、清理孤儿 attempt 和未结算 reservation、从 checkpoint stage 申请新 lease、只继续未完成的协议阶段。已成功的外部副作用不得再次执行。测试中模拟 host crash 后，研究工具没有被重复调用，最终工件仍能审计。

## 坑四：审批必须绑定“精确意图”

“允许 `protected_submit`”不是安全审批，因为同一工具可以提交不同金额和参数。审批对象至少绑定 job、attempt、operation、action、参数摘要、审批人、decision 和 revision：

```python
class ApprovalDecision(BaseModel):
    approval_id: UUID
    job_id: UUID
    operation_id: UUID
    decision: Literal["approved", "rejected"]
    approver_id: str
    action: str
    arguments_sha256: str
```

恢复前重新校验这些字段。任何字段不匹配都不能继续执行；拒绝的审批不能通过换一个 approval ID 绕过；revision 过期必须重新申请。RC 测试覆盖了审批通过、审批拒绝和审批后恢复。

## 坑五：工具幂等键必须绑定请求内容

幂等键不是“随便生成一个 UUID”。同一个 key 换参数必须被拒绝：

```sql
CREATE TABLE tool_receipts (
    idempotency_key TEXT PRIMARY KEY,
    request_sha256  TEXT NOT NULL,
    output_json     TEXT NOT NULL
);
```

```python
request_json = json.dumps(
    {"name": name, "arguments": arguments},
    ensure_ascii=False, separators=(",", ":"), sort_keys=True,
)
digest = sha256(request_json.encode()).hexdigest()
old = select_receipt(idempotency_key)
if old:
    if old.request_sha256 != digest:
        raise RuntimeError("idempotency key reused with different arguments")
    return json.loads(old.output_json), True
```

测试必须跨 runtime 实例或跨进程执行。Lab 覆盖了 SQLite 重启后收据仍有效，以及同 key 换参数会失败。

## 坑六：子进程协议不能只传最终 JSON

Agent 框架通常跑在隔离的 subprocess 中。只让子进程最后打印一个结果，会丢失中间状态，也无法安全地做预算结算。

Lab 使用带序号的 frame 协议，把意图和结算分开：

```json
{
  "kind": "intent",
  "frame_sequence": 12,
  "event": {
    "event_type": "tool.requested",
    "operation_id": "op-123",
    "payload": {
      "name": "protected_submit",
      "arguments": {"amount_usd": 125},
      "idempotency_key": "job-1:op-123"
    }
  },
  "reservation": {"reservation_id": "res-456", "amount": {"tool_calls": 1}}
}
```

父进程收到并验证 intent 后才接受 reservation；工具完成后再发 settlement。协议不完整时必须 fail closed。

## 坑七：免费模型也需要成本与节流模型

“免费”不等于“没有预算问题”。免费网关仍然有每日配额、请求间隔限制、429/502/503/504、调用次数上限，以及 token 统计不完整等问题。

```python
result.metadata.update({
    "model_provider": model.provider,
    "pricing_catalog": pricing.name,
    "pricing_catalog_sha256": contract_digest(pricing),
    "catalog_cost_usd": catalog_cost(result, pricing),
})
```

付费模型执行前计算 worst-case cost：

```python
worst_case = max_model_calls * (
    (max_input_tokens * input_rate
     + max_output_tokens * output_rate
     + max_output_tokens * reasoning_rate) / 1_000_000
    + request_rate
)
if worst_case > max_cost_usd:
    raise PermissionError("worst-case cost exceeds run budget")
```

遇到缺价格不能把成本当成 0。缺价格默认应该是 `ineligible`。

## 坑八：ground truth 错误，比模型幻觉更容易被忽略

RC 观察中，我把 7 件库存商品的期望价格写成了 55.5、总价写成 388.5；确定性工具实际返回单价 129.5。LangGraph 正确调用工具并算出 906.5，却因错误 ground truth 得到 80 分。

这条运行没有被覆盖，而是保留为审计证据，然后创建 v2 任务契约修正期望值。这说明任务定义必须和原始结果一起版本化，评分错误不能靠重新跑一次掩盖，报告还应区分模型失败和评测数据错误。

声明式 evaluator 的最小安全模型：

```python
class DeclarativeEvaluator(BaseModel):
    output: dict[str, Any] = {}
    output_mode: Literal["subset", "exact"] = "subset"
    required_tools: list[str] = []
    forbidden_tools: list[str] = []
    allow_tool_errors: bool = False
```

它允许自定义任务，但不允许用户把任意 Python scorer 注入执行进程。

## 坑九：先保存原始结果，再做可重算的加权评分

如果评分和运行绑定，就无法回答“质量权重从 70% 改成 40% 后排名如何”。重新调用模型又会引入新的随机性和网关状态。

ScoreProfile 是独立策略对象：

```yaml
schema_version: 1
name: balanced-v1
group_by: [framework]
minimum_samples: 1
require_all_completed: true
metrics:
  - id: quality
    source: score.total
    direction: higher
    weight: 0.55
    minimum: 0
    maximum: 100
  - id: cost
    source: cost.catalog_usd
    direction: lower
    weight: 0.10
    minimum: 0
    maximum: 0.05
    missing: ineligible
```

归一化和加权保持纯函数：

```python
def normalize(value: float, rule: MetricRule) -> float:
    bounded = max(0, min(1, (value - rule.minimum)
                          / (rule.maximum - rule.minimum)))
    if rule.direction == "lower":
        bounded = 1 - bounded
    return bounded * 100

weighted_points = normalized * rule.weight / total_weight
```

报告保存 `score_profile_sha256`、`pricing_catalog_sha256` 和每个 `result_sha256`。换权重只会生成新的比较视图，不会重新调用模型：

```bash
uv run agent-lab compare \
  --matrix 20260917T083911Z-d5c844 \
  --score-profile config/score-profiles/balanced-v1.yaml \
  --pricing config/pricing/free-glm-v1.yaml
```

## 坑十：公平比较的关键是固定变量

框架横评很容易变成“每个框架各写一套 prompt、工具包装和输出解析”，这样比较的其实是 harness，不是框架。

| 变量 | 要求 |
| --- | --- |
| 任务 | 同一份 case YAML 和版本号 |
| 提示词 | 同一原始 prompt，框架包装必须可记录 |
| 工具 | 同一工具目录、参数和确定性数据 |
| 模型 | 同一 provider/model/temperature/token limit |
| 成本 | 同一份带生效时间的价格表 |
| 重复 | 交错执行，避免先跑的框架独占网关状态 |
| 评分 | 保存原始结果后用同一 ScoreProfile 重算 |

修正后的共享 Matrix 使用 `glm-4.5-air` 和同一外部任务：

| Framework | Task score | Duration | SDK tokens | Calls | Weighted score |
| --- | ---: | ---: | ---: | ---: | ---: |
| LangGraph 1.2.9 | 100 | 18.706s | 1,262 | 3 model / 2 tool | 99.2503 |
| OpenAI Agents 0.18.3 | 100 | 18.663s | 1,442 | 3 model / 2 tool | 99.2337 |

差距只有 0.0166 分，主要来自 token 指标。一次重复不能宣称框架胜负，至少要运行交错的三次或更多，并报告均值、离散程度和失败样本。

## 坑十一：自定义工具和自定义任务不是同一个难度

自定义 prompt、case ID、输出期望和工具子集，可以用严格 YAML 契约安全实现。自定义工具实现则会引入任意代码执行、网络和文件系统权限、凭据访问、工具版本漂移、结果不可重复以及外部副作用恢复问题。

因此 RC 只允许外部任务组合预置工具：

```text
外部 YAML -> 严格解析 -> 预置工具 catalog 校验 -> 隔离 ToolRuntime
```

GA 之前应该增加签名 manifest、权限声明、输入输出 schema、side-effect class、幂等能力和沙箱启动方式；不能把 `python: import os` 作为“灵活评测插件”。

## 坑十二：备份恢复不能只复制数据库文件

SQLite 只保存索引和事件，checkpoint、最终结果和大输出通常在 artifact store。只备份 `runtime.db`，可能得到“状态 succeeded，但终态工件不存在”的假成功。

```python
with sqlite3.connect(source_db) as src, sqlite3.connect(backup_db) as dst:
    src.backup(dst)

shutil.copytree(source_artifacts, backup_artifacts)

restored = RuntimeOperator(backup_db, backup_artifacts)
for job in restored.list():
    audit = restored.audit(job.job_id)
    assert audit["gap_free"]
    assert audit["outstanding_reservations"] == 0
    assert audit["terminal_artifact_verified"] is not False
    assert audit["checkpoint_verified"] is not False
```

本次演练中，14 个 Job 的 `(job_id, revision, status)` 在恢复副本中完全一致，所有审计均通过。

## 最终建议：先把评测台做成证据系统，再做排行榜

稳妥的发布顺序是：冻结任务、工具、模型和价格契约；确保事件、预算和工件可审计；对审批、取消、崩溃和重启做故障注入；保存不可变原始结果；用可重算权重生成比较视图；最后才做排行榜和可视化。

Lab V2 RC2 可以作为受控单机 RC 继续观察，还不能称为 GA。当前 GA 门槛包括任意自定义工具的隔离插件协议、交互式可视化、多次重复统计、ground truth preflight，以及 Windows live recovery、备份自动化、签名/SBOM 和多 worker 协调。

项目实现和测试代码见 [agent-framework-lab](https://github.com/caozuohua/agent-framework-lab)，RC2 观察报告见 [validation-2026-09-17-rc-observation.md](https://github.com/caozuohua/agent-framework-lab/blob/agent/deep-dive-v1/docs/validation-2026-09-17-rc-observation.md)。
