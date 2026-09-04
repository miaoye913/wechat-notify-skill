# 项目规则（AGENTS.md）

## 微信完成通知（WeChat Notify）

当用户要求「任务/对话/项目跑完后用微信通知我」（或等价说法）时，agent 必须遵守：

1. 在任务**收尾时**（无论成功还是失败都必须执行）运行：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>"
   ```
2. 结果摘要包含：任务名、成功/失败、关键结果或错误摘要（简短）
3. 若命令非零退出（ClawBot 超过 24 小时/10 次未对话会下发失败），用服务号兜底重试：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>" -c wechat
   ```
4. 若环境提供 MCP 工具 `send_wechat_message`，可直接调用（等价）
5. 只在完成/失败时通知一次，不要每个中间步骤都发

工具详情见 `D:\deepseek_harness\wechat-push\README.md`（token 已配置，无需用户提供）。
