# 开发脚手架模板（多 AI 协作工程规范）

> 从一个实际多 AI 协作项目的实践中提炼的通用工程脚手架，适用于**网站开发、应用程序开发、APP 开发**等各类软件项目。
> 目标：让任何 AI（WorkBuddy / ZCode / Claude Code / Trae…）接入项目时，都能在同一套纪律下接力工作，且每一次推进、改动、排障都有据可查。

## 这套脚手架解决什么问题

| 痛点 | 解法 |
|---|---|
| AI 每次会话"失忆"，重复解释背景 | 分层事实源：规则自动加载 + doc 文档即事实源 + 交接板接力 |
| 多个 AI 改来改去互相冲突 | 单持有者交接板 + git 分支纪律 |
| 改了什么、为什么改，事后说不清 | CHANGELOG 强制结构化记录 + 触发/豁免清单 |
| 声称"已修复"实际没修好 | 修复落地验证（Read 确认 + 实际运行验证） |
| 同样的坑反复踩 | 已知技术陷阱清单（固化为规则强制条目） |
| 凭据/敏感数据泄进 git 或外发 | .env 隔离 + 红线清单 |
| 凭感觉开发、方向漂移 | 里程碑驱动 + 决策记录表（先改设计文档再改代码） |

## 目录结构

```
dev-scaffold/
├── README.md            本文件
├── 设计说明.md          核心设计思路（七大支柱，含每条的理由）
└── template/            ← 新项目时把此目录内容复制到项目根目录
    ├── AGENTS.md                          项目规则（跨 AI 工具通用权威源，唯一正文）
    ├── CLAUDE.md                          Claude Code 入口（一行 @AGENTS.md 引入）
    ├── .workbuddy/memory/MEMORY.md        项目记忆（知识沉淀，非规则）
    ├── .gitignore                         通用忽略规则（含凭据/产物/多语言）
    ├── .env.example                       凭据占位模板
    └── doc/
        ├── 00-项目总览与协作规范.md          （模板，含多工具规则映射）
        ├── 01-架构设计与决策记录.md          （模板，含 D 表格式）
        ├── 05-里程碑与进度.md                （模板）
        ├── CHANGELOG.md                      （模板）
        ├── 调试记录.md                       （模板）
        └── 会话交接.md                       （模板）
```

## 新项目启用

**推荐：一条命令**（Python 3.11+，零第三方依赖）：

```bash
# 方式一：交互问答（自动生成配置）
python init.py <新项目目录>

# 方式二：配置文件驱动（可复现/可脚本化）
cp scaffold.config.example.toml scaffold.config.toml   # 填写后
python init.py <新项目目录> --config scaffold.config.toml
```

init.py 会：复制 `template/` 全部内容（含隐藏目录）→ 按配置替换 `{{占位符}}` → 打印替换统计与残留占位符清单（残留项=需人工填写的自由内容）→ 可选 `git init` + 首次提交（`[git] init = true`）。

**手动方式（备选）**：

1. 复制：把 `template/` 下全部内容（含隐藏目录）复制到新项目根目录
2. 改规则：`AGENTS.md` 中替换 `{{占位符}}`——项目名、技术栈、目录结构；技术栈定稿前可先留空
3. 改文档：`doc/00` 填项目背景与机器/环境分工；`doc/05` 写里程碑计划
4. 初始化：`git init && git add -A && git commit`；凭据进 `.env`（从 `.env.example` 复制，永不入库）
5. 开工：新 AI 会话第一句 = 读规则 + doc/05 + 会话交接板；此后按铁律接力

## 同步到 Gitea / GitHub

本仓库经审核后推送：
```bash
git remote add origin <仓库地址>
git push -u origin main
```
建议仓库保持**私有**（含工程规范虽不涉密，但工作流细节暴露给公众无益）。新项目使用本模板时，同样按私有仓库起步。

## AI 工具兼容机制速查（✅实测 ＞ 📄官方文档 ＞ ❓未验证）

| 工具 | 规则加载 | 证据 |
|---|---|---|
| WorkBuddy / CodeBuddy | 根目录 `AGENTS.md`；`.codebuddy/rules/*.md` 亦自动加载；`.workbuddy/memory/` 记忆注入 | AGENTS.md=📄官方文档+社区多源印证；后两者=✅实测（2026-09-27 真实项目会话） |
| ZCode | 根目录 `AGENTS.md`（含符号链接形式） | ✅实测（2026-09-27：AGENTS.md 软链接被自动注入；记忆目录软链接共享 `.workbuddy/memory/` 读写均通） |
| opencode、Cursor、Codex、Gemini CLI、Windsurf、Zed | 根目录 **`AGENTS.md`**（opencode 以 CLAUDE.md 兜底） | 📄各自官方文档（AGENTS.md 开放标准采纳列表） |
| Claude Code | ≥v2.1.277 原生读 `AGENTS.md`（无 CLAUDE.md 时）；模板已含 `CLAUDE.md`（一行 `@AGENTS.md`，新旧版本通吃） | 📄官方文档（memory 页，明确认可 `ln -s` 符号链接共享） |
| Trae | `.trae/rules/`（无引入机制，需复制正文并保持同步） | ❓未实测 |
| 其他（dsh 等） | 以其官方文档为准；遵循 AGENTS.md 约定则零配置 | ❓dsh 官方文档未确认项目级 AGENTS.md 自动加载，接入前先实测 |

**要点**：规则正文只存 `AGENTS.md` 一份；其他入口只允许一行引入或符号链接（Trae 除外）；规则与记忆分离（`.workbuddy/memory/` 是记忆不是规则）。WorkBuddy 求稳可两者都放：`.codebuddy/rules/` 放一行指针指向 AGENTS.md。符号链接桥接的操作规范与三坑（Windows 提权 / 跨机相对路径 / git 可移植性）见 `template/doc/00` §3.4。
