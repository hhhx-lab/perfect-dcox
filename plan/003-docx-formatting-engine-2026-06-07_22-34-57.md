---
mode: plan
change_id: add-docx-formatting-engine
cwd: /Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范
task: 实现基于 profile 的 Word 解析、DOC/DOCX 转换、基础格式重排和 DOCX/PDF 输出
source_document: docs/word-format-agent-web-product-plan.md
created_at: 2026-06-07T22:34:57+08:00
qualification_status: passed
---

# Plan: 实现 DOCX 解析与基础重排引擎

## 背景与动机

产品要解决的核心问题是把用户上传的 Word 文件自动规范为目标论文排版格式。为保证稳定性，格式修改不能由 Agent 直接随意改文档，而应由确定性文档处理引擎读取 profile 后执行页面、字体、标题、段落、表格、题注、公式和参考文献等规则。
<!-- 下游：proposal.md 的 motivation -->

## Goal

- 建立文档解析与格式重排引擎，支持 `.doc` 自动转 `.docx`、`.docx` 结构解析、基于 profile 应用基础格式规则，并输出规范化 DOCX。
- 支持将规范化 DOCX 导出为 PDF，并把输出文件与排版任务关联。
<!-- 下游：proposal.md 的 scope -->

## Non-goals

- 不实现 Agent 自动判断复杂标题层级；低置信度结构识别留给后续 Agent change。
- 不实现完整参考文献内容校正、公式 OCR、复杂封面填充或跨引用自动重建。
- 不承诺任意混乱 Word 100% 完美重排；复杂问题由后续质检与 Agent 修正闭环处理。
<!-- 下游：proposal.md 的 scope -->

## 当前仓库事实

- 产品方案要求 Word 文档解析器读取输入 Word 并生成中间结构表示，解析段落文本、样式、字体、字号、缩进、行距、标题候选、表格、图片、题注、公式、脚注、页眉页脚、分节符、分页符和目录字段：`docs/word-format-agent-web-product-plan.md:208`、`docs/word-format-agent-web-product-plan.md:212`、`docs/word-format-agent-web-product-plan.md:223`。
- 产品方案要求 `.doc` 输入先转为 `.docx` 再处理：`docs/word-format-agent-web-product-plan.md:225`。
- 产品方案定义格式重排引擎为确定性执行层，职责包括应用页面设置、默认字体段落、标题样式、目录、页眉页脚、页码、正文、摘要、表格、图表题、公式、参考文献和清理多余空段：`docs/word-format-agent-web-product-plan.md:239`、`docs/word-format-agent-web-product-plan.md:245`、`docs/word-format-agent-web-product-plan.md:256`。
- 产品方案推荐使用 `python-docx`、直接 OpenXML、LibreOffice headless 和 Pandoc：`docs/word-format-agent-web-product-plan.md:258`、`docs/word-format-agent-web-product-plan.md:263`。
- 产品方案要求 MVP 支持 `.doc`、`.docx`，旧版 `.doc` 使用 LibreOffice headless 转 `.docx`，最终 PDF 使用 LibreOffice 自动导出：`docs/word-format-agent-web-product-plan.md:826`、`docs/word-format-agent-web-product-plan.md:837`、`docs/word-format-agent-web-product-plan.md:850`。
- 本地 ECNU 格式样本要求 A4 纵向、无网格、页边距上 2.5cm、下 2.0cm、左 3.0cm、右 2.5cm，段落首行缩进 2 字符，1.5 倍行距，英文 Times New Roman：`格式集/华东师范大学毕业论文格式要求.doc:9`、`格式集/华东师范大学毕业论文格式要求.doc:17`。
- 本地 ECNU 格式样本要求每页阿拉伯数字页码位于页面底端居中，表名在表格上方且中外文对照，图名在图下方且中外文对照，表格采用三线表，公式独立成行居中斜体：`格式集/华东师范大学毕业论文格式要求.doc:51`、`格式集/华东师范大学毕业论文格式要求.doc:52`。
- 现有 OpenSpec specs 基线：未验证；补证路径为初始化 OpenSpec 后读取 `openspec/specs/` 中与 document formatting、file conversion、output generation 相关的 `spec.md`。
<!-- 下游：specs baseline，proposal.md 的 context -->

## 改动边界

- 新增后端 document 模块，覆盖 `.doc` 转 `.docx`、`.docx` 解析、中间结构表示和 DOCX 输出。
- 新增基于 profile 的格式应用能力，覆盖页面、正文、标题、表格、题注、公式段落和参考文献基础段落规则。
- 新增 PDF 导出能力，将 DOCX 输出转换为 PDF 并登记输出文件。
- 新增任务状态更新和错误处理，使排版失败能反馈可诊断原因。
- 可能需要新增或修改 OpenSpec specs 领域：`document-input`、`docx-formatting`、`document-output`。
<!-- 下游：proposal.md scope，design.md scope，spec deltas 范围 -->

## 约束

- 文档处理必须优先使用项目独立 Python 环境和本机文档工具链，不能使用 sudo pip 或混用系统 Python。
- `.doc` 必须先转换为 `.docx` 后处理，不直接编辑二进制 `.doc`。
- 最终输出必须保留可编辑 DOCX，PDF 只是交付稿。
- 格式重排不得删除正文语义内容；对无法确定的结构只能保守处理或标记给质检。
- 复杂 Word 特性应优先通过 OpenXML 处理，避免只靠视觉或浏览器打印。
<!-- 下游：design.md 的 constraints -->

## 验收标准

1. 上传 `.doc` 文件时，后端能使用 LibreOffice headless 生成 `.docx` 中间文件，并记录转换状态；转换失败时任务失败并返回错误原因。
2. 上传 `.docx` 文件时，解析器能提取段落数量、表格数量、图片/绘图对象概览、标题候选和基础样式信息。
3. 使用 ECNU profile 对常规论文样例执行重排后，输出 DOCX 的页面边距、正文宋体/Times New Roman、小四或 profile 配置字号、1.5 倍行距、首行缩进和标题样式符合 profile。
4. 对输入中的普通表格，系统能按 profile 指定规则应用三线表基础边框样式。
5. 系统能为排版任务生成 DOCX 输出文件，并在请求生成 PDF 时生成对应 PDF 输出文件。
6. 排版任务状态能从 queued/running 转为 completed 或 failed，前端能显示输出文件或错误原因。
<!-- 下游：spec deltas 的 Scenarios，tasks.md 的 verification -->

## 验证方式

- 运行文档模块单元测试，覆盖 `.doc` 转换、`.docx` 解析、profile 应用、输出登记和失败分支。
- 使用 `格式集/华东师范大学毕业论文格式要求.doc` 或另一个小型 `.doc` 样例验证转换链路。
- 对生成 DOCX 运行 `codex-docx-inspect`，确认段落、表格、字符统计可读取。
- 对生成 PDF 运行 `codex-pdf-inspect`，确认页数正常、文本可抽取。
- 手工通过 Web 上传样例 Word，选择 ECNU profile，下载 DOCX/PDF 并检查任务状态和输出链接。
<!-- 下游：tasks.md 的验证步骤 -->

## 迁移 / 回滚 / 降级

- 低风险，主要新增文档处理模块；迁移 N/A。
- 如果 LibreOffice 不可用，应将转换或 PDF 任务标记为 failed，并提示 `SOFFICE_BIN` 配置问题。
- 若 OpenXML 写入失败，应保留原始上传文件和错误日志，不覆盖原文件。
<!-- 下游：proposal.md 的 risks，spec deltas 的 REMOVED/MODIFIED -->

## 参考

- `docs/word-format-agent-web-product-plan.md:208`
- `docs/word-format-agent-web-product-plan.md:225`
- `docs/word-format-agent-web-product-plan.md:239`
- `docs/word-format-agent-web-product-plan.md:258`
- `docs/word-format-agent-web-product-plan.md:826`
- `格式集/华东师范大学毕业论文格式要求.doc:9`
- `格式集/华东师范大学毕业论文格式要求.doc:17`
- `格式集/华东师范大学毕业论文格式要求.doc:51`
- `格式集/华东师范大学毕业论文格式要求.doc:52`
- `plan/001-bootstrap-web-platform-2026-06-07_22-34-57.md`
- `plan/002-profile-management-2026-06-07_22-34-57.md`
- `plan/004-agent-rule-extraction-2026-06-07_22-34-57.md`
- `plan/005-quality-agent-fix-loop-2026-06-07_22-34-57.md`

