#!/usr/bin/env python
"""上下文自查（**只读**）—— 规则「上下文预算」条的配套工具。

用途：不靠猜。直接读本会话转录的最新一轮 prompt_tokens，判断该不该收尾换会话。
背景：实测「总成本 ∝ 轮次 × 上下文长度」——上下文越重，之后每一轮都更贵
      （某项目实测：平均每次工具调用背着 24.4 万 tok，搬运量 : 产出 = 354 : 1）。

用法：
    python scripts/ctx_check.py                     # 查当前项目最近活跃的会话
    python scripts/ctx_check.py --json              # 机器可读
    python scripts/ctx_check.py --list              # 列最近 6 个会话及各自上下文
    python scripts/ctx_check.py --session 1a9c3377  # 指定会话 id 前缀
    python scripts/ctx_check.py --project /path/to/project

阈值（**双条件**判定：绝对值 + 是否开启新工作，不是单一硬线）：
    < 300K       正常，不干预
    300K ~ 500K  预警：开启新的大块工作前必须先收尾换会话（收尾类小改动可继续）
    > 500K       硬线：禁止开启任何新工作，只能收尾并换会话

为什么不用单一硬线：绝对值不决定成本，「剩余轮次 × 当前长度」才决定 ——
大项目在 400K 只做 3 轮收尾是无害的，小任务在 250K 还要跑 200 轮才是灾难。

只读：仅读本地转录 jsonl；不写文件、不发网络请求。零第三方依赖。
"""

import argparse
import glob
import json
import os
import re
import sys
import time

WARN_TOK = 300_000
HARD_TOK = 500_000


def project_slug(path):
    """项目目录 -> 转录目录 slug。例：K:\\coding\\myproj -> k-coding-myproj"""
    drive, rest = os.path.splitdrive(os.path.abspath(path))
    drive = drive.rstrip(":").lower()
    parts = [p for p in re.split(r"[\\/]+", rest) if p]
    return (drive + "-" + "-".join(parts)) if parts else drive


def tail_usage(fp, chunk=262144, max_rounds=4):
    """从文件尾部倒着读，返回最后一条可解析的 rawUsage（prompt_tokens, usage dict）。

    转录文件可能几十 MB，且正在被写入（末行可能不完整）——故从尾部按块读并容错跳过。
    """
    size = os.path.getsize(fp)
    with open(fp, "rb") as f:
        end = size
        for _ in range(max_rounds):
            start = max(0, end - chunk)
            f.seek(start)
            data = f.read(end - start)
            lines = data.split(b"\n")
            if start > 0:
                lines = lines[1:]  # 首行可能被切断
            for raw in reversed(lines):
                if b"rawUsage" not in raw:
                    continue
                try:
                    obj = json.loads(raw.decode("utf-8", "replace"))
                except Exception:
                    continue
                usage = (obj.get("providerData") or {}).get("rawUsage") or {}
                if usage.get("prompt_tokens"):
                    return usage["prompt_tokens"], usage
            if start == 0:
                break
            end = start
    return None, None


def pick_transcript(proj_dir, session_prefix=None):
    files = [p for p in glob.glob(os.path.join(proj_dir, "*.jsonl"))
             if not p.endswith(".file-rollback.ndjson")]
    if session_prefix:
        files = [p for p in files if os.path.basename(p).startswith(session_prefix)]
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def grade(tokens):
    if tokens > HARD_TOK:
        return "HARD", "硬线", "禁止开启任何新工作 —— 只能收尾并换会话"
    if tokens > WARN_TOK:
        return "WARN", "预警", "开启新的大块工作前必须先收尾换会话（收尾类小改动可继续）"
    return "OK", "正常", "不干预"


def main():
    ap = argparse.ArgumentParser(description="上下文自查（只读）")
    ap.add_argument("--project", default=os.getcwd(), help="项目根目录（默认当前目录）")
    ap.add_argument("--session", default=None, help="会话 id 前缀（默认取最近修改的）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--list", action="store_true", help="列出最近 6 个会话及各自上下文")
    args = ap.parse_args()

    slug = project_slug(args.project)
    proj_dir = os.path.join(os.path.expanduser("~"), ".workbuddy", "projects", slug)

    if not os.path.isdir(proj_dir):
        msg = f"未找到转录目录：{proj_dir}\n（项目 slug = {slug}；用 --project 指定正确根目录）"
        print(msg if not args.json else json.dumps({"error": msg}, ensure_ascii=False))
        return 2

    if args.list:
        files = [p for p in glob.glob(os.path.join(proj_dir, "*.jsonl"))
                 if not p.endswith(".file-rollback.ndjson")]
        files.sort(key=os.path.getmtime, reverse=True)
        print(f"最近活跃会话（{slug}）")
        for p in files[:6]:
            sid = os.path.basename(p).split(".")[0][:8]
            stamp = time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(p)))
            tk, _ = tail_usage(p)
            if not tk:
                print(f"  {sid}  {stamp}          -")
                continue
            print(f"  {sid}  {stamp}  {tk:>9,} tok  [{grade(tk)[0]}]")
        return 0

    fp = pick_transcript(proj_dir, args.session)
    if not fp:
        msg = f"目录下没有匹配的转录 jsonl：{proj_dir}"
        print(msg if not args.json else json.dumps({"error": msg}, ensure_ascii=False))
        return 2

    tokens, usage = tail_usage(fp)
    if not tokens:
        msg = f"未在转录中读到 prompt_tokens：{os.path.basename(fp)}"
        print(msg if not args.json else json.dumps({"error": msg}, ensure_ascii=False))
        return 2

    cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    level, label, advice = grade(tokens)
    session_id = os.path.basename(fp).split(".")[0][:8]

    if args.json:
        print(json.dumps({
            "session": session_id, "prompt_tokens": tokens, "cached_tokens": cached,
            "cached_pct": round(cached / tokens * 100, 1) if tokens else 0,
            "level": level, "advice": advice,
        }, ensure_ascii=False))
        return 0

    print(f"上下文自查 · 会话 {session_id}（项目 {slug}）")
    print(f"  最新 prompt_tokens : {tokens:,} tok")
    if cached:
        print(f"  其中缓存命中       : {cached:,} tok（{cached / tokens:.1%}）")
    print(f"  等级               : [{level}] {label} —— {advice}")
    print(f"  阈值               : 预警 {WARN_TOK:,} / 硬线 {HARD_TOK:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
