---
name: wechat-notify
description: 给用户微信发通知消息（任务完成/失败/提醒）。当用户要求"跑完/完成后用微信通知我"时使用。默认发到微信 ClawBot 对话，失败时可用服务号兜底（-c wechat）。工具路径 D:/deepseek_harness/wechat-push/wxnotify.py，token 已配置无需用户提供。
---

# 微信完成通知（WeChat Notify）

当用户要求「任务/对话/项目跑完后用微信通知我」（或等价说法）时，agent 必须遵守：

## 执行要求

1. 在任务**收尾时**（无论成功还是失败都必须执行）运行：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>"
   ```
2. 结果摘要须包含：任务名、成功/失败、关键结果或错误摘要（简短）
3. 若命令非零退出（例如 ClawBot 超过 24 小时/10 次未对话导致下发失败），
   用服务号兜底重试一次：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>" -c wechat
   ```
4. 若环境中存在 MCP 工具 `send_wechat_message`，也可直接调用（等价）
5. 不要每个中间步骤都通知；只在任务完成或失败时通知一次

## 工具说明

- 路径：`D:\deepseek_harness\wechat-push\wxnotify.py`
- 第一个位置参数 = 消息内容（必填）；`-t/--title` 标题；`-c/--channel` 渠道（默认 clawbot，`wechat` 为兜底）
- token 已配置在同目录 `token.txt`；不要输出/展示 token
- 返回 `OK: 服务端已接收` 即成功（code=200，异步投递，以手机微信收到为准）
