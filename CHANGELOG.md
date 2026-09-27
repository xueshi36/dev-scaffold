# CHANGELOG（每次改动一条，倒序追加）

格式：`## YYYY-MM-DD · <会话名>`，条目：`- <类型> 改动内容（原因 / 影响范围）`

## 2026-09-27 · WorkBuddy（脚手架优化会话）

- feat: **新增 init.py 配置化初始化器**（`scaffold.config.example.toml` + `init.py`，Python 3.11+ 标准库零依赖）——根治"新项目手改 43 处占位符"摩擦。行为：复制 template/（含隐藏目录）→ TOML 配置或交互问答驱动替换已知命名占位符（{{项目名}}/项目一句话/背景/技术栈/目录结构/运行方式）→ 残留 {{...}} 扫描报告（区分"待人工填写"与 .env.example 教学示例）→ 可选 git init（`-b main`）+ 首次提交
  - 验证：✅ 实测通过——配置驱动模式全流程（中文路径"测试项目 中台"，11 文件复制、8 处替换落地 Read 确认、git 提交 23c447d、工作区干净）；边界三项（默认分支=main、非空目录拒绝、缺必填项报错）均符合预期；临时目录已清理
- docs: **工具映射表增加证据等级标注**（✅实测 ＞ 📄官方文档 ＞ ❓未验证）——原表把"WorkBuddy 兼容 AGENTS.md"与".codebuddy/rules/ 注入"混为一谈。实测结论（2026-09-27 取证渗透中台会话）：`.codebuddy/rules/*.md` 注入与 `.workbuddy/memory/` 记忆注入为✅实测；根目录 AGENTS.md 兼容为📄官方文档+社区多源印证（官方 Project 页本轮访问 404，未做端到端实测）；ZCode/Trae 为❓未验证。涉及：README.md 兼容速查表、设计说明.md 支柱二、template/doc/00 §3.1
- docs: README「新项目启用五步」升级为「一条命令（init.py）+ 手动五步（备选）」
