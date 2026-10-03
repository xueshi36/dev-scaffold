#!/usr/bin/env python
"""收尾助手 —— 把收尾时原本 4 次独立 Edit（每次都背着整个上下文各跑一轮 LLM）压成 1 次调用。

一次做完：
  1. `doc/CHANGELOG.md` 顶部插入条目（跳过代码围栏里的格式示例；有占位行则替换之）
  2. `doc/05-里程碑与进度.md` 勾选里程碑（可选；支持两种写法，见下）
  3. `doc/会话交接.md` 释放持有者（可选）
  4. 顺带体检：规则文件规模是否超注入上限、AGENTS.md 与权威源是否已漂移
  5. 打印变更摘要

背景：某项目实测写操作中 51.5% 是文档更新，收尾四件套累计 194 次 Edit / 5,551 万 tok。
      —— **次数才是成本，不是处数**。合并写入是收益最直接的一条优化。

用法：
    python scripts/closeout.py --session "WorkBuddy 主 agent" \\
        --title "上下文成本优化" --body .tmp_cleanup/closeout_body.md \\
        --milestone M1 --release

    --body -             从 stdin 读正文
    --dry-run            只预览，不写文件
    --project <dir>      指定仓库根（默认脚本所在仓库的上一级；**测试时指向临时副本**）
    --date YYYY-MM-DD    指定日期（默认今天）
    --changelog / --milestones / --handoff   覆盖默认文件路径

里程碑勾选的两种写法（自动识别）：
    A. 复选框项本身带编号：`- [ ] **M5-18** …`  -> 直接勾选该行
    B. 编号在标题上：`### M1 名称` + 其下若干 `- [ ] …` -> 勾选该组内全部未勾选项

安全：
  - 写前把原文件备份到 `<项目>/.tmp_cleanup/closeout_backup/`
  - 若 CHANGELOG 顶部已存在同标题条目，报错退出（防重复插入）
  - 保留原文件行尾风格（CRLF / LF）；代码围栏内的 `## ` 不会被误当作插入锚点
  - 零第三方依赖
"""

import argparse
import datetime
import os
import re
import shutil
import sys

DEFAULT_PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RULES_LIMIT_CHARS = 5000
RULES_SRC = os.path.join(".codebuddy", "rules", "project-rules.md")
RULES_DERIVED = "AGENTS.md"


def load(path):
    """返回 (lines, newline_style)，换行归一化为 \\n。"""
    with open(path, "r", encoding="utf-8", newline="") as f:
        raw = f.read()
    crlf = raw.count("\r\n")
    lf = raw.count("\n") - crlf
    return raw.replace("\r\n", "\n").split("\n"), ("\r\n" if crlf > lf else "\n")


def save(path, lines, nl, backup_dir, dry_run=False):
    if dry_run:
        return
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(path, os.path.join(backup_dir, os.path.basename(path)))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))


def read_body(spec):
    if spec == "-":
        return sys.stdin.read().rstrip("\n").split("\n")
    with open(spec, "r", encoding="utf-8") as f:
        return f.read().rstrip("\n").split("\n")


def fence_mask(lines):
    """True = 该行处于 ``` / ~~~ 围栏内（含围栏行本身）——用于避免把示例代码当正文锚点。"""
    mask, in_fence = [], False
    for l in lines:
        s = l.strip()
        if s.startswith("```") or s.startswith("~~~"):
            mask.append(True)
            in_fence = not in_fence
            continue
        mask.append(in_fence)
    return mask


def insert_changelog(path, session, title, body, date, backup_dir, dry_run):
    lines, nl = load(path)
    head = f"## {date} · {session}（{title}）"
    mask = fence_mask(lines)
    for i, line in enumerate(lines):
        if not mask[i] and line.strip() == head:
            raise SystemExit(f"[中止] CHANGELOG 已存在同标题条目，未做任何修改：{head}")

    placeholder = next((i for i, l in enumerate(lines)
                        if not mask[i] and l.strip() in ("（暂无记录）", "（暂无记录。）")), None)
    if placeholder is not None:
        lines[placeholder:placeholder + 1] = [head, ""] + body + [""]
        save(path, lines, nl, backup_dir, dry_run)
        return f"CHANGELOG.md : 第 {placeholder + 1} 行替换占位行并插入《{title}》（{len(body)} 行正文）"

    idx = next((i for i, l in enumerate(lines) if not mask[i] and l.startswith("## ")), None)
    if idx is None:
        sep = next((i for i, l in enumerate(lines) if not mask[i] and l.strip() == "---"), None)
        idx = len(lines) if sep is None else sep + 1
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1
    lines[idx:idx] = [head, ""] + body + [""]
    save(path, lines, nl, backup_dir, dry_run)
    return f"CHANGELOG.md : 第 {idx + 1} 行插入《{title}》（{len(body)} 行正文）"


def check_milestone(path, mid, date, backup_dir, dry_run):
    lines, nl = load(path)

    direct = re.compile(r"^(\s*)- \[ \] (.*" + re.escape(mid) + r".*)$")
    hits = [i for i, l in enumerate(lines) if direct.match(l)]
    if hits:
        i = hits[0]
        lines[i] = re.sub(r"^(\s*)- \[ \] ", r"\1- [x] ", lines[i], count=1)
        if date not in lines[i]:
            lines[i] = lines[i].rstrip() + f"（{date} 勾选）"
        save(path, lines, nl, backup_dir, dry_run)
        return f"doc/05       : 第 {i + 1} 行勾选 {mid}（复选框直接匹配）"

    head = re.compile(r"^(#{2,6})\s*" + re.escape(mid) + r"\b")
    for i, l in enumerate(lines):
        m = head.match(l)
        if not m:
            continue
        level = len(m.group(1))
        end = len(lines)
        for k in range(i + 1, len(lines)):
            m2 = re.match(r"^(#{2,6})\s", lines[k])
            if m2 and len(m2.group(1)) <= level:
                end = k
                break
        ticked = 0
        for k in range(i + 1, end):
            if re.match(r"^\s*- \[ \] ", lines[k]):
                lines[k] = re.sub(r"^(\s*)- \[ \] ", r"\1- [x] ", lines[k], count=1)
                if date not in lines[k]:
                    lines[k] = lines[k].rstrip() + f"（{date} 勾选）"
                ticked += 1
        if not ticked:
            return f"doc/05       : {mid} 组内没有未勾选项 —— 跳过"
        save(path, lines, nl, backup_dir, dry_run)
        return f"doc/05       : 勾选 {mid} 组内 {ticked} 项（第 {i + 1} 行起的标题分组）"

    return f"doc/05       : 未找到 {mid}（编号有误，或该项已勾选）—— 跳过"


def release_handoff(path, session, title, date, backup_dir, dry_run):
    lines, nl = load(path)
    i = next((k for k, l in enumerate(lines) if l.strip() == "## 当前持有者"), None)
    if i is None:
        return "交接板       : 未找到「## 当前持有者」段 —— 跳过"
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
    lines[i + 1:j] = ["",
                      f"（空）——无会话持有。最近一次持有：{session}"
                      f"（{date}，**{title}**，详见 CHANGELOG {date}）。",
                      ""]
    save(path, lines, nl, backup_dir, dry_run)
    return f"交接板       : 释放持有者（原段落 {j - i - 1} 行 -> 1 行）"


def health_check(proj):
    """规则分发体检：规模是否超注入上限、权威源与派生副本是否漂移。非致命。"""
    out = []
    src = os.path.join(proj, RULES_SRC)
    dst = os.path.join(proj, RULES_DERIVED)

    def size(p):
        try:
            with open(p, "r", encoding="utf-8", newline="") as f:
                return len(f.read().replace("\r\n", "\n"))
        except OSError:
            return None

    n_src, n_dst = size(src), size(dst)
    if os.path.islink(dst):
        out.append("⚠️  AGENTS.md 是符号链接 —— Windows 默认 core.symlinks=false，"
                   "跨机 clone 会退化为含目标路径的文本文件（git 也无法自愈）；建议改为实体文件")
    if n_src is None and n_dst is None:
        return out
    for label, n in (("权威源 .codebuddy/rules/project-rules.md", n_src),
                     ("AGENTS.md", n_dst)):
        if n is not None and n > RULES_LIMIT_CHARS:
            out.append(f"⚠️  {label} 已 {n:,} 字符，超过实测注入上限量级"
                       f"（{RULES_LIMIT_CHARS:,}）—— 根目录 AGENTS.md 的注入段会被静默截断，"
                       f"权威源须放 .codebuddy/rules/ 并跑 scripts/sync_rules.py")
    if n_src is not None and n_dst is not None and not os.path.islink(dst):
        a = open(src, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        b = open(dst, encoding="utf-8", newline="").read().replace("\r\n", "\n")
        if a != b:
            out.append("⚠️  AGENTS.md 与权威源内容不一致（已漂移）—— 跑 scripts/sync_rules.py 同步")
    return out


def main():
    ap = argparse.ArgumentParser(description="收尾助手：一次调用更新 CHANGELOG / doc05 / 交接板")
    ap.add_argument("--session", required=True, help='会话名，如 "WorkBuddy 主 agent"')
    ap.add_argument("--title", required=True, help="本次改动标题")
    ap.add_argument("--body", required=True, help="正文 markdown 路径，或 - 表示 stdin")
    ap.add_argument("--milestone", default=None, help="要勾选的里程碑编号，如 M1 / M5-18")
    ap.add_argument("--release", action="store_true", help="释放交接板持有者")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="日期，默认今天")
    ap.add_argument("--project", default=DEFAULT_PROJ, help="仓库根（测试时指向临时副本）")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    ap.add_argument("--changelog", default=None, help="覆盖 CHANGELOG 路径")
    ap.add_argument("--milestones", default=None, help="覆盖里程碑文件路径")
    ap.add_argument("--handoff", default=None, help="覆盖交接板路径")
    args = ap.parse_args()

    proj = os.path.abspath(args.project)
    changelog = args.changelog or os.path.join(proj, "doc", "CHANGELOG.md")
    milestones = args.milestones or os.path.join(proj, "doc", "05-里程碑与进度.md")
    handoff = args.handoff or os.path.join(proj, "doc", "会话交接.md")
    backup_dir = os.path.join(proj, ".tmp_cleanup", "closeout_backup")
    if not os.path.exists(changelog):
        raise SystemExit(f"[中止] 缺少 CHANGELOG：{changelog}")

    body = read_body(args.body)
    tag = "[预览] " if args.dry_run else ""
    print(f"{tag}收尾：{args.date} · {args.session}（{args.title}）")
    print(f"  {insert_changelog(changelog, args.session, args.title, body, args.date, backup_dir, args.dry_run)}")
    if args.milestone:
        if os.path.exists(milestones):
            print(f"  {check_milestone(milestones, args.milestone, args.date, backup_dir, args.dry_run)}")
        else:
            print(f"  doc/05       : 文件不存在，跳过里程碑勾选（{milestones}）")
    if args.release:
        if os.path.exists(handoff):
            print(f"  {release_handoff(handoff, args.session, args.title, args.date, backup_dir, args.dry_run)}")
        else:
            print(f" 交接板       : 文件不存在，跳过持有者释放（{handoff}）")
    for line in health_check(proj):
        print(f"  {line}")
    print("\n--dry-run：未写入任何文件" if args.dry_run
          else f"\n备份位于 {backup_dir}（回滚：把备份复制回 doc/ 即可）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
