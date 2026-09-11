# AI Agent 工程师学习路线图研究报告（2025–2026）

## Executive Summary

本报告面向"已有后端工程基础、希望系统转型为 AI Agent 工程师"的开发者，梳理 **Python 工程、Linux 系统、数据结构与算法、AI/Agent 工程** 四条主线的整合学习路径。核心结论是：这四条线不是四份彼此独立的清单，而是围绕同一个能力闭环收敛——**Linux 提供 Agent 的运行与隔离边界，Python 提供工程化底座，算法提供检索/规划/限流/缓存的内核，AI/Agent 是最终交付形态**。建议采用 12 个月、每周 10–15 小时的双轨节奏（主线项目 + 贯穿式算法训练），并以"可运行的产出物"而非"看完的课程数"作为唯一里程碑判据。在时间受限时，存在一条 6 个月的最小可用路径。

## Background：为什么是这四条线

AI Agent 工程师与传统后端工程师的差别，不在模型本身，而在**围绕模型的系统工程**：如何把一次不稳定的模型调用，包装成可恢复、可观测、可评测、可审计的运行时。这个目标恰好落在四类能力的交集上：

- 模型调用失败要重试与限流 → 需要并发与算法；
- 工具调用要有权限边界与沙箱 → 需要 Linux 内核能力；
- 上下文、检索、评测要可维护 → 需要 Python 工程化；
- 最终形态是一套服务 → 需要容器、部署与可观测性。

因此四线必须交叉推进，而非串行"先学完 A 再学 B"。

## 一、总览：四线合一的阶段划分

| 阶段 | 周期 | Python | Linux | 算法（贯穿） | AI / Agent |
| --- | --- | --- | --- | --- | --- |
| P0 环境基线 | 第 1–2 周 | uv + ruff + pytest + mypy 模板仓库 | Shell 最小集 + SSH 密钥登录 | 复杂度分析 | 通读 Anthropic《Building Effective Agents》 |
| P1 工程打底 | 第 3–10 周 | 类型系统、Pydantic v2、asyncio、FastAPI 流式服务 | 权限/进程/cgroup v2/systemd/网络 | 数组、哈希、双指针、二分、排序 | 原生 API 手写 ReAct Agent；结构化输出 |
| P2 应用构建 | 第 11–24 周 | 数据栈、profiling、打包发布 | 容器化、反代 TLS、VPS 加固、可观测性 | 树、堆、图、DFS/BFS、拓扑排序、回溯、DP 入门 | RAG（混合检索+重排）、评测、MCP server/client |
| P3 Agent 深化 | 第 25–40 周 | 异步多工具运行时、性能优化 | eBPF/perf 排障、Landlock/seccomp 沙箱 | 并查集、Trie、贪心、高级 DP、字符串算法 | LangGraph 1.0 有状态工作流、多 Agent、A2A |
| P4 生产化 | 第 41–52 周 | vLLM 本地部署、服务切换 | 高可用、备份、监控告警 | 图算法综合、位运算、综合题 | 可观测+评测回归+安全防护的生产级 Agent |

每周建议投入 10–15 小时：工作日 1–1.5 小时（以算法为主），周末 5–6 小时（以项目为主）。

## 二、Python 工程线（贯穿全程，重点在前 24 周）

### 2.1 版本与语言特性基线

当前生产基线建议选 **Python 3.12/3.13**，新项目可上 **3.14**（3.14 已稳定，3.15 处于 RC，正式版预计 2026-10）。需要掌握的语言特性集中在：

- **类型系统**：类型注解、PEP 695 泛型语法（3.12+）、`Protocol`、`TypedDict`；大型项目应上 `--strict` 模式。
- **Pydantic v2**：Agent 领域几乎所有的"结构化输出"都依赖它，Rust 核心带来显著性能提升。
- **asyncio**：`TaskGroup`（3.11+）与 `asyncio.timeout()` 是 Agent 并发的正确姿势。
- **自由线程（PEP 779）**：3.14 起官方支持但非默认，构建名 `python3.14t`；C 扩展兼容性仍不完整，**不建议作为 Agent 服务默认运行时**，仅用于评估。
- **JIT（PEP 744）**：仍属实验特性，开启方式为 `PYTHON_JIT=1`，自由线程构建下不可用。

需要明确扬弃的旧习惯：`from __future__ import annotations` 在 3.14 的延迟注解求值（PEP 649）之后多数场景可移除；`setup.py` 与 `requirements.txt` 手工管理应被锁文件取代。

### 2.2 工程化工具链

2026 年的主流答案已经收敛：

| 环节 | 推荐 | 说明 |
| --- | --- | --- |
| 包管理 | **uv**（0.12.x） | Rust 实现；0.12 起 `uv init` 默认生成 src layout 的"包"结构；新项目事实标准，但仍未到 1.0，注意破坏性变更 |
| Lint/Format | **ruff**（0.15.x） | 一站式替代 flake8 + black + isort + pyupgrade |
| 类型检查 | pyright / mypy | 大型项目建议 pyright 提速 + mypy 严格模式做门禁 |
| 测试 | pytest 8.4+ / pytest-asyncio 1.4+ / hypothesis | Agent 场景必须覆盖异步测试与超时/取消路径 |
| CI | GitHub Actions + `astral-sh/setup-uv` | 流水线应在 60 秒内跑完 lint + 类型 + 单测 |

### 2.3 数据与 AI 工程栈

- **NumPy 2.x + Pandas 3.0**：Pandas 3.0 默认启用 Copy-on-Write 与 PyArrow 字符串，链式赋值彻底失效，升级前需先处理弃用警告。
- **Polars**：数据量超过 1GB 的 group-by/join 比 Pandas 快 5–30 倍；建议双轨（重 ETL 用 Polars，交由 scikit-learn 前 `.to_pandas()` 零拷贝）。
- **PyTorch 2.x**：`torch.compile` 在推理场景可带来 1.3–2 倍吞吐提升。
- **Hugging Face Transformers 5.x**：已移除 TensorFlow/JAX 后端，定位收敛为"模型定义层"，训练与推理分别交给第三方 trainer 与 vLLM/SGLang。
- **FastAPI + Pydantic v2**：FastAPI 新版已完全移除 Pydantic v1 支持，做 Agent 服务时不要再依赖 v1 写法。

### 2.4 并发写法（Agent 场景最关键）

| 需求 | 正确用法 |
| --- | --- |
| 全部成功才继续，任一失败即取消 | `asyncio.TaskGroup` |
| 允许部分失败、需要逐条结果 | `gather(..., return_exceptions=True)` |
| 单任务超时隔离 | 每个任务包 `asyncio.wait_for` |
| 限流 LLM API | `asyncio.Semaphore(N)`，**注意它限的是并发数而非 TPM**，需叠加 token 感知限流与指数退避 |
| 阻塞调用 | `asyncio.to_thread()`，绝不阻塞事件循环 |

禁忌同样明确：不要裸 `create_task()` 而不持有引用（任务可能被 GC 静默回收），不要在 `except Exception` 中吞掉 `CancelledError`。线上排障首推 **py-spy**（进程外采样、零改码、开销低于 1%），容器中需授予 `SYS_PTRACE`。

### 2.5 里程碑

1. `uv + ruff + mypy` 模板仓库，CI 全绿且 `uv build` 产出 wheel。
2. 类型完备的 Pydantic v2 校验层，`--strict` 零报错。
3. FastAPI 流式 LLM 服务（SSE + async generator），客户端断开后服务端任务被正确取消。
4. 异步多工具 Agent 运行时：`TaskGroup` + 单工具 `wait_for` + `Semaphore` 限流 + 重试退避。
5. 自建 embedding 检索服务（FAISS / pgvector），P95 延迟低于 100ms。
6. 带 profiling 的压测优化：提交前后火焰图对比，P95 降低 30% 以上。
7. vLLM 本地部署，Agent 层仅切换 `base_url` 即完成云端/本地切换。

## 三、Linux 系统线（前 24 周为主，与 Python 并行）

### 3.1 必须熟练的最小集

Shell 层面：`set -euo pipefail`、管道与重定向、`grep/sed/awk`、`sort | uniq -c | sort -nr`、`jq`、`tmux`；现代替代工具 `rg / fd / bat / fzf / ncdu`。判据很具体：**能用一条管道从 1GB Nginx 日志中统计出 Top IP 与状态码分布**。

### 3.2 与 Agent 直接相关的内核能力

这是 Linux 线区别于普通运维教程的关键。AI Agent 的沙箱不是"跑个 Docker 就安全了"：

- **权限最小化**：专用低权用户 + 工作目录 `chmod 700`；systemd 硬化项 `NoNewPrivileges=yes`、`ProtectSystem=full`、`ProtectHome=yes`、`PrivateTmp=yes`、`CapabilityBoundingSet=`、`ReadWritePaths=`。
- **容器加固**：`--cap-drop=ALL`、`--read-only`、`--security-opt=no-new-privileges`、seccomp profile。必须理解 **Docker group 权限约等于 root，容器并非天然安全边界**。
- **Landlock（Linux 5.13+）**：无需 root 即可把进程可读写的目录限定在指定路径之下，是当前"给编码 Agent 做文件级沙箱"的轻量方案；强隔离则用 gVisor 或 Firecracker 微虚拟机。
- **cgroup v2**：统一层级下的 `memory.max` / `cpu.max` / `io.max`，配合 PSI（`memory.pressure`）判断真实压力。注意 **cgroup v1 已被逐步移除**（Ubuntu 26.04 起仅 v2，Kubernetes 1.35 起移除 v1 支持）。

### 3.3 网络与 VPS 加固

针对"单台 1GB VPS 部署 Agent"这一典型场景，加固清单应包含：SSH 改非默认端口 + 仅密钥认证 + 禁用 root 登录 + 禁用密码认证；`ufw default deny incoming` 后再放行必要端口（注意 **Docker 会绕过 UFW 规则**，需改用 `DOCKER-USER` 链或 nftables 直接管理）；`fail2ban`（`maxretry=3`、`bantime=3600`）；`unattended-upgrades` 自动安全更新；**配置 2GB swap 并调低 `vm.swappiness`**（1GB 内存跑 Agent 必需）；`/tmp` 挂载 `noexec,nosuid,nodev`；保留基线快照与恢复文档。

### 3.4 容器、编排与可观测性

**单台 VPS 部署 Agent，Docker + Compose 足够，不需要 Kubernetes**；只有当出现多节点、高可用、团队共享或自动扩缩需求时再学 K8s（从 minikube/kind 起步）。可观测性栈建议：日志用 `journald` + Loki（配 Grafana Alloy 采集，存储成本约为 Elasticsearch 的十分之一），指标用 Prometheus + node_exporter + cAdvisor + Grafana，排障用 `strace / perf`，进阶用 eBPF（bpftrace 一行命令即可追踪系统调用）。

### 3.5 里程碑实验

1. systemd 将服务做成开机自启，配置 journald 日志与 logrotate 轮转。
2. `systemd-run --scope -p MemoryMax=100M` 限制内存并触发 OOM，在 `dmesg` 中确认。
3. `bpftrace` 追踪一次 `openat` 系统调用，打印目标进程打开的文件路径。
4. SSH 加固 + fail2ban，验证密码登录被拒且违规 IP 被封禁。
5. Docker 化 Agent 服务并施加内存/CPU 限制 + 只读根文件系统。
6. Compose 部署 + Caddy 反代 + 自动 TLS，`curl -I` 返回 200 且证书有效。
7. `strace -c` / `perf` 定位慢请求的 syscall 与热点函数。
8. Landlock 或 seccomp 沙箱化 CLI Agent，验证受限进程写 `/etc` 返回 EACCES。
9. Prometheus + Grafana 看板，配置 CPU > 80% 告警。
10. 模拟磁盘满故障，用 `df/du/ncdu` 定位并恢复。

## 四、数据结构与算法线（贯穿 52 周，每日 60–90 分钟）

### 4.1 认知框架

必须内化的不只是大 O，而是**三个尺度的区分**：最坏、平均、摊还（动态数组扩容、哈希表扩容、并查集路径压缩都是摊还而非单次）。工程判断尺：n ≤ 20 上指数/回溯，n ≤ 5000 上 O(n²)，n ≤ 10⁶ 上 O(n log n)，n ≥ 10⁸ 必须 O(n) 且做常数优化。此外，**常数因子与缓存局部性常比理论阶更重要**——连续内存数组在真实硬件上经常打败链式结构。

### 4.2 与 AI/Agent 的硬映射（本报告的核心论点）

算法不是"为了面试才学"的负担，它在 Agent 工程中高频出现。以下八个映射可直接作为学习动机：

| 算法/数据结构 | Agent 工程中的真实落点 |
| --- | --- |
| 分层可导航图 + 跳表 | **HNSW 向量索引**：pgvector、Qdrant、FAISS 默认使用；关键参数 M / efConstruction / efSearch |
| k-means + 倒排表 | **IVF 向量索引**：`nlist≈√n`，`nprobe` 调节召回率 |
| 堆 / 优先队列 | **重排（rerank）Top-K**、beam search、合并 K 路 |
| 哈希表 + 双向链表 | **LRU 缓存** O(1)；LFU 用频率桶 + minFreq 指针 |
| 令牌桶 / 滑动窗口 | **LLM API 限流**；分布式场景用 Redis + Lua 原子化 |
| DAG + 拓扑排序（Kahn） | **Agent 任务规划**：把任务拆成依赖图分层并行执行，DFS 检测环 |
| 分块 + 滑动窗口 + 递归摘要 | **上下文压缩**，对抗 "lost in the middle" |
| MinHash + LSH / Rabin-Karp | 数据去重、内容寻址 |

### 4.3 刷题策略

三个主流题单（Blind 75、Grind 75、NeetCode 150）重叠度约 85%，选择哪一个并不重要，**按模式刷而非按题号刷**才是关键。推荐路线：先用 Blind 75 做 4–6 周快速覆盖，再用 NeetCode 150 系统补齐（含贪心、高级图、二维 DP），总计 16 周左右可达到 Hard 题可解。复习必须用间隔重复（Anki SM-2 或 1/3/7/14/30 天的表格），每天复习 5–10 题封顶。核心信条：**深度 20 题 × 5 遍 > 广度 100 题 × 1 遍**。

关于面试趋势需要客观说明：非算法类后端岗位的算法权重确有下降（部分数据称降至 20–25%，系统设计升至 35–40%），但**AI/大模型岗位并未降低算法权重，而是新增了"组件手撕"这条第二轨**——Self-Attention/MHA、K-Means、MLP 反向传播、top-p/Beam Search、LoRA 都可能被要求现场手写。结论是：算法是下限，系统设计与项目经验是上限。上述权重数字多来自社区统计，仅供参考。

### 4.4 里程碑

1. 手写 O(1) 的 LRU 与 LFU（LeetCode 146 / 460），并能口述实现原理。
2. 令牌桶 + 滑动窗口限流器（Redis + Lua 原子化），并发单测不掉令牌。
3. Top-K 检索/重排：堆实现或 Redis ZSET，对比暴力方案耗时。
4. HNSW 简化版或 IVF 索引，与暴力检索对比 `recall@10 ≥ 0.95`。
5. Trie 实现的 tokenizer 前缀服务或敏感词过滤，百万词查询低于 10ms。
6. Agent DAG 调度器：拓扑排序分层并行 + 环检测 + 失败重试。
7. 用 BFS/DP/A* 解决 Agent 规划问题，输出最优路径与代价。
8. Mini-RAG：分块 + embedding + ANN + cross-encoder 重排，产出 recall/precision 评估表。

## 五、AI / Agent 工程线（第 3 周启动，第 11 周后成为主线）

### 5.1 术语已经换代

2025 年最重要的概念迁移是 **prompt engineering 被 context engineering 取代并包含**。Anthropic 在 2025-09 给出正式定义：统一编排 system instructions、tools、MCP、外部数据与消息历史。与之配套的核心认知是 **context rot**——token 越多，模型召回越差，上下文是有限预算而非免费资源。学习时应直接以"上下文工程"为组织框架，而不是继续停留在单轮 prompt 调优。

### 5.2 应用层：RAG 的生产范式

2025–2026 年的 RAG 已经远离"纯向量检索 + 固定 512 token 切分"的早期做法。生产范式是：**混合检索（BM25 + dense，用 RRF 融合）+ cross-encoder 重排 + 语义/层级分块**。其中 cross-encoder 重排通常带来 20–35% 的准确率提升，代价是 200–500ms 额外延迟；语境化检索（contextual retrieval）与语义分块另有 20–30% 增益。评测必须分层做——检索质量、忠实度（faithfulness）、答案相关性要分开度量，工具选 RAGAS 或 DeepEval。

### 5.3 Agent 层：框架选型的当前事实

需要区分"产品层"与"运行时层"。当前主流框架的状态如下：

| 框架 | 状态 | 定位 |
| --- | --- | --- |
| LangChain 1.0 + LangGraph 1.0 | 2025-10 GA | 所有 Agent 跑在 LangGraph runtime 上，生态最广、支持有状态与持久化执行 |
| Microsoft Agent Framework | 2026-04 1.0 GA | AutoGen + Semantic Kernel 合并产物，后两者进入维护模式 |
| OpenAI Agents SDK | 2025-03 | Handoff + guardrails + 默认 tracing |
| Claude Agent SDK | 2025-09 更名 | 子 Agent + 权限钩子 + MCP 一等公民 |
| Google ADK | 2025-05 v1.0 | Sequential/Parallel/Loop + A2A 支持，多语言 |

选型建议明确：**先用原生 API 手写 ReAct loop，不要一上来就上框架**。Anthropic 官方明确把过早的框架抽象称为反模式——在没理解 Agent Loop 之前，框架只会掩盖问题。理解循环后，若无云厂商绑定，优先学 LangGraph 1.0。

### 5.4 协议与运行时

**MCP（Model Context Protocol）** 自 2024-11 由 Anthropic 发布，2025-12 捐赠给 Linux Foundation 下的 Agentic AI Foundation，规格已演进到 2026 年的无状态化版本，生态已有上万 server。**A2A（Agent2Agent）** 由 Google 于 2025-04 发布、同年捐赠 Linux Foundation，2026-04 达到 v1.0（多租户 + 签名 Agent Card）。这两个协议是"Agent 之间、Agent 与工具之间"的互操作层，属于必须动手实现一遍的内容。

可观测性方面，**OpenTelemetry GenAI 语义约定**已成为事实标准（`gen_ai.*` 属性与 `invoke_agent`/`create_agent` 等 span），落地工具选 Langfuse（开源）、LangSmith、Arize Phoenix 或 AgentOps。

### 5.5 生产化与安全

成本控制三大手段：prompt caching、模型分级路由、上下文压缩。评测要同时做离线 evals 与线上多轮 evals。安全方面以 **OWASP LLM Top 10（2025 v2.0）** 为准，其中与 Agent 最相关的是 LLM01 提示注入、LLM06 过度授权、LLM07 系统提示泄露；另有专门的 Agentic Top 10 覆盖目标劫持与工具滥用。防护手段归结为最小权限、人在环审批、输入输出 guardrails 与间接注入检测。

### 5.6 里程碑

1. 纯手写 ReAct Agent（无框架），调用至少 2 个工具完成多步任务，输出完整推理与工具轨迹。
2. 自建 ≥50 条真实任务的结构化输出评测集，准确率可量化。
3. 带记忆与工具的 RAG 助手：混合检索 + 重排 + 引用来源 + 跨会话记忆。
4. 自建 MCP server，接入任意 MCP client。
5. LangGraph 1.0 有状态工作流：支持检查点恢复与人在环审批中断/续跑。
6. 多 Agent 协作系统：supervisor + 至少 2 个子 Agent，上下文隔离。
7. 生产级 Agent：OTel trace → Langfuse，CI 回归评测，注入用例全部通过。
8. （可选）从零训练小型语言模型跑通 pretrain→SFT→推理。

## 六、交叉整合：四线如何收束到一个项目

这是本路线图与传统"四个清单拼盘"的根本区别。建议把最终项目设计成**一个同时压测四条线**的系统：

1. **沙箱边界来自 Linux**：用 systemd 硬化 + cgroup v2 内存上限 + Landlock 文件白名单约束 Agent 进程，而不是简单地 `docker run`。
2. **并发与限流来自 Python + 算法**：`asyncio.TaskGroup` 管理多工具并发，Semaphore 控制并发数，令牌桶控制速率，LRU 缓存复用工具结果。
3. **检索内核来自算法 + Python**：HNSW/IVF 索引 + cross-encoder 重排（堆取 Top-K），预处理用 Polars，服务用 FastAPI。
4. **任务规划来自图算法**：把多步任务建成 DAG，用拓扑排序分层并行，DFS 检测依赖环。
5. **可观测性来自 Linux + AI**：OTel GenAI span 经 Langfuse 汇聚，主机与容器指标由 node_exporter/cAdvisor 供给 Prometheus，内核层排障用 bpftrace。
6. **交付形态来自两端**：Python 打包（uv build）+ 容器化（Compose + Caddy TLS）部署到 VPS。

当这六条全部打通，学习者的能力已经越过"会调 API"的阶段，进入"能负责一个 Agent 服务上线"的层次。

## 七、最小可用路径（时间受限时的降级方案）

如果无法投入 12 个月，可压缩为 **6 个月、每周 12 小时**：

- 砍掉：Kubernetes、eBPF、小模型训练、高级 DP 与字符串算法、多 Agent 系统。
- 保留：uv/ruff/pytest/FastAPI/Pydantic、Linux 基础 + VPS 加固 + Docker Compose、手写 ReAct Agent + RAG + 一个 MCP server、NeetCode 150 精刷。
- 判据不变：仍然要求每个阶段有可运行的产出物，而不是"看完了"。

## 八、常见反模式

1. **教程地狱**：只看不写。任何超过 40 分钟没有代码产出的学习都值得警惕。
2. **先框架后原理**：直接上手 LangChain，遇到问题无法定位是模型、提示、还是编排的错。
3. **追求数学完备**：手推注意力反向传播对应用工程师没有边际收益，理解 QKV/softmax 与梯度下降直觉即可。
4. **算法只刷不总结**：不按模式归类、不做间隔重复，等于用最高成本换最低留存。
5. **过早引入复杂度**：单机 VPS 就上 K8s，单 Agent 就上多智能体，属于典型的过度工程。
6. **忽视评测与可观测性**：这是 demo 与生产之间最大的鸿沟，也是最容易被跳过的部分。

## 九、结论

这四条线的最优推进方式是**交叉而非串行**：Python 与前 8 周的工程化打底决定了后续所有项目的质量上限；Linux 的系统能力决定了 Agent 能否安全地触碰真实世界；算法决定了检索、规划、限流、缓存这些"看不见但决定性能"的环节；AI/Agent 则是前三者收束的交付形态。以 12 个月为周期、以可运行产出物为里程碑，是当前最务实的路径。若时间受限，6 个月的最小可用路径同样能覆盖从零到"能上线一个 Agent 服务"的核心能力。

## Limitations

1. **版本时效性**：AI/Agent 生态迭代极快，本报告中 LangChain 1.0、Microsoft Agent Framework 1.0、MCP 与 A2A 的规格版本均为 2025–2026 年核实结果，落地时请以官方 spec 复核；Python 3.15 尚未正式发布，相关特性以 RC 状态为准。
2. **二手数据**：部分数字（如 RAG 重排的准确率提升幅度、非算法岗位的算法权重占比、"生产力提升 35–40%"）来自厂商口径或社区统计，未经独立审计，应视为方向性参考。
3. **厂商中立性**：本报告刻意避免推荐单一厂商技术栈；框架选型的"新手建议"基于生态广度与官方文档质量，不构成对任何产品的背书。
4. **个体差异**：时间估算基于每周 10–15 小时的稳定投入，实际进度受既有基础、项目复杂度与学习方式影响较大。

## References

1. [Anthropic – Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
2. [Anthropic – Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
3. [Anthropic – Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
4. [Anthropic – Donating MCP and establishing the Agentic AI Foundation](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
5. [Linux Foundation – Agentic AI Foundation formation](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
6. [Model Context Protocol – Specification changelog (2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28/changelog)
7. [Model Context Protocol – One Year of MCP (2025-11-25)](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary)
8. [LangChain – 1.0 GA announcement (LangChain & LangGraph)](https://forum.langchain.com/t/we-launched-1-0-versions-of-langchain-and-langgraph/1904/1)
9. [Microsoft – Introducing Microsoft Agent Framework](https://azure.microsoft.com/en-us/blog/introducing-microsoft-agent-framework/)
10. [OpenTelemetry – GenAI semantic conventions](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai)
11. [OWASP – LLM Top 10 2025 (v2.0)](https://genai.owasp.org/)
12. [Karpathy – nanochat](https://github.com/karpathy/nanochat)
13. [Karpathy – Neural Networks: Zero to Hero](https://github.com/karpathy/nn-zero-to-hero)
14. [3Blue1Brown – Attention in transformers](https://www.3blue1brown.com/lessons/attention)
15. [DeepLearning.AI – Short Courses](https://www.deeplearning.ai/short-courses/)
16. [Python – What's New in Python 3.14](https://docs.python.org/3/whatsnew/3.14.html)
17. [Python – Free-Threading Guide](https://py-free-threading.github.io/)
18. [Astral – uv documentation](https://docs.astral.sh/uv/)
19. [Astral – Ruff documentation](https://docs.astral.sh/ruff/)
20. [Python Developer Tooling Handbook](https://pydevtools.com/handbook)
21. [pandas – What's new in 3.0](https://pandas.pydata.org/docs/whatsnew/v3.0.0.html)
22. [PyTorch – Official tutorials](https://pytorch.org/tutorials)
23. [Hugging Face – Transformers documentation](https://huggingface.co/docs/transformers)
24. [vLLM – Documentation](https://docs.vllm.ai/)
25. [py-spy – GitHub](https://github.com/benfred/py-spy)
26. [The Missing Semester of Your CS Education (MIT)](https://missing.csail.mit.edu/)
27. [OverTheWire – Bandit wargame](https://overthewire.org/wargames/bandit/)
28. [SadServers – Linux troubleshooting CTF](https://sadservers.com/)
29. [Brendan Gregg – eBPF / performance resources](https://www.brendangregg.com/)
30. [bpftrace – GitHub](https://github.com/bpftrace/bpftrace)
31. [Kubernetes v1.35 Release Notes](https://kubernetes.io/blog/2025/12/17/kubernetes-v1-35-release)
32. [Ubuntu – Official firewall documentation (nftables/ufw)](https://documentation.ubuntu.com/security/security-features/network/firewall)
33. [Prometheus – Documentation](https://prometheus.io/docs/)
34. [Grafana – Documentation](https://grafana.com/docs/)
35. [Hello 算法](https://www.hello-algo.com/)
36. [NeetCode – Roadmap and practice](https://neetcode.io/)
37. [Tech Interview Handbook – Grind 75](https://www.techinterviewhandbook.org/grind75)
38. [labuladong 的算法笔记](https://labuladong.online/algo/)
39. [代码随想录](https://programmercarl.com/)
40. [MIT OCW – 6.006 Introduction to Algorithms](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/pages/syllabus/)
41. [UC Berkeley – CS61B Data Structures](https://sp21.datastructur.es/)
42. [IVF vs HNSW – vector index comparison](https://lycoristechnologies.com/blog/ivf-vs-hnsw-vector-index)
43. [GAP: Graph-Based Agent Planning (arXiv 2510.25320)](https://arxiv.org/pdf/2510.25320v1)
44. [Chip Huyen – AI Engineering (O'Reilly)](https://www.oreilly.com/library/view/ai-engineering/9781098166298/)
45. [Stanford CS336 – Language Modeling from Scratch](https://stanford-cs336.github.io/)
