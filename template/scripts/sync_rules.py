#!/usr/bin/env python
"""规则分发同步器 —— 让「权威源」与「派生副本」保持一致。

## 为什么需要它

根目录 `AGENTS.md` 是跨 AI 工具的事实标准，但实测 WorkBuddy 把根目录 AGENTS.md
注入到 `<project_guidance>` 段时**该段有长度上限、超限静默截断**（末尾出现
`[...too long, omitted...]`）；而 `.codebuddy/rules/*.md` 走另一个注入通道，**完整无截断**。

实测数据点（同一份规则、同一会话）：
    5,376 字符 -> guidance 段完整
    8,434 字符 -> guidance 段被截断，可见部分止于 ≈7,890 字符，丢掉尾部两整节

⇒ 规则**长**了以后，权威源必须放 `.codebuddy/rules/`，根目录 `AGENTS.md` 降为
**派生副本**（供 ZCode 等只认根目录 AGENTS.md 的工具读）。本脚本负责把两者对齐。

## 用法

    python scripts/sync_rules.py              # 自动判定权威源并同步到另一侧
    python scripts/sync_rules.py --check      # 只检查是否一致（不一致 exit 1，可用于 CI / 收尾自检）
    python scripts/sync_rules.py --status     # 只打印两侧规模与上限预警，不写文件
    python scripts/sync_rules.py --source agents   # 反向：以 AGENTS.md 为权威源
    python scripts/sync_rules.py --project <dir>   # 指定仓库根
    python scripts/sync_rules.py --dry-run    # 只预览

## 约定

- 权威源：`.codebuddy/rules/project-rules.md`（默认）
- 派生副本：`AGENTS.md`（实体文件，**不要用符号链接**）
- 规则规模上限参考值 `RULES_LIMIT_CHARS = 5000` —— 超过就该切到本模式
- 零第三方依赖
"""

import argparse
import glob
import os
import shutil
import sys

RULES_LIMIT_CHARS = 5000
SRC_REL = os.path.join(".codebuddy", "rules", "project-rules.md")
DST_REL = "AGENTS.md"


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def size_chars(path):
    try:
        return len(read_text(path))
    except OSError:
        return None


def warn_extra_rules(proj):
    """提示 .codebuddy/rules/ 下未被镜像的其他 md（只镜像 project-rules.md）。"""
    d = os.path.dirname(os.path.join(proj, SRC_REL))
    if not os.path.isdir(d):
        return []
    others = [os.path.basename(p) for p in sorted(glob.glob(os.path.join(d, "*.md")))
              if os.path.basename(p) != "project-rules.md"]
    if others:
        return [f"注意：{os.path.relpath(d, proj)} 下还有 {', '.join(others)} —— "
                f"本脚本只镜像 project-rules.md，这些文件不会同步到 AGENTS.md"]
    return []


def status(proj):
    src = os.path.join(proj, SRC_REL)
    dst = os.path.join(proj, DST_REL)
    lines = []
    n_src, n_dst = size_chars(src), size_chars(dst)
    for label, rel, n in (("权威源", SRC_REL, n_src), ("派生副本", DST_REL, n_dst)):
        if n is None:
            lines.append(f"  {label:8s} {rel:38s} 不存在")
        else:
            flag = "  ⚠️ 超过上限参考值" if n > RULES_LIMIT_CHARS else ""
            lines.append(f"  {label:8s} {rel:38s} {n:6,d} 字符{flag}")
    if os.path.islink(dst):
        lines.append("  ⚠️ AGENTS.md 是符号链接 —— Windows 默认 core.symlinks=false，"
                     "跨机 clone 会退化为含目标路径的文本文件，且 git 无法自愈；"
                     "建议用 --force 换成实体文件")
    lines += [f"  {w}" for w in warn_extra_rules(proj)]
    return lines


def main():
    ap = argparse.ArgumentParser(description="规则权威源 <-> 派生副本 同步器")
    ap.add_argument("--project", default=os.getcwd(), help="仓库根（默认当前目录）")
    ap.add_argument("--source", choices=["rules", "agents"], default="rules",
                    help="权威源在哪一侧（默认 rules = .codebuddy/rules/project-rules.md）")
    ap.add_argument("--check", action="store_true", help="只检查一致性，不一致 exit 1")
    ap.add_argument("--status", action="store_true", help="只打印状态")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    ap.add_argument("--force", action="store_true", help="允许把符号链接换成实体文件")
    args = ap.parse_args()

    proj = os.path.abspath(args.project)
    rules = os.path.join(proj, SRC_REL)
    agents = os.path.join(proj, DST_REL)
    print(f"项目：{proj}")
    for l in status(proj):
        print(l)

    if args.status:
        return 0

    has_rules, has_agents = os.path.exists(rules), os.path.exists(agents)

    if args.source == "rules":
        src, dst = rules, agents
    else:
        src, dst = agents, rules

    if not os.path.exists(src):
        print(f"\n[中止] 权威源不存在：{src}")
        if has_agents and not has_rules:
            print("提示：当前是「单份」模式（规则只在 AGENTS.md）。规则规模仍在上限内时无需同步；"
                  "\n      一旦超过上限参考值，把正文移到 .codebuddy/rules/project-rules.md 后重跑本脚本。")
        return 2

    src_text = read_text(src)

    if os.path.exists(dst):
        if os.path.islink(dst):
            if not args.force:
                print(f"\n[中止] {os.path.relpath(dst, proj)} 是符号链接 —— "
                      f"跨机 clone 会退化、git 无法自愈。加 --force 换成实体文件。")
                return 3
            print(f"\n将把符号链接 {os.path.relpath(dst, proj)} 换成实体文件")
        else:
            dst_text = read_text(dst)
            if dst_text == src_text:
                print(f"\n[一致] {os.path.relpath(dst, proj)} 与权威源内容相同，无需同步。")
                return 0
            if args.check:
                print(f"\n[不一致] {os.path.relpath(dst, proj)} 与权威源已漂移 —— 跑一次本脚本即可同步。")
                return 1
    elif args.check:
        print(f"\n[缺失] {os.path.relpath(dst, proj)} 不存在 —— 派生副本未生成。")
        return 1

    if args.dry_run:
        print(f"\n[预览] 将用 {os.path.relpath(src, proj)} 覆盖 {os.path.relpath(dst, proj)}"
              f"（{len(src_text):,} 字符）—— 未写入任何文件")
        return 0

    if os.path.exists(dst):
        shutil.copy2(dst, dst + ".bak")
        if os.path.islink(dst):
            os.unlink(dst)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(src_text)
    print(f"\n[已同步] {os.path.relpath(src, proj)} -> {os.path.relpath(dst, proj)}"
          f"（{len(src_text):,} 字符）")
    if os.path.exists(dst + ".bak"):
        print(f"        上一版备份：{os.path.relpath(dst + '.bak', proj)}（确认无误后可删）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
