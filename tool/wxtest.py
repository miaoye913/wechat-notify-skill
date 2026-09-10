#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wxtest.py — 通知链路测试例程（微信 + 飞书，端到端自检）

运行: python wxtest.py [--timeout 秒]
步骤:
  1) 配置检查   (微信 token/密钥、飞书凭证)
  2) 连通性     (PushPlus AccessKey + ClawBot 绑定)
  3) 微信发送   (ClawBot，失败自动换服务号)
  4) 飞书发送   (凭据校验 + 发一条测试消息)
  5) 回环验证   (等待你在微信回复 ok)

退出码: 0 全部通过 / 1 有失败 / 2 缺必要配置
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
API = "https://www.pushplus.plus"
FEISHU_API = "https://open.feishu.cn/open-apis"
PASS_N, FAIL_N, WARN_N = 0, 0, 0


def log(ok, msg):
    global PASS_N, FAIL_N
    if ok:
        PASS_N += 1
        print(f"  [PASS] {msg}", flush=True)
    else:
        FAIL_N += 1
        print(f"  [FAIL] {msg}", flush=True)
    return ok


def warn(msg):
    global WARN_N
    WARN_N += 1
    print(f"  [WARN] {msg}", flush=True)


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


def _read_env(fname, keys):
    cfg = {}
    path = os.path.join(BASE, fname)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        cfg[k.strip()] = v.strip()
        except Exception:
            pass
    for k in keys:
        if os.environ.get(k):
            cfg[k] = os.environ[k]
    return cfg


def env_load():
    cfg = _read_env("gate.env", ("PUSHPLUS_USER_TOKEN", "PUSHPLUS_SECRET_KEY"))
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


def feishu_env():
    cfg = _read_env("feishu.env", ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_USER_OPEN_ID"))
    return cfg.get("FEISHU_APP_ID", ""), cfg.get("FEISHU_APP_SECRET", ""), cfg.get("FEISHU_USER_OPEN_ID", "")


def feishu_token(app_id, app_secret):
    resp = http("POST", f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
                {"app_id": app_id, "app_secret": app_secret})
    if resp.get("code") == 0:
        return resp.get("tenant_access_token"), None
    return None, f"{resp}"


def feishu_send(app_id, app_secret, open_id, text):
    tok, err = feishu_token(app_id, app_secret)
    if err:
        return False, err
    resp = http("POST", f"{FEISHU_API}/im/v1/messages?receive_id_type=open_id",
                {"receive_id": open_id, "msg_type": "text",
                 "content": json.dumps({"text": text}, ensure_ascii=False)},
                headers={"Authorization": f"Bearer {tok}"})
    return resp.get("code") == 0, resp


def main():
    timeout = 90
    if len(sys.argv) > 1 and sys.argv[1] == "--timeout" and len(sys.argv) > 2:
        try:
            timeout = int(sys.argv[2])
        except Exception:
            pass
    print("== 通知链路测试例程（微信 + 飞书）==", flush=True)

    print("[1/5] 配置检查", flush=True)
    user_token, secret, token_file = env_load()
    f_app_id, f_secret, f_open_id = feishu_env()
    log(bool(token_file), f"微信 token.txt 存在且非空 ({token_file[:6]}***)" if token_file else "微信 token.txt 缺失")
    log(bool(user_token and secret), "微信 gate.env 开放接口密钥已配置" if (user_token and secret) else "微信 gate.env 密钥缺失")
    if f_app_id and f_secret and "xxxx" not in f_app_id:
        log(True, f"飞书凭证已配置 (App ID {f_app_id[:10]}***)")
        if not f_open_id:
            warn("飞书 open_id 未记录，可运行 feishu_whoami.py 自动获取")
    else:
        warn("飞书凭证未配置（跳过飞书检查；可在 feishu.env 中配置）")
    if not (user_token and secret) or not token_file:
        print("微信链路配置不全，无法继续微信部分（可只配飞书使用）", flush=True)
        return 2

    print("[2/5] PushPlus 连通性", flush=True)
    ak, err = get_ak(user_token, secret)
    log(ak is not None, f"AccessKey 获取 ({err if err else 'OK'})")
    if not ak:
        return 1
    bi = http("GET", f"{API}/api/open/clawBot/botInfo", headers={"access-key": ak})
    bound = bi.get("code") == 200 and bool(bi.get("data"))
    log(bound, f"ClawBot 绑定 ({json.dumps(bi.get('data', bi), ensure_ascii=False) if bound else bi})")

    print("[3/5] 微信发送测试", flush=True)
    ok1, r1 = send_wechat(token_file, "【wxtest】微信发送测试——看到请回复 ok", "clawbot")
    if not ok1:
        ok1, r1 = send_wechat(token_file, "【wxtest】微信发送测试(服务号兜底)——看到请回复 ok", "wechat")
    log(ok1, f"微信消息已发送 ({r1.get('msg') if isinstance(r1, dict) else r1})")

    print("[4/5] 飞书发送测试", flush=True)
    if f_app_id and f_secret and "xxxx" not in f_app_id:
        tok, ferr = feishu_token(f_app_id, f_secret)
        log(tok is not None, f"飞书 tenant_access_token ({ferr if ferr else 'OK'})")
        if tok and f_open_id:
            ok2, r2 = feishu_send(f_app_id, f_secret, f_open_id,
                                  "【wxtest】飞书发送测试——此通道无 24h 保活限制")
            log(ok2, f"飞书消息已发送 ({r2.get('msg') if isinstance(r2, dict) else r2})")
        elif tok and not f_open_id:
            warn("飞书 open_id 缺失，跳过发送（运行 feishu_whoami.py 获取）")
    else:
        warn("飞书未配置，跳过")

    print(f"[5/5] 回环验证：{timeout} 秒内请在微信回复 ok", flush=True)
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
    log(got is not None, f"收到微信回复: {got}" if got else "超时未收到微信回复（可稍后 wxlisten --once 验证）")
    print(f"== 汇总: {PASS_N} PASS / {FAIL_N} FAIL / {WARN_N} WARN ==", flush=True)
    return 0 if FAIL_N == 0 else 1


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
