# 内部 QC 交付门

## 1. 模块职责与边界

本模块负责 DOCX/PDF 的内部校验、失败原因归纳和安全自动修正。主导出流通过 `InternalDeliveryGateService` 检查候选 DOCX 和可选 PDF，只有全部通过后文档导出引擎才登记最终文件。历史 `quality_reports` API 仍保留给兼容和调试场景，但不再作为用户主流程产物。

本模块不负责首次格式化，不抽取格式规则，也不向用户承诺 schema 或引擎无法验证的规则已经合规。

## 2. 核心实现链路

### 内部交付门

1. `backend/app/documents/service.py` 生成候选 DOCX 后调用 `backend/app/quality/delivery_gate.py:InternalDeliveryGateService.validate_docx`。
2. `validate_docx` 先检查 Profile 中的 `unsupported_rules`；如果配置为 fail-closed 且存在不支持规则，直接返回失败。
3. `inspect_docx_quality` 检查页面、页边距、页眉页脚、正文/标题、表格、题注、字段、TOC、分节、脚注尾注、图片、编号和原始 LaTeX 残留。
4. 如果剩余问题全为可安全重套格式的类型，内部 gate 可调用 `format_docx_with_profile` 生成修正候选并重跑检查。
5. DOCX 通过后，如请求 PDF，导出服务生成 PDF 并用 `validate_pdf` 检查 envelope、页数、文本可抽取和明显空白页。
6. gate 结果以 `delivery_gate_summary` 写回 job/batch item；失败只返回简短原因，不产生用户下载报告。

### 兼容质量报告链路

1. `backend/app/api/quality_reports.py` 仍可按输出文件创建 `QualityReport`。
2. `backend/app/quality/service.py` 汇总 `QualityIssue` 并持久化报告。
3. `fix_planning.py` 和 `fix_execution.py` 仍支持确认式白名单修复，用于调试或兼容旧流程。

## 3. 输入、输出与状态

- 输入：候选 DOCX、可选 PDF、`FormatProfile`、输出 FileRecord。
- 输出：内部 `InternalDeliveryGateResult`、兼容 `QualityReport`、兼容 `FixLoopRecord`。
- 状态：job 的 `delivery_gate_summary`、metadata 中兼容报告和修复记录。
- 副作用：内部自动修正时会在工作目录生成 gate-fixed DOCX；兼容 API 会写入 report/fix-loop metadata。

## 4. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/quality/delivery_gate.py` | 内部 fail-closed 放行门、自动安全修正和简短失败原因 | `InternalDeliveryGateService`, `InternalDeliveryGateResult` | 调整最终下载放行规则 |
| `backend/app/quality/inspection.py` | DOCX/PDF 检查器 | `inspect_docx_quality`, `inspect_pdf_quality` | 新增格式检查、模板适配检查 |
| `backend/app/quality/service.py` | 兼容质量报告服务 | `QualityReportService` | 调试/兼容报告 |
| `backend/app/quality/fix_planning.py` | 兼容白名单修复计划 | `FixPlanService`, `validate_fix_plan` | 扩展安全修正动作 |
| `backend/app/quality/fix_execution.py` | 兼容修复执行 | `FixLoopExecutionService` | 调整旧 fix-loop 行为 |
| `backend/app/api/quality_reports.py` | 兼容质量报告 API | `build_quality_reports_router` | 保留或下线旧接口 |

## 5. 关键规则与实现细节

- `QualitySummary.remaining_issue_count` 统计 warning/fail/unsupported；只要不为 0，不能放行最终交付。
- `unsupported_rules` 在 `delivery_gate.fail_on_unsupported_rules=true` 时直接阻断导出。
- 内部自动修正只允许重套 Profile 这类格式动作，不做语义内容改写。
- PDF 只有在最终 DOCX 已通过后才导出和检查。
- 候选 DOCX 或 gate-fixed DOCX 不写入最终 `output_file_ids`，除非 gate 通过。

## 6. 常见需求改动入口

- 新增检查项：改 `inspection.py`，必要时在 `delivery_gate.py` 中定义失败摘要。
- 调整放行策略：改 `DeliveryGateSettings` 和 `InternalDeliveryGateService`。
- 调整兼容报告：改 `service.py` 和 `api/quality_reports.py`。

## 7. 测试与验证

- 相关测试：`backend/tests/test_quality_reports.py`、`backend/tests/test_quality_reports_api.py`、`backend/tests/test_document_worker.py`、`backend/tests/test_production_profile_pipeline.py`。
- 后端测试命令：`cd backend && uv run pytest`。
- 手工验证：生成候选 DOCX 后确认只有通过内部 QC 的最终 DOCX/PDF 可下载。
