---
title: "启动流程与内核开发：从 UEFI 到第一个补丁"
date: 2026-11-05T21:20:00+08:00
publishDate: 2026-11-05T21:20:00+08:00
description: "把开机拆成固件、引导器、内核解压、initramfs、真实 root 与 PID 1 六段，给出按段定位启动故障的命令；再讲清内核开发为什么走邮件列表、MAINTAINERS 与合并窗口，以及本地编译验证的安全边界。"
tags: ["Linux", "启动流程", "内核开发", "initramfs", "systemd"]
categories: ["Linux 原理系列"]
draft: false

ai:
  agent: "WorkBuddy"
  model: "Hunyuan Hy"
  provider: "Tencent"
---

# 启动流程与内核开发：从 UEFI 到第一个补丁

**结论先行**：开机不是「一下子进系统」，而是一条**信任链 + 初始化链**：固件把控制权交给引导器，引导器把内核与 initramfs 载入内存，内核初始化硬件后先用 initramfs 里的临时根找到真正的根文件系统，最后才把 PID 1 交给用户态。启动故障的定位方法因此非常朴素——**先判断卡在哪一段，再去看那一段的日志**。内核开发同理：它不是 GitHub 式的 PR 流程，而是「子系统维护者分层 + 邮件列表补丁 + 合并窗口」的制度。

本篇是「Linux 原理系列」第 07 篇，衔接[第 04 篇文件系统](/posts/2026-11-05-linux-os-04-vfs-filesystems/)与[第 00 篇全景报告](/posts/2026-11-05-linux-os-00-panorama/)中的开发流程部分。

## 一、六段启动链

```mermaid
flowchart LR
    A["UEFI / BIOS 自检"] --> B["GRUB / systemd-boot"]
    B --> C["内核解压与 start_kernel"]
    C --> D["initramfs 临时根"]
    D --> E["挂载真实 root"]
    E --> F["PID 1 systemd → targets"]
    style C fill:#e7f0ff,stroke:#2b5fbf,color:#1b3a72
    style D fill:#f8f9fa,stroke:#adb5bd,color:#343a40
    style F fill:#e9f5ef,stroke:#2c7a5b,color:#1e5c43
```

| 段 | 做了什么 | 卡住时的典型表现 |
| :--- | :--- | :--- |
| 固件 | 硬件初始化、安全启动校验、找 EFI 启动项 | 黑屏、找不到启动设备 |
| 引导器 | 读配置、加载 `vmlinuz` 与 `initrd`、传内核参数 | GRUB 菜单/救援模式、`error: file not found` |
| 内核 | 解压、初始化 CPU/内存/中断、探测设备驱动 | Kernel panic、无法识别磁盘 |
| initramfs | 提供挂载真实根所需的驱动（LVM、RAID、加密、NVMe） | `dracut` 救援 shell、找不到 root 设备 |
| 真实 root | 切换根、执行真正的 init | `Failed to mount /sysroot` |
| PID 1 | systemd 按 target 并行拉起服务 | 服务超时、进入 emergency mode |

**initramfs 为什么存在**：内核不可能把天下所有磁盘控制器、LVM、LUKS 驱动都编进主镜像，于是发行版生成一个包含「本机所需驱动」的临时根，先靠它把真正的根挂上。所以换主板、换磁盘控制器、加 LUKS 或升级内核后忘记重建 initramfs，是启动失败的经典原因。

## 二、按段定位：一份可复用的命令清单

```bash
# 本次/上次启动的日志与耗时
journalctl -b                       # 本次启动全部日志
journalctl -b -1                    # 上次启动（崩溃后排查必备）
journalctl -b -p err                # 只看错误级
dmesg -T | tail -60                 # 内核环形缓冲，含硬件/驱动早期消息
systemd-analyze                     # 内核 + 用户态各耗时
systemd-analyze blame | head -15    # 最慢的服务
systemd-analyze critical-chain      # 关键依赖链

# 引导与内核参数
cat /proc/cmdline                   # 实际生效的内核参数
efibootmgr -v                       # UEFI 启动项（UEFI 系统）
ls -lh /boot/vmlinuz-* /boot/initramfs-*
lsinitrd /boot/initramfs-$(uname -r).img | head -30   # RHEL 系；Debian 系用 lsinitramfs

# 重建 initramfs（改动驱动/加密配置后）
dracut -f                           # RHEL / Fedora 系
update-initramfs -u -k all          # Debian / Ubuntu 系
```

| 现象 | 优先检查 |
| :--- | :--- |
| 内核 panic 且提到 `VFS: Unable to mount root fs` | initramfs 缺驱动、root= 参数或 UUID 变了 |
| 卡在 `A start job is running for dev-xxx.device` | fstab 里的设备不存在或超时，检查 UUID 与 `nofail` |
| 升级内核后起不来 | 引导器配置未更新、initramfs 未重建、模块签名/Secure Boot 拒绝加载 |
| 服务大面积超时 | 依赖顺序、网络未就绪、磁盘只读，`journalctl -b -u <unit>` |
| 只有某次启动异常 | `journalctl -b -1` 与 `journalctl --list-boots` 对比 |

内核模块这一层也要会看：

```bash
uname -r
lsmod | head
modinfo <module>                    # 参数、依赖、签名信息
ls /lib/modules/$(uname -r)/
cat /proc/sys/kernel/printk        # 控制台日志级别
```

启用 Secure Boot 的机器要求内核模块带可信签名，树外模块（显卡驱动、ZFS、自建驱动）常因此静默加载失败；`dmesg` 里找 `module verification failed` 或 `Required key not available`。DKMS 的作用是让树外模块随内核升级自动重编译，**不解决签名问题**。

## 三、内核开发流程：邮件列表，不是 Pull Request

[第 00 篇全景报告](/posts/2026-11-05-linux-os-00-panorama/)给过一张流程图，这里补上可操作的部分。主线开发是 **2 周合并窗口 + 约 7 周 rc + 9~10 周一版**；只有 Linus 合入 mainline，路径是「贡献者 → 子系统 maintainer → linux-next 集成 → pull request → Linus」。

```bash
# 1. 找到该改哪儿、该发给谁（补丁文件准备好后）
git clone --depth=1 https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
scripts/checkpatch.pl --no-tree 0001-my-fix.patch
scripts/get_maintainer.pl drivers/net/foo/bar.c      # 按 MAINTAINERS 路径匹配

# 2. 生成带 DCO 签名的补丁
git commit -s -m "net: foo: fix off-by-one in bar"
git format-patch -1
# 3. 用 git send-email 发给 get_maintainer.pl 给出的收件人 + 对应 linux-* 邮件列表
```

几个新手最容易踩的点：

- **`Signed-off-by` 是 DCO 声明**，表示你有权以该许可证贡献这段代码，不是「签字画押」。`git commit -s` 自动生成。
- **收件人靠 `get_maintainer.pl`，不是凭感觉抄邮件列表**；同时 Cc 相关列表，让评审公开可追溯。
- **先过 `checkpatch.pl`**：编码风格、行宽、提交信息格式等机械问题应在发出前解决。
- **Rust 状态别误读**：7.0 移除了 experimental 标记，但各子系统 maintainer 仍可拒绝 Rust，也不等于 C 代码迁移——这一点在全景报告里有证据等级标注。

本地编译验证（**只在测试机做**）：

```bash
cp /boot/config-$(uname -r) .config
make olddefconfig
make -j"$(nproc)"                 # 编译内核与模块
make modules_install install      # 会改 /boot 与引导配置，别在生产机执行
```

生产环境请用发行版内核与厂商支持的内核包；自己装主线内核会同时失去发行版的 backport、KABI 保证与安全更新通道。升级前务必保留一个已知可启动的内核条目与救援介质。

## 四、把两条链合起来看

启动链自底向上依赖本系列前面的所有层次：内核初始化内存与调度（[02](/posts/2026-11-05-linux-os-02-process-scheduler/)、[03](/posts/2026-11-05-linux-os-03-memory-management/)）、靠驱动找到块设备并挂根（[04](/posts/2026-11-05-linux-os-04-vfs-filesystems/)）、systemd 借 cgroup 组织服务（[06](/posts/2026-11-05-linux-os-06-cgroup-v2/)）。而内核开发链则是这条技术栈的「上游」：任何线上问题最终都可以追溯到某个子系统与它的维护者。

## 系列导航

- [00 · Linux 操作系统全景：可核查的深度研究报告](/posts/2026-11-05-linux-os-00-panorama/)
- [01 · Linux 到底是什么：内核、发行版与一次系统调用的旅程](/posts/2026-11-05-linux-os-01-kernel-syscall/)
- [02 · 进程与调度：从 fork 到 EEVDF](/posts/2026-11-05-linux-os-02-process-scheduler/)
- [03 · 内存管理：虚拟内存、页表与 OOM](/posts/2026-11-05-linux-os-03-memory-management/)
- [04 · VFS 与文件系统：一次写盘的完整路径](/posts/2026-11-05-linux-os-04-vfs-filesystems/)
- [05 · 网络栈与 eBPF：从 sk_buff 到可编程内核](/posts/2026-11-05-linux-os-05-network-ebpf/)
- [06 · cgroup v2 与容器资源边界](/posts/2026-11-05-linux-os-06-cgroup-v2/)
- [07 · 启动流程与内核开发：从 UEFI 到第一个补丁](/posts/2026-11-05-linux-os-07-boot-and-kernel-dev/)（本篇）
- [08 · 性能观测与调优：USE 方法与四层瓶颈判别](/posts/2026-11-05-linux-os-08-performance-observability/)
- 基础篇：[文件权限与特权提升](/posts/2026-09-14-linux-permissions-security/) · [信号机制与守护进程](/posts/2026-09-14-linux-signals/) · [网络命名空间与容器隔离](/posts/2026-09-14-linux-network-namespaces/) · [systemd 与自动化运维](/posts/2026-09-14-linux-systemd-ops/)

---

*引导器、initramfs 工具与Secure Boot 行为因发行版而异，命令请按实际系统选择；内核编译安装只应在可随时重装或回滚的测试环境进行。*
