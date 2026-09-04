#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wxtest.py — 微信通知链路测试例程（自检 + 端到端回环）

运行: python wxtest.py [--timeout 秒]
步骤:
  1) 配置检查   (token.txt / gate.env)
  2) 连通性     (PushPlus AccessKey + ClawBot 绑定)
  3) 发送测试   (发一条测试消息到微信 ClawBot，失败自动换服务号)
  4) 回环验证   (等待你在微信回复 ok，收到即证明"发→收"全通)
  5) 汇总       PASS/FAIL 报告

退出码: 0 全部通过 / 1 有失败 / 2 缺配置
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
API = "https://www.pushplus.plus"
PASS_N, FAIL_N = 0, 0


def log(ok, msg):
    global PASS_N, FAIL_N
    if ok:
        PASS_N += 1
        print(f"  [PASS] {msg}", flush=True)
    else:
        FAIL_N += 1
        print(f"  [FAIL] {msg}", flush=True)
    return ok


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


def env_load():
    cfg = {}
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
    for k in ("PUSHPLUS_USER_TOKEN", "PUSHPLUS_SECRET_KEY"):
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    tf = os.path.join(BASE, "token.txt")
    token = ""
    if os.path.isfile(tf):
        try:
            with open(tf, encoding="utf-8") as f:
                token = f.read().strip()
        except Exception:
            pass
    return cfg.get("PUSHPLUS_USER_TOKEN", ""), cfg.get("PUSHPLUS_SECRET_KEY", ""), token


def get_ak(user_token, secret):
    resp = http("POST", f"{API}/api/common/openApi/getAccessKey",
                {"token": user_token, "secretKey": secret})
    if resp.get("code") != 200:
        return None, f"code={resp.get('code')} msg={resp.get('msg')}"
    return resp["data"].get("accessKey"), None


def send_wechat(token, content, channel):
    payload = {"token": token, "title": "wxtest 测试", "content": content,
               "channel": channel, "template": "txt"}
    resp = http("POST", f"{API}/send", payload)
    return resp.get("code") == 200, resp


def main():
    timeout = 90
    if len(sys.argv) > 1 and sys.argv[1] == "--timeout" and len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except Exception:
            pass
    print("== 微信通知链路测试例程 ==", flush=True)
    print("[1/4] 配置检查", flush=True)
    user_token, secret, token_file = env_load()
    log(bool(token_file), f"token.txt 存在且非空 ({token_file[:6]}***)" if token_file else "token.txt 缺失")
    log(bool(user_token and secret), "gate.env 开放接口密钥已配置" if (user_token and secret) else "gate.env 密钥缺失")
    if not (user_token and secret) or not token_file:
        print("请先配置 token.txt 与 gate.env（见 README 快速开始）", flush=True)
        return 2
    print("[2/4] PushPlus 连通性", flush=True)
    ak, err = get_ak(user_token, secret)
    log(ak is not None, f"AccessKey 获取 ({err if err else 'OK'})")
    if not ak:
        return 1
    bi = http("GET", f"{API}/api/open/clawBot/botInfo", headers={"access-key": ak})
    bound = bi.get("code") == 200 and bool(bi.get("data"))
    log(bound, f"ClawBot 绑定 ({json.dumps(bi.get('data', bi), ensure_ascii=False) if bound else bi})")
    print("[3/4] 发送测试消息", flush=True)
    ok1, r1 = send_wechat(token_file,
                          "【wxtest】发送链路测试——看到这条消息请回复 ok", "clawbot")
    if not ok1:
        ok1, r1 = send_wechat(token_file,
                              "【wxtest】发送链路测试(服务号兜底)——看到请回复 ok", "wechat")
    log(ok1, f"测试消息已发送 ({r1.get('msg') if isinstance(r1, dict) else r1})")
    print(f"[4/4] 回环验证：{timeout} 秒内请在微信回复 ok", flush=True)
    got = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = http("GET", f"{API}/api/open/clawBot/getMsg", headers={"access-key": ak})
        if isinstance(resp, dict) and resp.get("code") == 200:
            for item in resp.get("data") or []:
                t = str(item.get("text", "")).strip()
                if t and item.get("type") in (1, 3):
                    got = t
                    break
        if got:
            break
        time.sleep(5)
    log(got is not None, f"收到微信回复: {got}" if got else f"超时未收到回复（可稍后手动 wxlisten --once 验证）")
    print(f"== 汇总: {PASS_N} PASS / {FAIL_N} FAIL ==", flush=True)
    return 0 if FAIL_N == 0 else 1


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
