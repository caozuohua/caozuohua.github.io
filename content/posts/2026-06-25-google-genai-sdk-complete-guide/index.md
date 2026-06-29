---
title: "google-genai SDK 全流程指南：Vertex AI + Gemini API 实战"
date: 2026-06-25
publishDate: 2026-06-25
description: "Google 官方 Python SDK google-genai 完整教程，覆盖 Vertex AI / Gemini API 双模式认证、streaming、function calling、thought_signature 多轮坑、代理层设计模式"
tags: ["google", "genai", "gemini", "vertex-ai", "python", "sdk", "proxy", "streaming"]
categories: ["技术"]
draft: false
aliases: ["/posts/google-genai-sdk-complete-guide/"]
---

## 为什么要写这篇？

最近在给 Hermes-lite 接入 Gemini 3.x 模型时，踩了不少 google-genai SDK 的坑——尤其是多轮 tool call 时 `thought_signature` 丢失导致 400、streaming 模式下 function_call args 是片段、`response.text` 莫名其妙打 stderr Warning 等问题。

查了一圈官方文档和社区资料，发现这些坑分散在各处，所以整理了一篇一站式指南，把从安装到上线的完整路径、所有踩坑点都写清楚。

---

## 一、SDK 概览

**包名**：`google-genai`（PyPI）
**仓库**：googleapis/python-genai
**当前版本**：v2.10.0（2026-06-24）
**Python**：3.9+
**License**：Apache-2.0

google-genai 统一封装了两条后端：

- **Gemini Developer API**：`api_key` 认证，适合快速开发
- **Vertex AI**：`project + location`，gcloud ADC 认证，VPC 上最方便

通过 `Client` 的一个接口切换，代码几乎零改动。

---

## 二、Google Cloud VPS 上全流程配置

### 2.1 环境准备

```bash
# 创建 venv（推荐 Python 3.12+）
python3 -m venv /opt/genai-env
source /opt/genai-env/bin/activate

# 安装 SDK
pip install google-genai

# 验证
python3 -c "from google import genai; print('OK', google.genai.__version__)"
```

### 2.2 认证：Vertex AI 模式（gcloud ADC）

VPC 上最方便——**Application Default Credentials**，无需手动管理密钥。

```bash
# 登录（交互式，只需首次）
gcloud auth login

# 设置项目
gcloud config set project YOUR_PROJECT_ID

# 验证 ADC
gcloud auth application-default login

# 确认权限（需要 roles/aiplatform.user 或更大角色）
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud config get-value account)"
```

**环境变量方式（可选，覆盖默认）**：

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="global"   # 或 us-central1 等
```

### 2.3 认证：API Key 模式（Gemini Developer API）

```bash
export GOOGLE_API_KEY="AIza..."
# 或
export GEMINI_API_KEY="AIza..."   # 优先级低于 GOOGLE_API_KEY
```

### 2.4 创建 Client

```python
from google import genai

# Vertex AI（自动读 ADC）
client = genai.Client()

# Vertex AI（显式指定）
client = genai.Client(
    vertexai=True,
    project="your-project-id",
    location="global",
)

# Gemini Developer API
client = genai.Client(api_key="AIza...")
```

### 2.5 代理配置（VPC 走代理访问 Google API）

```bash
# 环境变量
export HTTPS_PROXY="http://proxy-host:port"
export HTTP_PROXY="http://proxy-host:port"

# 或代码中指定
from google.genai import types
http_options = types.HttpOptions(
    base_url="https://my-proxy.example.com",
)
client = genai.Client(vertexai=True, project="...", http_options=http_options)
```

---

## 三、核心用法

### 3.1 基础文本生成

```python
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Explain quantum computing in 3 sentences.",
)
print(response.text)
```

**注意**：`response.text` 是快捷属性。如果 response 包含 function_call parts，访问 `.text` 会 emit 一个 stderr Warning。安全做法是遍历 `response.candidates[0].content.parts`。

### 3.2 多轮对话

```python
# 单轮
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=["Hello, I'm Bob.", "What's my name?"],
)

# 多轮（手动管理 history）
history = [
    {"role": "user", "parts": [{"text": "My name is Bob."}]},
    {"role": "model", "parts": [{"text": "Nice to meet you, Bob!"}]},
    {"role": "user", "parts": [{"text": "What did I just say?"}]},
]
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=history,
)
```

### 3.3 Streaming

```python
for chunk in client.models.generate_content_stream(
    model="gemini-3.5-flash",
    contents="Write a long essay on AI safety.",
):
    # chunk 是 Candidate 对象，不是 str
    for part in chunk.candidates[0].content.parts:
        if part.text:
            print(part.text, end="", flush=True)
        # thought part（thinking models）
        if part.thought:
            print(f"[THOUGHT]: present, thought_signature={'yes' if part.thought_signature else 'no'}")
```

**⚠️ 避坑**：不要用 `chunk.text`，它在有 function_call 时打 stderr Warning。遍历 `parts`。

### 3.4 Function Calling

```python
from google.genai import types

# 定义工具
get_weather_func = types.FunctionDeclaration(
    name="get_current_weather",
    description="Get the current weather in a given location",
    parameters={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City name",
            }
        },
        "required": ["location"],
    },
)

# 调用
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="What's the weather in Berlin?",
    config=types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[get_weather_func])],
    ),
)

# 提取 function call
for part in response.candidates[0].content.parts:
    if part.function_call:
        fn = part.function_call
        print(f"Call: {fn.name} with {fn.args}")
        # 执行你的函数
        result = {"temperature": 22, "condition": "Sunny"}

# 第二轮：把结果喂回去
function_response = types.Part.from_function_response(
    name=fn.name,
    response={"result": result},
)

final_response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents=[
        response.candidates[0].content,  # 原始 assistant message
        types.Content(role="user", parts=[function_response]),
    ],
    config=types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[get_weather_func])],
    ),
)
print(final_response.text)
```

---

## 四、Gemini 3.x 的 thought_signature 坑（重点！）

这是接入 Gemini 3.x 时最容易踩的坑，也是文档里说得最模糊的地方。

### 问题现象

第二轮 tool call 返回 400：

```
"Function call is missing a thought_signature"
```

### 原因

Gemini 3.x 模型在 thinking 模式下会返回 `thought_signature`（二进制 blob）。**多轮 tool call 时必须在下一轮把 thought_signature 原样传回**，否则校验失败。

### 三种解法

**解法 1：Interactions API（SDK 自动处理，推荐）**

```python
# SDK 自动管理 thought_signature，不用手动传
interaction = client.interactions.create(model="gemini-3.5-flash")
```

**解法 2：手动 generate_content（自己捕获和回放）**

```python
# 第一轮
response = client.models.generate_content(...)

# 提取 thought_signature
thought_sigs = {}
for part in response.candidates[0].content.parts:
    if part.function_call and part.thought_signature:
        thought_sigs[part.function_call.id] = part.thought_signature

# 第二轮：把 thought_signature 塞回每个 function_call
for part in response.candidates[0].content.parts:
    if part.function_call and part.function_call.id in thought_sigs:
        part.thought_signature = thought_sigs[part.function_call.id]
```

**解法 3：Proxy 层兜底策略**

上游框架（如 Hermes）不传 `extra_content` 时，proxy 在 response 时缓存 `{tool_call_id: signature_bytes}`，下一轮 request 时自动注入。这是最务实的方案——不动上游核心，只在 proxy 层做适配。

---

## 五、Streaming + Function Call 组合

Streaming 模式下 function call 的 arguments 是**增量 delta**，需要聚合：

```python
accum_args = ""
accum_name = ""

for chunk in client.models.generate_content_stream(
    model="gemini-3.5-flash",
    contents="Get weather for Berlin",
    config=types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=[get_weather_func])],
    ),
):
    for part in chunk.candidates[0].content.parts:
        if part.function_call:
            accum_name = part.function_call.name
            # args 是 JSON 字符串 delta
            accum_args += part.function_call.args

# 聚合后解析
import json
if accum_name:
    args = json.loads(accum_args)
    print(f"Execute {accum_name}({args})")
```

**⚠️ 避坑**：`part.function_call.args` 在 streaming 中是**不完整的 JSON 片段**，必须全部拼接完再 `json.loads()`，否则 JSONDecodeError。

---

## 六、OpenAI 兼容代理模式（Proxy Pattern）

这是我在 Hermes-lite 上实际用的方案。当上游框架只支持 OpenAI API 时，用 proxy 桥接到 google-genai：

```
Upstream (OpenAI protocol) --> Proxy (127.0.0.1:port) --> google-genai SDK --> Vertex AI
```

**为什么不改上游核心**：

- 上游可能有 100+ provider，改一个影响全局
- Proxy 独立测试、独立重启、独立 debug
- 上游升级时零改动

**核心翻译点**：

| OpenAI 概念 | Gemini 概念 | 翻译 |
|-------------|-------------|------|
| `role: "function"` (tool result) | `role: "user"` + `function_response` part | 必须改 |
| `parts: []` (empty) | 拒绝："Model input cannot be empty" | 用 `"."` 占位 |
| `tool_calls[].id` | `function_call.id` | 映射 |
| `extra_content.google_thought_signature` | `part.thought_signature` (binary) | base64 编码/解码 |
| `chunk.text` (streaming) | 遍历 `chunk.candidates[0].content.parts` | 避免 Warning |
| `model: "vertexai:gemini-3.5-flash"` | `model: "gemini-3.5-flash"` | 剥离前缀 |

**前缀清洗**：上游可能传 `vertexai:gemini-3.5-flash` 或 `vertexai/gemini-3.5-flash`，proxy 需剥离：

```python
PREFIXES = ("vertexai", "vertex", "vertex-ai", "vertexai-genai")
# 先按 : 分割，再按 / 分割
```

---

## 七、Vertex AI 特有配置

### 可用模型（2026-06）

| 模型 ID | 特点 | Context |
|---------|------|---------|
| gemini-3.5-flash | 最新 flash，性价比最高 | 1M |
| gemini-3.1-flash-lite | 低成本，适合简单任务 | 1M |
| gemini-3.1-pro | 最强推理 | 1M |
| gemini-3-flash-preview | 3 系列 preview | 1M |
| gemini-2.5-pro | 上一代旗舰 | 1M |
| gemini-2.5-flash | 上一代 flash | 1M |

### 安全设置（Vertex AI 特有）

```python
from google.genai import types

response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="...",
    config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ],
    ),
)
```

### 系统指令

```python
response = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="Hello",
    config=types.GenerateContentConfig(
        system_instruction="You are a helpful weather assistant. Always respond in JSON.",
    ),
)
```

---

## 八、避坑速查

| 现象 | 原因 | 解决 |
|------|------|------|
| `response.text` 打 stderr Warning | 含 function_call parts 时触发 | 遍历 `parts` 代替 `.text` |
| 400 "Model input cannot be empty" | Gemini 拒绝空 parts | 空字符串用 `"."` 占位 |
| 400 "missing a thought_signature" | 多轮 tool call 没回传 signature | Interactions API 或手动捕获回放 |
| `json.loads(args)` 抛 JSONDecodeError | streaming 中 args 是片段 | 全部拼接完再 parse |
| `project` + `api_key` 同时传 → ValueError | 两种认证互斥 | 只传一组 |
| `base_url` 不生效 | 构造函数不支持 | 用 `types.HttpOptions(base_url=...)` |

---

## 九、调试工具箱

```python
# 1. 查看原始 HTTP 请求
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. 检查 ADC 是否生效
import google.auth
creds, project = google.auth.default()
print(f"Project: {project}, Credentials type: {type(creds).__name__}")

# 3. 验证模型可用性
for model in client.models.list():
    print(model.name)
    break

# 4. curl 直接调 Vertex AI REST API
# curl -X POST \
#   -H "Authorization: Bearer $(gcloud auth print-access-token)" \
#   -H "Content-Type: application/json" \
#   "https://us-central1-aiplatform.googleapis.com/v1/projects/PROJECT_ID/locations/us-central1/publishers/google/models/gemini-3.5-flash:generateContent" \
#   -d '{"contents": [{"role": "user", "parts": [{"text": "Hello"}]}]}'
```

---

## 十、总结：决策树

```
需要接入 Gemini 模型？
├── 上游支持 OpenAI API？
│   ├── 是 → 写 Proxy（OpenAI → google-genai）
│   └── 否 → 直接用 google-genai SDK
├── 认证方式？
│   ├── Vertex AI（VPC 推荐）→ gcloud ADC（免密钥）
│   └── Gemini API → API Key
├── 需要 streaming？
│   ├── 是 → generate_content_stream + 遍历 parts
│   └── 否 → generate_content
├── 需要 function calling？
│   ├── 是 → 定义 FunctionDeclaration + 处理 thought_signature
│   └── 否 → 直接传 tools
└── 多轮对话？
    ├── 简单 → 手动管理 history list
    └── 复杂 → 用 Interactions API（SDK 自动管理 state）
```

**个人建议**：如果是新项目，直接用 Vertex AI + ADC + Interactions API，几乎不用处理密钥和 state 管理。如果是老项目接 Gemini（比如我这种场景），Proxy 模式是最平滑的迁移路径。
