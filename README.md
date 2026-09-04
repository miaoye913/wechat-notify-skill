# wechat-notify-skill — AI 环境「微信通知 + 双通道问答」部署包

一套开箱即用的能力，让你电脑上的任何 AI（**DSH / Codex / Copilot / Claude Code** 等）可以：

- 📲 **任务完成/失败时给你发微信通知**（默认微信 ClawBot 对话，失败自动切「推送加」服务号兜底）
- 💬 **双通道问答**：AI 提问时把问题推送到微信并挂监听，你用微信回复或前端回复均可
- 🧪 **测试例程**：说一句"运行测试例程"，自动端到端自检整条链路
- 🔌 **MCP 工具**：`send_wechat_message`，注册后 AI 直接调用

纯云端推送（PushPlus），**不碰个人微信自动化灰区、无封号风险**；监听脚本纯代码、等待零 AI token 消耗。

---

## 目录结构

```
wechat-notify-skill/
├── README.md                 ← 本文件（通用部署指南）
├── install.py                ← 跨平台安装器（Windows/macOS/Linux，Python 3.8+）
├── templates/                ← 规则模板（{{TOOL_DIR}} 占位符由 install.py 替换为实际路径）
│   ├── agent-rules.md.tpl    ←   通用规则（Codex AGENTS / Copilot / Claude / DSH 共用）
│   ├── skill-wechat-notify.md.tpl  ← Codex 技能版（带 frontmatter）
│   └── gate.env.example      ←   开放接口密钥配置示例
└── tool/                     ← 工具（零依赖，Python 标准库）
    ├── wxnotify.py           ←   发送：AI/脚本 → 微信
    ├── wxlisten.py           ←   接收：微信 → 本机（--wait/--once/--status）
    ├── wxtest.py             ←   测试例程：端到端自检 + 微信回环
    └── wxnotify_mcp.py       ←   MCP Server（可选，暴露 send_wechat_message）
```

## 前置要求（首次约 15 分钟）

1. **Python 3.8+**（`python --version` 确认）
2. **微信手机版**：有新版本内置的 **ClawBot 插件**入口则体验最佳（我→设置→插件，灰度功能）；
   没有也能用（走服务号形态）
3. **PushPlus 账号**：手机微信扫码关注公众号「推送加」+ 完成**实名认证**（小额第三方核验费，不实名不能发送）

## 快速开始（新电脑部署）

### 1. 获取仓库并安装

```bash
git clone https://github.com/miaoye913/wechat-notify-skill.git
cd wechat-notify-skill
# 就地部署（工具留在本仓库 tool/，规则指向它）：
python install.py
```

如果你想把工具放在别的目录运行（比如跟项目放一起），装的时候指过去：
`python install.py --tool-dir D:/my-tools/wechat-push`
规则文件里的所有命令路径会自动指向该目录。想让 **DSH/项目级**也生效，加 `--project-dir <项目根目录>`。

> 可先 `python install.py --dry-run` 预览将要写入的位置。
> 安装目标：`~/.codex/AGENTS.md`、`~/.codex/skills/wechat-notify/SKILL.md`、
> `~/.github/copilot-instructions.md`、`~/.claude/CLAUDE.md`、可选 `<project>/AGENTS.md`。

### 2. 配置密钥

```bash
# 方式一（推荐，避免手滑）：安装时直接传入
python install.py --token 你的用户token --secret 你的secretKey

# 方式二：手动编辑 install.py 生成的模板
#   <工具目录>/gate.env   ← PUSHPLUS_USER_TOKEN / PUSHPLUS_SECRET_KEY
#   <工具目录>/token.txt  ← 用户 token（一行）
```

密钥获取：pushplus.plus → 个人中心（用户 token）；**开发设置**（自己设置 ≥32 位 secretKey，
并把本机**公网 IP** 加入安全 IP 列表——家庭宽带 IP 变化后需回来更新；`wxtest.py` 可帮你确认）。

### 3. 绑定 ClawBot 渠道（可选但推荐）

pushplus 个人中心 → 渠道配置 → 微信 ClawBot → 立即绑定 → 微信扫码 → 在微信里给 ClawBot 发条消息 → 点「我已发送」→ 状态"已激活"。

### 4. 跑测试例程验证

```bash
python tool/wxtest.py
```

看到 `6 PASS / 0 FAIL` 即全部打通（最后一步会请你在微信回复 ok 完成回环验证）。
**注意**：如需用 `wxlisten.py`（接收），需完成第 2 步的开放接口配置。

### 5. 开始使用

各 AI 客户端**开新会话**后，直接说：

- 「这个任务跑完用微信通知我」→ 自动推送
- 「运行测试例程」→ 端到端自检
- 提问时 AI 会按规则把问题推送到微信并挂监听，你**在微信里回复即可**（前端回复也行）

## 日常用法

| 场景 | 做法 |
|---|---|
| 对话触发 | 对任意已部署环境的 AI 说「任务跑完微信通知我」（成败都会报） |
| 命令行 | `python tool/wxnotify.py "内容" -t "标题"`（默认 ClawBot）；`-c wechat` 服务号兜底 |
| 拉取微信消息 | `python tool/wxlisten.py --once`；挂监听等回复 `--wait --timeout 30` |
| MCP 工具 | 注册 `tool/wxnotify_mcp.py` 后调用 `send_wechat_message(content, title?, channel?)` |
| 自检 | `python tool/wxtest.py` |

## 渠道与限制

- **ClawBot 渠道**（默认）：形态最好；微信限制**每下发 10 次或每 24 小时**需用户主动对话一次，否则发不出 → 规则已内置失败自动切服务号兜底
- **服务号渠道**（`-c wechat`）：无保活限制，适合兜底
- **等待监听零 AI token**：轮询纯代码，只有处理时才调 AI

## 常见问题

- **收不到消息？** 检查：公众号消息开关、微信侧"通知消息管理"、官网"最新请求"页报文；或运行 `wxtest.py`
- **安全 IP 403？** 家庭宽带公网 IP 变了，去 pushplus 开发设置更新白名单
- **Codex/Copilot 没反应？** 规则在新会话加载；确认 install.py 写入成功（看输出的路径）
- **想给别的微信发？** 设计上只发给"你自己"（你的 PushPlus 账号），避免打扰他人与风险
- **ClawBot 渠道绑定失败？** 一个微信只能绑一个 ClawBot；确认手机有插件入口（灰度）

## 开发维护

- **改规则措辞/行为**：改 `templates/*.md.tpl`（占位符 `{{TOOL_DIR}}` 别删）→ 重跑 `python install.py --tool-dir ...` 同步各端
- **改工具逻辑**：改 `tool/*.py` → 同步到你的运行实例（若分离）→ 跑 `wxtest.py` 回归
- 密钥文件（`gate.env`/`token.txt`）已被 `.gitignore` 排除，永不入库

## 版本

- v1.x：固定路径的分发副本（作者本机布局），v2.0.0 起改为模板 + 安装器，可在任意电脑部署
- 完整历史见 GitHub Releases
