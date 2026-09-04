# wechat-notify-skill — AI 环境「微信完成通知」技能（集中版）

一套「**任务 / 对话 / 项目跑完 → 微信通知我**」的通用能力，按各家 AI 客户端的约定整理成可分发副本，支持 **DSH、Copilot、Codex、Claude Code** 等环境，未来迁移到新机器或分享给其他账号直接照做即可。

> 核心思路：内容同一套（源模板 `agent-rules.md`），按各客户端"只认自家门口"的规则**投递**到对应位置。不是重复维护，是分发。

---

## 目录结构

```
wechat-notify-skill/
├── README.md                        ← 本文件（介绍 + 用法）
├── agent-rules.md                   ← 规则源模板（想改行为，改这里）
├── claude/
│   └── CLAUDE.md                    ← 部署到 Claude Code 全局：~/.claude/CLAUDE.md
├── copilot/
│   └── copilot-instructions.md      ← 部署到 GitHub Copilot 全局：~/.github/copilot-instructions.md
├── codex/
│   ├── AGENTS.md                    ← 部署到 Codex 全局：~/.codex/AGENTS.md
│   └── skills/wechat-notify/
│       └── SKILL.md                 ← 部署到 Codex 技能目录：~/.codex/skills/wechat-notify/SKILL.md
├── dsh/
│   └── AGENTS.md                    ← 部署到 DSH 项目根（工作区指令，DSH 自动注入）：<项目根>/AGENTS.md
└── tool/
    ├── wxnotify.py                  ← 发送工具（Python 标准库，零依赖，真正的执行者）
    └── wxnotify_mcp.py              ← MCP Server（stdio，零依赖，暴露 send_wechat_message 工具）
```

## 各环境部署位置速查

| 环境 | 放哪个文件 | 目标位置（Windows） | 生效时机 |
|---|---|---|---|
| DSH | `dsh/AGENTS.md` | 项目根目录 `AGENTS.md`（DSH 自动注入会话指令） | 新会话 |
| Codex | `codex/AGENTS.md` | `C:\Users\<你>\.codex\AGENTS.md` | 新会话 |
| Codex | `codex/skills/wechat-notify/SKILL.md` | `C:\Users\<你>\.codex\skills\wechat-notify\SKILL.md` | 新会话 |
| Copilot | `copilot/copilot-instructions.md` | `C:\Users\<你>\.github\copilot-instructions.md` | 新会话 |
| Claude Code | `claude/CLAUDE.md` | `C:\Users\<你>\.claude\CLAUDE.md` | 新会话 |
| MCP 工具 | `tool/wxnotify_mcp.py` | 任意稳定路径，注册进各客户端（见下） | 配置后 |

## 快速开始（首次配置，约 10 分钟）

### 1. 准备 PushPlus token（一次性）
1. 手机微信扫码关注公众号「**推送加**」，完成**实名认证**（不实名无法发送）
2. 打开 https://www.pushplus.plus 微信登录 → 个人中心 → 新建一个「消息 token」
3. （可选，推荐）渠道配置 → 微信 ClawBot → 扫码绑定激活，通知形态更好
4. 把 token 存为 `tool/token.txt`（**该文件已被 .gitignore 排除，绝不会上传**）

### 2. 部署规则文件
把上表左边文件复制到右边位置即可（注意目录是否存在，`.github`、`.claude` 等可能需要新建）。Codex 的 MCP 注册（可选）：

```toml
# 追加到 C:\Users\<你>\.codex\config.toml
[mcp_servers.wechat_notify]
command = "python"
args = ["D:/<你的路径>/wechat-notify-skill/tool/wxnotify_mcp.py"]
```

VSCode 项目级（`.vscode/mcp.json`）：

```json
{
  "servers": {
    "wechat-notify": {
      "command": "python",
      "args": ["D:/<你的路径>/wechat-notify-skill/tool/wxnotify_mcp.py"]
    }
  }
}
```

### 3. 验证

```powershell
# 只检查请求内容，不发
python tool/wxnotify.py "测试" --dry-run
# 真发一条到手机微信（默认 ClawBot 对话）
python tool/wxnotify.py "链路测试成功" -t "测试"
# MCP server 协议自测（不发消息）
python tool/wxnotify_mcp.py --selftest
```

## 双通道问答：提问 ↔ 微信监听（v1.1 新增）

AI 提问时，可以同时挂一个**纯代码监听**（不做 AI 处理）等待你在微信里的回复：

- `tool/wxlisten.py --wait` —— **等待模式**（AI 提问期间挂后台）：每 10s 拉一次微信 ClawBot 消息，检测到新消息自动退出（exit 0）；`--timeout N` 分钟超时（exit 2）
- `tool/wxlisten.py --once` —— 按需拉取一次并存 `inbox/`
- `tool/wxlisten.py --status` —— 自检密钥/绑定

结束条件（二选一，满足即停）：① 用户在前端回答了选项（由 AI 主动结束监听）② 用户在微信 ClawBot 里回复了（监听检测到消息自动退出，消息落盘 `inbox/`）。

**注意**：`getMsg` 是"拉取即消费"队列——每条消息只返回一次，拉到务必落盘；AI 提问时应把**问题本身也推送到微信**（用 `wxnotify.py`），否则用户在微信里看不到问题。

运行前提：PushPlus 开放接口（个人中心→开发设置配置 secretKey + 安全 IP），密钥放 `gate.env`（**该文件含密钥，不要入库**）：

```env
PUSHPLUS_USER_TOKEN=你的用户token
PUSHPLUS_SECRET_KEY=你的secretKey
```

## 日常用法

- **对话触发**（所有已部署环境通用）：对 AI 说「**这个任务跑完用微信通知我**」（等价说法均可），agent 会在任务收尾时（成功或失败）自动推送
- **命令行**：

```powershell
python tool/wxnotify.py "构建通过，耗时 3 分钟" -t "任务名"      # 默认 ClawBot 渠道
python tool/wxnotify.py "内容" -t "标题" -c wechat              # 服务号兜底（无保活限制）
```

- **MCP 工具**：`send_wechat_message(content, title?, channel?)`

## 渠道与限制

| 渠道 | 参数 | 形态 | 限制 |
|---|---|---|---|
| ClawBot（默认） | `-c clawbot` | 微信 ClawBot 对话，体验最好 | 每下发 10 次或每 24 小时需在微信里主动与 ClawBot 说句话，否则发不出 |
| 推送加服务号 | `-c wechat` | 服务号会话（可置顶） | 无保活限制，适合兜底 |

规则文件内置了"失败自动换 `-c wechat` 重试"的兜底逻辑。

## 安全备注

- `token.txt` 已 gitignore；token 是微信通知的钥匙，只存本机，别提交、别发给第三方
- 规则文件本身不含任何密钥，可放心公开/分享

## 维护

- 想改规则措辞/行为：改 **`agent-rules.md`** 源模板，再同步到 `claude/` `copilot/` `codex/` `dsh/` 各副本（内容一致）
- 想改发送逻辑：改 `tool/wxnotify.py`（MCP 与 CLI 共用同一套发送逻辑，由 `tool/wxnotify_mcp.py` 调用）

## 相关链接

- PushPlus 消息接口文档：https://www.pushplus.plus/doc/guide/api.html
- PushPlus 官方 MCP Server：https://github.com/pushplus/pushplus-MCP-Server-TypeScript（需 Node ≥18；本仓库 `tool/wxnotify_mcp.py` 为零依赖替代）
