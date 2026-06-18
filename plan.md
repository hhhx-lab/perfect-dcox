# Word/PDF 自定义格式导出生产化升级计划

版本：v2.0 规划稿
日期：2026-06-11
目标产品：Perfect DOCX / Word Format Agent

## 1. 一句话目标

把当前“Profile + 基础 formatter + 内部 QC 校验”的雏形，升级为“可视化规则配置 + Agent 严格抽取 + 标准 JSON Profile + 模板系统 + 确定性 FormatCompiler + 内部 QC 交付门闭环”的生产级 Word/PDF 格式导出系统。

最终用户应该可以：

1. 通过可视化页面配置格式规则，或与 Agent 对话，或上传格式要求文档。
2. 系统把所有格式要求沉淀为一份可版本化、可校验、可复用的标准 JSON Profile。
3. 用户选择 Profile，上传自己的 Word 文档。
4. 后端基于模板、Profile 和原文档生成规范化 DOCX/PDF。
5. 系统在后台执行内部 QC 校验，自动修正可修正项。
6. 只有格式规则、模板适配和文档正常性全部通过内部 QC 后，才开放最终 DOCX/PDF 下载；否则明确给出失败原因、无法支持项和人工复核项。

## 2. 当前架构基线

当前仓库已经具备可继续演进的基础，不需要推倒重来。

已有能力：

- 前后端分离：`frontend/` 使用 React + TypeScript + Vite，`backend/` 使用 FastAPI。
- Profile 模型：`backend/app/profiles/models.py` 中已有 `FormatProfile`，覆盖页面、字体、正文、标题、摘要、图表题注、公式、参考文献、页眉页脚和基础交付设置。
- Agent 规则入口：`backend/app/agents/requirements.py` 已要求 LLM 可用时才执行规则抽取，不配置 LLM 时会 fail closed。
- 文档格式化：`backend/app/documents/formatter.py` 已有 `format_docx_with_profile`，能应用页面设置、页眉页脚、正文/标题样式、题注、公式、参考文献和基础表格线。
- 文档服务：`backend/app/documents/service.py` 已有 `.doc` 转 `.docx`、DOCX 格式化、PDF 导出和文件登记流程。
- 内部 QC 校验：`backend/app/quality/inspection.py` 已覆盖 DOCX 页面、页边距、页眉页脚、正文/标题、表格、题注、字段刷新、TOC、分节复杂度、脚注尾注、图片题注、编号列表、PDF 可读性等检查。后续该能力只作为内部交付门，不产出用户可见诊断文件。
- 前端工作台：`frontend/src/App.tsx` 已包含需求入口、Profile、上传处理、输出下载和修复闭环，但当前是单文件式复杂状态管理，后续需要拆分。

当前主要短板：

- Profile schema 还偏基础，无法充分表达封面、目录、分节、编号、多级标题、模板页面、图表/公式/参考文献的复杂规则。
- Agent 输出尚未被约束为完整的 v2 Profile schema、证据链和能力边界声明。
- formatter 当前更像“在原文档上尽量套格式”，缺少编译器式分层架构。
- 缺少模板系统，固定封面页、声明页、目录页、页眉页脚组合难以稳定复用。
- 前端缺少真正的规则工作台体验：可视化配置、Agent 抽取结果对照、证据查看、Profile 差异对比、模板绑定、导出状态解释。
- 测试需要升级为真实样本文档矩阵，而不是只测单一路径。

## 3. 产品方案

### 3.1 用户画像

核心用户：

- 学生：需要把课程报告、毕业论文快速整理成学校要求格式。
- 教师/助教：需要批量检查和规范学生文档。
- 行政/科研人员：需要按固定机构模板导出报告。
- 内容服务人员：需要维护多套格式模板并批量生成交付文档。

### 3.2 产品定位

这是一个“格式规则编译与交付系统”，不是一个普通 Word 编辑器。

产品不追求替代 Word，而是解决：

- 格式规则难以理解。
- 不同模板要求不一致。
- 手工改格式容易漏。
- 大量文档重复排版耗时。
- 导出后无法确认是否真的合规。

### 3.3 核心工作流

#### 流程 A：可视化配置 Profile

用户直接在页面配置：

- 页面尺寸、方向、页边距、装订线。
- 正文中文字体、西文字体、字号、颜色、行距、缩进、对齐。
- 标题级别、编号规则、段前段后、分页策略。
- 摘要、关键词、目录、正文、参考文献、致谢、附录等章节规则。
- 页眉页脚、页码起始页、页码格式、奇偶页规则。
- 表格、图片、公式、题注、交叉引用规则。
- 固定封面页、声明页、目录页模板绑定。
- 输出格式 DOCX/PDF。

适用场景：用户已经知道格式要求，想快速创建或微调 Profile。

#### 流程 B：对话 Agent 创建 Profile

用户和 Agent 对话，例如：

> 正文宋体小四，英文 Times New Roman，1.5 倍行距，黑色，标题黑体三号居中，页边距上 3 下 2.5 左 3 右 2.5。

Agent 必须：

- 拆解每条规则。
- 对缺失字段发起追问。
- 把自然语言映射成标准 JSON Profile。
- 标注每条规则来源、置信度、是否需要确认。
- 明确说出当前引擎不支持的规则。

适用场景：用户没有结构化规则，只知道自然语言要求。

#### 流程 C：上传格式文件创建 Profile

用户上传格式要求 `.doc` / `.docx` / 后续可扩展 PDF。

Agent 必须：

- 提取格式要求文档文本。
- 识别页面、正文、标题、页眉页脚、题注、参考文献等规则。
- 输出 Profile 草案。
- 给出 evidence：每条规则引用原文片段。
- 给出 missing_fields：文档没有说清楚的规则。
- 给出 unsupported_rules：当前系统还无法自动执行的规则。

适用场景：学校、期刊、机构提供了正式格式要求文件。

#### 流程 D：模板绑定

用户可以上传或选择一个 DOCX 模板，用于：

- 固定封面。
- 原创性声明。
- 授权声明。
- 目录页。
- 页眉页脚结构。
- 特定章节骨架。
- 默认样式集。

Profile 只负责规则，Template 负责固定版面和结构。

#### 流程 E：上传待处理文档并导出

用户选择：

- 一个 Profile。
- 可选模板。
- 一份或多份待处理 Word 文档。
- 输出格式 DOCX/PDF。

系统执行：

```text
输入文档
  -> 文档结构分析
  -> 模板加载
  -> 内容映射
  -> Profile 编译
  -> 候选 DOCX 生成
  -> 内部 QC 校验
  -> 自动修正
  -> 最终交付判定
  -> 最终 DOCX/PDF 导出
  -> 下载交付物
```

### 3.4 “百分百合规”的产品口径

不能口头承诺所有 Word 复杂情况都百分百自动成功。正确口径是：

- Profile schema 能表达的规则，必须由 FormatCompiler 执行。
- 内部 QC 校验器能验证的规则，最终必须 100% pass。
- 如果规则超出 schema 或校验器能力，必须进入 `unsupported_rules` 或 `manual_review_required`。
- 只要存在 `fail`、`warning`、`unsupported`，前端不得开放“合规完成”下载态。
- 用户看到的“合规完成”只代表“已声明规则 + 可机器验证规则全部通过”。

内部 QC 不作为独立产品功能，不生成用户下载的诊断文件。它只负责阻断或放行最终导出：通过则发布最终 DOCX/PDF；失败则返回面向用户的简短失败原因和下一步动作。

这才是商业级可信承诺。

## 4. 目标架构

### 4.1 总体架构

```text
Frontend Workbench
  - Visual Profile Builder
  - Agent Chat Intake
  - Rule Document Upload
  - Template Manager
  - Batch Export Console
  - Export Result Panel

Backend API
  - Profile API
  - Requirement Session API
  - Template API
  - Export Job API
  - Export Result API
  - Batch API

Agent Layer
  - Rule Extraction Agent
  - Profile Review Agent
  - Missing Field Question Agent
  - Export Failure Explanation Agent

Core Engine
  - Profile Schema v2
  - Template Loader
  - Document Analyzer
  - Format Compiler
  - OOXML Patcher
  - Internal QC Gate
  - Auto Adjust Loop

Storage
  - Profiles
  - Templates
  - Uploads
  - Outputs
  - Manifests
```

### 4.2 关键原则

1. Agent 不直接改 Word。

   Agent 只负责理解、提问、抽取、解释，不允许自由修改 DOCX。

2. 标准 JSON Profile 是唯一格式规则源。

   视觉编辑器、Agent 对话、格式文件抽取，最终都必须写入同一套 schema。

3. FormatCompiler 是唯一导出入口。

   API、脚本、batch、测试都调用同一个编译器，不允许多套导出逻辑分叉。

4. 模板和规则分离。

   模板提供固定页面和结构，Profile 提供格式规则，输入文档提供内容。

5. 内部 QC 交付门必须 fail closed。

   不确定、不支持、验证失败，都不能显示为成功。

## 5. 标准 JSON Profile v2 设计

### 5.1 Profile 顶层结构

建议新增 `schema_version: "2.0.0"`，并把当前 `FormatProfile` 升级为更完整的结构。

```json
{
  "schema_version": "2.0.0",
  "id": "ecnu-thesis",
  "name": "华东师范大学毕业论文格式",
  "version": "1.0.0",
  "status": "active",
  "source": "user",
  "description": "",
  "locale": "zh-CN",
  "units": "cm",
  "page": {},
  "styles": {},
  "sections": [],
  "numbering": {},
  "header_footer": {},
  "tables": {},
  "figures": {},
  "equations": {},
  "references": {},
  "template_binding": {},
  "delivery_gate": {},
  "unsupported_rules": [],
  "evidence": []
}
```

### 5.2 必须覆盖的规则域

#### page

- 纸张：A4、Letter、自定义尺寸。
- 方向：portrait、landscape。
- 页边距：top、bottom、left、right、gutter。
- 分节策略：全局统一、指定章节分节。
- 页面垂直对齐。

#### styles

统一管理样式 token：

- `body`
- `title`
- `heading_1` 到 `heading_9`
- `abstract_title`
- `abstract_body`
- `keywords`
- `caption_table`
- `caption_figure`
- `equation`
- `reference_heading`
- `reference_item`
- `appendix_heading`
- `toc_title`
- `toc_item`

每个 style 支持：

- 中文字体。
- 西文字体。
- 字号 pt。
- 字色。
- 加粗/斜体。
- 行距。
- 段前段后。
- 首行缩进。
- 悬挂缩进。
- 对齐。
- 大纲级别。
- 是否分页前。
- 是否与下段同页。

#### sections

用于表达文档结构：

- 封面。
- 声明页。
- 中文摘要。
- 英文摘要。
- 目录。
- 正文。
- 参考文献。
- 致谢。
- 附录。

每个 section 支持：

- 识别规则。
- 是否必需。
- 顺序约束。
- 起始页策略。
- 是否新页。
- 绑定样式。
- 页码策略。
- 是否出现在目录。

#### numbering

支持：

- 多级标题编号：一、1、1.1、第一章、Chapter 1 等。
- 图表编号：图 1、图 1-1、表 1、表 1-1。
- 公式编号：右对齐 `(1)`、`(1-1)`。
- 参考文献编号：`[1]`。
- 附录编号：附录 A、附录 1。

#### header_footer

支持：

- 首页不同。
- 奇偶页不同。
- 按 section 配置。
- 页眉文本。
- 页眉横线。
- 页码位置。
- 页码格式。
- 页码起始页。
- 罗马数字/阿拉伯数字切换。

#### template_binding

支持：

- 绑定模板 ID。
- 固定页占位符。
- 内容插槽。
- 封面字段映射。
- 声明页保留策略。
- 样式继承策略。

#### delivery_gate

支持：

- 必检规则列表。
- 容忍误差。
- 是否允许人工复核项。
- 是否允许 unsupported。
- 最大自动修正轮次。
- 输出格式要求。

### 5.3 Evidence 设计

每条 Agent 抽取规则都要有证据：

```json
{
  "rule_path": "styles.body.font.size_pt",
  "source_type": "document",
  "quote": "正文采用宋体小四号字，行距为1.5倍",
  "confidence": 0.94,
  "requires_confirmation": false
}
```

没有 evidence 的规则不能自动进入 active Profile，只能作为默认值或待确认项。

## 6. Agent 方案

### 6.1 是否使用 LangChain

可以使用 LangChain，但它不是核心。核心是结构化输出、校验和可测试。

LangChain 适合用于：

- prompt 模板管理。
- structured output parser。
- 多步骤 rule extraction chain。
- retry/fallback。
- tracing。

不建议把 LangChain 做成不可控的多 Agent 自由协作。建议采用固定链路：

```text
Source Reader
  -> Rule Extraction Chain
  -> Schema Normalization Chain
  -> Evidence Alignment Chain
  -> Profile Validation
  -> Missing Field Question Generation
```

### 6.2 Agent 职责边界

Agent 可以做：

- 从自然语言或格式文档中抽取规则。
- 生成缺失字段追问。
- 解释 Profile 规则。
- 解释导出失败原因和无法支持的规则。
- 建议用户如何处理 unsupported 规则。

Agent 不可以做：

- 直接修改 DOCX。
- 跳过 schema 校验。
- 无证据生成硬规则。
- 在 LLM 不可用时假装完成分析。
- 把 unsupported 规则静默变成 pass。

### 6.3 规则抽取 Agent 输出

必须输出：

```json
{
  "profile_draft": {},
  "rules": [],
  "missing_fields": [],
  "unsupported_rules": [],
  "evidence": [],
  "questions": [],
  "confidence_summary": {}
}
```

后端必须执行：

1. JSON parse。
2. Pydantic schema validate。
3. rule path validate。
4. evidence coverage validate。
5. deterministic guard 覆盖明确规则。
6. unsupported rule separation。

### 6.4 多 Agent 拆分

建议先做固定链路，不急着做复杂多 Agent。

第一阶段：

- `RuleExtractionAgent`
- `ProfileValidationAgent`
- `QuestionGenerationAgent`

第二阶段：

- `TemplateMappingAgent`
- `ExportFailureExplanationAgent`

第三阶段：

- `RegressionDiagnosisAgent`

## 7. FormatCompiler 技术落地

### 7.1 设计目标

把当前 `format_docx_with_profile` 升级为模块化编译器：

```text
FormatCompiler.compile(input_docx, profile, template=None) -> CompileResult
```

CompileResult 包含：

- final_docx_path
- optional_pdf_path
- compile_audit
- applied_rules
- skipped_rules
- unsupported_rules
- internal_qc_result
- user_visible_failure_reason

### 7.2 后端模块结构

建议新增：

```text
backend/app/format_compiler/
  __init__.py
  compiler.py
  models.py
  profile_resolver.py
  template_loader.py
  document_analyzer.py
  content_mapper.py
  style_registry.py
  style_applier.py
  section_applier.py
  numbering_applier.py
  header_footer_applier.py
  caption_applier.py
  table_applier.py
  equation_applier.py
  reference_applier.py
  ooxml_patcher.py
  internal_qc.py
```

保留当前：

- `backend/app/documents/converter.py`
- `backend/app/documents/exporter.py`
- `backend/app/quality/inspection.py`，短期作为内部 QC 校验实现，后续可迁移或改名为 `internal_qc/`

逐步迁移当前 formatter 逻辑到 `format_compiler/`。

### 7.3 编译流程

```text
1. normalize_input
   - .doc 转 .docx
   - 校验文件可打开

2. analyze_document
   - 提取段落、表格、图片、公式、脚注尾注、页眉页脚、样式、分节
   - 给每个 block 标注 role

3. load_template
   - 无模板：使用空白基础模板
   - 有模板：读取固定页、占位符、样式定义、section 配置

4. resolve_profile
   - 合并 profile defaults
   - 合并模板默认值
   - 校验 schema
   - 输出 ResolvedProfile

5. map_content
   - 原文档内容映射到模板插槽
   - 保留正文、表格、图片、公式等内容

6. apply_styles
   - 正文、标题、题注、参考文献、摘要、目录等样式

7. apply_sections
   - 封面、声明页、摘要、目录、正文、参考文献、附录
   - 插入分页符和分节符

8. apply_numbering
   - 多级标题编号
   - 图表编号
   - 公式编号
   - 参考文献编号

9. apply_header_footer
   - 页眉页脚
   - 页码域
   - 首页/奇偶页规则

10. patch_ooxml
    - python-docx 不支持的 OOXML 设置
    - updateFields
    - TOC field
    - numbering.xml
    - styles.xml

11. save_candidate_docx

12. internal_qc

13. auto_adjust_if_needed

14. publish_final_docx

15. export_pdf_if_requested

16. final_delivery_gate
```

### 7.3.1 内部 QC 校验清单

内部 QC 是导出流水线的硬门槛，但不产出用户下载的诊断文件。它只返回机器可读的 `internal_qc_result` 和面向用户的简短失败原因。

内部 QC 必须检查：

1. 格式规则是否执行到位。

   - 页面尺寸、方向、页边距、装订线。
   - 正文/标题/题注/参考文献字体、字号、颜色、行距、缩进、对齐。
   - 标题层级、编号、目录域、页码域。
   - 表格线、图表题注、公式编号、参考文献悬挂缩进。

2. 模板适配是否正常。

   - 固定封面、声明页、目录页是否保留。
   - 正文内容是否插入到正确 slot。
   - 模板页眉页脚是否被正确继承或覆盖。
   - 模板样式和 Profile 规则冲突是否按优先级解决。
   - 插入正文后是否出现空白页、重复封面、内容错位、slot 残留。

3. 文档结构是否健康。

   - DOCX 能被 `python-docx` 和 LibreOffice 打开。
   - OOXML package 没有缺失 relationship、styles、numbering、header/footer parts。
   - 字段刷新策略已写入。
   - 分节、页码、目录、编号不会导致 Word 打开时报修复。

4. 输出是否可交付。

   - 最终 DOCX 存在且非空。
   - 若请求 PDF，PDF 能成功导出、页数大于 0、文本可抽取。
   - 输出文件名、MIME type、下载 URL 正确登记。

QC 结果处理：

- 全部通过：发布最终 DOCX/PDF 下载。
- 可自动修正：进入 `auto_adjust`，重跑内部 QC。
- 不可自动修正：阻断最终下载，前端展示简短失败原因和建议动作。
- unsupported：阻断“合规完成”状态，除非用户明确选择“带人工复核风险下载”。

### 7.4 python-docx 与 OOXML 分工

使用 `python-docx`：

- 打开、保存 DOCX。
- 段落、run、字体、字号、颜色。
- 表格基础样式。
- 页边距、页面尺寸。
- 基础页眉页脚。

直接修改 OOXML：

- 多级编号。
- TOC 域。
- PAGE 域精细控制。
- updateFields。
- 样式 East Asia 字体。
- 页眉横线。
- 分节复杂设置。
- 部分表格边框。
- 文档兼容设置。

不建议使用前端 JS 作为核心导出：

- JS 适合做配置、预览、轻量导出。
- 复杂 DOCX/PDF 生产更适合后端 Python + OOXML。
- 前端导出会让模板、字体、PDF、分节、域刷新和内部 QC 校验更难统一。

### 7.5 CLI 脚本

新增：

```text
scripts/build_final_docx.py
```

用途：

```bash
cd backend
uv run python ../scripts/build_final_docx.py \
  --input path/to/input.docx \
  --profile path/to/profile.json \
  --template path/to/template.docx \
  --output path/to/final.docx \
  --pdf
```

注意：

- CLI 只作为入口。
- 不能在脚本里重写业务逻辑。
- 必须调用 `backend/app/format_compiler/compiler.py`。

## 8. 模板系统

### 8.1 TemplateRecord

新增模板实体：

```json
{
  "template_id": "ecnu-thesis-template",
  "name": "华东师范大学毕业论文模板",
  "version": "1.0.0",
  "status": "active",
  "file_id": "file_xxx",
  "slots": [],
  "variables": [],
  "created_at": "",
  "updated_at": ""
}
```

### 8.2 模板插槽

模板中使用约定占位符：

- `{{cover.title}}`
- `{{cover.author}}`
- `{{cover.student_id}}`
- `{{cover.school}}`
- `{{content.abstract_zh}}`
- `{{content.abstract_en}}`
- `{{content.toc}}`
- `{{content.body}}`
- `{{content.references}}`
- `{{content.appendix}}`

初期可以只支持：

- 固定封面页整体保留。
- 正文插入到指定位置。
- 页眉页脚继承模板。

后续再做字段级封面填充。

### 8.3 模板 API

新增：

- `POST /api/templates`：上传模板。
- `GET /api/templates`：模板列表。
- `GET /api/templates/{template_id}`：模板详情。
- `POST /api/templates/{template_id}/versions`：新增模板版本。
- `POST /api/templates/{template_id}/archive`：归档模板。
- `POST /api/templates/{template_id}/inspect`：检查模板插槽、样式和固定页。

## 9. 前端升级方案

### 9.1 信息架构

前端从单页堆叠改成工作台结构：

```text
Sidebar
  - 总览
  - 创建 Profile
  - Profile 库
  - 模板库
  - 文档处理
  - 批量任务
  - 设置
```

### 9.2 创建 Profile 页面

提供三种入口：

1. 可视化配置
2. 对话 Agent
3. 上传格式文件

三种入口都进入同一个 Profile Draft 页面。

### 9.3 Profile Draft 页面

必须展示：

- 规则摘要。
- 缺失字段。
- 待确认字段。
- Agent evidence。
- unsupported rules。
- JSON 预览。
- 保存 Profile。

### 9.4 可视化规则编辑器

按规则域分 Tab：

- 页面
- 正文
- 标题
- 编号
- 摘要/关键词
- 图表/公式
- 参考文献
- 页眉页脚
- 模板
- 交付门

每个字段应该有：

- 当前值。
- 来源：用户配置 / Agent / 模板默认 / 系统默认。
- 是否必需。
- 是否已验证。

### 9.5 文档处理页面

用户选择：

- Profile。
- Template。
- 输出格式。
- 单文件或批量文件。

页面展示：

- 处理进度。
- 每份文件状态。
- DOCX 下载。
- PDF 下载。
- 导出失败原因。
- 自动修正记录。

### 9.6 前端技术拆分

当前 `frontend/src/App.tsx` 状态过多。建议拆成：

```text
frontend/src/
  app/
    AppShell.tsx
    routes.tsx
  api/
    client.ts
    profiles.ts
    templates.ts
    jobs.ts
    validation.ts
  components/
    Layout/
    Upload/
    ExportStatus/
    ProfileEditor/
    AgentChat/
  pages/
    DashboardPage.tsx
    ProfileCreatePage.tsx
    ProfileLibraryPage.tsx
    TemplateLibraryPage.tsx
    DocumentExportPage.tsx
    BatchJobsPage.tsx
    ExportResultPage.tsx
  types/
    profile.ts
    template.ts
    validation.ts
```

视觉原则：

- 不做营销式大 hero。
- 使用工作台风格：左侧导航、顶部状态、主区域表单与结果。
- 规则配置用 tabs、表格、分组面板、开关、下拉、数字输入和颜色选择器。
- 导出结果用清晰状态：可下载、已自动修正、需要补充规则、无法自动处理。

## 10. 后端 API 升级

### 10.1 Profile API

保留已有 API，新增：

- `POST /api/profiles/validate`：校验 Profile JSON。
- `POST /api/profiles/{profile_id}/versions/{version}/diff`：比较两个版本。
- `GET /api/profiles/{profile_id}/versions/{version}/schema`：返回 schema。
- `POST /api/profiles/{profile_id}/versions/{version}/upgrade`：v1 到 v2 迁移。

### 10.2 Requirement Session API

升级现有：

- 输出 v2 Profile Draft。
- 输出 evidence coverage。
- 输出 unsupported rules。
- 输出 questions。
- 支持用户逐项确认。

### 10.3 Export Job API

扩展 `POST /api/jobs`：

```json
{
  "input_file_id": "file_xxx",
  "profile_id": "ecnu-thesis",
  "profile_version": "1.0.0",
  "template_id": "ecnu-template",
  "template_version": "1.0.0",
  "output_formats": ["docx", "pdf"],
  "delivery_gate": true,
  "auto_adjust": true
}
```

### 10.4 Export Result API

新增：

- `GET /api/jobs/{job_id}/result`

返回：

- applied_rules
- skipped_rules
- unsupported_rules
- template_slots_used
- internal_qc_status
- format_rule_status
- template_fit_status
- docx_integrity_status
- pdf_export_status
- user_visible_failure_reason
- final_output_ids

## 11. 存储与生产化

### 11.1 当前本地存储

当前可以继续使用：

- `storage/files`
- `storage/outputs`
- `storage/manifests`
- `storage/metadata.json`

### 11.2 生产化目标

后续引入：

- PostgreSQL：Profile、Template、Job、Export Result、Audit Log。
- Redis：队列、进度、锁。
- 对象存储：上传文件、模板、输出文件。

### 11.3 表设计方向

核心表：

- `profiles`
- `profile_versions`
- `templates`
- `template_versions`
- `files`
- `export_jobs`
- `batch_runs`
- `export_results`
- `agent_sessions`
- `audit_logs`

## 12. 测试与验收

### 12.1 测试样本库

建立：

```text
tests/fixtures/documents/
  simple_report.docx
  thesis_with_cover.docx
  thesis_with_toc.docx
  thesis_with_tables.docx
  thesis_with_figures.docx
  thesis_with_equations.docx
  thesis_with_references.docx
  complex_mixed.docx

tests/fixtures/profiles/
  ecnu_thesis_v2.json
  course_report_v2.json
  journal_template_v2.json

tests/fixtures/templates/
  ecnu_template.docx
  course_report_template.docx
```

### 12.2 自动化测试

必须覆盖：

- Profile schema validation。
- v1 Profile -> v2 Profile migration。
- Agent structured JSON parse。
- evidence coverage。
- unsupported rules separation。
- FormatCompiler 单模块测试。
- end-to-end DOCX export。
- DOCX internal QC pass/fail。
- template fit pass/fail。
- PDF export and inspect。
- batch export。
- auto adjust loop。

### 12.3 验收标准

MVP 升级完成标准：

1. 用户可通过可视化配置创建 v2 Profile。
2. 用户可通过对话 Agent 创建 v2 Profile。
3. 用户可上传格式要求文档创建 v2 Profile，并看到 evidence。
4. 用户可上传模板 DOCX 并绑定 Profile。
5. 用户可选择 Profile + Template 发起导出任务。
6. 候选 DOCX 必须通过内部 QC，确认格式规则、模板适配和文档正常性均符合要求后才发布最终 DOCX 下载。
7. 若配置 `SOFFICE_BIN`，最终 DOCX 通过内部 QC 后才导出 PDF，并通过基础 PDF 检查后发布 PDF 下载。
8. 不支持规则必须显示为 unsupported，不得静默通过。
9. 复杂样本文档至少覆盖 8 类 fixture。
10. 前端工作流不再依赖用户理解内部 fix-loop 术语，而是用“可下载 / 自动修正中 / 需要补充规则 / 无法自动处理”表达。

## 13. 分阶段实施计划

### Phase 1：Profile v2 与规则抽取稳定化

目标：先把规则表达做准。

任务：

- 新增 `FormatProfileV2` Pydantic 模型。
- 生成 `schemas/format_profile.v2.schema.json`。
- 实现 v1 -> v2 迁移。
- 改造 requirement session 输出 v2 draft。
- Agent 输出增加 evidence、unsupported_rules、questions。
- 添加 Profile validate API。
- 前端增加 JSON 预览和规则确认页面。

验收：

- 三套测试 Profile 可通过 schema 校验。
- 上传格式文件时，无 LLM 配置必须明确报错。
- Agent 输出非法 JSON 必须失败。
- 每条非默认规则必须有 evidence 或用户确认。

### Phase 2：FormatCompiler 骨架

目标：把 formatter 从单函数升级为编译器架构。

任务：

- 新增 `backend/app/format_compiler/`。
- 实现 `CompileRequest`、`CompileResult`。
- 封装当前 `format_docx_with_profile` 为 compiler adapter。
- 拆分 style、section、header_footer、table、caption applier。
- 新增 `scripts/build_final_docx.py`。
- 将 jobs service 改为调用 compiler。

验收：

- 旧 Profile 路径仍可导出。
- CLI 可以独立生成 DOCX。
- 后端 API 和 CLI 调用同一套 compiler。

### Phase 3：模板系统

目标：支持固定封面页、声明页和模板样式。

任务：

- 新增 TemplateRecord。
- 新增模板上传、列表、详情 API。
- 实现 TemplateLoader。
- 支持模板固定页保留。
- 支持正文插入 slot。
- 支持 Profile 绑定 template。
- 前端增加模板库页面。

验收：

- 上传模板后可以绑定 Profile。
- 导出文档保留模板封面。
- 正文内容插入模板指定区域。

### Phase 4：复杂格式规则执行

目标：提升论文级稳定性。

任务：

- 多级标题编号。
- TOC 域生成和刷新策略。
- 图表题注编号。
- 公式编号。
- 参考文献悬挂缩进和编号。
- 分节和页码起始策略。
- 页眉横线和奇偶页支持。

验收：

- thesis_with_toc、thesis_with_tables、thesis_with_figures、thesis_with_equations fixtures 通过交付门。

### Phase 5：前端工作台重构

目标：把前端从功能堆叠变成清晰工作台。

任务：

- 拆分 `App.tsx`。
- 新增 sidebar layout。
- 新增 Profile 创建三入口。
- 新增 Profile 编辑器 tabs。
- 新增 Template 管理。
- 新增 Export Console。
- 新增 Export Result 页面。
- 优化下载区域，直接展示 DOCX/PDF、失败原因和下一步动作。

验收：

- 用户不看 README 也能完成从创建 Profile 到下载 DOCX/PDF。
- 页面不出现“修复什么”这类内部术语困惑，改为面向用户的导出状态。

### Phase 6：生产化队列与存储

目标：让系统可长期运行和批量处理。

任务：

- 接入 PostgreSQL。
- 接入 Redis 队列。
- Job 状态持久化。
- 文件对象存储抽象。
- 审计日志。
- 并发限制。
- 失败重试。

验收：

- 批量 10 份文档可稳定处理。
- 任务失败可恢复、可追踪、可重试。

## 14. 风险与对策

### 风险 1：Word OOXML 复杂度高

对策：

- python-docx 负责常规操作。
- OOXML patcher 负责复杂字段。
- 每个复杂规则都做 fixture。
- 不支持项明确进入 unsupported。

### 风险 2：Agent 抽取不稳定

对策：

- temperature 固定为 0。
- 使用 structured output。
- schema validate。
- evidence 必填。
- deterministic guard 覆盖明确硬规则。
- LLM 失败直接报错，不生成假 Profile。

### 风险 3：用户误以为任何格式都能百分百

对策：

- UI 明确区分“已机器验证通过”和“需要人工复核”。
- unsupported 不允许被隐藏。
- 下载页只展示最终导出状态、可下载文件和必要失败原因，不提供额外诊断文件下载入口。

### 风险 4：前端配置过于复杂

对策：

- 使用常用规则优先。
- 高级规则折叠。
- Agent 帮用户解释规则。
- JSON 预览给高级用户。

### 风险 5：模板和 Profile 冲突

对策：

- 明确优先级：用户显式 Profile > 模板绑定规则 > 系统默认。
- 冲突时进入 confirmation。
- compile result audit 记录最终采用值。

## 15. 关键技术决策

1. 核心导出放后端 Python，不放前端 JS。
2. Agent 只输出规则 JSON，不直接改 DOCX。
3. Profile schema 是唯一规则源。
4. 模板 DOCX 只负责固定结构和版面。
5. FormatCompiler 是唯一导出入口。
6. 内部 QC 交付门决定是否允许“合规完成”和最终下载。
7. 不支持规则必须可见。

## 16. 首批开发任务建议

优先做这 10 件事：

1. 新建 `schemas/format_profile.v2.schema.json`。
2. 新建 `backend/app/profiles/v2_models.py`。
3. 新建 v1 -> v2 migration。
4. 改造 Agent prompt 和 parser，让其输出 v2 draft + evidence。
5. 新建 `backend/app/format_compiler/compiler.py`。
6. 把当前 formatter 包装成 compiler 第一版。
7. 新建 `scripts/build_final_docx.py`。
8. 新建 TemplateRecord 和模板 API。
9. 前端新增 Profile Draft 确认页。
10. 增加 3 个真实 DOCX fixture 的端到端测试。

## 17. 里程碑

### M1：规则稳定

可通过三种入口生成可验证 Profile v2。

### M2：导出稳定

同一个 Profile 用 API 和 CLI 都能生成一致 DOCX，并通过内部 QC 后才发布下载。

### M3：模板可用

固定封面 + 正文插入 + 样式编译跑通。

### M4：交付闭环

导出后自动检查、自动修正，内部 QC 全通过后发布最终 DOCX/PDF；失败时只展示简短原因和下一步动作，不生成用户可见诊断文件。

### M5：体验可用

普通用户不懂技术也能完成“格式规则 -> Profile -> 上传文档 -> 下载结果”。

## 18. 最终判断

这套升级不是小修小补，而是一次中大型架构升级。但它不需要推翻当前项目。

最重要的转变是：

```text
从：Agent/formatter 尽量帮用户套格式
到：Agent 抽取规则，Profile 表达规则，FormatCompiler 编译规则，内部交付门验证规则
```

只要这个方向落地，系统才有机会支持不同学校、不同期刊、不同机构模板，而不是只针对某一种格式做硬编码。
