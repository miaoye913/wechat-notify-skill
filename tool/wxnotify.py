#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信推送工具（PushPlus 服务号通道）— Python 版（仅标准库，无需 pip 安装）

用法:
  python wxnotify.py "任务跑完了"                    # content 必填
  python wxnotify.py "构建通过" -t "任务完成"          # 指定标题
  python wxnotify.py "..." --token <token>           # 显式指定 token
  python wxnotify.py "..." -c clawbot                # 走微信 ClawBot 渠道（需先在 pushplus 渠道配置绑定激活）
  python wxnotify.py "..." --dry-run                 # 只打印请求，不发送

token 解析顺序: --token 参数 > 环境变量 PUSHPLUS_TOKEN > 同目录 token.txt
渠道说明: -c/--channel 默认 clawbot（微信 ClawBot 对话）;
          微信限制: 每下发 10 次或每 24 小时需在微信里主动与 ClawBot 对话一次，否则消息下不来；
          需要无保活限制的兜底通道时用 -c wechat（推送加服务号）。

说明: 接口返回 code=200 只代表服务端已接收（异步处理），最终以手机微信实际收到为准。
      退出码: 0 成功 / 1 发送失败 / 2 缺少 token
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://www.pushplus.plus/send"
CODE_HINTS = {
    903: "token 无效，请检查是否复制正确",
    905: "账号未实名认证，需先完成实名认证才能发送",
    900: "今日请求次数受限，明天再试",
    888: "积分不足",
}


def resolve_token(arg_token):
    if arg_token:
        return arg_token.strip()
    env = os.environ.get("PUSHPLUS_TOKEN")
    if env:
        return env.strip()
    tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.txt")
    if os.path.isfile(tf):
        with open(tf, encoding="utf-8") as f:
            return f.read().strip()
    return None


def main():
    ap = argparse.ArgumentParser(description="PushPlus 微信推送")
    ap.add_argument("content", help="消息内容（必填）")
    ap.add_argument("-t", "--title", default="微信通知", help="消息标题（可选）")
    ap.add_argument(
        "-c",
        "--channel",
        default="clawbot",
        choices=["wechat", "clawbot", "cp", "mail", "qq"],
        help="发送渠道，默认 clawbot（微信 ClawBot）；wechat=推送加服务号（无保活限制的兜底）",
    )
    ap.add_argument("--token", default=None, help="PushPlus token")
    ap.add_argument("--dry-run", action="store_true", help="只打印请求内容，不发送")
    a = ap.parse_args()

    token = resolve_token(a.token)
    if not token:
        sys.stderr.write(
            "缺少 token：用 --token 指定，或设置环境变量 PUSHPLUS_TOKEN，"
            "或把 token 存入脚本同目录的 token.txt\n"
        )
        return 2

    payload = {"token": token, "title": a.title, "content": a.content, "channel": a.channel}
    if a.channel == "clawbot":
        payload["template"] = "txt"  # ClawBot 渠道建议 txt 模板，正文完整展示
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    if a.dry_run:
        print(f"[DryRun] POST {ENDPOINT}")
        print(f"  body = {body.decode('utf-8')}")
        return 0

    req = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP 错误: {e.code} {e.reason}\n")
        return 1
    except Exception as e:  # 网络/TLS/超时等
        sys.stderr.write(f"请求异常: {e}\n")
        return 1

    code = resp.get("code")
    if code == 200:
        print(f"OK: 服务端已接收 (msg={resp.get('msg')})，请留意手机微信是否收到")
        return 0
    hint = CODE_HINTS.get(code, "")
    sys.stderr.write(f"FAIL: code={code} msg={resp.get('msg')} {hint}\n".rstrip())
    return 1


if __name__ == "__main__":
    # 管道/重定向时统一 UTF-8 输出；交互终端保持系统默认编码
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not sys.stderr.isatty():
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
