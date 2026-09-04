#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wechat-notify-skill 安装器（跨平台：Windows / macOS / Linux）

在目标电脑上把「微信完成通知」规则部署到各 AI 客户端（Codex / Copilot / Claude Code），
准备密钥配置文件，并给出验证指引。DSH / 项目级 AGENTS.md 通过 --project-dir 可选安装。

用法:
  python install.py [--tool-dir PATH] [--project-dir PATH]
                    [--token XXX --secret XXX] [--dry-run] [--skip-config]

选项:
  --tool-dir PATH    工具实际所在目录，默认 <本仓库>/tool
                     （若工具被复制到别处运行，请传该目录，规则里的路径会指向它）
  --project-dir PATH 额外把规则写入该目录的 AGENTS.md（项目级生效，如 DSH 工作区）
  --token XXX        直接写入密钥配置（PushPlus 用户 token）
  --secret XXX       PushPlus 开发设置 secretKey（≥32 位）
  --dry-run          只打印将要执行的动作，不写入
  --skip-config      不生成/不检查 gate.env 与 token.txt

安装目标（自动检测用户主目录）:
  ~/.codex/AGENTS.md                          Codex 全局
  ~/.codex/skills/wechat-notify/SKILL.md      Codex 技能
  ~/.github/copilot-instructions.md           GitHub Copilot 全局
  ~/.claude/CLAUDE.md                         Claude Code 全局
  <project-dir>/AGENTS.md                     DSH / 项目级（可选）

装完后:
  1) 在 pushplus.plus 完成实名认证
  2) 把 <tool-dir>/gate.env 与 token.txt 配好（或装时用 --token/--secret）
  3) （可选，推荐）pushplus 渠道配置绑定微信 ClawBot
  4) 运行 python <tool-dir>/wxtest.py 验证端到端
"""
import argparse
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TPL_DIR = os.path.join(ROOT, "templates")


def norm(p):
    return os.path.abspath(p).replace("\\", "/")


def render(tpl_name, tool_dir):
    with open(os.path.join(TPL_DIR, tpl_name), encoding="utf-8") as f:
        return f.read().replace("{{TOOL_DIR}}", tool_dir)


def write_text(path, text, dry):
    if dry:
        print(f"  [dry] 写入 {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  [OK] 写入 {path}")


def ensure_env_file(example_name, dst, dry):
    if os.path.isfile(dst):
        print(f"  [skip] 已存在: {dst}")
        return
    src = os.path.join(TPL_DIR, example_name)
    if dry:
        print(f"  [dry] 从模板创建 {dst}")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    print(f"  [OK] 已创建模板（请编辑填写）: {dst}")


def main():
    ap = argparse.ArgumentParser(description="wechat-notify-skill 安装器")
    ap.add_argument("--tool-dir", default=os.path.join(ROOT, "tool"))
    ap.add_argument("--project-dir", default=None)
    ap.add_argument("--token", default=None)
    ap.add_argument("--secret", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-config", action="store_true")
    a = ap.parse_args()

    home = os.path.expanduser("~")
    tool_dir = norm(a.tool_dir)
    print(f"== wechat-notify-skill 安装 ==")
    print(f"工具目录: {tool_dir}")

    # 1) 部署规则/技能文件
    print("[1/3] 部署规则到 AI 客户端")
    rules = render("agent-rules.md.tpl", tool_dir)
    skill = render("skill-wechat-notify.md.tpl", tool_dir)
    targets = [
        (os.path.join(home, ".codex", "AGENTS.md"), rules, "Codex 全局"),
        (os.path.join(home, ".codex", "skills", "wechat-notify", "SKILL.md"), skill, "Codex 技能"),
        (os.path.join(home, ".github", "copilot-instructions.md"), rules, "GitHub Copilot 全局"),
        (os.path.join(home, ".claude", "CLAUDE.md"), rules, "Claude Code 全局"),
    ]
    for path, text, label in targets:
        print(f"  - {label}: {path}")
        write_text(path, text, a.dry_run)
    if a.project_dir:
        pd = os.path.join(norm(a.project_dir), "AGENTS.md")
        print(f"  - DSH/项目级: {pd}")
        write_text(pd, rules, a.dry_run)
    else:
        print("  - (未指定 --project-dir，跳过 DSH/项目级 AGENTS.md)")

    # 2) 密钥配置
    if a.skip_config:
        print("[2/3] 跳过密钥配置 (--skip-config)")
    else:
        print("[2/3] 密钥配置")
        ensure_env_file("gate.env.example", os.path.join(tool_dir, "gate.env"), a.dry_run)
        tf = os.path.join(tool_dir, "token.txt")
        if a.token:
            write_text(tf, a.token.strip() + "\n", a.dry_run)
        elif not os.path.isfile(tf):
            if a.dry_run:
                print(f"  [dry] 提示用户创建 {tf}")
            else:
                print(f"  [提示] 请创建 {tf}，内容为你的 PushPlus 用户 token（一行）")
        else:
            print(f"  [skip] 已存在: {tf}")
        if a.token and a.secret and not a.dry_run:
            env = f"PUSHPLUS_USER_TOKEN={a.token.strip()}\nPUSHPLUS_SECRET_KEY={a.secret.strip()}\n"
            os.makedirs(tool_dir, exist_ok=True)
            with open(os.path.join(tool_dir, "gate.env"), "w", encoding="utf-8") as f:
                f.write(env)
            print(f"  [OK] gate.env 已写入密钥")

    # 3) 收尾提示
    print("[3/3] 完成。接下来：")
    print("  1) 若未实名：pushplus.plus 个人中心完成实名认证（否则无法发送）")
    print("  2) 建议在 pushplus 渠道配置中绑定微信 ClawBot（体验最好；也可只用服务号）")
    print("  3) 把本机公网 IP 加入 pushplus 开发设置的『安全 IP』（wxlisten/wxtest 需要）")
    print("  4) 运行测试例程验证: python \"{}/wxtest.py\"".format(tool_dir))
    print("  5) 各 AI 客户端需开新会话，规则才会被加载")
    return 0


if __name__ == "__main__":
    if not sys.stdout.isatty():
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
