#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
notify.py — 统一通知入口（飞书优先，微信自动兜底）

用法:
  python notify.py "任务跑完了" [-t 标题] [--channel auto|feishu|clawbot|wechat]

逻辑（--channel auto，默认）:
  1) 飞书（feishu_send.py）—— 无 24h 保活限制，首选
  2) 飞书失败/未配置 → 微信 ClawBot（wxnotify.py -c clawbot）
  3) ClawBot 失败 → wxnotify.py 内部会自动切服务号(wechat)兜底

退出码: 0 至少一个通道发送成功 / 1 全部失败 / 2 缺配置
"""
import argparse
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or "python"


def run_script(script, args):
    """直接继承 stdout/stderr，返回 returncode（避免管道捕获问题）"""
    path = os.path.join(BASE, script)
    if not os.path.isfile(path):
        print(f"[skip] 脚本不存在: {path}")
        return 2
    print(f"--- {script} ---")
    return subprocess.run([PY, path] + args).returncode


def main():
    ap = argparse.ArgumentParser(description="统一通知入口（飞书优先，微信兜底）")
    ap.add_argument("content", help="消息内容（必填）")
    ap.add_argument("-t", "--title", default=None, help="标题")
    ap.add_argument("--channel", default="auto", choices=["auto", "feishu", "clawbot", "wechat"])
    a = ap.parse_args()

    base_args = [a.content] + (["-t", a.title] if a.title else [])

    if a.channel == "feishu":
        return run_script("feishu_send.py", base_args)
    if a.channel in ("clawbot", "wechat"):
        return run_script("wxnotify.py", base_args + ["-c", a.channel])

    # auto: 飞书优先 → 微信兜底
    rc = run_script("feishu_send.py", base_args)
    if rc == 0:
        print("=> 已通过【飞书】发送")
        return 0
    print("[fallback] 飞书通道未成功，切换微信通道…")
    rc2 = run_script("wxnotify.py", base_args)
    if rc2 == 0:
        print("=> 已通过【微信】发送（服务号/ClawBot 兜底链）")
        return 0
    print("=> 所有通道均发送失败，请检查配置")
    return 1


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
