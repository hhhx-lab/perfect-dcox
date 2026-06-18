# 前端工作台

## 1. 模块职责与边界

本模块承载浏览器端四步工作台：创建或选择 Profile、绑定可选模板、上传待处理 Word 文档、导出并下载内部校验通过的 DOCX/PDF。当前实现集中在 `frontend/src/App.tsx`，API 类型和请求封装集中在 `frontend/src/api/client.ts`。前端不直接生成 DOCX/PDF，不执行 LLM，不展示用户可下载质量报告。

## 2. 核心实现链路

1. `App` 首屏加载 `/api/health` 和 `/api/profiles`，在侧栏显示 LLM/PDF 配置状态。
2. Profile 创建区提供三种入口：对话 Agent、上传格式文档、可视化编辑。三种入口最终都进入同一 `FormatProfile` v2 draft。
3. 对话和格式文档入口调用 `POST /api/requirement-sessions`；补充消息调用 `POST /api/requirement-sessions/{session_id}/messages`；确认保存调用 `POST /api/requirement-sessions/{session_id}/confirm`。
4. 可视化入口编辑当前 Profile draft 的命名、页面、页边距、文档网格、正文中英文字体、字号、字色、首行缩进、段距、标题 1-3 级、目录、序号、页眉页脚、页码、表格、插图、摘要、公式、参考文献、计量/计价单位、模板绑定和内部校验字段，并通过 Profile API 保存。
5. 模板区上传 `.doc/.docx` 模板，保存 `template_file_id`，导出时传给 job/batch API。
6. 待处理文档区上传一份或多份 `.doc/.docx`。
7. 导出区调用 `POST /api/jobs` 或 `POST /api/batches`，传入 `profile_id`、`profile_version`、`template_file_id` 和 `output_formats`。
8. 最终下载只展示后端返回的 `output_file_ids` 或 batch item final file ids；失败时展示 `error_message` 或 `failure_reason`。

## 3. 输入、输出与状态

- 输入：用户自然语言规则、格式要求 `.doc/.docx`、模板 `.doc/.docx`、待处理 `.doc/.docx`、Profile 表单字段、输出格式勾选。
- 输出：Profile 保存请求、文件上传请求、job/batch 创建请求、最终下载链接。
- 状态：`health`、`profiles`、`selectedProfile`、`profileDraft`、`requirementSession`、`templateFileRecord`、`inputFileRecords`、`job`、`batchRun`、`outputFiles`。
- 副作用：通过后端 API 写入 metadata 和文件；浏览器只负责展示和下载。

## 4. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `frontend/src/App.tsx` | 四步工作台 UI 和状态编排 | `App`, `createRequirementSession`, `uploadRuleAndAnalyze`, `saveVisualProfile`, `createJob`, `createBatch` | 调整主流程、页面布局、导出状态 |
| `frontend/src/api/client.ts` | API 类型、请求封装和下载 URL 拼接 | `apiClient`, `FormatProfile`, `JobRecord`, `BatchFormatRun` | 后端 API 契约变化、Profile v2 字段 |
| `frontend/src/styles.css` | 工作台视觉样式和响应式布局 | CSS classes | UI 视觉优化、移动端适配 |
| `frontend/src/main.tsx` | React 应用挂载入口 | `createRoot` | 应用壳层变化 |

## 5. 关键规则与实现细节

- 主流程不显示质量报告下载或 fix-loop 操作；内部 QC 结果只通过导出状态、最终文件和失败原因体现。
- PDF 勾选受后端 `soffice_configured` 控制；没有 LibreOffice 时前端默认不请求 PDF。
- 批量 item 的 `quality_report_id` 和 `fix_loop_ids` 作为兼容字段存在，但主 UI 不渲染它们。
- Profile v2 的 evidence、missing、unsupported 会在 Agent 结果区展示摘要，保存后仍随 Profile draft 传递。
- 可视化编辑器写回同一个 Profile v2 draft，不维护独立的前端私有格式；旧 profile 状态进入编辑器时会补齐 v2 默认字段。
- 表格编辑区显式配置表名位置、中外文对照、三线表、跨页表头和表注；插图编辑区显式配置图名位置、中外文对照、文中插入方式以及半栏/通栏图宽限制。
- 下载 URL 由 `apiClient.downloadFileUrl` 拼接，权限和文件存在性由后端判断。

## 6. 常见需求改动入口

- 新增 Profile 字段：同步改 `api/client.ts` 的 `FormatProfile` 类型和 `App.tsx` 可视化编辑区。
- 新增导出参数：改 `api/client.ts` 的 `createJob/createBatch` payload 和导出区控件。
- 调整页面视觉：改 `styles.css`，保持四步主流程不变。

## 7. 测试与验证

- 前端构建：`cd frontend && npm run build`。
- 浏览器 smoke：对话入口、格式文档入口、可视化编辑、模板上传、待处理文档上传、单文件导出、批量导出、最终 DOCX/PDF 下载。
