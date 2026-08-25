---
title: "Luck Ops MCP：把 Lark 多云运维做成成熟 Agent 可接入的标准工具"
date: 2026-08-25T11:40:00+08:00
publishDate: 2026-08-25T11:40:00+08:00
description: "将 luck-agent 的多云 VPS、固定操作、Lark 审批和审计能力抽成轻量 MCP Server，让 Hermes、OpenClaw 等成熟 Agent 安全复用。"
tags: ["MCP", "多云运维", "Lark", "AI Agent", "Human-in-the-Loop", "VPS"]
categories: ["AI Agent", "系统架构"]
draft: false
---

当一个个人 Agent 同时负责聊天、记忆、博客、Lark 卡片、多云 VPS、SSH、systemd、Docker、审批和审计时，最先出现的问题不是模型不够聪明，而是边界越来越难解释。

继续给 Agent 增加工具，最终会得到另一个通用 Agent；改用成熟 Agent，又可能丢掉已经验证过的运维安全能力。

更好的拆法是：

> 保留 Lark 多云运维的专业能力，但把它从通用 Agent 中抽出来，做成独立的 `luck-ops-mcp`。

Hermes、OpenClaw、Codex 或其他 MCP Client 负责理解用户意图；`luck-ops-mcp` 只负责资产、权限、审批、执行和审计。

## 产品边界

`luck-ops-mcp` 负责：

- AWS、GCP、Azure 等目标目录；
- 主机、资源、服务和日志查询；
- 固定、登记过的运维操作；
- 用户、目标、服务和操作权限；
- Lark 人工审批；
- 执行前置条件、结果验证和回滚说明；
- 操作状态和审计记录。

它不负责：

- 通用聊天；
- Agent 推理和任务规划；
- 博客写作、英语学习和知识问答；
- Agent 长期对话记忆；
- 任意远程 Shell；
- 根据模型临时生成系统命令。

这样可以把系统分成三层：

```text
交互层：Lark / Web / CLI
推理层：Hermes / OpenClaw / 其他成熟 Agent
执行层：luck-ops-mcp / vps_sysops
```

其中只有执行层持有运维凭据，推理层永远不是最终授权者。

## 为什么适合 MCP

MCP 把上下文和动作分成 Resources 与 Tools：稳定、可读的资产适合 Resources，会产生行为的操作适合 Tools。客户端可以通过标准协议发现 schema，而不需要为每个 Agent 重写插件。

MCP Resources 支持 URI、资源模板、分页和更新订阅，很适合多云资产目录。[MCP Resources 规范](https://modelcontextprotocol.io/specification/2025-11-25/server/resources)

MCP Tools 支持输入和输出 JSON Schema，并提供 `readOnlyHint`、`destructiveHint`、`idempotentHint` 和 `openWorldHint` 等风险提示。[MCP Tool Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema)

但这些 annotation 只是给客户端看的提示，不能替代服务端权限检查。一个恶意或有 Bug 的客户端完全可以直接调用工具。

## 一个 Server，不是一个万能 Tool

最危险的设计是：

```json
{
  "name": "vps_manage",
  "arguments": {
    "command": "ssh host systemctl restart service"
  }
}
```

这只是把 Shell 套了一层 JSON，模型仍然能够改变主机、命令、参数和执行范围。

正确做法是一个 MCP Server 暴露少量窄工具：

| Tool | 类型 | 用途 |
|---|---|---|
| `ops_list_targets` | 只读 | 获取当前身份可见的目标 |
| `ops_list_services` | 只读 | 获取目标上的服务资产 |
| `ops_get_status` | 只读 | 主机、资源和服务健康 |
| `ops_query_logs` | 只读 | 有界、脱敏、分页日志 |
| `ops_list_operations` | 只读 | 查询服务允许的固定动作 |
| `ops_request_operation` | 创建请求 | 冻结参数并发起审批，不直接执行 |
| `ops_get_operation` | 只读 | 查询审批、执行和验证状态 |
| `ops_cancel_operation` | 状态变更 | 取消尚未开始的请求 |

对应的 Resources 可以是：

```text
ops://targets
ops://targets/{target_id}
ops://targets/{target_id}/services
ops://operations/catalog
ops://operations/{request_id}
ops://audit/recent
```

资产发现与操作授权必须分开。把一台机器或服务加入目录，不能自动赋予 restart、backup 或 restore 权限。

## 统一资源模型

多云运维最容易乱在名称上。同一个“实例”在不同平台可能叫 VM、EC2、Compute Instance；同一个服务又可能运行在 systemd、用户级 systemd 或 Docker Compose。

内部统一使用：

```text
Provider → Account → Region → Target → Service → Operation
```

调用参数只接受固定 ID：

```json
{
  "target_id": "gcp-free-vps-oregon",
  "service_id": "new-api",
  "operation": "restart"
}
```

模型可以把这些 ID 展示成人类名称，但不能自己拼接 SSH host、systemd unit 或脚本路径。

## Operation Contract 是真正的产品核心

每一个变更动作都必须预先登记完整契约：

```json
{
  "operation_id": "new-api.restart.v1",
  "service_id": "new-api",
  "action": "restart",
  "risk": "medium",
  "read_only": false,
  "destructive": false,
  "idempotent": true,
  "allowed_targets": ["gcp-free-vps-oregon"],
  "required_scopes": ["ops:request"],
  "approval_policy": "lark_user",
  "timeout_seconds": 60,
  "preconditions": [
    "target is reachable",
    "fixed wrapper is installed"
  ],
  "verification": [
    "systemd service is active",
    "/v1/models returns an authenticated response"
  ],
  "rollback": "restart does not modify persistent configuration"
}
```

只有登记了以下字段的操作才能上线：

- 固定入口；
- 精确目标约束；
- 所需权限；
- 风险等级；
- 参数 schema；
- 前置条件；
- 超时和并发限制；
- 幂等策略；
- 验证步骤；
- 回滚说明；
- 输出脱敏规则；
- 审批策略。

这个思想比 MCP 本身更重要。MCP 解决“怎么接入”，Operation Contract 解决“允许接入者做什么”。

## 审批采用“申请后服务端执行”

常见审批流程是：Agent 创建验证码，用户确认，再把验证码交给 Agent 调一次执行工具。

这个方案的问题是审批凭据会进入模型上下文，而且第二次调用的参数可能和用户看到的不一致。

更安全的状态机是：

```text
Agent 调用 ops_request_operation
        ↓
服务端验证并冻结操作快照
        ↓
Lark 发送批准/拒绝卡片
        ↓
用户点击，服务端校验身份和快照
        ↓
服务端执行固定入口并验证
        ↓
Agent 用 request_id 查询结果
```

第一次调用只返回：

```json
{
  "status": "approval_required",
  "request_id": "op_01K...",
  "summary": "重启 GCP 上的 new-api",
  "expires_at": "2026-08-25T12:10:00Z"
}
```

审批记录至少绑定：

```text
request_id
requester identity
approver identity
target_id
service_id
operation_id + version
normalized arguments hash
created_at / expires_at
```

批准、拒绝、过期和取消都是不可逆终态。重复点击必须幂等；参数 hash 不一致必须拒绝；审批过期默认拒绝，不能自动批准。

MCP Elicitation 可以让 Server 请求用户输入或打开外部审批页面，但不同客户端支持程度仍不一致。[MCP Elicitation](https://modelcontextprotocol.io/specification/2025-11-25/client/elicitation)

因此第一版继续使用已验证的 Lark 卡片更稳妥。成熟 Agent 的 Lark Gateway 只需要一个确定性 callback 插件，把卡片事件转发给 `luck-ops-mcp`；不能让模型解释“用户大概是批准了”。

## 工具返回必须结构化

所有工具使用同一个 envelope：

```json
{
  "status": "ok",
  "request_id": "req_01K...",
  "target": {
    "id": "gcp-free-vps-oregon",
    "provider": "gcp"
  },
  "summary": "new-api 运行正常",
  "data": {},
  "evidence": [
    {
      "check": "systemd",
      "status": "ok",
      "message": "active"
    }
  ],
  "warnings": [],
  "error": null,
  "started_at": "2026-08-25T12:00:00Z",
  "finished_at": "2026-08-25T12:00:02Z"
}
```

状态集合固定为：

```text
ok
partial
error
approval_required
queued
running
cancelled
expired
```

模型需要的是短摘要和结构化证据，不是几千行原始 journald。完整日志应该保留在服务端，通过分页和短期资源 URI 按需读取。

## 认证和权限

本地单用户可以使用 stdio：

```text
Agent → stdio → luck-ops-mcp
```

跨机器或多个客户端使用 Streamable HTTP：

```text
Agent → HTTPS + OAuth 2.1 → luck-ops-mcp
```

远程模式至少需要：

- HTTPS；
- Token audience 校验；
- `ops:read`、`ops:request`、`ops:admin` 分级 scope；
- OAuth subject 到 Lark open_id 的显式映射；
- 用户、目标、服务和操作四层 allowlist；
- 调用与任务级限流；
- 云凭据和 SSH key 只保存在 MCP Server。

MCP 的 HTTP 授权规范要求令牌绑定到目标资源，并禁止把其他资源服务器的 token 当作 MCP 凭据透传。[MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)

## 长任务先用稳定兼容层

备份、部署和跨主机验证可能超过普通工具调用超时。MCP Tasks 可以描述持久异步任务，支持查询、取消和延迟结果，但当前仍属于实验能力。[MCP Tasks](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/tasks)

第一版使用：

```text
ops_request_operation → request_id
ops_get_operation(request_id) → 当前状态
```

以后再对支持 MCP Tasks 的客户端增加原生适配。两种协议表面必须复用同一个 Operation Store，不能维护两套状态机。

## 怎样做到真正轻量

如果把完整 luck-agent 留着，再增加独立 MCP 服务，就不算轻量。`luck-ops-mcp` 必须删除通用 Agent 能力：

- 不依赖 LangGraph；
- 不依赖 LLM Client；
- 不保存聊天记忆；
- 不运行浏览器；
- 不加载三个云厂商的大型 SDK；
- 不启动第二套任务编排；
- 不允许任意 Shell。

最小进程只需要：

```text
MCP Streamable HTTP
SQLite Operation Store
Policy + Audit
SSH/vps_sysops Adapter
Lark REST + callback
```

如果继续用 Python，可以通过 `httpx` 直接调用 Lark REST，避免为了几张审批卡加载完整渠道运行时。第一版目标是单进程、无容器、SQLite、空闲内存不超过 80 MiB。

如果 Python 版稳定后仍无法达到预算，再重写为 Go 单文件程序；不应该在验证产品边界之前先进行语言重写。

## 从现有 luck-agent 迁移

现有代码已经拥有三块重要资产：

```text
ServiceAssetSpec       只读服务目录
ServiceOperationSpec   固定变更契约
VpsSysopsAdapter       本地/SSH 执行边界
```

迁移时应先抽领域层，再接 MCP：

```text
ops_domain/
  models.py
  catalog.py
  policy.py
  operations.py
  audit.py

ops_adapters/
  vps_sysops.py
  ssh.py
  lark_approval.py

transports/
  mcp_server.py
  health.py
```

MCP handler 只负责 schema 转换。目标约束、审批、审计和执行验证都必须留在领域层，这样以后增加 REST、CLI 或 A2A 入口也不会复制安全逻辑。

## MVP 顺序

第一阶段只读：

1. `ops_list_targets`；
2. `ops_list_services`；
3. `ops_get_status`；
4. `ops_query_logs`；
5. 结构化输出和脱敏；
6. Hermes/OpenClaw 接入验证。

第二阶段审批：

1. `ops_request_operation`；
2. Lark 卡片 callback；
3. 不可变快照和过期机制；
4. `ops_get_operation`；
5. 审计和重复点击测试。

第三阶段只开放一个变更动作，例如 `luck-agent restart`。完成真实批准、拒绝、过期、错误目标、执行失败、验证失败和重复请求测试后，才逐项增加 new-api backup、A2A restart 等动作。

## 最终定位

`luck-ops-mcp` 不应该成为又一个 Agent，它的产品定位应该非常窄：

> 一个带 Lark 人工审批、多云资产目录、固定操作契约和完整审计的轻量运维 MCP Server。

成熟 Agent 可以更换，模型可以更换，Lark 之外也可以增加入口；只有运维动作的服务端契约不能由模型决定。

如果说[极简 Agent 实用测试基准](/posts/2026-08-25-minimal-agent-practical-benchmark/)解决“怎么证明它够轻、够稳”，[轻量个人助理选型](/posts/2026-08-25-minimal-personal-agent-framework-evaluation/)解决“谁来负责通用助理”，那么 `luck-ops-mcp` 解决的就是最后一个问题：如何把真正有差异化、也最危险的能力安全地留下来。
