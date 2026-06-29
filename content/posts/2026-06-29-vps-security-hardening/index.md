---
title: "VPS 安全加固：从 0 到三层防御实战记录"
date: 2026-06-29
publishDate: 2026-06-29
description: "一台裸奔的海外 VPS，跑着 new-api、x-ui、Hermes Agent 三个服务，端口审计发现 3000 + 50404 公网监听——我是怎么一步步把它变成铁桶的。"
tags: ["VPS", "Security", "GCP", "iptables", "Docker"]
categories: ["DevOps"]
draft: false
aliases: ["/posts/vps-security-hardening"]
---

> 一台裸奔的海外 VPS，跑着 new-api、x-ui、Hermes Agent 三个服务，端口审计发现 3000 + 50404 公网监听——我是怎么一步步把它变成铁桶的。

## 背景：一台裸奔的 VPS

上个月整理 GCP 免费赠金 VPS，发现上面跑着：

- **new-api**（端口 3000）— AI API 代理网关
- **x-ui**（端口 50404）— 代理面板
- **Hermes Agent**（内部端口）— 个人 AI 助理

三个服务全部 `0.0.0.0` 绑定，直接暴露在公网。用 `nmap` 扫了一下自己的 IP：

```
$ nmap -Pn <my-ip>
PORT      STATE SERVICE
3000/tcp  open  ppp
50404/tcp open  unknown
```

更要命的是，new-api 后台后来审计发现了 **7 个陌生 bot 账号**，说明已经被扫到了。ROOT_PASSWORD 还是默认的弱密码。

这篇文章记录我从"裸奔"到"三层防御"的完整过程，每一步都是真实踩坑后的总结。

## 第一层：GCP Firewall — 在流量进主机前挡住

**核心思路**：在 GCP 层面直接拒绝，流量根本不到你的主机。

GCP Firewall 支持按 **instance tag** 匹配规则。我先创建了一个 tag `secure-server`，然后写规则：

```bash
# 拒绝所有入站，只允许特定端口
gcloud compute firewall-rules create deny-all-ingress \
  --direction=INGRESS \
  --priority=65534 \
  --network=default \
  --action=DENY \
  --rules=all \
  --target-tags=secure-server \
  --source-ranges=0.0.0.0/0
```

**踩坑**：规则创建后测试 `nc -zv <ip> 3000`，发现还是通的。排查半小时发现——**instance 没打 tag**。规则存在但没 target，等于没配。

```bash
# 给 instance 打 tag
gcloud compute instances add-tags <instance-name> \
  --tags=secure-server \
  --zone=<zone>
```

打完 tag 再测，`nc` 直接 timeout，第一层生效。

**验证方法**：

```bash
$ nc -zv -w 3 <my-ip> 3000
# timeout = 成功挡住
```

## 第二层：Port Bind — 让服务只监听 localhost

**核心思路**：即使防火墙被绕过，服务本身也不监听公网 IP。

### new-api 改 systemd unit

```ini
# /etc/systemd/system/new-api.service
[Service]
# 原来：Environment="BIND_ADDRESS=0.0.0.0:3000"
# 改成：
Environment="BIND_ADDRESS=127.0.0.1:3000"
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart new-api
```

### x-ui 的情况

x-ui 面板默认绑定 `0.0.0.0`，改配置路径在 `/root/x-ui/config.json`。但 x-ui 的 Reality 出站配置有个坑——**面板给的 vless:// 链接和二维码信息不准确**，IP/端口/公钥需要手动核实后重设。

```bash
# 查看实际监听
ss -tlnp | grep -E '3000|50404'
# 期望输出：127.0.0.1:3000（new-api 已改好）
#          0.0.0.0:50404（x-ui 仍监听公网，靠第一层保护）
```

**为什么 x-ui 可以不改？** 因为第一层 GCP Firewall 已经挡住了 50404 的公网访问。这就是纵深防御——单层失效不影响整体。

## 第三层：iptables DOCKER-USER — 内核层兜底

**核心思路**：Docker 容器会绕过 ufw/iptables 的 INPUT 链，必须在 DOCKER-USER 链上做规则。

### 为什么需要第三层？

Docker 的网络架构有个特点：容器流量走的是 `FORWARD` 链，不是 `INPUT` 链。你在 ufw 里配的规则对 Docker 容器完全无效。

```bash
# 查看 Docker 是否绕过了 ufw
sudo iptables -L DOCKER-USER -n -v
# 默认是空的，所有流量都放行
```

### 编写加固脚本

```bash
#!/bin/bash
# /usr/local/bin/iptables-hardening.sh

# 清空 DOCKER-USER 链
iptables -F DOCKER-USER 2>/dev/null || iptables -N DOCKER-USER

# 允许已建立的连接
iptables -A DOCKER-USER -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN

# 允许 localhost 互访
iptables -A DOCKER-USER -i lo -j RETURN

# 拒绝 Docker 容器访问内部网络（防止 SSRF）
iptables -A DOCKER-USER -d 10.0.0.0/8 -j DROP
iptables -A DOCKER-USER -d 172.16.0.0/12 -j DROP
iptables -A DOCKER-USER -d 192.168.0.0/16 -j DROP

# 默认拒绝其他入站
iptables -A DOCKER-USER -j DROP
```

### 自愈机制：iptables-hardening.service

**踩坑**：Docker restart 会清空 DOCKER-USER 链的自定义规则。容器重启一次，加固全丢。

```ini
# /etc/systemd/system/iptables-hardening.service
[Unit]
Description=iptables DOCKER-USER hardening
After=docker.service
Wants=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/iptables-hardening.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

```bash
# 开机自启 + Docker 重启后自动恢复
sudo systemctl enable --now iptables-hardening.service
```

## 额外加固：攻击者真的来了

端口加固做完后，我回头审计 new-api 后台，发现了更严重的问题：

### 被入侵痕迹

- **7 个陌生 bot 账号**：用户名格式 `bot_xxxx`，注册时间集中在某三天
- **ROOT_PASSWORD 弱密码**：还是部署时的默认值
- **注册功能未关闭**：任何人都能注册新账号

### 一键修复

```bash
# 1. 关闭注册
# new-api 后台设置 → REGISTER_ENABLED=false

# 2. 删除攻击者账号（通过 API 或数据库直接操作）
sqlite3 /opt/new-api/data/new-api.db \
  "DELETE FROM users WHERE username LIKE 'bot_%';"

# 3. 改 ROOT_PASSWORD 为 47 字符随机 token
openssl rand -base64 35

# 4. 验证
sqlite3 /opt/new-api/data/new-api.db \
  "SELECT username, created_at FROM users WHERE username LIKE 'bot_%';"
# 应返回 0 行
```

### x-ui 加固

```bash
# 改 x-ui 登录路径为随机 secret path
# 原来：面板路径 /admin
# 改成：面板路径 /a1b2c3d4e5f6/
# 效果：扫描器扫 /admin 直接 404
```

## 总结：纵深防御思维

| 层级 | 机制 | 防什么 | 失效场景 |
|------|------|--------|----------|
| 第一层 | GCP Firewall + instance tag | 公网扫描、暴力破解 | tag 未打、规则优先级错 |
| 第二层 | 服务绑定 127.0.0.1 | 服务被直接访问 | 配置被改、新服务默认 0.0.0.0 |
| 第三层 | iptables DOCKER-USER | Docker 容器被横向穿透 | Docker restart 后规则丢失 |

**核心原则**：任何单层失效，其他层仍然兜住。

### 端到端验证清单

```bash
# 1. 公网扫描应该全 timeout
nc -zv -w 3 <my-ip> 3000  # timeout ✓
nc -zv -w 3 <my-ip> 50404  # timeout ✓

# 2. 本地服务正常
curl -s http://127.0.0.1:3000/api/status  # 200 ✓

# 3. Docker 容器无法访问内网
docker run --rm alpine ping -c 1 192.168.1.1  # 不通 ✓

# 4. 加固服务在运行
systemctl is-active iptables-hardening.service  # active ✓
```

### 适用场景

这套方案适合所有跑海外 VPS 的个人开发者：

- 跑 AI API 代理（new-api / one-api）
- 跑代理服务（x-ui / 3x-ui）
- 跑个人服务（博客、Agent、监控）

**不需要企业级安全设备，一台 $5/月的 VPS 也能做到基本免疫公网扫描。**
