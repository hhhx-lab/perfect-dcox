---
mode: plan
change_id: add-agent-rule-extraction
cwd: /Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范
task: 引入 Agent 将格式要求文档或自然语言拆解为可确认、可版本化的 profile 草案
source_document: docs/word-format-agent-web-product-plan.md
created_at: 2026-06-07T22:34:57+08:00
qualification_status: passed
---

# Plan: 实现 Agent 规则抽取与 Profile 草案确认

## 背景与动机

用户希望上传格式要求文档或输入自然语言描述后，Agent 自动细拆 Word 格式规则，并进入 profile 管理和排版流程。为了降低幻觉风险，Agent 只能生成结构化 profile 草案、不确定项和来源证据，用户确认后才保存为可执行 profile。
<!-- 下游：proposal.md 的 motivation -->

## Goal

- 支持用户通过格式要求 `.doc/.docx` 或自然语言描述创建 profile 抽取任务。
- Agent 将输入拆解为符合 schema 的 profile draft、uncertain_items 和 evidence，并在 Web 端展示给用户确认、修改和保存。
<!-- 下游：proposal.md 的 scope -->

## Non-goals

- 不让 Agent 直接修改最终 DOCX 或绕过 profile schema。
- 不实现结构识别 Agent 对待排版论文正文的深度标注；本 change 只处理格式规则抽取。
- 不保证任意格式要求文档都能一次性无误抽取；不确定项必须显式暴露给用户确认。
<!-- 下游：proposal.md 的 scope -->

## 当前仓库事实

- 产品方案明确规则抽取 Agent 输入包括格式要求文档正文、示例模板 Word 结构和用户自然语言描述，输出包括结构化 profile 草案、不确定规则列表和需要用户确认的问题：`docs/word-format-agent-web-product-plan.md:163`、`docs/word-format-agent-web-product-plan.md:167`、`docs/word-format-agent-web-product-plan.md:175`。
- 产品方案列出 Agent 拆解维度包括页面设置、正文字体与段落、标题层级、摘要与关键词、目录、页眉页脚与页码、图题/表题/公式、表格样式、参考文献、注释、封面和附录：`docs/word-format-agent-web-product-plan.md:177`、`docs/word-format-agent-web-product-plan.md:190`。
- 产品方案要求 Agent 输出必须是结构化 JSON/YAML，不允许只输出自然语言：`docs/word-format-agent-web-product-plan.md:783`、`docs/word-format-agent-web-product-plan.md:785`。
- 产品方案规定 Agent 不允许直接写入最终 DOCX、删除正文内容、修改论文语义、擅自改参考文献或公式内容、未确认时重写低置信度标题层级：`docs/word-format-agent-web-product-plan.md:804`、`docs/word-format-agent-web-product-plan.md:813`。
- 产品方案要求 Agent 幻觉风险通过来源证据、规则确认页、profile 版本、schema 校验和独立质检应对：`docs/word-format-agent-web-product-plan.md:920`、`docs/word-format-agent-web-product-plan.md:934`。
- 产品方案 API 草案包含创建 profile 抽取任务和获取 profile 抽取结果，结果包含 `profile_draft` 和 `uncertain_items`：`docs/word-format-agent-web-product-plan.md:552`、`docs/word-format-agent-web-product-plan.md:577`、`docs/word-format-agent-web-product-plan.md:589`。
- 本地 ECNU 格式样本包含可抽取规则，例如 A4、页边距、首行缩进、1.5 倍行距、Times New Roman、摘要字数和正文/标题字体字号：`格式集/华东师范大学毕业论文格式要求.doc:9`、`格式集/华东师范大学毕业论文格式要求.doc:35`。
- 现有 OpenSpec specs 基线：未验证；补证路径为初始化 OpenSpec 后读取 `openspec/specs/` 中与 agent rule extraction、profile draft、LLM safety 相关的 `spec.md`。
<!-- 下游：specs baseline，proposal.md 的 context -->

## 改动边界

- 新增 profile extraction API 和异步任务类型。
- 新增 Agent Worker 中的 Rule Extraction Agent。
- 新增格式要求文档正文提取流程，至少支持 `.doc/.docx` 作为规则来源。
- 新增前端规则抽取页面，展示 profile draft、uncertain_items、来源证据和保存入口。
- 新增 Agent 输出 schema 校验与失败处理。
- 可能需要新增或修改 OpenSpec specs 领域：`agent-rule-extraction`、`profile-draft-confirmation`、`llm-output-safety`。
<!-- 下游：proposal.md scope，design.md scope，spec deltas 范围 -->

## 约束

- Agent 产物必须通过 profile schema 校验后才能进入保存流程。
- Agent 必须输出来源证据或未能定位证据的标记，不得把无来源推断写成确定事实。
- 用户确认前，profile draft 不能作为 active profile 使用。
- LLM API Key 和模型名必须从 `.env` 读取，不能硬编码。
- 抽取失败或低置信度项必须展示给用户，不得静默使用默认值。
<!-- 下游：design.md 的 constraints -->

## 验收标准

1. 用户上传格式要求 `.doc/.docx` 后，系统能提取正文并创建 profile extraction job。
2. 用户输入自然语言规则后，系统能创建 profile extraction job，且不要求上传文件。
3. Agent job 完成后返回 `profile_draft`、`uncertain_items` 和 evidence 列表；每个 uncertain item 至少包含字段路径、说明和建议处理方式。
4. 使用 `格式集/华东师范大学毕业论文格式要求.doc` 作为输入时，profile draft 至少抽取出 A4、页边距、正文缩进、1.5 倍行距、Times New Roman、摘要字数、正文宋体小四、标题黑体小四、页码位置、三线表、图表题注位置和公式排版规则。
5. Web 端能展示 Agent 拆解结果，并允许用户修改后保存为 draft 或 active profile。
6. Agent 输出非法 JSON/YAML、schema 不合法或缺少必要字段时，任务状态为 failed 或 needs_review，并展示可读错误。
<!-- 下游：spec deltas 的 Scenarios，tasks.md 的 verification -->

## 验证方式

- 运行 Agent 输出 schema 测试，覆盖合法输出、非法 JSON、缺少 evidence、未知字段和非法枚举。
- 使用 ECNU 格式要求样本执行一次 profile extraction，检查抽取字段和 uncertain_items。
- 手工在 Web 端上传格式要求文档，确认用户可以查看、修改并保存 profile draft。
- 检查 `.env.example` 中 LLM 相关配置说明完整，代码中没有硬编码 API Key。
<!-- 下游：tasks.md 的验证步骤 -->

## 迁移 / 回滚 / 降级

- 低风险，主要新增 Agent 任务和 profile draft 流程；数据库如新增 extraction jobs 或 agent_messages，需要迁移和回滚脚本。
- 当 LLM 不可用时，规则抽取任务应失败并提示配置或服务问题；已有手动 profile 管理能力仍可使用。
- 当 Agent 输出低置信度时，降级为用户手动确认，不自动保存 active profile。
<!-- 下游：proposal.md 的 risks，spec deltas 的 REMOVED/MODIFIED -->

## 参考

- `docs/word-format-agent-web-product-plan.md:163`
- `docs/word-format-agent-web-product-plan.md:177`
- `docs/word-format-agent-web-product-plan.md:552`
- `docs/word-format-agent-web-product-plan.md:577`
- `docs/word-format-agent-web-product-plan.md:783`
- `docs/word-format-agent-web-product-plan.md:804`
- `docs/word-format-agent-web-product-plan.md:920`
- `格式集/华东师范大学毕业论文格式要求.doc:9`
- `格式集/华东师范大学毕业论文格式要求.doc:35`
- `plan/001-bootstrap-web-platform-2026-06-07_22-34-57.md`
- `plan/002-profile-management-2026-06-07_22-34-57.md`
- `plan/003-docx-formatting-engine-2026-06-07_22-34-57.md`
- `plan/005-quality-agent-fix-loop-2026-06-07_22-34-57.md`

