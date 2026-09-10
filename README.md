# wechat-notify-skill — 微信通知（AI ↔ 你的微信，独立工程）

让电脑上的任何 AI（DSH / Codex / Copilot / Claude Code 等）**通过微信**给你发通知、并接收你的回复。

> 本工程只做**微信**通道。飞书通道是另一个独立工程：[feishu-notify-skill](https://github.com/miaoye913/feishu-notify-skill)（无 24h 保活限制）。两者可共存、互不干扰。

## 能力

- 📲 **任务完成/失败通知**：默认发到微信 ClawBot 对话，形态最好
- 🔄 **自动兜底**：ClawBot 因微信的 **24h/10 条保活窗口**失效时，脚本自动切「推送加」服务号（无窗口限制）重发——不需要人工干预
- 💬 **双通道问答**：AI 提问时把问题推送到微信并挂纯代码监听，你在微信或前端任一路回复即结束
- 🧪 **测试例程**：一句「运行测试例程」完成端到端自检（含微信回环）
- 🔌 **MCP 工具**：`send_wechat_message`，注册后 AI 直接调用
- 💰 **等待零 token**：监听是纯轮询代码，不调用任何大模型

## 目录结构

```
wechat-notify-skill/
├── README.md               ← 本文件
├── install.py              ← 安装器（标记块注入，可与飞书工程共存）
├── templates/
│   ├── wechat-agent-rules.md.tpl   ← 规则模板（{{TOOL_DIR}} 占位符）
│   ├── wechat-skill.md.tpl         ← Codex 技能模板
│   └── gate.env.example            ← 开放接口密钥模板
├── wxnotify.py             ← 发送（默认 ClawBot，失败自动切服务号）
├── wxlisten.py             ← 接收（--wait 等待 / --once 拉取 / --status 自检）
├── wxnotify_mcp.py         ← MCP Server（可选）
└── wxtest.py               ← 测试例程（端到端 + 回环）
```

## 前置（一次性）

1. **Python 3.8+**
2. 手机微信关注公众号「**推送加**」并完成**实名认证**（否则接口返回 905 无法发送）
3. **推荐**：pushplus 渠道配置 → 绑定**微信 ClawBot**（扫码 + 在微信里主动发一条消息激活）
4. **接收功能**需要开放接口密钥：pushplus「开发设置」里设置 `secretKey`，并把本机**公网 IP** 加入安全 IP 白名单

## 快速开始

```bash
git clone https://github.com/miaoye913/wechat-notify-skill.git
cd wechat-notify-skill
python install.py --project-dir <你的项目目录>   # 部署规则到 Codex/Copilot/Claude（可选项目级）
# 配置密钥：复制 templates/gate.env.example 为 gate.env 填写；或写入 token.txt（用户 token）
python wxtest.py                                  # 端到端自检（会真发一条微信，按提示回复 ok）
```

## 日常用法

| 场景 | 命令 |
|---|---|
| 发通知（默认 ClawBot，自动兜底） | `python wxnotify.py "任务跑完了" -t "构建成功"` |
| 强制走服务号（无保活限制） | `python wxnotify.py "内容" -c wechat` |
| 等待回复（提问用） | `python wxlisten.py --wait --timeout 300` |
| 拉取微信消息 | `python wxlisten.py --once` |
| 自检 | `python wxlisten.py --status` |
| 测试例程 | `python wxtest.py` |

对话触发（部署后）：对 AI 说「**任务跑完用微信通知我**」「**运行测试例程**」。

## 微信通道的限制（务必知悉）

- **保活窗口**：每下发 10 条或每 24 小时，需要你在微信里主动与 ClawBot 对话一次，否则主动下发会失败 → 本工程**已内置自动切换服务号兜底**，通知不会丢
- **收的方向不受限制**：你随时给 ClawBot 发消息都能到达，且每发一条就重置窗口
- **服务号只能发不能收**：想"回复 AI"请用 ClawBot 会话
- 服务号渠道：实名用户 200 条/天；相同内容 1 小时最多 3 条

## 常见问题

- **收不到消息？** 跑 `wxtest.py`；或检查公众号消息开关、微信"通知消息管理"、官网"最新请求"页
- **接收报 403**：本机公网 IP 变了，去 pushplus 开发设置更新安全 IP 白名单
- **ClawBot 发送失败**：正常——脚本会自动切服务号；想避免可每天跟 ClawBot 说句话
- **需要 24h 也不失效的双工通道？** 用飞书工程（另一个仓库）

## 安全

`token.txt` / `gate.env` 含密钥，已被 `.gitignore` 排除，勿外传。
