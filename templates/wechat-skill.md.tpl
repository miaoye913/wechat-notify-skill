---
name: wechat-notify
description: 通过微信给用户发送通知（任务完成/失败/提醒），支持双通道问答与测试例程。当用户要求「任务跑完用微信通知我」或需要微信通道收发时使用。默认 ClawBot 渠道、失败自动切服务号兜底。工具目录 {{TOOL_DIR}}，凭证已配置无需用户提供。
---

# 微信完成通知（WeChat Notify · 独立工程）

## 执行要求

1. 任务**收尾时**（成败都必须执行）运行：
   ```
   python "{{TOOL_DIR}}/wxnotify.py" "<结果摘要>" -t "<任务名>"
   ```
2. 摘要包含：任务名、成功/失败、关键结果或错误摘要（简短）
3. 默认 ClawBot 渠道；**脚本已内置保活兜底**（ClawBot 因 24h/10 次未对话失败时自动切服务号重发）
4. 指定渠道：`-c clawbot` / `-c wechat`；存在 MCP 工具 `send_wechat_message` 时也可直接调用
5. 只在完成/失败时通知一次

## 工具说明

- 发送 `{{TOOL_DIR}}/wxnotify.py` · 接收 `{{TOOL_DIR}}/wxlisten.py` · 测试 `{{TOOL_DIR}}/wxtest.py`
- 配置：`token.txt` + `gate.env`（本工程目录，勿外传/勿入库）

## 三种模式怎么选（先判别再执行）

| 用户意图 | 模式 | 做法 | 监听 |
|---|---|---|---|
| 「跑完通知我」 | ① 通知 | `wxnotify.py "<摘要>" --tag 通知`（ClawBot，失败自动切服务号） | 不需要 |
| 「问我，等我答」 | ② 单次问答 | `wxnotify.py` 提问 + `wxlisten.py --wait --timeout 300` | 一次性 |
| 「聊会儿 / 开启对话模式」 | ③ 对话 | `wxlisten.py --listen` + 循环 `wxchat.py --wait-new` | 常驻 |

口诀：**单向发=通知；要等你一句=`--wait`；多轮来回=`--listen`+chat 循环**。
状态查询：`wxchat.py --status`（监听是否在跑 / 未读数 / 模式提示）。
消息加 `--tag 通知` 或 `--tag 对话`，用户一眼分清。
微信特性：ClawBot 24h/10 条保活窗口在对话中会被你的发言自动续上；`getMsg` 拉取即消费，但未监听时消息滞留在 PushPlus 不会丢。

## 双通道问答

1. `python "{{TOOL_DIR}}/wxnotify.py" "<问题+选项>" -t "提问"`
2. `python "{{TOOL_DIR}}/wxlisten.py" --wait --timeout 30`（后台）
3. 用户前端或微信任一路回复 → 结束监听（微信回复会落盘 `inbox/`）

## 测试例程

`python "{{TOOL_DIR}}/wxtest.py"` → 配置/连通/发送/回环四项检查，输出 PASS/FAIL。
