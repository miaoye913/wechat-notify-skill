#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信通知 MCP Server（零依赖，stdio 传输，Python 标准库）

暴露工具: send_wechat_message(content, title?, channel?)
  - content: 消息正文（必填）
  - title:   标题（默认"微信通知"）
  - channel: clawbot（默认，微信 ClawBot 对话）| wechat（推送加服务号兜底）
底层复用 PushPlus /send 接口与同目录 token.txt，无需额外安装。

注册示例:
  Codex   (~/.codex/config.toml)
    [mcp_servers.wechat_notify]
    command = "python"
    args = ["D:/deepseek_harness/wechat-push/wxnotify_mcp.py"]
  其他客户端见 wechat-push/README.md

自测: python wxnotify_mcp.py --selftest   （stub 发送，不真发）
"""
import json
import os
import sys
import urllib.request

ENDPOINT = "https://www.pushplus.plus/send"
BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE, "token.txt")

TOOL = {
    "name": "send_wechat_message",
    "description": (
        "给用户微信发一条通知（任务完成/失败/提醒）。默认发到微信 ClawBot 对话；"
        "若因超过 24 小时或 10 次未对话导致失败，可传 channel='wechat' 走推送加服务号兜底。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "消息正文（必填）"},
            "title": {"type": "string", "description": "消息标题（默认 微信通知）"},
            "channel": {
                "type": "string",
                "enum": ["clawbot", "wechat"],
                "description": "默认 clawbot；wechat 为无保活限制的服务号兜底",
            },
        },
        "required": ["content"],
    },
}


def get_token():
    t = os.environ.get("PUSHPLUS_TOKEN")
    if t:
        return t.strip()
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return None


def send(content, title="微信通知", channel="clawbot"):
    token = get_token()
    if not token:
        return {"ok": False, "error": "缺少 token：请设置环境变量 PUSHPLUS_TOKEN 或确保同目录有 token.txt"}
    payload = {"token": token, "title": title, "content": content, "channel": channel}
    if channel == "clawbot":
        payload["template"] = "txt"
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"请求异常: {e}"}
    if resp.get("code") == 200:
        return {"ok": True, "msg": resp.get("msg", "")}
    return {"ok": False, "error": f"code={resp.get('code')} msg={resp.get('msg')}"}


def rpc(msg):
    mid = msg.get("id")
    method = msg.get("method")

    def ok(result):
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2025-06-18",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "wechat-notify", "version": "1.0.0"},
        })
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [TOOL]})
    if method == "tools/call":
        params = msg.get("params", {}) or {}
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        if name != "send_wechat_message":
            return err(-32602, f"未知工具: {name}")
        result = send(
            str(args.get("content", "")),
            str(args.get("title", "微信通知")),
            str(args.get("channel", "clawbot")),
        )
        text = json.dumps(result, ensure_ascii=False)
        return ok({"content": [{"type": "text", "text": text}], "isError": not result.get("ok", False)})
    return err(-32601, f"未知方法: {method}")


def main_loop():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue
        resp = rpc(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


def selftest():
    global send
    send = lambda content, title="", channel="": {"ok": True, "stub": True, "channel": channel}  # noqa: E731
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cases = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "selftest", "version": "0"}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "send_wechat_message",
                    "arguments": {"content": "自测消息", "channel": "wechat"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "unknown_tool", "arguments": {}}},
    ]
    for c in cases:
        print(json.dumps(rpc(c), ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        print("SELFTEST:")
        selftest()
    else:
        main_loop()
