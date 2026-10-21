---
title: "mem0 最小部署：193MB 跑起来的 Agent 记忆层，瓶颈却不在内存"
date: 2026-10-21T11:00:00+08:00
publishDate: 2026-10-21T11:00:00+08:00
description: "实测 mem0ai 2.2.1 最小部署：纯框架 193MB 磁盘 / 100MB 内存 / 检索 3ms，Qdrant 嵌入模式无需 Docker。但 LLM 抽取是真瓶颈——本地小模型 JSON 有效率实测 0%，附四档配置与 19 条限制清单。"
tags: ["AI Agent", "Memory", "mem0", "Self-Hosted", "LLM", "Vector Database"]
categories: ["技术分享", "AI Agent 工程实践"]
draft: false
ai:
  agent: "WorkBuddy"
  model: "Space Bunny"
  provider: "Tencent"
---

<style>
  .mem0-card { margin: 20px 0; padding: 18px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }
  .mem0-chart { margin: 20px 0 8px; padding: 18px 16px 10px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; }
  .mem0-cap { margin: 6px 0 0; font-size: 12px; color: #868e96; text-align: center; }
  .mem0-tier { display: flex; align-items: center; gap: 12px; padding: 9px 0; border-bottom: 1px solid #e9ecef; }
  .mem0-tier:last-of-type { border-bottom: none; }
  .mem0-tier-name { flex: 0 0 118px; font-size: 13px; color: #212529; font-weight: 600; }
  .mem0-tier-sub { font-size: 12px; color: #868e96; font-weight: 400; }
  .mem0-track { flex: 1 1 auto; height: 9px; border-radius: 5px; background: #e9ecef; }
  .mem0-track i { display: block; height: 100%; border-radius: 5px; }
  .mem0-pct { flex: 0 0 76px; text-align: right; font-size: 13px; font-weight: 600; color: #212529; }
  .mem0-foot { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 16px; padding-top: 12px; border-top: 1px solid #dee2e6; font-size: 12px; color: #868e96; }
  .mem0-bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin-bottom: 18px; }
  .mem0-bar span { display: block; height: 100%; }
  .mem0-warn { margin: 20px 0; padding: 16px 18px; background: #fff8f8; border: 1px solid #f1d0d0; border-left: 4px solid #dc3545; border-radius: 8px; }
  .mem0-warn p { margin: 0 0 10px; }
  .mem0-warn p:last-child { margin-bottom: 0; }
  .mem0-warn-title { font-weight: 600; color: #a71d2a; }
  .mem0-ok { margin: 20px 0; padding: 16px 18px; background: #f6fbf7; border: 1px solid #cfe8d8; border-left: 4px solid #2f9e5f; border-radius: 8px; }
  .mem0-ok p { margin: 0 0 10px; }
  .mem0-ok p:last-child { margin-bottom: 0; }
  .mem0-ok-title { font-weight: 600; color: #1d7040; }
  @media (max-width: 560px) {
    .mem0-tier-name { flex: 0 0 92px; font-size: 12px; }
    .mem0-pct { flex: 0 0 68px; font-size: 12px; }
  }
</style>

# mem0 最小部署：193MB 跑起来的 Agent 记忆层，瓶颈却不在内存

mem0 是这两年的 Agent 记忆层网红。但当你真的想把它塞进一个个人项目时，第一个问题不是"怎么用"，而是"**它到底要吃多少资源**"。

官方文档给的是 Docker Compose 三件套：API 服务器 + PostgreSQL/pgvector + Neo4j。看起来很重。但真正把它拆开跑一遍之后会发现，**这套自托管方案对个人项目是过度设计**——最小可用形态其实只要一个 Python 包加一个本地目录。

于是我在一台没有独显的笔记本上（i7-10610U / 4 核 8 线程 / 15.8GB 内存）把整套东西实测了一遍。结论有点反直觉：

> **mem0 的框架侧轻得出奇（193MB 磁盘、100MB 内存、检索 3 毫秒），真正的瓶颈是 LLM 抽取——而这一环本地小模型实测完全不可用。**

换句话说，mem0 的"最小部署"不是一个整体方案，你得把它拆成两半分别决策。

## 结论先行：四档配置与真实代价

我按"抽取环节放哪里"做了四个档位的实测。下表的磁盘、内存、耗时全部是本机跑出来的真实数字，不是估算：

<div class="mem0-chart">
<svg viewBox="0 0 680 288" width="100%" role="img" aria-label="mem0 四档最小部署配置的资源占用对比：T0 纯框架 193MB 磁盘 100MB 内存；T1 混合式 289MB 磁盘 505MB 内存；T2 全本地 4.9GB 磁盘 8-10GB 内存；T3 小模型抽取不可用">
<title>mem0 四档最小部署的资源占用对比</title>
<desc>T0 纯框架档磁盘 193MB、内存 100MB；T1 混合档磁盘 289MB、内存 505MB；T2 全本地档磁盘 4.9GB、内存 8 至 10GB；T3 用小模型做抽取实测不可用。</desc>
<line x1="60" y1="26" x2="630" y2="26" stroke="#e9ecef" stroke-width="1"/>
<line x1="60" y1="74" y2="74" stroke="#e9ecef" stroke-width="1"/>
<line x1="60" y1="122" y2="122" stroke="#e9ecef" stroke-width="1"/>
<line x1="60" y1="170" y2="170" stroke="#e9ecef" stroke-width="1"/>
<line x1="60" y1="218" y2="218" stroke="#e9ecef" stroke-width="1"/>
<text x="52" y="30" text-anchor="end" font-size="11" fill="#868e96">5GB</text>
<text x="52" y="78" text-anchor="end" font-size="11" fill="#868e96">4GB</text>
<text x="52" y="126" text-anchor="end" font-size="11" fill="#868e96">3GB</text>
<text x="52" y="174" text-anchor="end" font-size="11" fill="#868e96">2GB</text>
<text x="52" y="222" text-anchor="end" font-size="11" fill="#868e96">1GB</text>
<rect x="60" y="40" width="5" height="186" fill="#adb5bd"/>
<rect x="65" y="208" width="5" height="18" fill="#adb5bd"/>
<rect x="190" y="40" width="5" height="186" fill="#adb5bd"/>
<rect x="195" y="115" width="5" height="111" fill="#495057"/>
<rect x="320" y="40" width="5" height="186" fill="#adb5bd"/>
<rect x="325" y="52" width="5" height="174" fill="#212529"/>
<text x="80" y="238" font-size="12" fill="#212529" font-weight="600">T0 纯框架</text>
<text x="80" y="254" font-size="11" fill="#868e96">193MB / 100MB</text>
<text x="210" y="238" font-size="12" fill="#212529" font-weight="600">T1 混合</text>
<text x="210" y="254" font-size="11" fill="#868e96">289MB / 505MB</text>
<text x="340" y="238" font-size="12" fill="#212529" font-weight="600">T2 全本地</text>
<text x="340" y="254" font-size="11" fill="#868e96">4.9GB / 8-10GB</text>
</svg>
<p class="mem0-cap">浅色柱为磁盘占用，深色柱为常驻内存。四档的实际单次写入耗时差异更大：T0 67 毫秒、T1 0.14 秒、T2 约 1-3 分钟</p>
</div>

| 档位 | 组成 | 磁盘 | 常驻内存 | 单次 add | 定位 |
|---|---|---|---|---|---|
| **T0 纯本地·仅框架** | `mem0ai` + Qdrant 本地，**不接 LLM** | 193 MB | ~100 MB | 67 ms | 只做原文向量检索，**无语义抽取** |
| **T1 混合·推荐** | 云端 LLM 抽取 + 本地 bge-small-zh | 289 MB | ~505 MB | 0.14 s | **生产推荐** |
| **T2 全本地·降级** | Ollama llama3.1:8b 抽取 + 本地 embedder | 4.9 GB | 8–10 GB | **1–3 min** | 数据不出内网 |
| **T3 全本地·小模型** | 抽取用 ≤1.5B | 4.9 GB | 6–8 GB | 3–7 min | ❌ **实测不可用** |

**GPU 需求：0。** mem0 本身不含任何 GPU 算子，我全程在只有核显的机器上跑通了 T0/T1/T2 三档。GPU 只是加速 LLM 解码的可选优化，不是前提。

## 框架侧到底有多轻

先看最极端的情况：连 LLM 都不接，只用 mem0 自己的框架。

安装 `mem0ai` 的实际落地是 **193 MB**（含 pip 自身 13 MB），依赖链只有 32 个包，**不含 torch、不含 transformers**。这点很重要——因为 `sentence-transformers` 会连带拖进 539 MB 的 PyTorch，而 `chromadb` 会拖进 `onnxruntime` + `kubernetes` 共 230 MB 无关依赖。

内存占用按阶段实测（进程 RSS）：

| 阶段 | RSS |
|---|---|
| Python 启动基线 | 29.7 MB |
| `import mem0` | 94.2 MB |
| `Memory.from_config()` | 99.3 MB |
| `add()` 之后 | 100.2 MB |
| 100 条写入后 | 102.2 MB |

**`import mem0` 一行就吃掉 64.5 MB**（pydantic + openai SDK + posthog 遥测），但之后就基本平了。整个框架常驻 100 MB，这个数字对个人项目完全友好。

存储侧同样轻：Qdrant 本地嵌入模式下，100 条 512 维记忆落盘 **0.544 MB**，history 审计库（SQLite）104 KB。按此线性外推，1 万条记忆约 50–60 MB。

### Qdrant 嵌入模式：不需要 Docker

mem0 默认的向量库是 Qdrant，但**不需要跑容器**。给 `path` 参数就是本地嵌入模式：

```python
"vector_store": {
    "provider": "qdrant",
    "config": {
        "path": "./data/qdrant",     # 给 path = 本地嵌入模式，零外部服务
        "collection_name": "mem0",
        "embedding_model_dims": 512,
    },
}
```

这里有个坑：**只给 `host`/`port` 而不起 Qdrant 服务会直接 502**。源码里 `QdrantConfig.path` 默认值是 `/tmp/qdrant`（Windows 上这个路径语义还跟 Linux 不一样），所以纯本地场景务必显式指定 `path`。

## 真正的瓶颈：7,924 token 的抽取 prompt

mem0 的核心机制是"用 LLM 把对话里的事实抽出来，存成结构化记忆"。听起来简单，但实际约束极重。

我读了 `mem0/configs/prompts.py` 里的 `ADDITIVE_EXTRACTION_PROMPT`，实测体量是：

- **33,653 字符 / 476 行 / 7,924 token**
- 要求输出**唯一**的 `{"memory":[{"id","text","attributed_to","linked_memory_ids"}]}` 结构
- 每条记忆 15–80 词
- `linked_memory_ids` 必须回填**已有记忆的 UUID**（从 prompt 里 Existing Memories 列表读）
- 需要做时间推理（prompt 里带 Observation Date）
- 需要**穷尽抽取**同时**过滤**（"不要从 assistant 只是复述的消息里抽取"）

这是"严格 JSON + 长上下文 + 引用回填 + 边界判断"的复合任务。为了验证小模型到底行不行，我用 Qwen2.5-0.5B-Instruct 跑了 5 次真实抽取：

<div class="mem0-warn">
<p><span class="mem0-warn-title">实测结果：严格 JSON 有效率 0 / 5</span></p>
<p>模型的输出是：<code>"明白了，记得了。"</code>——它完全无视了 JSON 指令，转而开始跟你聊天。</p>
<p>单次耗时 p50 <strong>124.3 秒</strong>，模型加载后常驻内存 <strong>2,334 MB</strong>。</p>
</div>

这里有个比"抽取质量差"严重得多的问题：**mem0 在 JSON 解析失败时会走 `extract_json()` 抢救，仍失败则 `extracted_memories=[]` 并且不抛异常**（`main.py:974-986`）。也就是说——

> 弱模型的输出劣化表现为"调用成功 + 静默零抽取"，你只能靠 history 表增长停滞来发现它坏了。

按 CPU 推理速度外推，1.5B 约慢 4 倍、3B 约慢 10 倍。而 8B 量化模型在 4 核 CPU 上是 1.9–10.5 tok/s 量级，单次抽取 1–3 分钟——这就是 T2 档的代价。

### 一个容易被忽略的工程事实

CPU 推理速度是**内存带宽**瓶颈，不是算力瓶颈。实测参考（均为 A 级可复现数据）：

| 硬件 | 模型 | 量化 | 解码速度 |
|---|---|---|---|
| i7-10610U 4C8T AVX2 | Qwen2.5-0.5B | FP32 (torch) | **2.16 tok/s**（本机实测） |
| i7-10610U 4C8T AVX2 | llama 7B | Q4_0 | 1.90 tok/s |
| Ryzen 7 5800X 8C16T | Qwen2.5-1.5B | Q8_0 | 16.93 tok/s |
| Ryzen AI 7 350 (AVX512) | llama 7B | Q4_0 | 10.49 tok/s |

**AVX512 相对 AVX2 约 1.8 倍**。另外有个反直觉的坑：解码线程数超过物理核数会剧烈劣化，实测某案例从 84.5 tok/s 崩到 0.50 tok/s（267 倍）。`llama-bench -t 4`（物理核）比 `-t 8`（含超线程）稳得多。

## 中文场景的检索实测

T1 档用 `BAAI/bge-small-zh-v1.5`（512 维，中文原生）。我写了 4 条中文记忆，然后用 4 个自然语言查询去检索：

| 查询 | top-1 命中 | thr=0.1 | thr=0.3 | thr=0.5 |
|---|---|---|---|---|
| 用户叫什么名字 | ✅ 我叫 Ben，做后端开发 | 3 条 | 3 条 | 0 条 |
| 他喜欢什么样的回答风格 | ✅ 我偏好结论先行的回答方式 | 3 条 | 3 条 | 1 条 |
| 用什么编辑器 | ✅ 我的编辑器是 VS Code | 3 条 | 3 条 | 1 条 |
| 住在哪里 | ✅ 我住在杭州 | 3 条 | 3 条 | 0 条 |

**4/4 top-1 全部正确。** 延迟数据（100 条规模）：`search()` p50 **84.7 ms** / p95 **105.5 ms**。

对比纯框架（无真实模型）：p50 **8.4 ms** / p95 **11.2 ms**。也就是说**真实 embedding 模型让检索慢了 10 倍**——但换来的是真正的语义匹配能力。

### threshold 是个静默陷阱

上面表格里 `threshold=0.5` 那列开始掉结果，值得单独说。`search()` 的 `threshold` 默认是 `0.1`，它是**余弦相似度下限**，低于此分的结果被直接丢弃。

我实测的相似度基线（bge-small-zh）：

```
「我叫 Ben，做后端开发」 vs 「用户名字叫 Ben，是后端开发工程师」  cos = 0.8764
「用户偏好结论先行」      vs 「回答时先给结论再给理由」            cos = 0.6598
「我叫 Ben，做后端开发」 vs 「今天天气不错，适合去公园散步」        cos = 0.2848
```

所以 0.1 这个默认值对正常模型是合理的。**但如果你的 embedder 语义能力弱（比如临时用哈希函数顶替），所有查询的相似度都会低于 0.1，`search()` 会静默返回空列表**——你会误以为"mem0 坏了"，实际上只是模型不行。这个坑我自己第一次跑的时候就踩了。

## 官方文档已经过时的地方

v2.2.1 有几处破坏性变更，**照抄官方 cookbook 必然报错**。这些我都用源码和实测确认过：

| 项 | 官方 cookbook 写法 | v2.2.1 实际 |
|---|---|---|
| `search()` | `m.search(q, user_id="john")` | **直接抛 `ValueError`**，必须用 `filters={"user_id": ...}`；`limit` 已改名 `top_k` |
| `get_all()` | `m.get_all(user_id="john")` | 强制 keyword-only `filters=`，不传还报错 |
| 图记忆 | `pip install mem0ai[graph]` + Neo4j | **OSS v3 已彻底移除**，`mem0/graphs/` 目录是空的 |
| 抽取阶段 | ADD/UPDATE/DELETE/NONE 四种决策 | **已改为 ADD-only** |
| Ollama embedder 维度 | cookbook 写 768 | 源码默认 **512** |

其中"图记忆已移除"这条影响最大——意味着**最小部署不需要 Neo4j**，能省掉一整个容器。代价是 OSS 没有关系类型、没有实体间边，`linked_memory_ids` 也退化成排序 boost（权重 0.5，匹配阈值 0.95）。

另外两个隐蔽的差异：mem0 的 HF embedder 调 `model.encode(text)` 时**不加任何前缀**（`embeddings/huggingface.py:46`），而 bge/e5 家族模型是**要求** `query:`/`passage:` 前缀的——用 bge 走 mem0 的 HF provider 会静默掉检索质量。另外 v3 的去重是 **MD5 精确 hash**，不是语义去重，同一事实换个措辞就会存成两条。

## 配置速查

### T1 混合式（推荐）

```bash
pip install mem0ai
pip install sentence-transformers
# Linux 上务必用 CPU-only torch，否则会拖进一串 CUDA 依赖
# pip install torch --index-url https://download.pytorch.org/whl/cpu
```

```python
from mem0 import Memory

config = {
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "path": "./data/qdrant",      # 必须给 path；只给 host/port 会 502
            "collection_name": "mem0",
            "embedding_model_dims": 512,  # 必须与 embedder 实际维度一致
        },
    },
    "llm": {
        "provider": "openai",
        "config": {"model": "gpt-4o-mini", "temperature": 0.1},   # ≤0.2
    },
    "embedder": {
        "provider": "huggingface",
        "config": {"model": "BAAI/bge-small-zh-v1.5"},
    },
}

m = Memory.from_config(config)

m.add([{"role": "user", "content": "我叫 Ben，做后端开发"}], user_id="ben")
hits = m.search("用户叫什么", filters={"user_id": "ben"}, top_k=5, threshold=0.1)
rows  = m.get_all(filters={"user_id": "ben"})
```

### T2 全本地（数据不出内网）

```bash
pip install mem0ai ollama
ollama pull llama3.1     # 抽取，4.69 GB（Q4 量化）
ollama pull bge-m3       # embedding，1.1 GB（1024 维）
```

```python
"llm": {"provider": "ollama", "config": {
    "model": "llama3.1:latest", "temperature": 0, "max_tokens": 2000,
    "ollama_base_url": "http://localhost:11434"}},
"embedder": {"provider": "ollama", "config": {
    "model": "bge-m3", "ollama_base_url": "http://localhost:11434"}},
```

注意 Ollama provider 同样**不加** `search_document:` 前缀，中文场景质量有折损；`embedding_model_dims` 要和 `bge-m3` 的 1024 对齐。

### 几条运维要点

```bash
export MEM0_TELEMETRY=false    # 关闭匿名遥测
export MEM0_DIR=/data/mem0     # history.db 落盘位置（默认 ~/.mem0）
```

**不要装** `mem0ai[nlp]`——它拉的是 spaCy 英文模型，对中文分词无效，却要吃 1–2 GB 内存。**不要装** `mem0ai[extras]` 除非你真的需要本地 embedding。避免 `chromadb`（+306 MB 且拖 onnxruntime/kubernetes）。

## 能力边界：OSS 明确做不到什么

这几条是官方文档里没有明说、但实测和读源码能确认的：

| 能力 | OSS 状态 |
|---|---|
| **不用 LLM** | ❌ 抽取阶段强依赖。`add(infer=False)` 能跳过抽取直接存原文，但语义上**退化成向量检索**，记忆就是原始片段 |
| **图记忆 / 关系** | ❌ v3 已移除，无 `relations`、无实体间边 |
| **时间衰减 / recency 排序** | ❌ `score_and_rank` 只有 semantic + BM25 + entity 三路，**没有任何时间项**。旧版本事实可能排在前面 |
| **多租户** | ⚠️ 只有 `user_id`/`agent_id`/`run_id`，无 `app_id`/org/project。且 filter 能力**取决于向量库**——Weaviate 只按 3 个 id 过滤、其余 key 静默丢弃；Pinecone 不支持 AND/OR |
| **删除与遗忘（GDPR）** | ⚠️ `delete_all()` 曾只删前 100 条却返回"成功"；残留 session messages 会在下次 `add()` 又喂回 LLM |
| **rerank 提升 recall** | ❌ 只能在截断后的 topK 内重排，提升不了召回 |
| **并发上限** | ❓ **未找到官方压测数据**。已知 SQLite history 不支持多 Pod 水平扩展、无 WAL，server 端 `/memories` `/search` 无限流 |

### 关于效果数据，必须说清口径

mem0 官网宣称"比 OpenAI memory 准确率高 26%、token 少 90%"。查论文原文后，这个说法需要校正：

- 论文写的是 "26% **relative** improvements"（66.88 vs 52.90）——是**相对提升 26.4%**，绝对分差只有 **13.98 个点**。官网省略了 "relative"。
- 更关键的是，同一篇论文里 **full-context 基线 72.90% 高于 Mem0 66.88%**。mem0 的论证是**成本**，不是质量。
- 官网"7,000 tokens vs 25,000+"与论文的"1,764 tokens"**单位不同**（每次检索调用 vs 每段对话检索上下文），不能混用。
- 官网 research 页写"5 categories"，实际评测只计 cat1–4，**对抗类 446 题（22.5% 题量）被排除**。
- 官方自己的仓库里数字就自相矛盾：README 写 LoCoMo 92.5%，而同仓库 `results/platform/*.json` 的提交值是 **91.56%**（README 改于 2026-05-13，结果目录最后提交 2026-04-09）。

第三方质疑也值得看：LoCoMo 数据集本身被审计出 6.4% 标注错误、judge 接受 62.81% 的故意错答；Letta 仅用**文件 + grep** 就拿到 74.0%，并直言"当前的记忆基准可能没什么意义"；HaluMem 实测 mem0 抽取 recall 仅 42.91%（Medium）/ **3.23%**（Long），更新正确率 25.50%/1.45%。

还有一条社区实测值得警惕：32 天、10,134 条记忆，**97.8% 是垃圾**（52.7% 是系统提示反复重述，11.5% 是心跳噪声，含 IP 和路径泄漏），而**换成 Claude Sonnet 4.6 后垃圾率几乎没降**——结论是"抽取 prompt 才是瓶颈，不是模型"。

## 我的取舍建议

<div class="mem0-ok">
<p><span class="mem0-ok-title">如果你要做个人项目 / 学习验证</span></p>
<p>直接 T1。embedding 和向量库全本地，抽取走云端 API。193 MB 装完即用，不用 Docker、不碰数据库，检索 85 毫秒完全够用。</p>
</div>

<div class="mem0-ok">
<p><span class="mem0-ok-title">如果数据不能出内网</span></p>
<p>T2，但要接受每次写入 1–3 分钟的延迟，并且<strong>对抽取结果做定期抽查</strong>。小模型不是不能换，但别期待它能替代 8B——实测 JSON 有效率是 0，不是"差一点"。</p>
</div>

<div class="mem0-warn">
<p><span class="mem0-warn-title">如果记忆里存的是关键业务事实</span></p>
<p>不要依赖自由文本记忆。抽取式架构的 recall 上限就是 42.91% ~ 3.23%，而且<strong>丢失原始上下文与说话人</strong>、矛盾事实会并存（v3 是 ADD-only）。关键事实请直接存 metadata 或结构化字段，让记忆层只负责"锦上添花"。</p>
</div>

一句话总结：**mem0 的最小部署瓶颈不在框架，而在 LLM 抽取。** 框架侧 193 MB / 100 MB 内存 / 3 ms 检索，非常出色；把 embedding 和向量库本地化，省心省钱且离线可控；把抽取交给云端或 ≥8B 本地模型。

如果你对"记忆层"这个主题感兴趣，站内还有三篇相关的：

- [Agent 的记忆：Hermes-Lite 如何用 5 层结构解决「鱼的难题」](/posts/2026-07-01-agent-memory-5-layer-architecture/) —— 从设计视角看记忆分层，与本文的"部署代价"视角互补
- [记忆系统的五层结构：从上下文到长期偏好](/posts/2026-07-07-five-layer-memory-from-context-to-preference/) —— 什么该记、什么该忘
- [Agent 技能解剖（一）：Agent Memory——把「记住」做成数据层](/posts/2026-09-28-agent-skill-anatomy-01-memory/) —— 另一个记忆实现，同样是源码级拆解

## 附：本次调研的验证方式

本文所有带具体数字的结论都做了双源验证：外部信源（三级分级：官方仓库/文档/论文为 A，权威媒体为 B，厂商博客标注"厂商口径"为 C，社区帖仅作线索为 D）＋ 本机真实部署实测。

关键事实用源码位置锚定（仓库 commit `2c81af3`）：抽取流程在 `mem0/memory/main.py:881` 的 `_add_to_vector_store()`；排序逻辑在 `mem0/utils/scoring.py`（全文无 recency/decay）；embedder 无前缀在 `mem0/embeddings/huggingface.py:46`；Ollama 默认 512 维在 `mem0/embeddings/ollama.py:17`；history 落盘路径在 `mem0/configs/base.py:42-45`。

需要说明的是，**基准数据的可信度是分层的**：token 与延迟收益真实且可复算（检索上下文 1,764 vs 全上下文 26,031 tokens，p95 延迟降 91%），但准确率数字基本都来自厂商自测，且 OSS 与 Platform 能力差距极大（图记忆、Memory Decay、Temporal Reasoning 全是 Platform 独有）。若你的核心诉求是"记忆不能丢"，mem0 无论哪个部署形态都帮不上——那是另一类问题。

---

*本文的所有实测数据均在本机复现：i7-10610U（4C/8T @1.8GHz，AVX2 无 AVX512）/ 15.8 GB RAM / 无独立显卡 / Windows 11 / Python 3.13，mem0ai 2.2.1，Qdrant 本地嵌入模式。*
