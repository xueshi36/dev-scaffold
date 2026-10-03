# CHANGELOG（每次改动一条，倒序追加）

格式：`## YYYY-MM-DD · <会话名>（<改动标题>）`，条目：`- <类型> 改动内容（原因 / 影响范围）`
（收尾用 `python scripts/closeout.py` 自动插入，勿手工 Edit）

## 2026-10-03 · WorkBuddy 主 agent（规则分发模型纠错 + 支柱八 + 三个配套脚本）

- docs: **规则分发模型纠错** —— 原「规则正文全项目只存 `AGENTS.md` 一份」在 WorkBuddy 上实测不成立：根目录 `AGENTS.md` 注入到 `<project_guidance>` 段，**该段有长度上限、超限静默截断**（实测 8,434 字符时可见部分止于 ≈7,890 字符，丢掉尾部两整节）；而 `.codebuddy/rules/*.md` 走另一通道**完整无截断**。改为**按规则规模分档**：< 5,000 字符单份 / ≥ 5,000 字符时权威源放 `.codebuddy/rules/project-rules.md`、`AGENTS.md` 降为**派生副本**。🔴 同时明确禁止「`.codebuddy/rules/` 只放一行指针指向 AGENTS.md」——那会让 WorkBuddy 拿到「被截断的正文 + 一行指针」，完整规则一节都拿不到
  - 涉及：README.md（兼容表 + 要点 + 目录结构）、设计说明.md 支柱二、template/doc/00 §3.1 + 新增 §3.1.1、template/AGENTS.md 抬头、template/CLAUDE.md
- feat(template): **新增支柱八「上下文成本纪律」** —— 前七柱都在讲「怎么把事做对」，没人管「做这件事本身花了多少钱」。含五条：八.1 上下文预算（**双条件**判定 `<300K` 正常 / `300K~500K` 预警 / `>500K` 硬线，外加比阈值更有效的「单会话单任务」）、八.2 读取纪律（大文档先 Grep 定位再分页 Read）、八.3 大输出落盘 + 摘要（信息不丢，只是不进上下文）、八.4 收尾一次写完、八.5 命令合并 + 子任务审慎。同步修订支柱三（收尾用脚本一次写完）与支柱四（**次数才是成本，不是处数**）
  - 涉及：设计说明.md（新增支柱八 + 修订支柱三/四 + 八大支柱）、template/AGENTS.md（新增 §八，原 §八 待定事项 → §九）、template/doc/00 §3.2 会话生命周期、template/doc/05（进度日志表降级为可选 —— 实测它是 Edit 热点首位）
- feat(scripts): **新增 `template/scripts/` 三个配套脚本**（Python 标准库零依赖）—— `ctx_check.py`（上下文自查，读本会话转录最新 `prompt_tokens` 并分级；`--json` / `--list`）、`closeout.py`（收尾一次写完 CHANGELOG + doc/05 勾选 + 交接板释放，并顺带体检规则分发；支持 `--dry-run` / `--project` / 路径覆盖；**跳过代码围栏**避免把格式示例误当插入锚点；支持两种里程碑写法）、`sync_rules.py`（规则权威源 ↔ 派生副本同步；`--status` / `--check`（exit 1 可挂 CI）/ `--dry-run` / `--force`）
- chore: `template/.gitignore` 增加 `.tmp_cleanup/`（大输出落盘日志与收尾备份的家）；仓库根新增 `.gitignore`（本仓库自身用，避免测试副本污染 `git status`）
- fix(docs): **公开仓库脱敏补全** —— README 已在 c480359 脱敏，但 `init.py:42` 交互示例、`template/doc/00` §3.1（**会随模板复制进每个新项目，影响最大**）、`CHANGELOG.md` 多条仍含内部项目名，另含本机代理端口等环境细节；全部改为中性表述
- docs(template): `template/doc/00` §3.4 补三条符号链接硬证据（33 字节退化 / **退化后 git 无法自愈** / 建链静默降级为 0 字节）；`template/doc/CHANGELOG.md` 与仓库 CHANGELOG 格式行同步为 closeout.py 的标题格式
  - 验证：✅ 全部实跑，证据如下
    - **ctx_check.py**：`--project` 指向无转录目录 → 正确报「未找到转录目录」并 exit 2；指向真实项目 → 输出 `196,499 tok（缓存 99.9%）[OK]`；`--list` 正确列出 6 个会话（含 `1a9c3377` 495,699 tok `[WARN]`）；`--json` 输出合法 JSON
    - **closeout.py**（在 `.tmp_cleanup/co_test*` 副本上跑，**真实 template/ 全程未被触碰**，`git status` 核对）：`--dry-run` 报「第 19 行替换占位行 / 勾选 M1 组内 2 项 / 释放持有者」；正式写入后 `diff` 三处**全部正确** —— CHANGELOG 占位行被替换且**围栏内示例未被误插**、doc/05 两项 `- [ ]`→`- [x]` 附日期、交接板持有者 3 行→1 行；同标题重跑正确中止 exit 1；无占位行分支正确插到 `---` 之后且围栏示例完好（仍在第 10 行）；副本清理后确认真实 `template/` 无污染
    - **sync_rules.py**：`--status` 单份模式正确识别；权威源缺失时 exit 2 并给出「单份模式」提示；造权威源后同步成功且 `grep` 确认 `AGENTS.md` 拿到标记；`--check` 一致 exit 0 / 人为制造漂移后 exit 1；`--dry-run` 校验 md5 未变；8,406 字符时正确触发「⚠️ 超过上限参考值」；多余 md 文件正确提示不会同步
    - **脱敏**：全仓 `grep -rn "取证渗透中台|192\.168|10089|xueshi36|github_pat|be9e85f3|7897|35776|44621|sdyp|kali-vm173"` → **无命中**（exit 1）
    - **陈旧表述**：`grep "七大支柱|只存 AGENTS.md 一份|全项目唯一的规则正文"` → 无命中；剩余「放一行指针」「唯一正文」两处命中均为**禁止性表述本身**（预期内）
    - 本次收尾**本身即用 `closeout.py` 执行**（吃狗粮）

## 2026-09-27 · ZCode（AGENTS.md 共享桥接会话）

- docs: **工具映射表证据升级 + dsh 结论落表**（本次逐家查官方文档核实）——① Claude Code ≥v2.1.277 **原生读根目录 AGENTS.md**（项目内无 CLAUDE.md 时；官方 memory 文档明确认可 `ln -s AGENTS.md CLAUDE.md` 符号链接共享，并注明 Windows 建链需开发者模式/管理员、编辑工具拒绝写穿链接）；② ZCode 升级为✅实测（2026-09-27 某真实项目：AGENTS.md 软链接被自动注入 + ZCode 记忆目录软链接共享 `.workbuddy/memory/` 读写全通）；③ opencode 官方确认 AGENTS.md 为主/CLAUDE.md 兜底/symlink 共享；④ dsh（DeepSeek Harness）❓官方文档未确认项目级 AGENTS.md 自动加载（其仓库内 AGENTS.md 仅面向贡献者），接入前先实测。涉及：README.md 兼容速查表、设计说明.md 支柱二、template/doc/00 §3.1、template/AGENTS.md 头注
- docs: **新增 template/doc/00 §3.4「符号链接桥接（规则入口 / 跨工具记忆共享）」**——方法论：两种建链场景（①权威源不在根目录→根 AGENTS.md 反向链接；②其他工具全局记忆目录→软链接到 `.workbuddy/memory/`）+ 实测三坑（Windows 建链需提权；跨机器共享盘必须相对路径目标，绝对路径会被客户端拿到本机解析而失败；git 仓库内符号链接在 Windows `core.symlinks=false` 克隆时退化为文本文件，故项目内链接建议不入库）+ 写穿限制（ZCode/Claude Code 编辑工具拒绝写穿符号链接，AI 改规则须直接编辑真实目标文件）+ 记忆共享约定（`.workbuddy/memory/` 唯一权威源，任一工具写入即全工具可见）
- feat(template): AGENTS.md 开工清单加读 `.workbuddy/memory/MEMORY.md`（WorkBuddy 之外的工具不会自动注入记忆，靠开工清单兜底读同一份记忆）；`.workbuddy/memory/MEMORY.md` 模板头注标注"跨工具共享权威源"
- chore(init.py): 「下一步」输出加第 4 条——多工具记忆桥接提示（指向 doc/00 §3.4）
  - 验证：✅ 实测——init.py 冒烟重跑通过（配置驱动建临时项目，12 文件复制、新提示行输出正常）；各文件改动 Read 确认落地；符号链接三坑与各工具结论均来自 2026-09-27 某真实项目项目实测或对应官方文档（claude code memory / opencode rules / agents.md）

## 2026-09-27 · WorkBuddy（脚手架优化会话）

- feat: **新增 init.py 配置化初始化器**（`scaffold.config.example.toml` + `init.py`，Python 3.11+ 标准库零依赖）——根治"新项目手改 43 处占位符"摩擦。行为：复制 template/（含隐藏目录）→ TOML 配置或交互问答驱动替换已知命名占位符（{{项目名}}/项目一句话/背景/技术栈/目录结构/运行方式）→ 残留 {{...}} 扫描报告（区分"待人工填写"与 .env.example 教学示例）→ 可选 git init（`-b main`）+ 首次提交
  - 验证：✅ 实测通过——配置驱动模式全流程（中文路径"测试项目 中台"，11 文件复制、8 处替换落地 Read 确认、git 提交 23c447d、工作区干净）；边界三项（默认分支=main、非空目录拒绝、缺必填项报错）均符合预期；临时目录已清理
- docs: **工具映射表增加证据等级标注**（✅实测 ＞ 📄官方文档 ＞ ❓未验证）——原表把"WorkBuddy 兼容 AGENTS.md"与".codebuddy/rules/ 注入"混为一谈。实测结论（2026-09-27 某真实项目会话）：`.codebuddy/rules/*.md` 注入与 `.workbuddy/memory/` 记忆注入为✅实测；根目录 AGENTS.md 兼容为📄官方文档+社区多源印证（官方 Project 页本轮访问 404，未做端到端实测）；ZCode/Trae 为❓未验证。涉及：README.md 兼容速查表、设计说明.md 支柱二、template/doc/00 §3.1
- docs: README「新项目启用五步」升级为「一条命令（init.py）+ 手动五步（备选）」
- chore: **仓库级 git 环境修复**——① 清除残留死代理（`http.proxy` 指向已失效的本地代理端口）改为空值直连；② `credential.helper=""`（实测本会话环境 GCM/helper-selector 启动即挂死 git 全部网络操作，远端 URL 已内嵌凭据，helper 冗余且有害；同法修至另一个项目仓库）
- ⚠️ 遗留：GitHub 远端本次**未推送**——实测 github.com 经本机会话代理超时/拒连，当前无法访问 GitHub；代理恢复后执行 `git push github main` 即可（Gitea 已同步一致）
