#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wxlisten.py — 微信消息「按需拉取」工具（你 → AI 方向）

你（用户）在微信 ClawBot 会话里发的消息，由 PushPlus 暂存。
本工具负责把它们拉下来：
  python wxlisten.py --once     # 拉取一次：打印新消息，并存入 inbox/
  python wxlisten.py --status   # 检查密钥/绑定/连通性
  python wxlisten.py --listen   # （可选）常驻轮询，自动落盘 inbox/

收到消息后怎么处理由 AI（我）来做：你回来喊一声，我 --once 拉取，
读内容 → 处理 → 需要回复时用 wxnotify.py 发回你的微信。

配置（优先级: 命令行 > 环境变量 > 同目录 gate.env > 同目录 gate-config.json）:
  PUSHPLUS_USER_TOKEN  PushPlus 用户 token（开放接口必须用户 token）
  PUSHPLUS_SECRET_KEY  开发设置中的 secretKey（≥32 位）
"""
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
INBOX = os.path.join(BASE, "inbox")
HEARTBEAT = os.path.join(INBOX, ".listener.heartbeat")


def touch_heartbeat():
    """刷新监听心跳，供 wxchat.py --status 判断常驻监听是否在运行"""
    os.makedirs(INBOX, exist_ok=True)
    try:
        with open(HEARTBEAT, "w", encoding="utf-8") as f:
            f.write(f"{os.getpid()} {time.time()}")
    except Exception:
        pass
API = "https://www.pushplus.plus"

DEFAULTS = {
    "PUSHPLUS_USER_TOKEN": "",
    "PUSHPLUS_SECRET_KEY": "",
    "POLL_INTERVAL": "10",
}


def load_config():
    cfg = dict(DEFAULTS)
    jf = os.path.join(BASE, "gate-config.json")
    if os.path.isfile(jf):
        try:
            with open(jf, encoding="utf-8") as f:
                cfg.update({k: str(v) for k, v in json.load(f).items()})
        except Exception:
            pass
    ef = os.path.join(BASE, "gate.env")
    if os.path.isfile(ef):
        try:
            with open(ef, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
        except Exception:
            pass
    for k in DEFAULTS:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


CFG = load_config()
_AK = {"key": None, "expire": 0}


def http(method, url, body=None, headers=None, timeout=20):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    h = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            return {"code": e.code, "msg": e.reason}
    except Exception as e:
        return {"code": -1, "msg": str(e)}


def get_access_key():
    now = time.time()
    if _AK["key"] and now < _AK["expire"] - 60:
        return _AK["key"], None
    if not CFG["PUSHPLUS_USER_TOKEN"] or not CFG["PUSHPLUS_SECRET_KEY"]:
        return None, "缺少 PUSHPLUS_USER_TOKEN / PUSHPLUS_SECRET_KEY"
    resp = http("POST", f"{API}/api/common/openApi/getAccessKey",
                {"token": CFG["PUSHPLUS_USER_TOKEN"], "secretKey": CFG["PUSHPLUS_SECRET_KEY"]})
    if resp.get("code") != 200:
        return None, f"getAccessKey 失败: code={resp.get('code')} msg={resp.get('msg')}"
    d = resp.get("data", {})
    _AK["key"] = d.get("accessKey")
    _AK["expire"] = now + int(d.get("expiresIn", 7200))
    return _AK["key"], None


def fetch_msgs():
    key, err = get_access_key()
    if err:
        return None, err
    resp = http("GET", f"{API}/api/open/clawBot/getMsg", headers={"access-key": key})
    if resp.get("code") != 200:
        return None, f"getMsg 失败: code={resp.get('code')} msg={resp.get('msg')}"
    return resp.get("data") or [], None


def save_inbox(text, mtype):
    os.makedirs(INBOX, exist_ok=True)
    fn = os.path.join(INBOX, time.strftime("%Y%m%d_%H%M%S") + f"_{abs(hash(text)) % 10000}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n类型: {'文字' if mtype == 1 else '语音'}\n内容: {text}\n")
    return fn


def pull_once(verbose=True):
    touch_heartbeat()
    # getMsg 为"拉取即消费"队列：每条消息只返回一次，直接全部落盘即可
    msgs, err = fetch_msgs()
    if err:
        print(f"[warn] {err}", flush=True)
        return 0, err
    new = 0
    for m in msgs or []:
        text = str(m.get("text", "")).strip()
        mtype = m.get("type")
        if not text or mtype not in (1, 3):
            continue
        fn = save_inbox(text, mtype)
        new += 1
        if verbose:
            print(f"[新消息] {text}\n  已存: {fn}", flush=True)
    if verbose:
        print(f"完成: 新消息 {new} 条。", flush=True)
    return new, None


def status():
    def mask(v):
        return v[:6] + "***" if v else "未配置"
    print("== wxlisten 配置检查 ==")
    print(f"PUSHPLUS_USER_TOKEN: {mask(CFG['PUSHPLUS_USER_TOKEN'])}")
    print(f"PUSHPLUS_SECRET_KEY: {mask(CFG['PUSHPLUS_SECRET_KEY'])}")
    key, err = get_access_key()
    print(f"AccessKey          : {'OK' if key else '失败: ' + (err or '')}")
    if key:
        bi = http("GET", f"{API}/api/open/clawBot/botInfo", headers={"access-key": key})
        print("ClawBot 绑定详情   :", bi.get("data", bi))
        print("（注意：拉取会消费消息，探测请用 --once / --wait）")


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if "--status" in args:
        status()
    elif "--wait" in args:
        # 等待模式：AI 提问期间挂起的纯监听。检测到新消息即退出(exit 0)，
        # 前端已回答时由 AI 主动结束本进程；--timeout N 分钟无消息则 exit 2
        timeout_min = 60
        if "--timeout" in args:
            try:
                timeout_min = int(args[args.index("--timeout") + 1])
            except Exception:
                pass
        deadline = time.time() + timeout_min * 60
        poll = max(3, int(CFG["POLL_INTERVAL"]))
        print(f"[wxwait] 开始监听微信消息（每 {poll}s 一次，超时 {timeout_min} 分钟）。", flush=True)
        while True:
            if time.time() > deadline:
                print("[wxwait] 超时，未收到微信消息。", flush=True)
                sys.exit(2)
            try:
                new, err = pull_once(verbose=False)
            except Exception as e:
                new, err = 0, str(e)
            if err:
                print(f"[wxwait] {err}", flush=True)
            if new:
                print(f"[wxwait] 检测到 {new} 条新微信消息，已存入 inbox/。", flush=True)
                sys.exit(0)
            time.sleep(poll)
    elif "--listen" in args:
        print("常驻监听启动（Ctrl+C 退出）", flush=True)
        touch_heartbeat()

        def _heartbeat_loop():
            while True:
                time.sleep(30)
                touch_heartbeat()

        threading.Thread(target=_heartbeat_loop, daemon=True).start()
        while True:
            try:
                pull_once(verbose=False)
            except Exception as e:
                print(f"[err] {e}", flush=True)
            time.sleep(max(3, int(CFG["POLL_INTERVAL"])))
    else:
        pull_once()
