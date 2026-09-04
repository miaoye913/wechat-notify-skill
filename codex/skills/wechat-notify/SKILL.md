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

## 双通道问答（向用户提问时可选增强）

需要向用户提问、且用户可能不在电脑前（或用手机更方便）时：

1. 先把**问题本身推送到微信**（否则用户微信里看不到问题）：
   `python "D:/deepseek_harness/wechat-push/wxnotify.py" "<问题+选项>" -t "提问"`
2. 再启动**纯代码监听**（不做 AI 处理，只检测微信回复）：
   `python "D:/deepseek_harness/wechat-push/wxlisten.py" --wait --timeout 30`（后台运行）
3. 告知用户：可直接回复，也可去微信 ClawBot 回复
4. 两个结束条件，满足即停：
   - 用户在前端回复 → 主动结束监听进程
   - 用户在微信回复 → 监听检测到消息**自动退出**（exit 0），消息已落盘 `inbox/`，读取最新一条作为用户回答
5. 处理完后如有必要，用 wxnotify.py 把结果回发微信

注意：`wxlisten.py` 需要 PushPlus 开放接口密钥（同目录 `gate.env`，已配置好）；`getMsg` 是拉取即消费队列，拉到即落盘。

## 测试例程（用户说「运行测试例程 / 测试一下微信通知能不能用」时执行）

1. 运行端到端自检：
   `python "D:/deepseek_harness/wechat-push/wxtest.py"`
2. 它会自动完成四步：① 配置检查（token.txt / gate.env）② PushPlus 连通性与 ClawBot 绑定 ③ 发一条测试消息到微信（失败自动换服务号兜底）④ 等用户微信回复 ok（默认 90 秒，可 `--timeout N`）
3. 把 PASS/FAIL 汇总报告给用户；有 FAIL 项按输出线索排查（密钥、安全 IP、绑定、24h 保活）
4. 测试会真发一条微信消息，属预期行为；不要在用户不知情时运行
