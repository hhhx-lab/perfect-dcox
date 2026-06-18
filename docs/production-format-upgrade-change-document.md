# 自定义 Word/PDF 格式导出生产化改动文档

版本：v1.20
日期：2026-06-12
最后验证：2026-06-12 18:15:03 +0800
适用项目：Perfect DOCX / Word Format Agent
对应 Change Plan：`docs/change-plans/CP-20260611-001.md`
对应 OpenSpec Change：`openspec/changes/update-production-export/`
当前状态：生产化升级进行中，已完成核心骨架与部分闭环；本文档已按当前仓库事实整理完成，但项目尚未达到“任意复杂论文百分百稳定”。

## 0. 文档用途与真实性边界

本文是当前生产化升级的完整改动记录，供后续研发、验收、提交和继续排期使用。它只记录已经在仓库中落盘、已被测试或代码事实支撑的内容；没有真实样本矩阵证明的能力，不写成“已百分百完成”。

阅读口径：

- “已完成”表示对应代码、测试或文档已在仓库中存在，并经过本轮基础验证。
- “当前限制”表示已有实现但未覆盖商业级复杂场景，后续仍要补强。
- “生产化缺口”表示距离用户要求的“一键全自动、复杂论文高稳定、全部规则内部 QC 后再下载”仍缺的内容。
- 内部 QC 只作为放行门，不作为用户可下载质量报告产品。
- LLM 是 Agent 规则抽取和最终版面校验的必要依赖；不可用时必须失败并报错，不能生成假规则。

## 1. 一句话结论

本轮改动已经把项目从“基础 Word 格式化原型”推进到“Profile JSON 驱动、Agent 参与、候选文件内部 QC 后再下载”的生产化链路雏形。

但必须明确：当前版本还不能诚实承诺“任意学校/期刊模板、任意复杂论文都百分百成功”。已经落地的是架构边界、核心数据契约、基础格式执行、内部交付门、LLM fail-closed、样本文档样式提取和前端能力入口；仍需继续补齐字段级 applier/verifier 注册表、逐字段全文 QC、统一工作台重构、复杂模板适配和真实样本矩阵。

## 2. 用户真实目标

用户要的不是“生成质量报告”，也不是“看起来差不多的格式化文件”，而是：

```text
输入自定义格式要求
  -> Agent / 上传格式规则文档 / 上传格式样本文档 / 可视化编辑
  -> 共同沉淀为标准 Profile JSON
  -> 选择 Profile 并上传待处理 Word
  -> 系统逐条执行 Profile 规则
  -> 内部 QC 逐条校验
  -> 不通过则自动安全修复并重新校验
  -> 最终 LLM 检查乱码、错位、空白页、图表出界等版面问题
  -> 全部通过后才允许下载 DOCX / PDF
```

核心原则：

- Agent 必须参与格式规则理解；LLM 不可用时必须报错，不能用默认规则伪装分析成功。
- Profile JSON 是唯一格式事实来源。
- Formatter 必须按 Profile JSON 执行，不能隐式跳过规则。
- QC 是内部交付门，不做用户可下载的质量报告产品。
- 不支持的规则必须明确进入 unsupported / partial / template_delegated 状态，并按策略阻断或降级。
- 最终给用户下载的只能是通过内部交付门的 DOCX/PDF。

## 3. 目标产品流程

### 3.1 Profile 创建入口

最终前端应是一个统一工作台，而不是割裂流程：

```text
左侧：Agent 对话与附件区
  - 用户自然语言输入
  - 上传格式规则文档
  - 上传格式样本文档
  - Agent 追问、总结、指出缺失项

右侧：Profile JSON 可视化规则树
  - 页面、分节、文档网格
  - 正文中英文字体、字号、字色、段落
  - 1-9 级标题样式与编号
  - 目录、页眉、页脚、页码
  - 摘要、关键词、公式、参考文献
  - 表格、图件、题注、中外文对照
  - 单位、计价单位、数字归一
  - 模板绑定、内部交付门、最终 LLM review
```

三种输入必须合流到同一份 Profile JSON：

- 直接对话：Agent 追问并总结格式需求。
- 上传格式规则文档：Agent 阅读学校、期刊、机构格式要求并拆解成结构化规则。
- 上传格式样本文档：系统读取真实 Word 样式，Agent 结合样式证据补全规则。

用户在可视化页面手动调整后的字段必须写入 `locked_fields`。后续 Agent 只能补全信息，不得覆盖锁定字段。

### 3.2 导出入口

导出流程应固定为：

```text
选择 Profile
  -> 可选绑定模板 DOCX
  -> 上传一个或多个待处理 Word
  -> FormatCompiler 生成 candidate.docx
  -> 内部 DOCX QC
  -> 可修复项自动重做
  -> PDF 导出与 PDF QC
  -> 最终 LLM 版面校验
  -> 发布 final.docx / final.pdf 下载
```

前端只展示：

- Profile 创建/选择状态。
- 导出进度。
- 内部校验中、自动调整中、PDF 导出中、最终版面检查中。
- 简短失败原因。
- 最终 DOCX/PDF 下载。

前端不展示：

- 可下载质量报告。
- 需要用户理解的 fix plan。
- 手动修复循环作为主流程。

## 4. 架构边界

目标架构分层如下：

```text
Agent 层
  -> 只负责理解、提问、拆解、归纳格式规则

Profile 层
  -> 保存完整格式契约、证据、缺失项、不支持项、锁定字段

Rule Registry 层
  -> 声明每个 Profile 字段是否可执行、可校验、如何阻断

FormatCompiler 层
  -> 按 Profile 和模板确定性生成候选 DOCX

Internal QC 层
  -> 按 Profile 逐条验证候选 DOCX/PDF

Final Layout Review 层
  -> LLM 检查最终版面健康，不替代确定性 QC

Frontend Workbench 层
  -> 提供对话、附件、可视化编辑、导出和下载
```

关键分工：

- Agent 不能直接自由修改 Word。
- Formatter 不能自由解释自然语言。
- QC 不能只检查“首个段落”或“代表样本”，生产目标必须按全文、逐对象、逐字段检查。
- LLM final review 只负责发现乱码、错位、空白页、图表出界等版面健康问题。

### 4.1 端到端数据流

当前目标链路按以下数据契约推进：

```text
用户输入
  -> natural_language / rule_document / style_sample_docx / visual_editor
  -> RequirementSession
  -> LLM Agent 生成或更新 Profile draft
  -> Profile v2 保存 evidence / missing_fields / unsupported_rules / locked_fields
  -> Rule Registry 生成 capability_coverage
  -> 用户选择命名 Profile
  -> 上传待处理 DOC/DOCX 与可选模板 DOCX
  -> FormatCompiler 生成 candidate.docx
  -> InternalDeliveryGateService 验证 DOCX
  -> 可安全修复时生成 candidate-gate-fixed.docx 并重新验证
  -> DOCX 转 PDF
  -> PDF QC
  -> LLM final layout review
  -> 全部通过后登记 final DOCX/PDF output file ids
  -> 前端开放下载
```

这条链路的关键约束是：Profile JSON 是唯一格式事实来源；candidate 文件不是最终交付物；任何 unsupported、QC fail、PDF fail 或必需 LLM review fail 都不能发布最终下载。

### 4.2 状态与失败语义

后端导出状态应统一表达为：

| 状态 | 含义 | 是否可下载最终文件 |
| --- | --- | --- |
| `completed` | DOCX、PDF、内部 QC 和最终版面校验均已通过 | 是 |
| `quality_failed` | 候选 DOCX/PDF 已生成，但内部交付门未通过 | 否 |
| `failed` | 编译、文件读取、转换、LLM 调用或不可恢复异常失败 | 否 |

用户侧只需要看到进度和简短失败原因；内部保留字段级 issue、verifier、auto-fix 记录，用于调试和后续迭代。

## 5. 已完成改动总览

### 5.1 Profile v2 模型升级

涉及文件：

- `backend/app/profiles/models.py`
- `backend/app/models.py`
- `frontend/src/api/client.ts`
- `profiles/ecnu_thesis.yaml`

已新增或扩展：

- `schema_version`
- `source_documents`
- `rule_evidence`
- `missing_fields`
- `unsupported_rules`
- `capability_coverage`
- `manual_overrides`
- `locked_fields`
- `template_binding`
- `delivery_gate`
- `llm_final_review`

已实现价值：

- Profile 从简单配置升级为可追溯、可锁定、可声明能力边界的格式契约。
- v1 profile 仍可加载，新增字段都有安全默认值。
- 字色等字段进入统一规范，例如黑色归一为 `000000`。

当前限制：

- `capability_coverage` 仍主要是状态声明；Rule Registry 已能解析 callable applier/verifier，内部交付门已检查 registry 声明的 DOCX verifier 是否出现在实际 QC 输出中，但导出执行链还没有完全改为由 registry 调度。
- 部分高级字段存在 schema，但真实文档验证覆盖还不足。

### 5.2 Requirement Session 与 Agent 入口

涉及文件：

- `backend/app/api/requirement_sessions.py`
- `backend/app/agents/requirements.py`
- `backend/app/models.py`
- `frontend/src/api/client.ts`
- `frontend/src/App.tsx`

已完成：

- 会话创建支持 `attachments`、`current_profile`、`locked_fields`。
- 追加消息支持携带当前 Profile 和锁定字段。
- 新增 `POST /api/requirement-sessions/{session_id}/attachments`。
- 后端会把历史对话、附件、当前 Profile、锁定字段共同传入 LLM 上下文。
- Agent 生成 Profile draft 后会恢复 `locked_fields` 的旧值，避免覆盖用户手动调整。
- Agent 默认开启 `llm_final_review.enabled=true`、`required=true`。
- LLM 不可用时 fail closed，不创建假 Profile draft。

已实现价值：

- 用户通过对话补充“字色要黑色”等规则时，可以进入同一会话状态。
- 用户上传格式规则文档、格式样本文档、自然语言补充后，最终都可以汇入同一个 Profile draft。

当前限制：

- 前端仍没有完全完成统一工作台重构。
- Agent 输出仍需更严格的 JSON Patch / schema merge 协议。

### 5.3 上传格式样本文档真实样式读取

涉及文件：

- `backend/app/agents/style_sample_extractor.py`
- `backend/app/agents/requirements.py`

已完成：

- 新增附件类型 `style_sample_docx`。
- 支持 `.doc` 通过 LibreOffice 转换后读取。
- 使用 `python-docx` 读取：
  - 页面宽高。
  - 页边距。
  - 正文段落样式样本。
  - 标题段落样式样本。
  - run 字体、字号、颜色、加粗、斜体。
  - 页眉页脚文本。
  - 表格数量和首表结构。
  - 图片尺寸样本。
- 样式证据写入 `ExtractionEvidence`，source 为 `style_sample_docx`。

已实现价值：

- 系统不再把上传的格式样本文档只当成纯文本。
- Agent 可以拿到真实 Word 样式证据，而不是只靠 OCR/文本描述。

当前限制：

- 目前仍偏样本统计，尚未完整读取所有 section、所有表格边框、复杂编号、TOC 字段、文档网格、图片锚定等全部 OOXML 细节。
- 样式证据到 Profile 字段路径的映射还需要继续细化。

### 5.4 Rule Registry 与 unsupported 阻断

涉及文件：

- `backend/app/documents/rule_registry.py`
- `backend/app/quality/delivery_gate.py`
- `backend/tests/test_rule_registry.py`

已完成：

- 新增 `RuleSpec` 基础注册表。
- 每条规则可以声明：
  - `field_path`
  - `formatter`
  - `qc`
  - `applier`
  - `verifier`
  - `unsupported_behavior`
  - `note`
- 新增 `registered_rule_specs()`。
- 新增 `find_supported_rule_specs_without_handlers()`。
- 新增 `resolve_rule_applier()` 与 `resolve_rule_verifier()`，supported applier/verifier 可以解析为 callable。
- `docx.*` verifier 现在会解析为可调用 wrapper，执行 `inspect_docx_quality` 并返回对应 `check_key` 的 `QualityIssue`。
- 新增 `find_supported_rule_specs_without_callables()`，用于检查 supported 字段是否只是字符串但无法实际解析。
- 新增 `supported_docx_verifier_check_keys()` 与 `find_supported_docx_verifier_keys_missing_from_issues()`，用于校验 registry 声明的 DOCX verifier 是否被真实 QC 输出覆盖。
- 新增 `DocxRegistryVerificationResult` 和 `verify_docx_rule_registry_coverage()`，将每个 supported DOCX Profile 字段映射到实际 QC `QualityIssue`。
- 新增 `supported_docx_formatter_applier_names()`，并在 formatter 侧声明 `FORMATTER_PIPELINE_APPLIERS` / `formatter_pipeline_applier_names()`，用测试保证 supported DOCX applier 已接入格式控制 pipeline。
- 新增 `verified_profile_fields` 内部 issue evidence：`inspect_docx_quality()` 会把 registry 对应的 Profile 字段写入 `QualityIssue.details`；registry 覆盖检查不再只接受同名 `check_key`，还要求 issue 明确声明验证了对应字段。
- 正文样式 QC 已从单一 `docx.body.style` 聚合项拆出字段级 verifier：
  - `docx.body.font.chinese`
  - `docx.body.font.latin`
  - `docx.body.font.size`
  - `docx.body.font.color`
  - `docx.body.line_spacing`
  - `docx.body.first_line_indent`
  - `docx.body.space_before`
  - `docx.body.space_after`
  - `docx.body.alignment`
- 标题样式 QC 已在保留 `docx.heading.style` 聚合项的同时拆出字段级 verifier：
  - `docx.heading.font.chinese`
  - `docx.heading.font.latin`
  - `docx.heading.font.size`
  - `docx.heading.font.color`
  - `docx.heading.font.weight`
  - `docx.heading.alignment`
  - `docx.heading.line_spacing`
  - `docx.heading.space_before`
  - `docx.heading.space_after`
  - `docx.heading.first_line_indent`
  - `docx.heading.pagination`
- 页眉页脚与页码 QC 已在保留 `docx.header_footer` / `docx.page_number` 聚合项的同时拆出字段级 verifier：
  - `docx.header_footer.header_text`
  - `docx.header_footer.footer_text`
  - `docx.header_footer.different_first_page`
  - `docx.header_footer.different_odd_even`
  - `docx.page_number.field`
  - `docx.page_number.format`
  - `docx.page_number.start`
- 表格和图件题注 QC 已在保留 `docx.visuals.caption_pairing` 聚合项的同时拆出字段级 verifier：
  - `docx.table.caption.position`
  - `docx.table.caption.bilingual`
  - `docx.figure.caption.position`
  - `docx.figure.caption.bilingual`
- 表格规则 QC 已在保留 `docx.table.borders` 聚合项的同时拆出字段级 verifier：
  - `docx.table.border_style`
  - `docx.table.header_repeat`
- 目录 QC 已在保留 `docx.toc.fields` 聚合项的同时拆出字段级 verifier：
  - `docx.toc.enabled`
  - `docx.toc.title`
  - `docx.toc.include_levels`
  - `docx.toc.show_page_numbers`
  - `docx.toc.right_align_page_numbers`
  - `docx.toc.use_hyperlinks`
  - `docx.toc.update_fields_on_open`
- 目录字段级检查已对齐 formatter 的兼容语义：v1 profile 中 `toc.enabled=true` 不等价于“必须生成目录”；只有 v2 profile 或 `sections` 中显式声明必需目录时，缺失目录才会阻断。
- 模板 QC 已从单一占位符聚合项拆出首批字段级 verifier：
  - `docx.template.body_slot`
  - `docx.template.placeholders`
- 新增 `blocking_unsupported_capabilities()`。
- `outputs` 被显式注册为导出编排字段。
- 未知字段默认 `formatter=unsupported`、`qc=unsupported`、`unsupported_behavior=block`。
- 内部交付门会先检查 `profile.unsupported_rules` 与 `profile.capability_coverage`。
- 内部交付门会在 DOCX QC 后检查 registry verifier 字段级覆盖完整性；如果某个 supported `docx.*` verifier 没有对应 `QualityIssue` 输出，会记录缺失的 `check_key` 和受影响 `field_path`，并 fail closed，不发布下载。
- 新增 `execute_docx_rule_verifiers()`：内部交付门会按 registry 的 `docx.*` verifier 清单逐个执行 callable，并在 `rule_registry.dispatch` 中记录实际执行过的 `check_key`、字段路径、issue id、status 和失败原因。
- 如果某个注册的 DOCX verifier callable 无法执行或返回非 `QualityIssue`，内部交付门会以 `profile.rule_registry.verifier_dispatch` fail closed，不发布下载。
- 新增 formatter applier 执行 trace：
  - `docx_formatter_field_paths_by_applier()` 能从 Rule Registry 反查 formatter applier 覆盖的 Profile 字段。
  - `summarize_docx_formatter_dispatch()` 会把 formatter call counts 汇总为字段级执行摘要。
  - `FormatterExecutionTrace` 会记录 `_apply_body_paragraph`、`_apply_page_settings`、`_apply_table_rules` 等 applier 的实际调用次数。
  - `FormatCompiler` 会把 trace 写入 compile metadata 的 `formatter_registry`，包括 `executed_field_paths`、`not_executed_field_paths`、`missing_registered_appliers` 和 `unexpected_appliers`，供 Job/Batch 内部调试和后续审计。

已实现价值：

- 避免“前端/Agent 能填，后端不处理也说成功”的一部分风险。
- 已有测试保证 supported RuleSpec 至少要有 applier/verifier 标识。
- 已有测试保证 supported RuleSpec 的 applier/verifier 能解析为 callable，并验证 `body.font.color` 的 DOCX verifier wrapper 可实际返回 `docx.body.style` issue。
- 已有测试保证 supported `docx.*` verifier 都能在真实 `inspect_docx_quality` 输出中找到，并验证内部交付门会阻断缺失 verifier 输出的情况。
- 已有测试保证 `body.font.color`、`figure.size_rules` 等 supported 字段能映射到实际 QC issue；当 `docx.figure.size` 输出缺失时，交付门会报告 `figure.size_rules` 缺失覆盖。
- 已有测试保证 registry 声明的 supported DOCX formatter applier 出现在 formatter pipeline 声明中，避免“标记 supported 但完全没接入格式脚本”。
- 已有测试保证没有 `verified_profile_fields` 字段级 evidence 的 QC issue 即使 `check_key` 匹配，也不能算作字段覆盖。
- 已有测试保证正文 `body.font.color` 映射到 `docx.body.font.color` 字段级 issue，而不是旧的聚合 `docx.body.style`。
- 已有测试保证标题 `headings.font.color` 映射到 `docx.heading.font.color` 字段级 issue，`headings.pagination` 映射到 `docx.heading.pagination`。
- 已有测试保证 `header_footer.header_text` 映射到 `docx.header_footer.header_text`，`header_footer.page_number_format` 映射到 `docx.page_number.format`。
- 已有测试保证 `table.border_style`、`table.header_repeat`、`table.caption.position`、`figure.caption.position` 映射到各自字段级 issue。
- 已有测试保证 `toc.title`、`toc.include_levels` 映射到目录字段级 issue，且目录标题 mismatch 仍能被 QC 发现。
- 已有测试保证 `template_binding.body_slot` 映射到 `docx.template.body_slot`，`template_binding.placeholder_policy` 映射到 `docx.template.placeholders`，并能在残留 `{{BODY}}` / `{{UNRESOLVED}}` 时产生字段级 warning。
- 已有测试保证 registry 会实际执行已注册 DOCX verifier dispatch，并且 `DocumentFormattingService.last_delivery_gate_summary["docx"]["rule_registry"]["dispatch"]` 会记录 `all_executed` 与 `executed_check_keys`。
- 已有测试保证 formatter trace 会记录已执行的 registry applier，并且 `DocumentFormattingService.last_delivery_gate_summary["compile"]["formatter_registry"]` 会记录 `executed_appliers`、`executed_field_paths` 与 `not_executed_field_paths`。
- 已有测试保证 formatter dispatch summary 能报告未执行 applier 对应的字段路径，以及意外 applier 名称。
- 未知字段会 fail closed。

当前限制：

- registry 已具备 callable resolver、formatter pipeline 接入防线、formatter applier trace、formatter 字段级执行摘要、带 evidence 的字段级 DOCX verifier 覆盖结果，以及内部交付门中的 DOCX verifier dispatch 执行摘要；正文、标题、页眉页脚、页码、表格规则、图表题注、目录和模板 body slot / placeholder policy 已拆到字段级 verifier，但 formatter 主流程仍未完全由 registry 动态编排。
- 目前 applier/verifier 仍保留函数名/check key 作为稳定标识，再由 resolver 转 callable。
- `partial`、`template_delegated`、`extract_only` 的阻断策略仍需更严格。

### 5.5 FormatCompiler 与模板绑定

涉及文件：

- `backend/app/documents/compiler.py`
- `backend/app/documents/template.py`
- `backend/app/documents/service.py`
- `backend/app/jobs/worker.py`
- `backend/app/api/jobs.py`
- `backend/app/api/batches.py`

已完成：

- 新增 `FormatCompiler` 作为生产导出入口。
- 支持可选模板绑定：
  - 读取模板文件。
  - 根据 `profile.template_binding.body_slot` 合并正文。
  - 支持页眉页脚继承策略。
  - 支持模板占位符策略。
- `DocumentFormattingService` 采用 candidate -> gate -> final 语义。
- Job、Batch、Worker 路径接入内部交付门和最终输出注册。

已实现价值：

- 后端形成候选文件和最终可下载文件的明确边界。
- 模板 DOCX 可以作为固定封面、声明页、目录页、页眉页脚结构的载体。

当前限制：

- 模板合并仍是保守实现。
- 多 slot、复杂分节继承、固定页重复、异常空白页仍需真实模板矩阵验证。

### 5.6 Formatter 规则执行能力

涉及文件：

- `backend/app/documents/formatter.py`
- `backend/app/documents/ooxml.py`
- `backend/app/documents/structure.py`

已增强能力：

- 页面设置、纸张尺寸、页边距、方向。
- 文档网格。
- 页眉页脚、首页不同、奇偶页不同。
- 页码字段、页码格式和起始值。
- TOC 字段生成和打开时刷新。
- 正文段落字体、字号、颜色、行距、首行缩进、段前段后、对齐。
- 标题段落样式、编号、缩进、段前段后、keep with next、page break before。
- 摘要、关键词、题注、公式、参考文献基础格式。
- 表格题注位置、图题位置、中外文题注补齐。
- 表格三线表、最简边框、全网格、表头重复。
- 图片尺寸规则基础处理。
- 单位规则、全角数字归一、数字单位空格归一，覆盖正文段落和表格单元格。

已覆盖用户明确提到的主要格式项：

- 正文中英文字体、字号、字色。
- 标题一级、二级、三级等层级字体、字号、字色。
- 行间距、页边距、首行缩进。
- 目录、页眉、页脚、文档网格。
- 序号、表名在表格正上方、图名在图件正下方。
- 中外文对照题注。
- 三线表。
- 插图 inline 场景。
- 半栏图/通栏图尺寸基础处理。
- 计量、计价单位规范。

当前限制：

- 执行顺序仍是函数式流程，不是严格“遍历 Profile JSON 每条规则并调用 registry applier”。
- 复杂论文中的多节、多模板、多样式冲突还需要更多真实样本压测。

### 5.7 内部 QC 交付门

涉及文件：

- `backend/app/quality/delivery_gate.py`
- `backend/app/quality/inspection.py`
- `backend/app/quality/final_layout_review.py`
- `backend/app/documents/service.py`

已完成：

- 新增 `InternalDeliveryGateService`。
- DOCX candidate 必须先通过内部 QC。
- PDF 导出后必须通过 PDF QC。
- 不支持规则会阻断。
- DOCX 正文样式检查从首个正文段落升级为遍历所有正文段落。
- DOCX 标题样式检查从首个标题段落升级为遍历所有标题段落。
- DOCX 表格题注检查逐个表格确认题注位于表格上方。
- DOCX 图片题注检查逐个 inline 图片确认题注位于图片下方。
- DOCX 双语表题/图题检查已从总数统计升级为逐表/逐图邻近配对检查。
- DOCX 图片尺寸检查已能逐个 inline 图片验证半栏图 `<= half_column_max_mm` 或通栏图 `full_width_min_mm-full_width_max_mm`。
- DOCX TOC 检查已能校验目录标题文本与 `profile.toc.title` 一致。
- DOCX 结构分类已优先识别 `目录` / `Contents` 为 TOC 标题，避免二次格式化时被标题编号污染成 `1 目录`。
- DOCX 模板占位符检查会阻断正文、页眉、页脚中残留的 `{{...}}`。
- DOCX 模板 body slot 残留和 unresolved placeholder 残留已进入字段级 QC，并能映射到 `template_binding.body_slot` / `template_binding.placeholder_policy`。
- DOCX 单位规则检查覆盖正文段落和表格单元格，并能报告具体 cell 位置。
- DOCX registry verifier dispatch 已接入内部交付门：每次 DOCX gate 都会执行注册表中的 `docx.*` verifier callable，并将执行摘要写入 `rule_registry.dispatch`。
- 支持一次安全自动修复：QC 失败后可重新调用 formatter 生成 `*-gate-fixed.docx`，再验一次。
- 最终 LLM 版面校验已接入：
  - 提取 PDF 前几页文本。
  - 本机存在 `pdftoppm` 时渲染前 3 页图片。
  - 调用 OpenAI-compatible chat completions。
  - 要求模型返回 JSON：`passed`、`summary`、`issues`。
  - Profile 要求 final review 且 reviewer 未配置时 fail closed。

已实现价值：

- 用户不会直接下载未经内部校验的候选文件。
- LLM 最终校验只做版面健康检查，不替代确定性 QC。

当前限制：

- QC 已有字段级 verifier registry 覆盖检查与 dispatch 执行摘要，但仍未覆盖全部复杂论文对象和全部模板语义。
- 复杂 TOC 场景、多 section 页眉页脚、模板固定页等仍需加强。
- 自动修复轮次、白名单动作和失败解释仍需继续生产化。

### 5.8 前端工作台升级

涉及文件：

- `backend/app/core/config.py`
- `.env.example`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/styles.css`
- `frontend/README.md`

已完成：

- 新增上传文件类型选择：
  - 格式规则文档。
  - 格式样本文档。
- 上传分析、对话补充都会带上 `current_profile` 和 `locked_fields`。
- 可视化编辑会把变更字段写入 `locked_fields`。
- Agent 抽取结果规则列表不再只展示前 8 条。
- 可视化编辑区新增 `llm_final_review` 开关。
- API 类型同步 Profile v2、附件、能力覆盖等字段。
- 页面样式做了初步重排和控件补强。
- 新增首屏工作台总览 `command-center`：
  - Agent / LLM 配置状态。
  - 当前 Profile JSON 名称、版本、锁定字段、证据和缺失项。
  - Rule Coverage supported / partial / template / blocked 统计。
  - Export Gate 当前导出状态、源文档数量、输出格式和 QC 状态。
- 新增右侧规则覆盖面板：
  - 展示字段路径。
  - 展示 formatter / QC 支持状态。
  - 展示 supported / partial / template / blocked 标签。
  - 展示 locked 字段状态。
- 后端默认 CORS 已自动补齐本地 Vite fallback 端口 `5173-5199`，避免 Vite 端口被占用后前端换端口导致 API 请求失败。

已实现价值：

- 用户已经可以区分“上传规则文档给 Agent 读”和“上传格式样本文档让系统提取样式”。
- 用户手动改动可以反馈给后端，降低被 Agent 覆盖的风险。
- 用户进入页面后能直接看到 Profile JSON、规则覆盖和导出放行状态，不必先翻完整表单。
- 浏览器联调已验证 `VITE_API_BASE_URL=http://127.0.0.1:8020/api`、前端 `http://127.0.0.1:5180/` 场景无 CORS 错误。

当前限制：

- 页面仍集中在 `App.tsx`，还没有完全拆成 `profile-intake` 与 `export` feature 组件。
- 规则覆盖面板已展示支持状态和 locked 状态，但还未完整展示每条规则的 evidence quote、confidence、source document 和用户确认状态。
- 规则树仍是首批可视化，不是完整 JSON tree inspector。
- 整体视觉已从单纯堆表单推进为控制台布局，但仍需继续拆组件、细化信息架构和响应式体验。

### 5.9 配置与文档

涉及文件：

- `.env.example`
- `README.md`
- `backend/README.md`
- `frontend/README.md`

已完成：

- `.env.example` 补充 LLM 相关配置说明。
- README 更新生产化导出语义。
- 后端 README 说明 LLM final layout review 与附件接口。
- 前端 README 说明新工作台能力和启动方式。

关键配置：

```dotenv
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_TIMEOUT_SECONDS=
```

规则：

- Agent 规则提取必须有 LLM。
- Profile 要求 final review 时，最终版面校验必须有 LLM。
- key/token 只通过 `.env` 配置，不写死在代码里。

### 5.10 模块级改动清单

| 模块 | 主要文件 | 已落盘改动 | 当前判断 |
| --- | --- | --- | --- |
| Profile 数据模型 | `backend/app/profiles/models.py`、`backend/app/models.py`、`profiles/ecnu_thesis.yaml` | Profile v2 metadata、证据、缺失项、不支持项、锁定字段、模板绑定、交付门、LLM final review | 核心模型已落地，仍需更多字段级验证覆盖 |
| Agent 规则抽取 | `backend/app/agents/requirements.py`、`backend/app/api/requirement_sessions.py` | 对话、规则文档、样本文档、当前 Profile、locked fields 合流；LLM fail-closed | 入口已合流，仍需更严格 JSON Patch / schema merge |
| 样本文档提取 | `backend/app/agents/style_sample_extractor.py` | 从 `.doc/.docx` 读取样式样本、页边距、字体、标题、页眉页脚、表格、图片尺寸 | 已能读取真实样式证据，复杂 OOXML 细节需加强 |
| Rule Registry | `backend/app/documents/rule_registry.py` | RuleSpec、capability coverage、unsupported 阻断、callable resolver、DOCX verifier 字段级覆盖检查、supported formatter applier 清单、formatter applier 字段映射、formatter 字段级执行摘要、`verified_profile_fields` evidence、DOCX verifier dispatch 执行摘要；正文 body、标题 headings、页眉页脚、页码、表格规则、图表题注、目录和模板 body slot / placeholder policy 字段已拆到字段级 verifier | 注册、字段级覆盖结果、formatter trace、dispatch 执行证据和覆盖门已落地，formatter 调度仍需继续 registry 化 |
| 格式编译 | `backend/app/documents/compiler.py`、`backend/app/documents/template.py` | 统一 FormatCompiler、模板绑定、正文 slot、页眉页脚继承、candidate/final 边界、formatter registry trace metadata；compile metadata 已包含 executed / not executed field paths | 骨架已落地，复杂模板矩阵未验收 |
| DOCX 格式执行与检查 | `backend/app/documents/formatter.py`、`backend/app/documents/ooxml.py`、`backend/app/documents/structure.py`、`backend/app/quality/inspection.py` | 页面、网格、正文、标题、目录、页眉页脚、题注、三线表、图片尺寸、单位等基础执行；声明 formatter pipeline appliers 并与 registry supported applier 测试对齐；记录 formatter applier execution trace 和字段级执行摘要；正文、标题、页眉页脚、页码、表格规则、图表题注、目录和模板 body slot / placeholder policy 字段级 QC 已拆出 | 覆盖用户主要规则，但执行仍偏函数式流程，模板固定页/多 slot 等仍需增强 |
| CLI 样本入口 | `scripts/build_final_docx.py` | 加载 Profile YAML/JSON，转换 `.doc`，编译 candidate，执行 DOCX 内部 gate，可选 PDF gate 和最终 LLM layout review，全部通过后才复制 final DOCX/PDF | 已可用于真实样本 smoke；还需纳入正式样本矩阵 |
| 内部交付门 | `backend/app/quality/delivery_gate.py`、`backend/app/quality/inspection.py`、`backend/app/quality/final_layout_review.py` | DOCX QC、PDF QC、自动安全修复、registry verifier 覆盖阻断、registry verifier dispatch 执行摘要、LLM final review | 放行边界已建立，仍需补齐复杂论文对象级 verifier 与多轮修复策略 |
| Job/Batch 编排 | `backend/app/documents/service.py`、`backend/app/jobs/worker.py`、`backend/app/api/jobs.py`、`backend/app/api/batches.py` | candidate -> gate -> final output ids，失败时不发布最终下载 | 主路径已接入，真实批量样本需继续验证 |
| 前端工作台 | `frontend/src/App.tsx`、`frontend/src/api/client.ts`、`frontend/src/styles.css` | 规则文档/样本文档上传、对话补充、可视化字段编辑、locked fields、首屏 command center、完整规则检查器、Profile JSON 展示、最终下载状态 | 可用性继续提升，但仍未完成 feature 组件拆分 |
| 文档与配置 | `.env.example`、`README.md`、`backend/README.md`、`frontend/README.md`、`docs/modules/` | 记录 LLM env、启动方式、Profile v2、生产化导出语义、本地 Vite fallback CORS、当前限制 | 已更新，需随下一轮实现继续同步 |

## 6. API 与数据契约

### 6.1 Requirement Session

相关接口：

```http
POST /api/requirement-sessions
GET  /api/requirement-sessions/{session_id}
POST /api/requirement-sessions/{session_id}/messages
POST /api/requirement-sessions/{session_id}/attachments
POST /api/requirement-sessions/{session_id}/confirm
```

创建会话请求示例：

```json
{
  "source_type": "conversation",
  "natural_language": "正文小四，黑色，宋体，标题黑体。",
  "attachments": [
    {
      "file_id": "file_x",
      "source_kind": "style_sample_docx",
      "filename": "已排版样本文档.docx"
    }
  ],
  "current_profile": null,
  "locked_fields": []
}
```

追加消息请求示例：

```json
{
  "content": "标题字色也要黑色。",
  "current_profile": {
    "id": "profile_x",
    "name": "华东师范大学论文格式",
    "body": {}
  },
  "locked_fields": [
    "body.font.color"
  ]
}
```

### 6.2 Profile v2 关键结构

```json
{
  "schema_version": "2.1.0",
  "source_documents": [],
  "rule_evidence": [],
  "missing_fields": [],
  "unsupported_rules": [],
  "capability_coverage": [],
  "manual_overrides": [],
  "locked_fields": [],
  "template_binding": {},
  "delivery_gate": {},
  "llm_final_review": {
    "enabled": true,
    "required": true,
    "check_garbled_text": true,
    "check_blank_pages": true,
    "check_overlap": true,
    "check_table_figure_overflow": true
  }
}
```

### 6.3 导出状态语义

- `completed`：最终 DOCX/PDF 已通过内部交付门，可下载。
- `quality_failed`：候选文件存在，但内部交付门未通过，不开放最终下载。
- `failed`：编译、转换、文件读取、LLM 调用等执行失败。

主流程不再把质量报告作为用户产品。

## 7. Profile JSON 覆盖清单

下面字段是生产化最低目标。进入 Profile 后，必须在 `capability_coverage` 声明状态，并最终绑定 formatter applier 与 QC verifier。

### 7.1 页面与分节

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `page.size` | A4、自定义宽高 | 已有基础 formatter/QC |
| `page.orientation` | 纵向/横向 | 已有基础 formatter/QC |
| `page.margins_cm` | 上下左右页边距 | 已有基础 formatter/QC |
| `page.gutter` | 装订线 | schema 有字段，真实验证不足 |
| `sections` | 封面、目录、正文、附录分节 | v2 字段存在，模板适配需加强 |
| `page_numbering` | 起始页码、格式、首页显示 | 已有基础能力，复杂分节需加强 |

### 7.2 文档网格

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `document_grid.enabled` | 是否启用 | 已有 OOXML 写入/检查 |
| `document_grid.chars_per_line` | 每行字符数 | 已有基础能力 |
| `document_grid.lines_per_page` | 每页行数 | 已有基础能力 |
| `document_grid.snap_to_grid` | 段落贴齐网格 | 已有段落应用/检查，需全文证明 |

### 7.3 正文样式

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `body.font.chinese` | 中文字体 | 已有应用/检查 |
| `body.font.latin` | 西文字体 | 已有应用/检查 |
| `body.font.size_pt` | 字号 | 已有应用/检查 |
| `body.font.color` | 字色 | 已有应用/检查，黑色归一为 `000000` |
| `body.line_spacing` | 行距 | 已有应用/检查 |
| `body.first_line_indent_chars` | 首行缩进 | 已有应用/检查 |
| `body.space_before_pt` / `body.space_after_pt` | 段前段后 | 已有应用/检查 |
| `body.alignment` | 对齐 | 已有应用/检查 |

### 7.4 标题样式与编号

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `headings[level].font` | 1-9 级字体、字号、颜色、字重 | 已有应用/检查，逐级 verifier 需加强 |
| `headings[level].paragraph` | 行距、段前段后、缩进、对齐 | 已有应用/检查 |
| `headings[level].numbering` | 编号格式 | 已有可见编号规则，复杂模式需增强 |
| `headings[level].outline_level` | 大纲级别 | 依赖 Word Heading 样式 |
| `headings[level].pagination` | 与下段同页、章前分页 | 已有基础应用/检查 |

### 7.5 目录

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `toc.enabled` | 是否生成目录 | 已有 TOC 字段生成；字段级 QC 已接入；v1 兼容 profile 不把默认 enabled 误判为必需目录 |
| `toc.title` | 目录标题文本 | formatter 会写入，字段级 QC 已检查与 Profile 一致 |
| `toc.include_levels` | 目录级别 | 已有字段 switch 检查和字段级 QC |
| `toc.show_page_numbers` | 是否显示页码 | 已有字段 switch 检查和字段级 QC |
| `toc.right_align_page_numbers` | 页码右对齐 | 已有字段 switch 检查和字段级 QC |
| `toc.use_hyperlinks` | 超链接 | 已有字段 switch 检查和字段级 QC |
| `toc.update_fields_on_open` | 打开时更新字段 | 已有 OOXML 设置/检查和字段级 QC |

### 7.6 页眉页脚

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `header_footer.header_text` | 页眉文本 | 已有应用/检查 |
| `header_footer.footer_text` | 页脚文本 | 已有应用/检查 |
| `header_footer.font` | 字体字号颜色 | 已有应用，复杂分节 QC 需加强 |
| `header_footer.footer_page_number` | 页码字段 | 已有应用/检查 |
| `header_footer.different_first_page` | 首页不同 | 已有基础能力 |
| `header_footer.different_odd_even` | 奇偶页不同 | 已有基础能力 |

### 7.7 摘要、关键词与中英文区分

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `abstract.zh` | 中文摘要标题/正文/关键词 | 已有基础格式化 |
| `abstract.en` | 英文摘要标题/正文/关键词 | 已有基础格式化 |
| `keywords.separator` | 关键词分隔符 | 需继续细化字段模型 |
| `body.font.chinese` / `body.font.latin` | 中英文区分字体 | 已有基础模型和应用 |

### 7.8 表格、图件与题注

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `table.caption.position` | 表名在表格正上方 | 已有移动/补齐与逐表检查 |
| `table.caption.bilingual` | 中外文对照 | 已有补齐能力，QC 已逐表检查中英文邻近配对 |
| `table.caption.numbering` | 表编号格式 | 已有基础能力 |
| `table.border_style` | 三线表/最简/全网格 | 已有应用/检查 |
| `table.header_repeat` | 表头重复 | 已有应用 |
| `figure.caption.position` | 图名在图件正下方 | 已有移动/补齐与逐图检查 |
| `figure.caption.bilingual` | 中外文对照 | 已有补齐能力，QC 已逐图检查中英文邻近配对 |
| `figure.size_rules` | 半栏/通栏尺寸 | 已有应用能力，QC 已逐个 inline 图片检查半栏/通栏宽度范围 |
| `figure.placement` | 文中相应处直接给出 | 目前主要覆盖 inline 场景 |

### 7.9 公式、参考文献与单位

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `equations` | 公式字体、对齐、编号 | 部分支持，需明确标记 partial |
| `references` | 参考文献字体、行距、悬挂缩进 | 已有基础能力 |
| `unit_rules.measurement_units` | 计量单位 | 已覆盖正文段落和表格单元格 |
| `unit_rules.currency_units` | 计价单位 | 已覆盖正文段落和表格单元格 |
| `unit_rules.normalize_fullwidth_numbers` | 全角数字归一 | 已覆盖正文段落和表格单元格 |
| `unit_rules.unit_spacing` | 数字与单位空格 | 已覆盖正文段落和表格单元格 |

### 7.10 模板与交付门

| 字段域 | 目标字段 | 当前状态 |
| --- | --- | --- |
| `template_binding` | 模板文件、正文 slot、页眉页脚继承 | 已有保守实现 |
| `template_binding.body_slot` | 模板正文插入位置 | 已有 TemplateLoader 消费；字段级 QC 会阻断最终 DOCX 中残留的 body slot marker |
| `template_binding.placeholder_policy` | 占位符失败/保留/删除策略 | 已有实现；字段级 QC / gate 会阻断最终 DOCX 中残留的 unresolved placeholders |
| `delivery_gate.fail_on_unsupported_rules` | 不支持规则阻断 | 已有 |
| `delivery_gate.allow_auto_fix` | 自动安全修复 | 已有一次 gate fix |
| `quality.strictness` | 严格等级 | 字段存在，策略需细化 |
| `llm_final_review` | 最终 LLM 版面校验 | 已有实现 |

## 8. 已验证事项

本次重新验证时间：2026-06-12 16:21:06 +0800。

完整验证结果（2026-06-12 16:21:06 +0800）：

```bash
cd backend && uv run pytest -q
# 168 passed, 2 warnings

cd frontend && npm run build
# tsc --noEmit && vite build passed

openspec validate update-production-export --strict --no-interactive
# Change 'update-production-export' is valid

git diff --check
# passed, no output
```

增量测试记录：

```bash
cd backend && uv run pytest tests/test_rule_registry.py tests/test_requirement_sessions_api.py -q
# 27 passed, 2 warnings

cd backend && uv run pytest tests/test_rule_registry.py -q
# 13 passed

cd backend && uv run pytest tests/test_rule_registry.py tests/test_document_worker.py::test_formatting_service_creates_docx_output_record tests/test_document_worker.py::test_delivery_gate_blocks_missing_registered_docx_verifier_output -q
# 15 passed, 1 warning

cd backend && uv run pytest tests/test_rule_registry.py tests/test_document_worker.py::test_formatting_service_creates_docx_output_record -q
# 14 passed, 1 warning

cd backend && uv run pytest tests/test_rule_registry.py tests/test_quality_reports.py::test_docx_quality_inspection_detects_toc_title_mismatch tests/test_document_worker.py::test_formatting_service_creates_docx_output_record -q
# 11 passed, 1 warning

cd backend && uv run pytest tests/test_document_worker.py::test_formatting_service_applies_template_policy_and_inherits_header_footer tests/test_document_worker.py::test_formatting_service_blocks_template_placeholder_residue -q
# 2 passed, 1 warning

cd backend && uv run pytest tests/test_foundation.py::test_default_cors_origins_include_vite_fallback_ports -q
# 1 passed, 1 warning

cd backend && uv run pytest tests/test_document_worker.py tests/test_production_profile_pipeline.py -q
# 17 passed, 1 warning

cd backend && uv run pytest tests/test_quality_reports.py -q
# 37 passed, 1 warning

cd backend && uv run pytest tests/test_document_formatting.py -q
# 14 passed

cd backend && uv run python ../scripts/build_final_docx.py --help
# passed

cd backend && uv run python ../scripts/build_final_docx.py --profile ../profiles/ecnu_thesis.yaml --input "/Users/hwaigc/workspace/计算机系统结构课程报告_RISC-V/输出/国内RISC-V架构现状及发展趋势课程报告.docx" --output "../storage/sample-smoke/riscv-ecnu-final.docx" --pdf-output "../storage/sample-smoke/riscv-ecnu-final.pdf" --work-dir "../storage/sample-smoke/full-work"
# status=completed; DOCX gate 64 pass / 0 warning / 0 fail; PDF gate 4 pass; LLM layout review pass

codex-docx-inspect storage/sample-smoke/riscv-ecnu-final.docx
# paragraphs=131 nonempty=119 tables=2 chars=17417

codex-pdf-inspect storage/sample-smoke/riscv-ecnu-final.pdf
# pages=19 text_chars=18913

cd backend && uv run pytest tests/test_document_formatting.py::test_formatter_moves_existing_table_caption_group_next_to_table tests/test_rule_registry.py tests/test_document_worker.py::test_formatting_service_creates_docx_output_record -q
# 15 passed, 1 warning
```

已覆盖的关键方向：

- RuleSpec 注册表完整性。
- RuleSpec supported callable resolver 与 DOCX verifier 覆盖完整性。
- Internal delivery gate 对 registry verifier 缺失输出 fail closed。
- Internal delivery gate 对 registry DOCX verifier dispatch 的执行摘要记录，包含 `all_executed` 和 `executed_check_keys`。
- Formatter applier execution trace 已写入 compile metadata，能记录本次导出实际执行的 registry applier、已触达字段、未触达字段和意外 applier。
- 未知 Profile 字段默认 unsupported 并阻断。
- DOCX 正文样式 QC 遍历所有正文段落。
- DOCX 标题样式 QC 遍历所有标题段落。
- DOCX 表格题注 QC 逐个表格检查题注位于上方。
- DOCX 图片题注 QC 逐个 inline 图片检查题注位于下方。
- DOCX 双语表题/图题 QC 逐表/逐图检查中英文题注邻近配对。
- DOCX 图片尺寸 QC 逐个 inline 图片检查半栏/通栏宽度区间。
- DOCX TOC 标题 QC 检查目录标题与 `profile.toc.title` 一致。
- DOCX TOC 字段级 QC 检查 `enabled/title/include_levels/show_page_numbers/right_align_page_numbers/use_hyperlinks/update_fields_on_open`，并对齐 v1/v2 目录必需语义，避免默认 `toc.enabled=true` 在非必需目录场景误阻断。
- DOCX Formatter 防止 TOC 标题在二次格式化/auto-fix 时被标题编号污染。
- DOCX 模板占位符残留阻断内部交付门。
- DOCX 模板 body slot 残留和 unresolved placeholder 残留已进入字段级 QC，并能映射到 `template_binding.body_slot` / `template_binding.placeholder_policy`。
- DOCX 单位规则 formatter/QC 覆盖表格单元格。
- DOCX 表题移动修复：已有同编号中英文表题但与表格之间夹有说明段落时，formatter 会把 caption group 移动到表格正上方；真实 RISC-V 课程报告样本已通过该场景。
- Requirement Session API。
- Agent LLM fail-closed。
- 追加消息保留 locked fields。
- `style_sample_docx` 附件提取样式证据。
- Profile v2 兼容性。
- Unsupported capability 阻断导出。
- Internal delivery gate 发布/阻断行为。
- Final LLM layout review 可用/不可用路径。
- Document worker 最终输出路径。
- 前端 TypeScript 构建。
- 默认 CORS 配置覆盖本地 Vite fallback 端口 `5173-5199`。
- 浏览器 smoke 已验证 `http://127.0.0.1:5180/` 连接 `http://127.0.0.1:8020/api` 时无 CORS/console warning/error，首屏 command center 和 Profile 面板正常渲染。
- 真实样本 smoke 已验证课程报告 DOCX -> final DOCX/PDF：DOCX gate、PDF gate、最终 LLM layout review、`codex-docx-inspect`、`codex-pdf-inspect` 均通过。

注意：

- 上述测试通过不等价于“复杂论文真实样本百分百稳定”。
- 真实样本矩阵验收仍未完成。

### 8.1 尚未完成的实物验收

以下验证还没有足够证据支撑“百分百完成”，不能写成已完成：

- 使用华东师范大学格式要求文档重新抽取完整 Profile，并人工核对 Agent 结构化结果。
- 使用 Agent 抽取出的 Profile 处理原始课程报告，导出 DOCX/PDF 后逐条比较规则命中情况；当前已用内置 `ecnu_thesis` Profile 完成一次真实课程报告 smoke。
- 使用复杂毕业论文样本验证多级标题、目录、页眉页脚、图表、参考文献、模板固定页。
- 使用真实模板 DOCX 验证封面、声明页、目录页、正文 slot、分节和页眉页脚继承。
- 在浏览器中完成完整流程：对话/上传规则/上传样本 -> 可视化规则树 -> 保存 Profile -> 上传 Word -> 下载 DOCX/PDF。
- 使用 `codex-docx-inspect` 与 `codex-pdf-inspect` 对最终产物做文件级检查。

## 9. 当前生产化缺口

### 9.1 P0：Rule Registry 仍需升级为调度执行注册表

当前已经有 `RuleSpec` 基础层、callable resolver、formatter pipeline applier 接入防线、formatter applier execution trace、formatter 字段级执行摘要、带 `verified_profile_fields` evidence 的字段级 DOCX verifier 覆盖结果、DOCX verifier dispatch 执行摘要和交付门阻断，但还需要把 formatter 生产导出链路继续升级为由 registry 直接编排调度：

```text
Profile field path
  -> formatter support status
  -> callable applier
  -> QC support status
  -> callable verifier
  -> unsupported behavior
  -> test coverage
```

目标形态示例：

```python
RuleSpec(
    field_path="body.font.color",
    formatter_status="supported",
    qc_status="supported",
    applier=apply_body_font_color,
    verifier=verify_body_font_color,
    unsupported_behavior="block",
)
```

没有注册的字段不得被当作合规支持。已注册字段也不能只停留在“能解析 callable / 能映射到 check_key / 出现在 pipeline 声明中”，必须有 formatter trace、issue-level `verified_profile_fields` evidence，并在交付门中留下 verifier dispatch 证据。后续要让 formatter 的实际执行顺序由 registry 或等价调度层统一驱动，并逐步把剩余聚合 check 拆成更细的字段级 verifier。

### 9.2 P0：QC 必须逐字段、全文、逐对象验收

必须继续补齐：

- 所有正文段落逐个检查字体、字号、颜色、行距、缩进、段前段后、对齐。
- 每一级标题逐个检查字体、字号、颜色、编号、间距、缩进、分页设置。
- 每个表格检查题注位置、双语题注、三线表、表头重复。
- 每个图片检查题注位置、双语题注、尺寸规则、是否出界。
- 每个 section 检查页眉、页脚、页码、首页不同、奇偶页不同。
- 目录字段检查 TOC switch、标题文本、页码、超链接、更新策略。
- 模板检查正文 slot、占位符残留、固定页重复、异常空白页。
- PDF 检查页数、文本可抽取性、明显空白页。
- LLM final review 检查乱码、错位、重叠、图表出界。

已识别的具体缺口：

- 当前 TOC QC 已拆到字段级检查并覆盖 switch、更新策略和目录标题文本；复杂手工目录、跨节目录和 Word 刷新后的页码真实性仍需加强。
- 双语题注已能逐表/逐图检查中英文邻近配对；后续仍需加强题注编号与章节编号模式的一致性验证。
- 图片尺寸规则已能按半栏图 `<=60mm`、通栏图 `100mm-130mm` 做逐 inline 图片宽度判定；后续仍需加强跨栏/浮动图、图片高度和 PDF 版面出界验证。

### 9.3 P0：前端需要完整统一工作台

必须继续补齐：

- 左侧统一 Agent 对话/附件入口。
- 右侧完整 Profile JSON 规则树。
- 每条规则展示来源、证据、置信度、formatter/QC 支持状态、是否锁定。
- 用户手动调整任意字段后立即同步 JSON 和 locked fields。
- Agent 后续补充只能补全，不得覆盖锁定字段。

建议拆分：

```text
frontend/src/features/profile-intake/
  ProfileIntakeWorkbench.tsx
  AgentConversation.tsx
  AttachmentPanel.tsx
  RuleTree.tsx
  ProfileVisualEditor.tsx

frontend/src/features/export/
  ExportWorkspace.tsx
  TemplateSelector.tsx
  DocumentUploadQueue.tsx
  ExportProgress.tsx
  DownloadPanel.tsx
```

### 9.4 P0：真实样本端到端验收未完成

至少需要三类样本：

1. 简单课程报告。
2. 复杂毕业论文。
3. 带封面、目录、页眉页脚、图表、参考文献、固定模板页的文档。

每类样本必须证明：

- Profile 可创建、保存、复用。
- DOCX 可导出。
- PDF 可导出。
- 内部 QC 全部通过。
- Final LLM review 通过。
- `codex-docx-inspect` 可解析。
- `codex-pdf-inspect` 可解析。
- 前端能下载最终 DOCX/PDF。

### 9.5 P1：模板适配仍需生产化

需要继续处理：

- 多 slot 模板。
- 固定封面页、声明页、目录页重复问题。
- 模板页眉页脚继承冲突。
- 模板分节与源文档分节合并。
- 异常空白页。
- 残留占位符。

### 9.6 P1：可观测性与失败解释

虽然用户不需要质量报告，但系统内部需要更清楚地记录：

- 哪个字段失败。
- 哪个 applier 执行过。
- 哪个 verifier 阻断。
- 是否自动修复过。
- 修复前后结果。
- 最终 LLM review 摘要。

这些信息应留在 job metadata / internal logs，不作为用户下载产品。

## 10. 后续实施路线

### Phase 1：补完 Rule Registry

- 把当前 callable resolver 继续升级为 registry-driven 调度层。
- 每个字段显式绑定 applier/verifier，并能由统一调度入口调用。
- 对 unsupported / extract_only / partial / template_delegated 建立统一阻断策略。
- 增加 registry 完整性测试。

### Phase 2：补完 QC Verifier Registry

- 继续将 `inspection.py` 中聚合检查拆成字段级 verifier；正文 body、标题 headings、页眉页脚、页码、表格规则、图表题注、目录和模板 body slot / placeholder policy 已完成第一批拆分，模板固定页、多 slot、异常空白页等仍需继续。
- 对正文、标题、表格、图片、页眉页脚、目录做全文/逐对象检查。
- 输出内部 `blocking_fields`，不暴露质量报告下载。

### Phase 3：重构前端统一工作台

- 从 `App.tsx` 拆出 feature 组件。
- 建立规则树和可视化编辑双向同步。
- 展示 evidence、source、support status、locked state。
- 删除主流程中用户可见质量报告/修复循环概念。
- 继续提升视觉设计和响应式布局。

### Phase 4：真实样本矩阵

- 准备三类真实样本和对应 Profile。
- 建立后端 smoke 脚本。
- 加入 DOCX/PDF inspect 检查。
- 记录每个样本的 pass/fail 和阻断字段。

### Phase 5：生产试用回归

- 启动后端和前端。
- 浏览器 smoke：
  - 创建 Profile。
  - 上传格式规则文档。
  - 上传格式样本文档。
  - 手动改规则。
  - 保存 Profile。
  - 上传待处理 Word。
  - 下载 DOCX/PDF。
- 后端测试、前端构建、OpenSpec validate、真实样本矩阵全部通过后，才能称为生产试用版。

## 11. 验证命令

后端：

```bash
cd backend && uv run pytest -q
```

前端：

```bash
cd frontend && npm run build
```

OpenSpec：

```bash
openspec validate update-production-export --strict --no-interactive
```

文档产物检查：

```bash
codex-docx-inspect <output.docx>
codex-docx-to-pdf <output.docx> <output_dir>
codex-pdf-inspect <output.pdf>
```

端到端样本建议命令：

```bash
python scripts/build_final_docx.py --profile <profile.json> --input <source.docx> --output <final.docx>
codex-docx-inspect <final.docx>
codex-docx-to-pdf <final.docx> <output_dir>
codex-pdf-inspect <final.pdf>
```

当前已有生产复用入口：

```bash
cd backend && uv run python ../scripts/build_final_docx.py --profile ../profiles/ecnu_thesis.yaml --input <source.docx> --output <final.docx> --pdf-output <final.pdf>
```

该脚本必须继续复用后端 `FormatCompiler` 和 `InternalDeliveryGateService`，不要用临时脚本替代生产入口。

## 12. 完成定义

只有同时满足以下条件，才可以称为“商业级一键全自动、带下载、自动二次修复、复杂论文高稳定”：

- Profile JSON 覆盖页面、网格、正文、标题、目录、页眉页脚、摘要、图表、公式、参考文献、单位、模板、交付门。
- 每个进入 Profile 的字段都有 capability coverage。
- 每个 `formatter=supported` 字段都有 callable applier。
- 每个 `qc=supported` 字段都有 callable verifier。
- 不支持字段在生产默认配置下阻断下载。
- Agent 规则提取必须依赖 LLM；LLM 不可用明确失败。
- 上传格式样本文档能读取真实样式，不只抽文本。
- 用户手动改过的字段不会被 Agent 覆盖。
- Formatter 按 Profile JSON 执行，不静默遗漏。
- QC 按 Profile JSON 逐条全文验收。
- 自动修复后必须重新 QC。
- Final LLM layout review 按配置执行；必需但不可用时阻断。
- 用户只下载通过内部交付门的 DOCX/PDF。
- 主流程不展示质量报告或修复报告产品。
- 三类真实样本矩阵全部通过。
- 后端测试、前端构建、OpenSpec validate、DOCX/PDF inspect 全部通过。

## 13. 文件索引

### 13.1 需求与 OpenSpec

- `docs/change-plans/CP-20260611-001.md`
- `openspec/changes/update-production-export/proposal.md`
- `openspec/changes/update-production-export/design.md`
- `openspec/changes/update-production-export/tasks.md`
- `openspec/changes/update-production-export/specs/profile-v2/spec.md`
- `openspec/changes/update-production-export/specs/production-export-pipeline/spec.md`
- `openspec/changes/update-production-export/specs/internal-qc-delivery-gate/spec.md`
- `openspec/changes/update-production-export/specs/frontend-export-workbench/spec.md`

### 13.2 后端核心

- `backend/app/profiles/models.py`
- `backend/app/models.py`
- `backend/app/api/requirement_sessions.py`
- `backend/app/api/jobs.py`
- `backend/app/api/batches.py`
- `backend/app/agents/requirements.py`
- `backend/app/agents/style_sample_extractor.py`
- `backend/app/documents/compiler.py`
- `backend/app/documents/template.py`
- `backend/app/documents/rule_registry.py`
- `backend/app/documents/formatter.py`
- `backend/app/documents/ooxml.py`
- `backend/app/documents/structure.py`
- `backend/app/documents/service.py`
- `backend/app/jobs/worker.py`
- `backend/app/quality/delivery_gate.py`
- `backend/app/quality/inspection.py`
- `backend/app/quality/final_layout_review.py`

### 13.3 前端核心

- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/styles.css`

### 13.4 文档与配置

- `.env.example`
- `README.md`
- `backend/README.md`
- `frontend/README.md`
- `scripts/build_final_docx.py`
- `profiles/ecnu_thesis.yaml`
- `docs/modules/`

### 13.5 测试

- `backend/tests/test_rule_registry.py`
- `backend/tests/test_requirement_sessions_api.py`
- `backend/tests/test_document_worker.py`
- `backend/tests/test_document_formatting.py`
- `backend/tests/test_quality_reports.py`
- `backend/tests/test_profiles.py`
- `backend/tests/test_production_profile_pipeline.py`

## 14. 当前状态判断

当前项目已经具备生产化方向的核心骨架：

- 可以继续用于本地试用和链路验证。
- 可以生成并下载基础格式化 DOCX/PDF。
- 可以通过 LLM 参与生成 Profile draft。
- 可以读取一部分真实样本文档样式。
- 可以通过内部 QC/LLM final review 阻断部分失败输出。

但在完成第 9 节和第 12 节之前，不能承诺：

- 任意学校/期刊格式模板都稳定成功。
- 复杂论文每一条格式规则都百分百命中。
- 前端体验已经达到最终产品级。
- 所有 Profile 字段都已经接入后续格式控制脚本。

下一步优先级：

1. 先把 Rule Registry 从字段覆盖结果继续推进为 formatter/QC 调度入口，并补 QC verifier registry。
2. 再重构前端统一工作台。
3. 最后做真实样本矩阵验收。

## 15. 给后续执行者的注意事项

- 不要把 LLM 不可用时的默认规则当作成功分析。
- 不要把 `quality_failed` 的 candidate 暴露成可下载最终文件。
- 不要新增用户可下载质量报告作为主流程产品。
- 不要只为了通过测试而检查第一段、第一张表、第一张图。
- 不要把未知 Profile 字段默默忽略。
- 不要绕过 `FormatCompiler` 直接写最终输出。
- 不要在 README 或界面里宣传“百分百成功”，除非第 12 节全部满足。

## 16. 本次整理结论

本文件现在承担三个用途：

1. 作为本轮生产化升级的完整事实记录：说明为什么改、改了哪些模块、现在能做到什么。
2. 作为继续开发的缺口清单：第 9、10、12 节是后续继续实现和验收的主依据。
3. 作为对外沟通边界：当前可以说“生产化链路骨架已建立并通过基础验证”，不能说“复杂论文百分百稳定”。

当前最重要的工程判断：

- OpenSpec change 的任务已全部打勾并通过 validate，但用户提出的商业级目标比这次 OpenSpec task 更高。
- 后端测试和前端构建已通过，说明现有代码没有基础回归；这不是复杂样本文档验收。
- 本次整理过程中修复了目录字段级 QC 对 v1 兼容 profile 的误阻断，并用针对性测试和全量后端测试确认恢复。
- 下一步不应继续堆零散格式规则，而应先把 Rule Registry 变成真正的字段级执行/QC 调度层。
- 前端需要围绕“Agent 对话 + 附件 + 规则树 + Profile JSON + 导出控制台”重构，而不是继续在单页里追加控件。

若后续继续实施，应优先处理：

1. Registry-driven formatter/QC 调度。
2. 字段级、全文、逐对象 verifier 覆盖。
3. 前端统一工作台与完整可视化规则树。
4. 三类真实样本矩阵端到端验收。
5. 通过验收后再更新 README 中的能力描述和发布说明。

## 17. 2026-06-12 17:28 增量实现与验证记录

本轮继续沿 `production-format-upgrade-change-document.md` 推进，没有把目标缩小为“测试过了就完成”。新增事实如下：

### 17.1 已修复的问题

- 修复 Agent Profile 中 `headings[1].font` / `headings[2].font` 这类 indexed field path 被旧能力注册表误判为 unsupported 的问题。
- 增加交付门 unsupported 适用性判断：`notes` / `appendix` 这类规则只在最终 DOCX 实际包含对应对象时才阻断；实际包含但不可执行时仍 fail-closed。
- 新增 `notes` Profile schema、Agent override 合并、formatter applier、rule registry、DOCX QC verifier。
- 脚注/尾注现在不是“仅保留”，而是会写入 `word/footnotes.xml` / `word/endnotes.xml` 的字体、字号、颜色、段前段后和行距，并由 `docx.notes` QC 反查。
- 旧 Agent Profile YAML 中历史生成的 `unsupported_rules: notes` 会被当前 registry 能力复核，不再误阻断已支持的 notes 字段。

### 17.2 真实样例链路证据

使用已有 LLM Agent Profile：

- Profile：`storage/sample-smoke/ecnu-agent-profile.yaml`
- 输入文档：`/Users/hwaigc/workspace/计算机系统结构课程报告_RISC-V/输出/国内RISC-V架构现状及发展趋势课程报告.docx`
- 输出 DOCX：`storage/sample-smoke/riscv-ecnu-agent-final.docx`
- 内部 PDF：`storage/sample-smoke/agent-final-work/riscv-ecnu-agent-final.pdf`

链路结果：

- DOCX gate：通过，`64 pass / 0 fail / 0 warning / 0 unsupported`。
- Rule registry：通过，`all_covered=true`，`dispatch.all_executed=true`。
- Formatter registry：`_apply_notes` 已执行，`notes`、`notes.font` 已进入 executed field paths。
- PDF gate：通过，`4 pass / 0 fail / 0 warning / 0 unsupported`。
- `codex-docx-inspect storage/sample-smoke/riscv-ecnu-agent-final.docx`：`paragraphs=132`，`nonempty=120`，`tables=2`。
- `codex-pdf-inspect storage/sample-smoke/agent-final-work/riscv-ecnu-agent-final.pdf`：`pages=19`，`text_chars=18954`。

### 17.3 真实 LLM 规则抽取已恢复

- 当前 LLM 诊断链路已确认可用：`GET /api/health/llm` 返回 `reachable=true`。
- 真实华东师范大学格式规则文档的 requirement session 已创建成功，HTTP 201。
- 当前仍保留 fail-closed 语义：如果后续模型返回值域不合规、unsupported 字段过多，或最终 layout review 失败，仍然不会放行最终下载。

结论：本地 DOCX/PDF 格式执行与内部 QC 已经通过真实样例；LLM 规则抽取链路已经恢复可用，但复杂论文的最终可下载闭环仍需真实样本矩阵继续验证。

### 17.4 本轮验证命令

```bash
cd backend && uv run pytest -q
cd frontend && npm run build
openspec validate update-production-export --strict --no-interactive
git diff --check
codex-docx-inspect storage/sample-smoke/riscv-ecnu-agent-final.docx
codex-pdf-inspect storage/sample-smoke/agent-final-work/riscv-ecnu-agent-final.pdf
```

验证结果：

- 后端测试：`186 passed, 2 warnings`
- 前端构建：通过
- OpenSpec validate：通过
- `git diff --check`：通过
- 前端构建：通过
- OpenSpec validate：通过
- `git diff --check`：通过
- DOCX/PDF inspect：通过

## 18. 2026-06-12 17:49 增量实现与验证记录

本轮继续补齐不依赖外部 LLM 的生产化缺口，重点是附录规则和 Agent 常见字段路径。

### 18.1 新增附录基础格式支持

- 新增 `profile.appendix` schema：
  - `appendix.title_font`
  - `appendix.body_font`
  - `appendix.title_alignment`
  - `appendix.body_alignment`
  - `appendix.body_line_spacing`
  - `appendix.body_first_line_indent_chars`
- Agent `profile_overrides.appendix.title_font/body_font` 现在会合并进 Profile，不再默认标为 unsupported。
- Formatter 识别 `附录...` / `Appendix...` 段落：
  - 附录标题执行 `_apply_appendix_heading`
  - 附录正文执行 `_apply_appendix_body`
- 文档结构分类器新增：
  - `APPENDIX_HEADING`
  - `APPENDIX_BODY`
- 普通正文 QC 不再把附录标题/正文误判为正文段落。
- 新增 `docx.appendix` 内部 QC：
  - 无附录时 pass + `not_applicable=true`
  - 有附录时检查标题字体、标题对齐、正文字体、正文缩进、正文行距、正文对齐。
- Rule Registry 新增：
  - `appendix`
  - `appendix.title_font`
  - `appendix.body_font`
- 历史 Agent Profile 中旧的 `unsupported_rules: appendix` 会由当前 registry 能力复核，不再误阻断已支持的基础附录格式。
- 未知附录子规则仍会 fail-closed，例如 `appendix.figure_numbering`。

### 18.2 收紧字段能力匹配

修复一个重要风险：以前父字段可能误覆盖未知子字段。现在能力注册匹配改为 exact / index-normalized：

- `headings[1].font` 会归一命中 `headings.font`。
- `headings[2].font.color` 会归一命中 `headings.font.color`。
- `appendix.figure_numbering` 不会被父级 `appendix` 误判为 supported。

同时补齐 Agent 常见字段：

- `table.caption`
- `figure.caption`
- `header_footer.header_alignment`
- `header_footer.footer_alignment`
- `references.style` 标为 partial，不宣称完整 GB/T 内容校验。

### 18.3 本轮验证证据

重新运行：

```bash
cd backend && uv run pytest -q
cd frontend && npm run build
openspec validate update-production-export --strict --no-interactive
git diff --check
codex-docx-inspect storage/sample-smoke/riscv-ecnu-final.docx
codex-pdf-inspect storage/sample-smoke/riscv-ecnu-final.pdf
```

结果：

- 后端测试：`186 passed, 2 warnings`
- 前端构建：通过
- OpenSpec validate：通过
- `git diff --check`：通过
- `codex-docx-inspect storage/sample-smoke/riscv-ecnu-final.docx`：
  - `paragraphs=131`
  - `nonempty=119`
  - `tables=2`
- `codex-pdf-inspect storage/sample-smoke/riscv-ecnu-final.pdf`：
  - `pages=19`
  - `text_chars=18912`

内置 ECNU Profile 真实课程报告导出重新通过：

- DOCX gate：`65 pass / 0 fail / 0 warning / 0 unsupported`
- Rule registry：`all_covered=true`
- Registry dispatch：`all_executed=true`
- PDF gate：`4 pass / 0 fail`
- LLM layout review：内置 profile 关闭 required review，因此以 disabled pass 形式通过。

### 18.4 仍未完成

- 三类真实样本矩阵仍未全部完成。
- 前端 feature 组件拆分仍未完成。
- 复杂模板、多 slot、固定封面/声明页、复杂分节仍需继续验证。

## 19. 2026-06-12 18:15 前端规则工作台收尾记录

本轮按用户要求做最后收口，重点补齐“所有入口最终落到完整 Profile JSON，并且用户能看清楚每条规则是否接入后续格式控制脚本 / QC / LLM”的前端缺口。

### 19.1 已完成改动

- `frontend/src/api/client.ts` 补齐后端已支持的 `notes` 和 `appendix` Profile 类型声明，避免前端保存或编辑时丢失脚注、尾注、附录格式字段。
- `frontend/src/App.tsx` 的 Profile 默认值补齐：
  - `notes.font`
  - `notes.line_spacing`
  - `notes.space_before_pt`
  - `notes.space_after_pt`
  - `appendix.title_font`
  - `appendix.body_font`
  - `appendix.title_alignment`
  - `appendix.body_alignment`
  - `appendix.body_line_spacing`
  - `appendix.body_first_line_indent_chars`
- 可视化编辑区新增“脚注、尾注”和“附录标题与正文”两组控件，用户手动调整后会通过现有 `updateDraft()` 进入同一个 Profile JSON，并同步 locked fields / coverage locked 状态。
- 右侧“规则覆盖”升级为完整规则检查器：
  - 展示全量 `capability_coverage`，不再只显示前 16 条。
  - 支持按 `all / supported / partial / unsupported / locked / missing / evidence` 过滤。
  - 支持按字段路径、状态、来源搜索。
  - 每条规则展示 Agent、Formatter、QC、LLM final review 的支持状态。
  - 展示规则来源、locked 状态、unsupported 行为、note。
  - 展示匹配的 evidence quote / note / confidence。
  - 展示缺失字段、unsupported rules、source documents。
  - 提供只读 `Profile JSON` 原文查看，方便确认 Agent、上传格式文档、上传样本文档和手动调整最终是否汇入同一份 JSON。
- `frontend/src/styles.css` 增加规则检查器、搜索、过滤、证据、不支持规则和 JSON 面板样式。

### 19.2 本轮验证证据

重新运行：

```bash
cd frontend && npm run build
cd backend && uv run pytest -q
openspec validate update-production-export --strict --no-interactive
git diff --check
```

结果：

- 前端构建：通过。
- 后端测试：`186 passed, 2 warnings`。
- OpenSpec validate：`Change 'update-production-export' is valid`。
- `git diff --check`：通过。

浏览器渲染检查：

- 使用系统 Google Chrome headless 打开 `http://127.0.0.1:5174`。
- 桌面宽度确认页面包含：
  - `自定义格式导出工作台`
  - `规则检查器`
  - `Profile JSON`
  - `脚注、尾注`
  - `附录标题与正文`
  - coverage filter。
- 移动宽度 `390px` 检查：`scrollWidth=390`、`clientWidth=390`，没有横向溢出。
- 检查过程无浏览器 console error / warning。
 - LLM 状态卡片显示 `reachable`，并可见 `gpt-5.4 可生成内容`。

### 19.3 当前真实进度判断

当前可以诚实认为：生产化主链路和核心数据契约已经基本成型，前端已经具备 Agent 对话、格式文档/样本文档入口、可视化编辑、完整规则检查器、Profile JSON 查看、模板上传、文档上传和 DOCX/PDF 下载入口。

当前不能诚实认为：项目已经达到“商业级任意复杂论文百分百稳定”。阻断原因仍然是：

- 真实样本矩阵还没有全部跑完。
- 模板复杂适配、多 slot、固定封面/声明页、复杂分节、页眉页脚继承冲突仍需要继续生产化。
- Registry-driven formatter/QC 还没有完全替代所有聚合式检查。
- 前端还没有按 feature 目录拆分组件，当前是可用工作台，但不是理想长期代码结构。
