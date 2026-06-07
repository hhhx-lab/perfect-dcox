---
mode: plan
change_id: add-quality-fix-loop
cwd: /Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范
task: 建立 DOCX/PDF 质检报告与 Agent 解释、修正计划、二次重排闭环
source_document: docs/word-format-agent-web-product-plan.md
created_at: 2026-06-07T22:34:57+08:00
qualification_status: passed
---

# Plan: 建立质检与 Agent 修正闭环

## 背景与动机

用户担心一键排版效果不好，这正是产品风险所在。产品方案已经把推荐形态定义为“一键排版 + 规则可确认 + 质检可解释 + Agent 逐项修正”，因此需要独立于排版引擎的质检系统和可控的 Agent 修正闭环，避免把“生成了文件”误报为“全部合规”。
<!-- 下游：proposal.md 的 motivation -->

## Goal

- 对规范化 DOCX/PDF 输出执行独立质检，生成结构化 JSON 和 Markdown 报告，明确 pass、fixed、warning、fail、unsupported。
- 对 warning/fail 项提供 Agent 解释、修正建议和可执行修正计划，用户确认后触发二次重排并更新报告。
<!-- 下游：proposal.md 的 scope -->

## Non-goals

- 不实现所有高级论文语义校对，例如全文参考文献真实性、论文内容质量、查重或语法润色。
- 不自动修改论文语义、公式内容或参考文献实质信息。
- 不把 unsupported 项伪装成 pass；无法判断的项目必须保留在报告中。
<!-- 下游：proposal.md 的 scope -->

## 当前仓库事实

- 产品方案规定自动质检要检查输出文档是否满足 profile，并将 Agent 修正作为流程最后一环：`docs/word-format-agent-web-product-plan.md:11`、`docs/word-format-agent-web-product-plan.md:13`。
- 产品方案工作流要求 DOCX 质检、PDF 质检共同进入合规报告，若存在失败项则由 Agent 解释与给出修正建议，用户确认后二次进入格式重排引擎：`docs/word-format-agent-web-product-plan.md:111`、`docs/word-format-agent-web-product-plan.md:121`。
- 产品方案要求质检独立于重排引擎，检查页面尺寸、边距、字体字号、标题、目录、页码、图题、表题、三线表、公式、参考文献、PDF 页数、文本可抽取和明显空白页：`docs/word-format-agent-web-product-plan.md:265`、`docs/word-format-agent-web-product-plan.md:283`。
- 产品方案定义检查结果分级为 `pass`、`fixed`、`warning`、`fail`、`unsupported`：`docs/word-format-agent-web-product-plan.md:285`、`docs/word-format-agent-web-product-plan.md:291`。
- 产品方案规定 Agent 修正闭环需要解释失败原因、判断是否可自动修、生成修正计划、调用格式重排引擎再次执行并更新报告：`docs/word-format-agent-web-product-plan.md:293`、`docs/word-format-agent-web-product-plan.md:301`。
- 产品方案列出交付质量指标包括 DOCX 可编辑性、PDF 页数正常、PDF 文本可抽取、无明显空白页、无 LaTeX 源码残留、图表和公式未异常跨页：`docs/word-format-agent-web-product-plan.md:890`、`docs/word-format-agent-web-product-plan.md:897`。
- 产品方案要求 MVP 验收中系统可以生成质检报告、Agent 可以解释质检失败项、常见正文/标题/页面/表格问题可自动修复，且报告必须列出未通过项：`docs/word-format-agent-web-product-plan.md:1085`、`docs/word-format-agent-web-product-plan.md:1098`。
- 现有 OpenSpec specs 基线：未验证；补证路径为初始化 OpenSpec 后读取 `openspec/specs/` 中与 quality report、agent fix loop、document output verification 相关的 `spec.md`。
<!-- 下游：specs baseline，proposal.md 的 context -->

## 改动边界

- 新增 DOCX/PDF 质检 worker 和 quality report 数据结构。
- 新增质检报告 API 和前端报告详情页，支持按 pass/fixed/warning/fail/unsupported 分组展示。
- 新增 Agent 解释与 Fix Planning Agent，针对可修复项生成结构化修正计划。
- 新增用户确认后触发二次重排的 API，二次任务必须保留原始报告和修正记录。
- 可能需要新增或修改 OpenSpec specs 领域：`quality-reporting`、`agent-fix-planning`、`format-job-retry`。
<!-- 下游：proposal.md scope，design.md scope，spec deltas 范围 -->

## 约束

- 质检引擎必须独立于重排引擎的成功状态，不得把排版任务 completed 自动视为质量通过。
- Agent 修正计划必须是结构化 JSON/YAML，并只能调用白名单格式化动作。
- 用户未确认前，不得对 warning/fail 项执行二次修正。
- 公式、参考文献和正文语义相关问题默认只标注和解释，不自动改实质内容。
- PDF 质检必须包含页数和文本可抽取性，不应只检查文件存在。
<!-- 下游：design.md 的 constraints -->

## 验收标准

1. 每次成功生成 DOCX/PDF 的排版任务都会产生 quality report，报告包含 summary、issue 列表、严重级别、对应 profile 规则、定位信息和建议动作。
2. 质检结果能区分 `pass`、`fixed`、`warning`、`fail`、`unsupported`，前端按分组展示并可筛选。
3. 对 DOCX 输出，系统至少检查页面边距、正文段落样式、标题样式、表格三线表基础规则、图表题注位置、公式原始 LaTeX 残留和页码存在性。
4. 对 PDF 输出，系统至少检查文件可打开、页数大于 0、文本可抽取、无明显空白页。
5. 对 warning/fail 项，Agent 能生成用户可读解释和结构化修正计划；不可自动修复项必须标注 `requires_manual_review`。
6. 用户在 Web 端确认可自动修复项后，系统创建二次修正任务，任务完成后生成新版 DOCX/PDF 和更新后的质检报告，并保留原报告引用。
7. 如果仍有未通过项，最终下载页不得显示“全部合规”，而应显示剩余 warning/fail/unsupported 摘要。
<!-- 下游：spec deltas 的 Scenarios，tasks.md 的 verification -->

## 验证方式

- 运行 quality 模块测试，覆盖 pass、warning、fail、unsupported 的报告生成。
- 使用人工构造的 DOCX 样例验证页面边距错误、正文行距错误、表格非三线表、缺页码、LaTeX 残留等问题能被报告捕获。
- 对生成 PDF 运行 `codex-pdf-inspect` 或等价检查，确认页数和文本可抽取性进入报告。
- 运行 Agent 修正计划 schema 测试，确认非法动作、缺少用户确认、修改语义字段时被拒绝。
- 手工在 Web 端执行一次“排版 -> 质检失败 -> Agent 解释 -> 用户确认 -> 二次修复 -> 新报告”的完整闭环。
<!-- 下游：tasks.md 的验证步骤 -->

## 迁移 / 回滚 / 降级

- 如新增 quality_reports、agent fix jobs 或 report artifacts，需要数据库迁移；回滚时保留输出文件但移除新表或回退到上一版本。
- 当质检 worker 失败时，排版输出可以保留，但任务整体应标记为 `completed_with_quality_error` 或等价状态，不能显示完全成功。
- 当 Agent 不可用时，报告仍应可查看，修正建议降级为规则引擎可判定的固定提示。
<!-- 下游：proposal.md 的 risks，spec deltas 的 REMOVED/MODIFIED -->

## 参考

- `docs/word-format-agent-web-product-plan.md:11`
- `docs/word-format-agent-web-product-plan.md:13`
- `docs/word-format-agent-web-product-plan.md:111`
- `docs/word-format-agent-web-product-plan.md:121`
- `docs/word-format-agent-web-product-plan.md:265`
- `docs/word-format-agent-web-product-plan.md:291`
- `docs/word-format-agent-web-product-plan.md:293`
- `docs/word-format-agent-web-product-plan.md:890`
- `docs/word-format-agent-web-product-plan.md:1085`
- `docs/word-format-agent-web-product-plan.md:1098`
- `plan/001-bootstrap-web-platform-2026-06-07_22-34-57.md`
- `plan/002-profile-management-2026-06-07_22-34-57.md`
- `plan/003-docx-formatting-engine-2026-06-07_22-34-57.md`
- `plan/004-agent-rule-extraction-2026-06-07_22-34-57.md`

