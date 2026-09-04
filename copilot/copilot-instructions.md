# 微信完成通知规则（WeChat Notify）

当用户要求「任务/对话/项目跑完后用微信通知我」（或等价说法）时，agent 必须遵守：

## 执行要求

1. 在任务**收尾时**（无论成功还是失败都必须执行）运行：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>"
   ```
2. 结果摘要须包含：任务名、成功/失败、关键结果或错误摘要（简短，一两句话）
3. 若命令非零退出（例如 ClawBot 因超过 24 小时/10 次未对话导致下发失败），
   用服务号兜底渠道重试一次：
   ```
   python "D:/deepseek_harness/wechat-push/wxnotify.py" "<结果摘要>" -t "<任务名>" -c wechat
   ```
4. 若环境中存在 MCP 工具 `send_wechat_message`（微信通知 MCP），也可直接调用它，效果等价
5. 不要每个中间步骤都通知；只在任务完成或失败时通知一次

## 工具说明（供 agent 参考，无需用户再提供任何配置）

- 路径：`D:\deepseek_harness\wechat-push\wxnotify.py`
- 参数：第一个位置参数 = 消息内容（必填）；`-t/--title` 标题；`-c/--channel` 渠道
- 默认渠道 clawbot（微信 ClawBot 对话，形态最好）；`-c wechat` 走「推送加」服务号（无保活限制的兜底）
- token 已配置在同目录 `token.txt`，不需要用户提供；不要输出/展示 token 内容
- 返回 `OK: 服务端已接收` 即成功（code=200，异步投递，以手机收到为准）
