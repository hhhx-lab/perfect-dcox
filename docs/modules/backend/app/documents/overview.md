# 文档导出引擎

## 1. 模块职责与边界

本模块负责把上传的 `.doc/.docx` 输入转换成规范化的最终 DOCX/PDF。目标态链路以 `FormatCompiler` 为唯一导出入口：先把输入文档转换和解析为可处理 DOCX，再加载 Profile v2 与可选模板，生成候选 DOCX，交给内部 QC 交付门校验和自动修正，全部通过后才登记最终 DOCX/PDF 文件。

本模块不负责从自然语言或格式要求文件中抽取规则；规则抽取属于 `backend/app/agents`。本模块不定义 Profile schema；Profile v2 属于 `backend/app/profiles`。本模块不向用户展示 QC 报告；QC 只作为内部放行门，由 `backend/app/quality` 提供检查与修正能力。

## 2. 核心实现链路

### 单文档导出链路

1. `backend/app/api/jobs.py:create_job` 校验 `input_file_id`、`profile_id`、`profile_version`、可选模板和输出格式，创建 `JobRecord(status=queued)`。
2. `backend/app/jobs/worker.py:process_placeholder_job` 将任务切换为 `running`，并调用 `DocumentFormattingService`。
3. `backend/app/documents/service.py:DocumentFormattingService.format_job` 读取上传文件、Profile v2、模板引用和工作目录，统一处理 `.doc` 转 `.docx`、DOCX 解析、编译、内部 QC 和最终文件登记。
4. `backend/app/documents/converter.py:convert_doc_to_docx` 只负责 `.doc` 到 `.docx` 的 LibreOffice 转换；`.docx` 直接进入解析。
5. `backend/app/documents/parser.py:parse_docx` 校验 DOCX 可解析，并为后续结构分析提供基础保障。
6. `backend/app/documents/compiler.py:FormatCompiler` 读取输入 DOCX、Profile v2 和可选模板，执行页面、正文、标题、多级编号、页眉页脚、题注、公式、参考文献和模板 slot 的确定性格式编译，产出候选 DOCX。
7. `backend/app/documents/template.py` 加载模板 DOCX，处理固定页、正文 slot、页眉页脚继承、占位符替换和模板适配元数据。
8. `backend/app/quality` 的内部 QC 交付门检查候选 DOCX 的 Profile 规则、模板适配、DOCX 健康和 PDF 可导出性；可修正项通过白名单动作自动修正后重跑检查。
9. `backend/app/documents/exporter.py:export_docx_to_pdf` 只在最终 DOCX 通过内部 QC 后导出 PDF。
10. `backend/app/storage/local.py:store_generated_file` 登记最终 DOCX/PDF，`JobRecord.output_file_ids` 只保存已放行的最终文件 id。

### 批量导出链路

1. `backend/app/api/batches.py:create_batch` 校验 Profile、输入文件、输出格式和可选模板。
2. 每个输入文件创建一个 `JobRecord(job_type="batch_format")`，复用单文档导出链路。
3. `_delivery_item_for_job` 只根据最终 `output_file_ids`、内部 QC 放行状态和失败原因构造 `DeliveryManifestItem`；不再创建用户可见质量报告。
4. `_write_manifest` 写入 batch manifest，manifest 只包含交付状态、最终 DOCX/PDF 下载 URL 和简短失败原因。

## 3. 输入、输出与状态

- 输入：上传的 `.doc/.docx` 文件、`profile_id`、`profile_version`、可选 `template_file_id` 或模板绑定信息、`output_formats`、`SOFFICE_BIN`。
- 输出：最终 DOCX `FileRecord`、可选最终 PDF `FileRecord`、单文档 `JobRecord`、批量 `BatchFormatRun`、manifest JSON。
- 状态：`JobRecord.status` 表达 queued/running/completed/quality_failed/export_failed/failed，`current_step` 表达当前阶段，`output_file_ids` 只保存最终可下载文件。
- 副作用：读取上传文件，写入 `storage/work/*` 候选文件和临时文件，写入 `storage/outputs/*` 最终文件，写入 `storage/manifests/*` 批量 manifest，更新 JSON metadata。

## 4. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/documents/service.py` | 编排转换、解析、Profile/模板加载、FormatCompiler、内部 QC、PDF 导出和最终文件登记 | `DocumentFormattingService.format_job` | 调整导出主链路、候选/最终文件策略、QC 放行策略 |
| `backend/app/documents/compiler.py` | Profile v2 到 DOCX 的确定性编译入口，统一 API、批量任务、脚本和测试调用 | `FormatCompiler`, `CompiledDocumentResult` | 新增格式规则、调整编译阶段、扩展支持能力 |
| `backend/app/documents/formatter.py` | 提供段落、样式、表格、题注和 OOXML 的底层格式化 helper | `format_docx_with_profile` 及内部 helper | 兼容旧 v1 formatter、抽取可复用格式化动作 |
| `backend/app/documents/template.py` | 读取模板 DOCX，应用固定页、正文 slot、页眉页脚继承和模板适配检查元数据 | `TemplateBinding`, `TemplateLoader` | 新增封面/声明/目录页模板能力、占位符规则 |
| `backend/app/documents/converter.py` | `.doc` 转 `.docx` 的 LibreOffice adapter | `convert_doc_to_docx` | 转换诊断、LibreOffice 环境适配 |
| `backend/app/documents/parser.py` | 校验和基础解析 DOCX | `parse_docx` | 扩展结构摘要、失败诊断 |
| `backend/app/documents/structure.py` | 识别段落角色和标题层级 | `classify_document`, `ParagraphRole` | 标题、摘要、目录、参考文献、题注识别规则 |
| `backend/app/documents/ooxml.py` | OOXML 层字段刷新、目录、编号、关系和文档健康辅助 | `enable_update_fields`, `inspect_ooxml_features` | 字段刷新、复杂 Word 结构检查 |
| `backend/app/documents/exporter.py` | 最终 DOCX 到 PDF 的 LibreOffice 导出 | `export_docx_to_pdf` | PDF 失败诊断、导出参数 |
| `backend/app/jobs/worker.py` | 执行 queued job 并写回状态、进度、输出和错误 | `process_placeholder_job`, `process_next_queued_job` | 队列化、异步 worker、任务状态变化 |
| `backend/app/api/jobs.py` | 单文档任务 HTTP API | `build_jobs_router`, `CreateJobRequest` | job 请求/响应契约变化 |
| `backend/app/api/batches.py` | 批量任务和 manifest API | `build_batches_router`, `DeliveryManifestItem` | 批量交付、manifest 字段、失败状态 |

## 5. 关键规则与实现细节

- Agent 不直接修改 DOCX；Agent 只能生成或解释 Profile v2，DOCX 修改必须经 `FormatCompiler`。
- `FormatCompiler` 是唯一权威导出入口；API、batch、CLI smoke 和测试都应调用同一编译路径。
- `format_docx_with_profile` 可以作为兼容层或底层 helper，但不能形成第二套独立导出链路。
- 模板和 Profile 分离：模板负责固定页面、页眉页脚骨架和内容 slot，Profile 负责格式规则，输入文档负责正文内容。
- 候选 DOCX 不直接暴露给用户；只有内部 QC 全部通过后的最终 DOCX/PDF 才写入 `output_file_ids`。
- 内部 QC 必须 fail closed：不支持、无法验证、自动修正后仍失败的规则，不能展示为合规完成。
- PDF 只从最终 DOCX 导出；如果 `SOFFICE_BIN` 缺失或导出失败，PDF 不得被标记为完成。
- `.doc` 输入依赖 LibreOffice 转换；转换失败时 job 进入失败状态并保留诊断消息。

## 6. 常见需求改动入口

- 新增 Profile v2 格式字段：通常先改 `backend/app/profiles/models.py`，再改 `backend/app/documents/compiler.py` 和内部 QC 检查项。
- 新增模板能力：通常改 `backend/app/documents/template.py`、`backend/app/documents/compiler.py`、相关 API 请求字段和模板适配测试。
- 调整最终下载条件：通常改 `backend/app/documents/service.py` 和 `backend/app/quality` 内部 QC 结果映射。
- 调整批量 manifest：通常改 `backend/app/api/batches.py`、`backend/app/models.py` 中的 `DeliveryManifestItem` 和前端 API 类型。
- 改 DOCX/PDF 环境诊断：通常改 `backend/app/documents/converter.py`、`backend/app/documents/exporter.py` 和 `DocumentFormattingService.format_job` 的错误映射。

## 7. 测试与验证

- 后端测试：`cd backend && uv run pytest`。
- 重点测试：`backend/tests/test_document_engine.py`、`backend/tests/test_document_formatting.py`、`backend/tests/test_document_worker.py`、`backend/tests/test_production_profile_pipeline.py`。
- 文档工具链 smoke：`codex-docx-inspect <output.docx>`、`codex-docx-to-pdf <output.docx> <output_dir>`、`codex-pdf-inspect <output.pdf>`。
- 手工验证：用格式要求文档生成 Profile v2，选择 Profile 和模板，上传待处理 Word，确认最终 DOCX/PDF 只在内部 QC 通过后开放下载。
