---
title: "Agent 技能解剖（二）：Ontology——用 schema 管住模型的不确定性"
date: 2026-09-28T21:10:00+08:00
publishDate: 2026-09-28T21:10:00+08:00
description: "装机量 29,080 的 Ontology 技能源码级拆解：追加式 JSONL 事件日志 + 重放的本质是事件溯源；schema.yaml 把可枚举的一致性检查从模型手里拿走。逐条核对了六类约束的真实实现覆盖度，指出文档承认的『仅文档级约束』边界，并给出把安全策略编码进数据模型而非提示词的方法。"
tags: ["AI Agent", "Prompt Engineering", "技能解剖", "知识图谱"]
categories: ["技术分享"]
draft: false
---

# Agent 技能解剖（二）：Ontology——用 schema 管住模型的不确定性

> 上一篇讲 Agent Memory，结论是「把记忆做成数据层」。但数据层有一个自带的问题：**数据一旦自由生长，就查不动、也信不过。**
> 这一篇讲那个问题的解法：给记忆加一层类型系统与约束校验。

## 问题的真正形态

用自然语言存储记忆，会遇到三类麻烦，而且它们都不会立刻暴露：

1. **形态漂移**。「项目」「Project」「project」是同一个东西；「进行中」「in progress」「active」也是同一个状态。写入时没人觉得有问题，三个月后查询时全都查不全。
2. **关系丢失**。「张三负责官网改版」这句话，在纯文本记忆里就是一句话。你没法问「张三还负责什么」，只能全文搜「张三」，然后自己读。
3. **无校验**。模型写下「会议结束时间早于开始时间」，存储层照单全收，没有任何环节会拒绝它。

`Ontology` 这个技能给出的答案是教科书式的：**因为语言是不确定的，那就不要再让语言承担一致性保证——把它压缩成「实体 + 类型 + 属性 + 关系」，然后用 schema 去校验。**

## 技能档案

| 项 | 值 |
|---|---|
| 技能名 | ontology |
| slug | `ontology` |
| 作者 | oswalpalash |
| 版本 | 1.0.4 |
| 下载量 | 286,820 |
| 安装量 | 29,080 |
| 星标 | 787 |
| 来源 | ClawHub |
| 存储介质 | `memory/ontology/graph.jsonl`（追加式）+ `memory/ontology/schema.yaml` |
| 入口 | `scripts/ontology.py`（create / get / query / list / update / delete / relate / related / validate / schema-append） |

数据抓取于 2026-09-28，口径为 SkillHub 聚合榜。

## 数据模型：只有两个结构

整个技能的数据模型可以压成两行：

```
Entity:   { id, type, properties, relations, created, updated }
Relation: { from_id, relation_type, to_id, properties }
```

内置类型覆盖了个人助理场景的绝大部分需求：

| 域 | 类型 |
|---|---|
| 人与组织 | `Person`、`Organization` |
| 工作 | `Project`、`Task`、`Goal` |
| 时空 | `Event`、`Location` |
| 信息 | `Document`、`Message`、`Thread`、`Note` |
| 资源 | `Account`、`Device`、`Credential` |
| 元 | `Action`、`Policy` |

注意 `Credential` 的定义：`{ service, secret_ref }`，并配了一条注释「**Never store secrets directly**」。这不是一句提醒，而是被 schema 强制执行的——后面会看到它怎么做到。

## 存储是事件日志，不是状态表

这是本技能最值得学的一点，而且它藏在实现里，SKILL.md 只用「Append-Only Rule」轻描淡写地带过。

`graph.jsonl` 的每一行是一条**操作记录**，而不是一条数据：

```jsonl
{"op":"create","entity":{"id":"p_001","type":"Person","properties":{"name":"Alice"}},"timestamp":"..."}
{"op":"create","entity":{"id":"proj_001","type":"Project","properties":{"name":"Website Redesign","status":"active"}},"timestamp":"..."}
{"op":"relate","from":"proj_001","rel":"has_owner","to":"p_001","properties":{},"timestamp":"..."}
```

读的时候靠 `load_graph()` 从头重放，得到当前状态：

```python
if op == "create":   entities[entity["id"]] = entity
elif op == "update": entities[entity_id]["properties"].update(record.get("properties", {}))
elif op == "delete": entities.pop(entity_id, None)
elif op == "relate": relations.append({...})
elif op == "unrelate": relations = [r for r in relations if not (…same triple…)]
```

这套设计有个正式名字：**事件溯源（Event Sourcing）**。它带来的性质正好命中前面那三类麻烦：

| 性质 | 含义 |
|---|---|
| 可审计 | 任何一条数据的来源与时间都在日志里，删不掉 |
| 可回滚 | 想撤销一次误操作，只需追加一条反向 op，历史不动 |
| diff 友好 | 纯文本行，版本控制里读得懂 |
| 失败安全 | 写操作是纯追加，不存在「改到一半崩了」的半状态 |
| 恢复简单 | 状态是日志的推导结果，日志在，状态就永远不会丢 |

代价也很实在：**每次读取都要全量重放**，复杂度 O(日志行数)。SKILL.md 自己给了升级路径——「For complex graphs, migrate to SQLite」。也就是说这个文件格式适合**数百到数千条**规模，再往上就该换存储引擎了。把它当成「原型期的正确起点」来看待，而不是终态。

## schema.yaml：把可校验的部分拿走

这是全技能的第二个核心。约束写在 `memory/ontology/schema.yaml`：

```yaml
types:
  Task:
    required: [title, status]
    status_enum: [open, in_progress, blocked, done]

  Credential:
    required: [service, secret_ref]
    forbidden_properties: [password, secret, token]

relations:
  has_owner:
    from_types: [Project, Task]
    to_types: [Person]
    cardinality: many_to_one

  blocks:
    from_types: [Task]
    to_types: [Task]
    acyclic: true
```

四种约束维度各司其职：

- `required` 解决**必填**；
- `xxx_enum` 解决**形态漂移**——状态只能是四个确定值中的一个，模型没法自由发挥；
- `forbidden_properties` 解决**安全**——`Credential` 上禁止出现 `password` / `secret` / `token`，逼你把真实密钥放到外部引用（`secret_ref`）里；
- `relations` 约束解决**结构性错误**——`has_owner` 的 from 只能是 Project 或 Task、to 只能是 Person；`cardinality: many_to_one` 表示一个项目只能有一个负责人；`blocks: acyclic` 表示任务依赖不能成环。

`forbidden_properties` 这一条尤其值得展开。它示范了一种和「在 prompt 里写『不要把密钥写进记忆』」完全不同的思路：

> **提示词是一种请求，schema 是一种拒绝。**

写在 prompt 里的安全规则，靠模型每轮自觉遵守，且随着上下文变长而衰减；写在 schema 里的安全规则，由 `validate` 命令在写入后检查，**违反就报错**，与模型状态无关。前者的失效是静默的，后者的失效是吵的。安全相关的约束，永远应该选后者。

## 约束覆盖度审计：文档说的和代码做的

到这里必须做一件事：**逐条核对 schema 里能声明的约束，代码是否真的实现了。** 因为「声明了但没人校验」的约束，比没有约束更危险——它会让人误以为有保护。

`validate_graph()` 的实际实现：

| 约束 | 实现状态 | 实现方式 |
|---|---|---|
| `required`（必填属性） | ✅ 已实现 | 遍历实体检查属性存在性 |
| `forbidden_properties`（禁用属性） | ✅ 已实现 | 遍历实体检查禁用键 |
| `*_enum`（枚举值） | ✅ 已实现 | 键名以 `_enum` 结尾即按枚举校验 |
| 关系两端类型 `from_types` / `to_types` | ✅ 已实现 | 校验实体类型是否在允许列表内 |
| 关系基数 `cardinality` | ✅ 已实现 | 按 from / to 计数，`one_to_one` / `one_to_many` / `many_to_one` 均检查 |
| 关系无环 `acyclic` | ✅ 已实现 | DFS 检测环，发现即报 `cyclic dependency detected` |
| `Event` 的 `end >= start` | ✅ 已实现（特例硬编码） | 仅对 `type == "Event"` 生效 |
| **其他全局 `constraints` 声明** | ❌ **未实现** | 代码里只有上述 Event 特例；SKILL.md 自己承认：other higher-level constraints **may still be documentation-only** |

这张表本身就说明了一个通用规律：**声明式约束的表达力，总是大于实现方的覆盖度。** YAML 里可以写出任何你想要的规则，但校验代码只会实现其中一部分。所以引入任何 schema 系统时，都应该先做一次这样的覆盖度对账，否则你会得到一种「看起来有护栏」的错觉。

顺带注意 `acyclic` 的实现细节：它只对**声明了 `acyclic: true` 的关系**做环检测，且检测范围是这一类关系的子图。所以「任务 A 阻塞任务 B、B 阻塞 A」会被抓到，但跨关系类型的环（A blocks B，B for_event E，E …）不会。约束的作用域永远比直觉窄。

## 安全工程：路径穿越

除了 prompt 注入，Agent 技能的第二个风险面是**文件路径**。这个技能里有一段很干净的实现：

```python
def resolve_safe_path(user_path, *, root=None, must_exist=False, label="path"):
    safe_root = (root or Path.cwd()).resolve()
    candidate = Path(user_path).expanduser()
    if not candidate.is_absolute():
        candidate = safe_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(safe_root)      # 关键：解析后必须仍在工作区根内
    except ValueError:
        raise SystemExit(f"Invalid {label}: must stay within workspace root '{safe_root}'")
```

三个要点：先 `resolve()` 把 `..` 与符号链接展开，**再**做 `relative_to` 归属校验；`root` 固定为工作区根；所有接受路径的子命令（`--graph` / `--schema` / `--file`）统一走这个函数。

为什么必须「先解析再校验」？因为 `../../etc/passwd` 这种字符串在未解析状态下看不出问题，只有展开成绝对路径后才能判断它是否越界。**任何允许模型指定文件路径的技能，都应该有这个函数。**

## 跨技能共享状态：Skill Contract

这是本技能最有前途、也最容易被忽略的设计。SKILL.md 建议调用方在自己的 frontmatter 里声明契约：

```yaml
ontology:
  reads: [Task, Project, Person]
  writes: [Task, Action]
  preconditions:
    - "Task.assignee must exist"
  postconditions:
    - "Created Task has status=open"
```

意义在于：**它把技能之间的耦合从「约定」变成了「声明」。**

想象一个邮件技能从邮件里抽出承诺，任务技能再把承诺转成任务。没有契约时，两者的数据交换靠字符串约定；有了契约，`ontology.create("Commitment", {...})` 写在图里、`ontology.query("Commitment", {"status": "pending"})` 读出来，中间不需要知道对方存在。

这就是「用图做中间层」相对「用文件做中间层」的实质差别：文件是**格式契约**，图是**语义契约**。

## 把计划写成图操作

技能的最后一节给出了一种颇有启发性的用法——把多步计划直接建模为图变换序列：

```
Plan: "Schedule team meeting and create follow-up tasks"

1. CREATE Event { title: "Team Sync", attendees: [p_001, p_002] }
2. RELATE Event -> has_project -> proj_001
3. CREATE Task  { title: "Prepare agenda", assignee: p_001 }
4. RELATE Task -> for_event -> event_001
5. CREATE Task  { title: "Send summary", assignee: p_001, blockers: [task_001] }
```

> Each step is validated before execution. Rollback on constraint violation.

这个思路的价值在于：**计划不再是模型脑内的一段文本，而是一串可校验的操作。** 第 3 步引用了 `p_001`——如果这个人在图里不存在，校验当场失败，你不会等到执行完三步之后才发现指派给了一个不存在的人。

这与后两篇要讲的自我改进机制形成互补：Self-Improving Agent 管的是**行为规则**的沉淀，Ontology 管的是**事实与关系**的一致性。

## 失效模式清单

| 失效模式 | 触发条件 | 后果 |
|---|---|---|
| 全量重放开销 | 图规模增长到数千条以上 | 每次查询线性变慢 |
| 类型名漂移 | 模型传入 `task` 而非 `Task` | 校验静默跳过（schema 里查不到该类型，不报错） |
| schema 无版本管理 | 多人/多会话改动 schema | 旧数据在新 schema 下校验失败 |
| 「仅文档级」约束 | 依赖 SKILL.md 里写了但代码没实现的规则 | 误以为有护栏 |
| 单文件并发写 | 多个 agent 同时追加 | 行交错 / 写入竞争 |
| 无身份校验 | 任意实体 id 可被引用 | 关系指向不存在的实体（`validate` 能抓到，但不会阻止写入） |
| 无索引 | 按属性查询需遍历全图 | 大图查询退化 |

第 2 条特别隐蔽：`validate_graph()` 里 `type_schemas.get(type_name, {})` 取了默认空字典，所以**schema 里没有定义的类型不会被报错，而是被完全跳过校验**。模型只要把 `Task` 写成 `Task ` 或 `Tasks`，就绕过了全部必填与枚举约束。这是「宽松校验」的典型代价——防的是错误，防不住拼写。

## 可迁移方法论

1. **能枚举的绝不放任。** 凡是状态、分类、角色这类取值有限的字段，一律用枚举约束。模型在开放文本上的自由度越大，你后期清洗的成本越高。
2. **写入用追加，改动用新事件。** 事件溯源的成本是重放，收益是可审计与可恢复。对 Agent 这种会「记错、改错、覆盖错」的系统，收益远大于成本。
3. **安全策略进 schema，不进 prompt。** 提示词是请求，schema 是拒绝。凡是「绝不能出现」的东西，靠校验，不靠叮嘱。
4. **给任何 schema 系统做覆盖度对账。** 声明了不校验，等于假的。
5. **技能接口显式化。** 声明 `reads` / `writes` / 前后置条件，比在 README 里写「本技能会读写 Task」有用得多。

最后回到开头的判断：这个技能适合「有明确实体关系、且规模不大」的场景——个人知识管理、项目跟踪、承诺与任务流转。它不适合把海量非结构化文本塞进去做检索（那是浏览器/向量库的活）。**它是记忆的骨架，不是记忆的仓库。**

## 本系列地图

| 篇 | 技能 | 一句话 |
|---|---|---|
| 一 | [Agent Memory](/posts/2026-09-28-agent-skill-anatomy-01-memory/) | 把「记住」做成三种异构数据 + 生命周期 |
| 二（本篇） | Ontology | 给记忆加一层 schema 与约束校验 |
| 三 | [Self-Improving Agent](/posts/2026-09-28-agent-skill-anatomy-03-self-improving/) | 把纠错日志晋升成规则与技能 |
| 四 | [Proactive Agent](/posts/2026-09-28-agent-skill-anatomy-04-proactive/) | 上下文存活的四个协议与主动性边界 |

> 数据说明：文中指标为 2026-09-28 从 SkillHub 聚合市场抓取的快照；代码结论基于当日下载的 `ontology` v1.0.4 技能包，可用 `lightmake.site/api/v1/download?slug=ontology` 复核。
