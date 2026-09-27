# CHANGELOG（每次改动一条，倒序追加）

格式：`## YYYY-MM-DD · <会话名>`，条目：`- <类型> 改动内容（原因 / 影响范围）`

## 2026-09-27 · ZCode（AGENTS.md 共享桥接会话）

- docs: **工具映射表证据升级 + dsh 结论落表**（本次逐家查官方文档核实）——① Claude Code ≥v2.1.277 **原生读根目录 AGENTS.md**（项目内无 CLAUDE.md 时；官方 memory 文档明确认可 `ln -s AGENTS.md CLAUDE.md` 符号链接共享，并注明 Windows 建链需开发者模式/管理员、编辑工具拒绝写穿链接）；② ZCode 升级为✅实测（2026-09-27 取证渗透中台：AGENTS.md 软链接被自动注入 + ZCode 记忆目录软链接共享 `.workbuddy/memory/` 读写全通）；③ opencode 官方确认 AGENTS.md 为主/CLAUDE.md 兜底/symlink 共享；④ dsh（DeepSeek Harness）❓官方文档未确认项目级 AGENTS.md 自动加载（其仓库内 AGENTS.md 仅面向贡献者），接入前先实测。涉及：README.md 兼容速查表、设计说明.md 支柱二、template/doc/00 §3.1、template/AGENTS.md 头注
- docs: **新增 template/doc/00 §3.4「符号链接桥接（规则入口 / 跨工具记忆共享）」**——方法论：两种建链场景（①权威源不在根目录→根 AGENTS.md 反向链接；②其他工具全局记忆目录→软链接到 `.workbuddy/memory/`）+ 实测三坑（Windows 建链需提权；跨机器共享盘必须相对路径目标，绝对路径会被客户端拿到本机解析而失败；git 仓库内符号链接在 Windows `core.symlinks=false` 克隆时退化为文本文件，故项目内链接建议不入库）+ 写穿限制（ZCode/Claude Code 编辑工具拒绝写穿符号链接，AI 改规则须直接编辑真实目标文件）+ 记忆共享约定（`.workbuddy/memory/` 唯一权威源，任一工具写入即全工具可见）
- feat(template): AGENTS.md 开工清单加读 `.workbuddy/memory/MEMORY.md`（WorkBuddy 之外的工具不会自动注入记忆，靠开工清单兜底读同一份记忆）；`.workbuddy/memory/MEMORY.md` 模板头注标注"跨工具共享权威源"
- chore(init.py): 「下一步」输出加第 4 条——多工具记忆桥接提示（指向 doc/00 §3.4）
  - 验证：✅ 实测——init.py 冒烟重跑通过（配置驱动建临时项目，12 文件复制、新提示行输出正常）；各文件改动 Read 确认落地；符号链接三坑与各工具结论均来自 2026-09-27 取证渗透中台项目实测或对应官方文档（claude code memory / opencode rules / agents.md）

## 2026-09-27 · WorkBuddy（脚手架优化会话）

- feat: **新增 init.py 配置化初始化器**（`scaffold.config.example.toml` + `init.py`，Python 3.11+ 标准库零依赖）——根治"新项目手改 43 处占位符"摩擦。行为：复制 template/（含隐藏目录）→ TOML 配置或交互问答驱动替换已知命名占位符（{{项目名}}/项目一句话/背景/技术栈/目录结构/运行方式）→ 残留 {{...}} 扫描报告（区分"待人工填写"与 .env.example 教学示例）→ 可选 git init（`-b main`）+ 首次提交
  - 验证：✅ 实测通过——配置驱动模式全流程（中文路径"测试项目 中台"，11 文件复制、8 处替换落地 Read 确认、git 提交 23c447d、工作区干净）；边界三项（默认分支=main、非空目录拒绝、缺必填项报错）均符合预期；临时目录已清理
- docs: **工具映射表增加证据等级标注**（✅实测 ＞ 📄官方文档 ＞ ❓未验证）——原表把"WorkBuddy 兼容 AGENTS.md"与".codebuddy/rules/ 注入"混为一谈。实测结论（2026-09-27 取证渗透中台会话）：`.codebuddy/rules/*.md` 注入与 `.workbuddy/memory/` 记忆注入为✅实测；根目录 AGENTS.md 兼容为📄官方文档+社区多源印证（官方 Project 页本轮访问 404，未做端到端实测）；ZCode/Trae 为❓未验证。涉及：README.md 兼容速查表、设计说明.md 支柱二、template/doc/00 §3.1
- docs: README「新项目启用五步」升级为「一条命令（init.py）+ 手动五步（备选）」
- chore: **仓库级 git 环境修复**——① 清除残留死代理 `http.proxy=http://127.0.0.1:7897`（旧 clash 端口）改为空值直连；② `credential.helper=""`（实测本会话环境 GCM/helper-selector 启动即挂死 git 全部网络操作，远端 URL 已内嵌凭据，helper 冗余且有害；同法修至取证渗透中台仓库）
- ⚠️ 遗留：GitHub 远端本次**未推送**——实测 github.com 经会话代理（44621）超时、经 35776 拒连，本机当前无法访问 GitHub；代理恢复后执行 `git push github main` 即可（本地 main=e5bb435，Gitea 已同步一致）
