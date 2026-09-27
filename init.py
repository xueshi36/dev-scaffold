#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dev-scaffold 项目初始化器（Python 3.11+，零第三方依赖）。

用法：
    python init.py <新项目目录>                        # 交互问答模式
    python init.py <新项目目录> --config scaffold.config.toml
    python init.py <新项目目录> --config x.toml --no-git

行为：
    1. 复制 template/ 全部内容（含隐藏目录）到目标目录
    2. 按配置替换 {{占位符}}（只替换已知命名占位符，其余保留并报告）
    3. 打印替换统计 + 残留占位符清单（残留 = 留待人工填写的自由内容）
    4. 可选 git init + 首次提交（配置 [git] init = true 或 --git）
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

SCAFFOLD_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = SCAFFOLD_ROOT / "template"

# 占位符内容前缀 → 配置键（对 {{...}} 内文本做前缀匹配，避免整串匹配因措辞微调失效）
PLACEHOLDER_MAP: list[tuple[str, str]] = [
    ("项目名", "project.name"),
    ("用一两句话说清", "project.brief"),
    ("项目背景", "project.background"),
    ("语言/框架", "stack.tech"),
    ("backend/", "stack.layout"),
    ("启动命令", "stack.run"),
]

# 这些文件里的 {{...}} 是教学示例，不算残留问题
EXAMPLE_FILES = {".env.example"}

INTERACTIVE_FIELDS = [
    ("project.name", "项目名（如：取证渗透中台）", None),
    ("project.brief", "项目一句话（做什么/给谁用/核心产出）", None),
    ("project.background", "项目背景（可留空，之后在 doc/00 补）", ""),
    ("stack.tech", "技术栈（可留空，定稿后再填）", ""),
    ("stack.layout", "目录结构，一行一条，空行结束（可留空）", ""),
    ("stack.run", "本地运行方式（可留空）", ""),
]


def die(msg: str) -> None:
    print(f"[init] 错误：{msg}", file=sys.stderr)
    sys.exit(1)


def cfg_get(cfg: dict, dotted: str):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def load_config(path: Path) -> dict:
    if not path.exists():
        die(f"配置文件不存在：{path}")
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        die(f"配置文件 TOML 解析失败：{e}")


def interactive_fill(cfg: dict) -> dict:
    print("== 未提供配置文件，进入交互问答（回车=使用默认/留空）==")
    for dotted, prompt, default in INTERACTIVE_FIELDS:
        if cfg_get(cfg, dotted) not in (None, ""):
            continue  # 已有值则不重复问
        try:
            raw = input(f"{prompt}：").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            die("交互被中断")
        if raw == "":
            if default is None:
                die(f"必填项未填：{dotted}")
            raw = default
        # 写入嵌套 dict
        parts = dotted.split(".")
        cur = cfg
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = raw
    return cfg


def replace_placeholders(text: str, cfg: dict) -> tuple[str, int]:
    """替换已知命名占位符；配置值为空/缺失则保留原占位符。返回(新文本, 替换次数)。"""
    count = 0
    out, i = [], 0
    while True:
        start = text.find("{{", i)
        if start < 0:
            out.append(text[i:])
            break
        end = text.find("}}", start + 2)
        if end < 0:
            out.append(text[i:])
            break
        inner = text[start + 2:end]
        replaced = False
        for prefix, key in PLACEHOLDER_MAP:
            if inner.startswith(prefix):
                val = cfg_get(cfg, key)
                if val:  # 仅非空才替换
                    out.append(text[i:start])
                    out.append(str(val))
                    count += 1
                    replaced = True
                break
        if not replaced:
            out.append(text[i:end + 2])  # 保留原占位符
            i = end + 2
        else:
            i = end + 2
    return "".join(out), count


def scan_residuals(root: Path) -> list[tuple[Path, int, str]]:
    """扫描残留 {{...}}（含未填的命名占位符与教学占位符）。"""
    residuals = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if "{{" in line and "}}" in line:
                residuals.append((p.relative_to(root), lineno, line.strip()[:80]))
    return residuals


def main() -> None:
    ap = argparse.ArgumentParser(description="dev-scaffold 项目初始化器")
    ap.add_argument("target", help="新项目目录（不存在或为空）")
    ap.add_argument("--config", default=None, help="TOML 配置文件路径")
    ap.add_argument("--yes", action="store_true", help="非交互模式：缺项按留空处理")
    ap.add_argument("--no-git", action="store_true", help="跳过 git init")
    ap.add_argument("--force", action="store_true", help="允许目标目录非空（覆盖式复制）")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if target.exists() and any(target.iterdir()) and not args.force:
        die(f"目标目录非空：{target}（确认覆盖请加 --force）")

    # 载入配置：--config > 脚手架根 scaffold.config.toml > 交互/非交互兜底
    if args.config:
        cfg = load_config(Path(args.config).resolve())
    elif (SCAFFOLD_ROOT / "scaffold.config.toml").exists():
        cfg = load_config(SCAFFOLD_ROOT / "scaffold.config.toml")
        print(f"[init] 使用默认配置：{SCAFFOLD_ROOT / 'scaffold.config.toml'}")
    else:
        cfg = {}
    if not args.config and not args.yes:
        cfg = interactive_fill(cfg)
    if not cfg_get(cfg, "project.name"):
        die("缺少必填项 project.name（配置文件或交互中提供）")

    # 1. 复制模板
    if not TEMPLATE_DIR.exists():
        die(f"模板目录不存在：{TEMPLATE_DIR}")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_DIR, target, dirs_exist_ok=True)
    n_files = sum(1 for p in target.rglob("*") if p.is_file())

    # 2. 占位符替换（UTF-8 文本文件；二进制原样跳过）
    total = 0
    for p in sorted(target.rglob("*")):
        if not p.is_file() or ".git" in p.parts:
            continue
        raw = p.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new_text, n = replace_placeholders(text, cfg)
        if n:
            # 保持原换行风格：decode/encode 不改动行尾字节
            p.write_bytes(new_text.encode("utf-8"))
            total += n

    # 3. 残留扫描
    residuals = scan_residuals(target)

    # 4. 可选 git init + 首次提交
    git_done = False
    want_git = cfg_get(cfg, "git.init")
    if want_git is None:
        want_git = True
    if want_git and not args.no_git:
        try:
            subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True,
                           capture_output=True, text=True)
            subprocess.run(["git", "add", "-A"], cwd=target, check=True,
                           capture_output=True, text=True)
            subprocess.run(
                ["git", "-c", "core.quotepath=false", "commit", "-m",
                 "chore: 项目初始化（dev-scaffold 模板）"],
                cwd=target, check=True, capture_output=True, text=True)
            git_done = True
        except FileNotFoundError:
            print("[init] 警告：未找到 git，跳过 git init")
        except subprocess.CalledProcessError as e:
            print(f"[init] 警告：git 操作失败（不影响文件初始化）：{e.stderr}")

    # 5. 报告
    print()
    print("== dev-scaffold 初始化完成 ==")
    print(f"目标目录：{target}")
    print(f"复制文件：{n_files} 个；占位符替换：{total} 处")
    print()
    print("残留 {{...}} 清单（= 留待人工填写，或教学示例可保留）：")
    if not residuals:
        print("  （无）")
    else:
        shown_file = None
        for rel, lineno, line in residuals:
            if rel.name in EXAMPLE_FILES:
                tag = " [示例，可保留]"
            else:
                tag = ""
            if str(rel) != shown_file:
                print(f"  {rel}{tag}")
                shown_file = str(rel)
            print(f"    L{lineno}: {line}")
    print()
    print("下一步：")
    print("  1. 补齐上述残留占位符（doc/00 背景、doc/05 里程碑计划等）")
    print("  2. 凭据从 .env.example 复制为 .env 填写（永不入库）")
    print("  3. 开首个 AI 会话：读 AGENTS.md + doc/05 + doc/会话交接.md")
    print("  4. （可选）多工具共享记忆：把其他 AI 工具的全局记忆目录软链接到")
    print("     .workbuddy/memory/，操作规范与三坑见 template/doc/00 §3.4")
    if not git_done and want_git and not args.no_git:
        print("  4. （git 未初始化成功，请手动 git init && git add -A && git commit）")


if __name__ == "__main__":
    # Windows 控制台中文输出兜底
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    main()
