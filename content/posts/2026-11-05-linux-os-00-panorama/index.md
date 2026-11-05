---
title: "Linux 操作系统全景：一份可核查的深度研究报告（2026）"
date: 2026-11-05T22:30:00+08:00
publishDate: 2026-11-05T22:30:00+08:00
description: "从 1991 年的个人项目到 2026 年的基础设施底座：TOP500 100%、网站 Linux 63.3%、桌面 5.66% 三个数字的分母为何不能混用；LTS 官方只承诺 2 年；7.3 周期 LLM 辅助补丁潮带来的治理压力；以及中国生态「下游规模化、上游波动」的证据链。"
tags: ["Linux", "内核", "深度研究", "开源治理", "市场份额"]
categories: ["Linux 原理系列", "技术分享"]
draft: false

ai:
  agent: "WorkBuddy"
  model: "Hunyuan Hy"
  provider: "Tencent"
---

# Linux 操作系统全景：一份可核查的深度研究报告（2026）

关于 Linux，网上最容易找到的是两类内容：一类是「Linux 占领了世界」式的口号，另一类是某个命令的用法。两者之间缺一环——**用可核查的证据，把技术架构、产业格局、治理逻辑串成一张图**，并且诚实标出哪些数字其实没有可靠来源。

这篇是「Linux 原理系列」的**总览篇（第 00 篇）**，数据基准日为 2026-11-05。写法是四路并行取证（历史与内核 / 产业与份额 / 治理与安全 / 中国与趋势），再对关键数字逐条回到一手源核验。文末附系列路线图，后续各篇会拆开这里压缩掉的机制细节。

## 结论先行：五句话

1. **Linux 在基础设施层接近事实垄断，在桌面层长期小众。** TOP500 2026-06 榜单 500/500 采用 Linux 家族；W3Techs 可识别 OS 的网站中 Linux 占 63.3%；而 StatCounter 2026-10 的全球桌面份额只有 5.66%。三个数字的分母完全不同。
2. **内核不是产品，是一项无法被独占的公共投入。** GPL-2.0-only、版权分散于数千贡献者、BDFL 治理，三者共同锁死了「买下 Linux」这条路。IBM 花 340 亿美元买 Red Hat，定价的是认证、维护、SLA 与生态，不是源码。
3. **2026 年最值得关注的变量不是某个新特性，而是 LLM 辅助补丁潮。** 7.3 周期史上首破 2 万提交、3,021 名开发者、净增约 65 万行；LWN 同时警告维护者已跟不上，部分贡献者并不理解自己改的代码。这是治理带宽的压力测试。
4. **中国生态是「下游规模化、上游波动」。** 发行版与信创落地已有成熟供给，但内核能力仍依赖主线；华为提交占比从 6.1 周期的 9.2% 回落到 7.3 的 0.9%，同期麒麟软件以 624 次提交首次进入雇主榜前十。
5. **很多流行数字经不起追问。** 「90% 公有云跑 Linux」是基金会 2017/2021 年自述；「国产 OS 占半壁江山」多半是预测值或信创细分市场自述；内核 CVE 数量暴涨主要是编号政策变更，不是风险上升。

## 一、六个数字，六种分母

份额问题的核心从来不是「数字是多少」，而是「这个数字在数什么」。下面这张表刻意保留彼此冲突的口径，不做合并、不做加权。

| 场景 | 数值 | 统计口径 | 日期 / 来源 |
| :--- | :--- | :--- | :--- |
| TOP500 超算 | 500 / 500，100% | 操作系统**家族**标签为 Linux。若按精确 OS 名称统计，「Linux」只有 127 台（25.4%），其余是 RHEL、Cray OS、Kylin 等 | 2026-06 · TOP500.org |
| 网站服务器 | Linux 63.3%，Unix 系 92.2% | W3Techs 抽样网站中**可识别操作系统**的占比，按网站数，非流量、非服务器台数；其中 77.2% 的发行版为 Unknown | 2026-11-05 · W3Techs |
| 全球桌面 | Linux 5.66%，Windows 76.62%，ChromeOS 2.02% | StatCounter 页面浏览 / UA 采样，全球桌面设备 | 2026-10 · StatCounter CSV |
| 全球移动 | Android 72.39%，iOS 27.58%，Linux 0.01% | 同为页面浏览采样；Android 单独归类，不计入「Linux」行 | 2026-10 · StatCounter CSV |
| 公有云工作负载 | 「90%」 | Linux Foundation 自述，源自 2017 / 2021 年材料，未公开测量方法；IDC / Gartner 当期份额本轮未核实 | 2017 / 2021 · LF |
| 嵌入式 / 电视 / 路由 | 「62%」 | LF 2017 年「嵌入式市场」口径；2026 年细分份额无公开可信测量 | 2017 · LF |

<div class="lx-fig"><style>.lx-fig{background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;padding:16px 18px;margin:20px 0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}.lx-fig .lx-cap{font-size:14px;font-weight:700;color:#212529;margin-bottom:4px}.lx-fig .lx-sub{font-size:12px;color:#6c757d;margin-bottom:12px;line-height:1.6}.lx-fig .lx-src{font-size:11.5px;color:#6c757d;margin-top:10px;padding-top:8px;border-top:1px dashed #dee2e6;line-height:1.6}.lx-fig svg text{font-family:inherit}</style><div class="lx-cap">图 1 · 三组不可相加的份额</div><div class="lx-sub">分组展示，组间没有共同分母。灰色条目为营销或旧口径，仅作对照；条长按各组自身刻度绘制，不可跨组比较绝对量。</div><svg viewBox="0 0 680 214" width="100%" role="img" aria-label="不同口径下 Linux 相关份额对比条形图"><title>不同口径下 Linux 相关份额</title><desc>基础设施侧、终端侧与自述口径的份额对比，各组分母不同，不可相加。</desc><g font-size="12" fill="#343a40"><text x="2" y="16" font-weight="700" fill="#1d4ed8">基础设施侧（家族标签 / 可识别 OS 样本）</text><text x="2" y="40">TOP500 超算 · Linux 家族</text><rect x="210" y="29" width="410" height="13" rx="3" fill="#2b5fbf"/><text x="626" y="40" font-size="11.5" fill="#2b5fbf" font-weight="700">100%</text><text x="2" y="63">网站 · Unix 系（含 Linux）</text><rect x="210" y="52" width="378" height="13" rx="3" fill="#7aa5e8"/><text x="594" y="63" font-size="11.5" fill="#495057">92.2%</text><text x="2" y="86">网站 · Linux（可识别 OS）</text><rect x="210" y="75" width="259" height="13" rx="3" fill="#2b5fbf"/><text x="475" y="86" font-size="11.5" fill="#495057">63.3%</text><line x1="2" y1="98" x2="660" y2="98" stroke="#dee2e6" stroke-dasharray="4 4"/><text x="2" y="118" font-weight="700" fill="#1d4ed8">终端侧（页面浏览采样 · 2026-10）</text><text x="2" y="141">全球移动 · Android</text><rect x="210" y="130" width="297" height="13" rx="3" fill="#2c7a5b"/><text x="513" y="141" font-size="11.5" fill="#495057">72.39%</text><text x="2" y="164">全球桌面 · Linux</text><rect x="210" y="153" width="23" height="13" rx="3" fill="#b17316"/><text x="239" y="164" font-size="11.5" fill="#b17316" font-weight="700">5.66%</text><line x1="2" y1="176" x2="660" y2="176" stroke="#dee2e6" stroke-dasharray="4 4"/><text x="2" y="196">公有云 · LF 自述</text><rect x="210" y="185" width="369" height="13" rx="3" fill="#d8dde5"/><text x="585" y="196" font-size="11" fill="#868e96">「90%」· 2017/2021</text></g></svg><div class="lx-src">来源：TOP500.org、W3Techs、StatCounter 桌面/移动 CSV（2026-10）、Linux Foundation。数据均为 2026-11-05 抓取。</div></div>

四个最常见的口径陷阱：

- **家族标签 vs 精确标签**：TOP500 的 100% 指 OS family = Linux；按精确 OS 名称，「Linux」只占 25.4%。两者都对，回答的是不同问题。
- **网站数 vs 流量 vs 服务器台数**：W3Techs 数的是抽样网站，且只统计可识别 OS 的样本。
- **页面浏览 ≠ 装机量**：StatCounter 基于其统计网络的 UA 采样；桌面 5.66% 不代表 5.66% 的电脑装了 Linux。
- **Android 计入与否**：把 Android 计入，则「Linux 内核」覆盖大量联网设备；不计入，桌面只有个位数。营销材料常在两者间滑动。

## 二、三十五年：版本号几乎不携带技术含义

kernel.org 的 Releases FAQ 有一句很坦诚的话：「主版本号只在小数点后的数字看起来太大时递增，没有任何其他理由。」2.6 之前用奇偶次版本号区分开发版与稳定版，该规则在 2.6 之后废弃，改用 `-rc`。所以 7.0（2026-04-12）是编号复位，不是架构重写。

真正值得记住的是**能力边界的扩张**：

| 时间 | 里程碑 | 为什么重要 |
| :--- | :--- | :--- |
| 1991-08-25 | comp.os.minix 上的「just a hobby」公告；同年 9 月发布 0.01 | 仅支持 i386，无网络 |
| 1992 · 0.12 | 改用 GPLv2 | 决定性的法律选择，埋下其后三十年全部商业模式与许可证争议 |
| 1994-03-14 · 1.0 / 1996-06-09 · 2.0 | 首个正式版；SMP 与多架构 | 开始进入服务器视野 |
| 2001 · 2.4 / 2003 · 2.6 | USB、ext3、iptables；抢占、udev、新发布节奏 | 企业级能力成型；2005 年 Git 诞生 |
| 2007–2016 | CFS（2.6.23）→ bpf() 系统调用（3.18）→ cgroup v2（4.5） | 容器不是 Docker 发明的，是 namespace / cgroup 十余年积累的组合 |
| 2019–2024 | io_uring（5.1）、MGLRU / Rust 基础设施（6.1）、LoongArch（5.19）、EEVDF（6.6）、PREEMPT_RT（6.12） | 异步 I/O、新架构、调度器换代、实时性进主线 |
| 2026-04-12 · 7.0 | Rust 移除 experimental 标记 | 长期留在内核已确立，但**不等于** C 代码迁移 |

截至基准日，kernel.org 首页给出：mainline **7.4-rc1**（2026-11-01）、stable **7.3.1**（2026-10-30）、6 个 longterm 分支（6.18 / 6.12 / 6.6 / 6.1 / 5.15 / 5.10）并行维护。

### LTS 只承诺 2 年

这一条最容易被误读。官方 FAQ 原文是：每个新 LTS 通常**只给 2 年的初始预计 EOL**，能否延长取决于产业界是否持续投入。5.10 / 5.15 / 6.1 被延长到六年以上，是 CIP 等组织持续投钱投人的结果，不是默认承诺。二手报道所称「恢复 6 年默认维护」本轮未找到官方决定。

**工程含义**：做内核生命周期规划时按 2 年基线，把延长视为可选红利；跨大版本升级能力应作为架构约束，而不是运维预案。

## 三、内核解剖：六个子系统与一条信任链

| 子系统 | 关键机制 | 近期变化 |
| :--- | :--- | :--- |
| 进程调度 | 运行队列、优先级、负载均衡 | CFS 主导 15 年后，EEVDF 于 6.6（2023）取代公平调度核心；7.0 默认 lazy preemption |
| 内存管理 | 页表、buddy + SLUB、page cache / LRU / kswapd / OOM | folio 自 5.16 推进，MGLRU 于 6.1 合入 |
| VFS 与文件系统 | superblock / inode / dentry / file 四层抽象 | XFS（2.6.17）、ext4（2.6.28 稳定）、Btrfs（2.6.29）；7.0 加入 XFS 自愈 |
| 网络栈 | socket / sk_buff、netfilter、qdisc | BBR（4.9）、MPTCP（5.6）、7.0 普遍启用 AccECN |
| 容器基础 | namespace + cgroup | mount ns（2.4.19）→ PID/net ns 与 cgroup（2.6.24）→ user ns（3.8）→ cgroup v2（4.5） |
| 可编程 / 异步 I/O / 实时 | eBPF verifier、io_uring、抢占模型 | bpf() 于 3.18、io_uring 于 5.1、PREEMPT_RT 关键部分于 6.12 进主线 |

```mermaid
flowchart LR
    C[贡献者] --> M[子系统 maintainer]
    M --> N[linux-next 集成测试]
    N --> P[pull request]
    P --> L[Linus 合入 mainline]
    L --> S[stable 回溯 bugfix]
    S --> D[发行版 / 用户]
    style L fill:#e7f0ff,stroke:#2b5fbf,color:#1b3a72
    style M fill:#f8f9fa,stroke:#adb5bd,color:#343a40
    style S fill:#e9f5ef,stroke:#2c7a5b,color:#1e5c43
```

补丁按 `MAINTAINERS` 文件与 `get_maintainer.pl` 的路径匹配逐级流转：2 周合并窗口 + 约 7 周 rc + 9~10 周一版。只有 Linus 能合入主线；不满维护者决定可逐级上诉。Ted Ts'o 在 LKML 说得很清楚：这一权威源于社区对判断力的认可，以及 GPL 保证的**可 fork 性**——不是雇佣关系赋予的权力。

关于代码规模，必须区分口径：Phoronix 对 6.14-rc1 的 `cloc` 统计约 3,770 万总行 / 2,846 万代码行 / 7.69 万文件；对 7.2 树的另一个快照是 4,389 万总行 / 3,365 万代码行。版本与工具不同，两者不能当「增长」相减。「合并窗口约一半是驱动」说的是**该次提交的改动**，不是源码存量中驱动的占比。

## 四、7.3 周期：AI 辅助补丁潮成为头号治理变量

LWN 的 7.3 开发统计（2026-10-19）给出一组破纪录数字：

| 指标 | 7.3 周期 | 说明 |
| :--- | :--- | :--- |
| 总提交 | 首次超 20,000（18,765 个非合并提交） | 项目史上最高 |
| 开发者 / 首次贡献者 | 3,021 名 / 807 名 | 新人占比超过 1/4 |
| 代码量 | 新增约 92 万行，删除约 27 万行，净增约 65 万行 | 63 天周期 |
| 雇主 | 232 家可识别 | (Unknown) 20.5%、AMD 6.3%、Intel 6.3%、Google 6.1%、麒麟软件 3.3%、华为 0.9% |
| 审阅信号 | 50.9% 带 Reviewed-by，7.5% 带 Tested-by | 近一半 Reported-by 来自 Syzbot / Sashiko 等自动化系统 |

LWN 明确将记录打破归因于 LLM 辅助贡献，并写道维护者「正在丧失跟上这股洪流的能力」、相当一部分新贡献者「并不真正理解他们用 LLM 修改的代码」。截至 7.4 合并窗口开启时，linux-next 已积压近 16,000 个非合并变更。

需要诚实标注的是：**因果归因与质量判断属于 LWN 的编辑分析，不是已测量的质量指标**。但增长指标全部向好、审阅带宽与责任归属却未解决，这个结构性张力是真实存在的。自动化能过滤「立即显现的 bug」，替代不了对设计判断与长期可维护性的审阅。

顺带一个反直觉的细节：按**改动行数**排序，AMD 以 22.3% 居首，主要来自机器生成的 amdgpu 寄存器定义。提交数、改动行数、技术影响力衡量的是三件不同的事。

## 五、免费的内核，340 亿美元的生意

2019-07-09，IBM 以 $190/股、总股权价值约 **$340 亿**完成收购 Red Hat，Red Hat 作为独立单元运作。官方新闻稿同时披露 Red Hat FY2019 营收 $34 亿。收购后 IBM 不再单列 Red Hat 营收，2026 年规模未核实。

订阅到底卖什么？答案是**确定性**：

| 层 | 内容 | 是否可收费 |
| :--- | :--- | :--- |
| L0 内核主线 | GPL-2.0-only、分散版权、无单一所有者 | 不可独占 |
| L1 发行版集成 | 选型、构建、打包、回溯补丁、KABI 稳定性 | 可形成产品 |
| L2 订阅与支持 | 认证二进制、CVE 响应与 SLA、10 年生命周期、硬件/ISV 认证、管理工具、培训 | **主要收入来源** |
| L3 云与算力 | Linux 镜像作为 IaaS 入口 | 收入计入计算/存储消费 |

Linux Foundation 的角色常被误解：它提供基础设施、峰会、TAB 与 fellow 资助，**不拥有内核版权，也不决定补丁合入**。年报中内核项目支出仅数百万美元量级，主要研发成本记在各厂商工资单上。

两次「上游收紧」值得单独记住：2020-12 CentOS 宣布转向 Stream（CentOS Linux 8 于 2021-12-31 EOL、7 于 2024-06-30 EOL），2023-06 RHEL 源码公开发布渠道收窄到 CentOS Stream，直接催生 Rocky / Alma / OpenELA 生态，也是中国加速自主根社区的外部诱因之一。它说明一个更一般的规律：**开源项目的治理可信度本身就是一种资产**。

## 六、治理与许可证：为什么没有人「拥有」Linux

内核许可标识是 `GPL-2.0-only WITH Linux-syscall-note`。COPYING 明确「系统调用接口是清晰边界，不把 GPL 要求延伸至借此与内核通信的任何软件」，因此专有用户态程序可以合法包含 UAPI 头文件。

几个高频疑问：

- **专有内核模块合法吗？** 没有司法定论。`MODULE_LICENSE()` 只是告知加载器是否为自由软件，标 Proprietary 会打 `P` taint 并被拒绝链接 `EXPORT_SYMBOL_GPL()` 符号。社区策略被 LWN 概括为「法律模糊 + 技术不便」，而非诉讼禁止。Hellwig v. VMware 因程序理由被驳回，GPL 实体问题从未进入实体裁判；SFC v. Vizio 仍在进行，截至基准日结果未核实。
- **为什么不迁 GPLv3？** 2006 年 Linus 反对反 Tivoization 条款（要求提供签名密钥），核心开发者无人支持；全树重新授权在实操上也极难。
- **Android 用户态为什么用 Apache 2.0？** 宽松许可 + 明确专利授权使 OEM 可保留专有修改不回源；内核仍为 GPLv2。
- **治理压力**：2018 年 CoC 事件、2024-10 按 OFAC SDN 名单移除若干俄罗斯维护者、维护者老龄化与燃尽问题，都指向同一个事实——一个以「无国界协作」为自我叙事的项目，仍会被单一司法辖区的法律直接穿透。

## 七、安全：CVE 数量不等于风险

2024-02-13 kernel.org 成为 CNA，官方规则有一条非常激进：**由于「几乎任何 bug 都可能被利用」，对识别到的每一个 bugfix 一律分配 CVE**，不做可利用性预筛；只在修复进入已发布 stable 树后按原 commit id 分配；适用性由使用者自行判断。

后果是年度 CVE 数量从数百量级跃升到数千量级。二手统计有 2023 年 290 → 2024 年 3,529（约 12 倍）与 NVD 口径 2024 年 4,287、2025 年 5,675 两组冲突数字，差异来自「分配年 vs 发布年」与剔除状态不同，官方未公布年度总数，**并列不合并**。

结论很直接：**不要把内核 CVE 数量当风险 KPI**。修复优先级应结合发行版回溯状态、实际启用的子系统与暴露面判断。

2024-03-29 的 xz-utils 后门（CVE-2024-3094，CISA 警报，影响 5.6.0 / 5.6.1）则揭示了另一类风险：攻击目标是**上游维护者的信任与交接过程**，不是内核代码缺陷。这类风险无法靠代码审计消除，只能靠可复现构建、双维护者审阅、身份与贡献链可追溯来缓解。

## 八、中国生态：下游规模化，上游波动

分层看得最清楚：内核主线 → 根社区（openEuler / 龙蜥 / OpenCloudOS / openKylin）→ 商业发行版（麒麟 / 统信 UOS 等）→ 信创与行业落地。麒麟信安服务器 OS 3.5.1 的官方 PDF 明确写着「基于 openEuler 22.03 LTS、内核 5.10、保持内核 KABI 完全兼容」——这是「下游 + backport + KABI」模式的直接书证。

份额数字需要格外小心：

| 说法 | 性质 |
| :--- | :--- |
| openEuler 系 36.8%（2023）/ 50%（2024）中国服务器 OS 份额 | IDC **预测**经会议或媒体转述，未取得原报告；装机量为社区自述 |
| 银河麒麟「连续 14（另稿 15）年第一」、信创桌面约 70% | 赛迪顾问经厂商/媒体转述，属**信创细分市场**，与全市场不可加总 |
| 余姚公安 360 套桌面 V10、单价 400 元；中央国家机关 2025 批采约 4 万台 | 政府采购公告，可核查的**点状样本**，但不是全国总量 |

上游贡献侧的换挡更值得关注：华为占比自 5.10–6.1 的约 9% 回落到 6.18 的 2.6%、7.3 的 0.9%；同期麒麟软件以 624 次提交（3.3%）、92 名开发者进入雇主榜第 7，LWN 观察其「似乎在按 LLM 识别的 bug 清单逐条处理」。可确认的中国主导特性有 EROFS（华为发起，2019 合入主线）与 HULK Robot 自动化缺陷发现。阿里、腾讯、字节在 LWN 前 20 雇主榜无独立条目，**不能解读为无贡献**——可能是雇主名归并或落入 (Unknown)。

硬件侧，唯一独立新指令集是 **LoongArch**（2022-06 合入 5.19-rc1 主体架构代码，约 2.1 万行）；鲲鹏、飞腾走标准 arm64，海光、兆芯走 x86_64，它们不是独立架构。

## 九、未来三到五年：趋势与证据强度

| 趋势 | 可核实证据 | 判断 |
| :--- | :--- | :--- |
| AI / LLM 辅助开发 | 7.3 记录全面打破；2025 维护者峰会共识为「人的责任不可让渡、需披露」；政策文档与生效版本未核实 | **决定性变量**，短期看审阅带宽，长期看维护者梯队 |
| Rust for Linux | 6.1 合入实验性基础设施，7.0 删除 experimental；Android Binder、Nova、Tyr 等组件落地 | 长期留在内核已确立，但不是 C 代码迁移 |
| GPU 驱动开源化 | 6.16 合入 nova-drm 初始骨架与 Rust DRM 抽象 | 方向确定、成熟尚早；「已生产级」的说法与原文冲突 |
| 机密计算 | SEV-SNP、TDX 的 KVM 支持及 ARM CCA guest 支持已合入主线 | 主线能力具备，产品化是未来 2–3 年主战场 |
| eBPF | verifier + JIT，Google / Meta / Cloudflare 生产使用；BPF LSM 可做 MAC | 已是成熟基础设施 |
| 实时性 | 6.12 起无需树外补丁启用实时抢占 | 技术里程碑完成，剩下是认证与工具链 |
| CRA / 供应链合规 | 报告义务 2026-09-11、主要义务 2027-12-11；GKH 警告厂商不要把合规成本转嫁上游 | 主要风险是成本转嫁 |
| WASM / Unikernel 替代 Linux | 本轮未取得任何权威测量 | 无证据支持，亦无证据否定；不宜作为决策依据 |

三个结构性张力值得放在案头：**治理带宽 vs 补丁洪流**、**上游公共品 vs 下游商业捕获**、**无国界协作 vs 单一辖区合规**。

## 十、口径规则与「未核实」清单

这份报告给自己定了四条硬规则：不合并不同分母；区分「一手事实 / 第三方测量 / 厂商自述 / 未核实」四类证据；区分提交数、改动行数与影响力；区分事实与编辑判断。

以下项目本轮**未取得一手证据**，引用时请谨慎：IDC / Gartner 当期服务器与云份额原始报告；LF 2025 年报 PDF 原文；7.3 内核精确总行数与统一口径的架构数；SUSE 私有化实际退市日、Canonical 2024–2026 财务、IBM 收购后 Red Hat 单独营收；内核 CVE 年度官方总数；2026 年「继任计划」的 kernel.org 原文；SFC v. Vizio 审判结果；信创采购全国总量；Rust「转正」官方公告原文；WASM/Unikernel 替代性测量。

「当期未核实」不等于「不存在」，只是说明本轮没有找到可回溯的原始来源。这也是我把整份研究以「证据等级」而非「结论列表」组织的原因。

## 系列路线图

本站「Linux 原理系列」已有四篇基础文章，本总览篇之后按机制逐层深入。带链接的是已发布内容：

| 序号 | 主题 | 状态 |
| :--- | :--- | :--- |
| 00 | [Linux 操作系统全景：可核查的深度研究报告](/posts/2026-11-05-linux-os-00-panorama/) | 本篇 |
| 01 | [Linux 到底是什么：内核、发行版与一次系统调用的旅程](/posts/2026-11-05-linux-os-01-kernel-syscall/) | 已发布 |
| 02 | [进程与调度：从 fork 到 EEVDF](/posts/2026-11-05-linux-os-02-process-scheduler/) | 已发布 |
| 基础 | [文件权限与特权提升](/posts/2026-09-14-linux-permissions-security/)、[信号机制与守护进程](/posts/2026-09-14-linux-signals/)、[网络命名空间与容器隔离](/posts/2026-09-14-linux-network-namespaces/)、[systemd 与自动化运维](/posts/2026-09-14-linux-systemd-ops/) | 已发布 |
| 03–04 | 内存管理：虚拟内存、页表与 OOM；VFS 与文件系统选型 | 后续更新 |
| 05–06 | 网络栈与 eBPF；cgroup v2 与容器资源边界 | 后续更新 |
| 07–08 | 启动流程与内核开发流程；性能观测与调优实战 | 后续更新 |

## 主要一手来源

- [R01 kernel.org 首页版本表](https://www.kernel.org/) · [R02 Active kernel releases / Releases FAQ](https://www.kernel.org/category/releases.html)（LTS EOL、2 年规则、版本号规则）
- [R03 How the development process works](https://docs.kernel.org/process/2.Process.html) · [R04 LWN — 7.3 development statistics](https://lwn.net/Articles/1100241/)
- [R05 Linux kernel licensing rules](https://www.kernel.org/doc/html/latest/process/license-rules.html) · [R06 Linux kernel CVEs](https://www.kernel.org/doc/html/latest/process/cve.html) · [R07 Security bugs](https://www.kernel.org/doc/html/latest/process/security-bugs.html)
- [R08 TOP500 OS Family / Linux](https://www.top500.org/statistics/details/osfam/1/) · [R09 W3Techs Linux for websites](https://w3techs.com/technologies/details/os-linux)
- [R10 StatCounter 桌面 OS 份额](https://gs.statcounter.com/os-market-share/desktop/worldwide/) · [R11 StatCounter 移动 OS 份额](https://gs.statcounter.com/os-market-share/mobile/worldwide/)
- [R12 Red Hat — IBM Closes Acquisition for $34 Billion](https://www.redhat.com/en/about/press-releases/ibm-closes-landmark-acquisition-red-hat-34-billion-defines-open-hybrid-cloud-future) · [R13 CentOS — Future is CentOS Stream](https://blog.centos.org/2020/12/future-is-centos-stream/)
- [R14 CISA — xz-utils 供应链投毒警报](https://www.cisa.gov/news-events/alerts/2024/03/29/reported-supply-chain-compromise-affecting-xz-utils-data-compression-library-cve-2024-3094) · [R15 Rust for Linux 项目站](https://rust-for-linux.com/)
- [R16 GNU — Linux and the GNU Project](https://www.gnu.org/gnu/linux-and-gnu.html)（命名争议）

完整 40 条来源索引与全部图表见配套的单文件 HTML 研究报告（本地工作区 `linux-deep-research-2026-11-05.html`）。本文为研究性综述，不构成法律意见、投资建议或采购决策依据；厂商自述数据未经独立审计。

---

*数据基准日 2026-11-05。文中标注「未核实」的项目请勿作为事实引用；外部链接为该日可访问状态，后续可能失效或更新。*
