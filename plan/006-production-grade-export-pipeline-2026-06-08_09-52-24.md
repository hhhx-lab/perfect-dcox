---
mode: plan
change_id: add-production-export-pipeline
cwd: /Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范
task: 生产化一键全自动格式导出、下载与自动修复闭环
source_document: N/A
created_at: 2026-06-08T09:52:24+08:00
qualification_status: passed
---

# Plan: 生产化一键全自动格式导出闭环

## 背景与动机

当前 MVP 已经打通上传、Profile、DOCX 格式化、规则抽取、质量报告和用户确认式 fix-loop 入口，但距离“商业级一键全自动导出”还差生产化闭环。下一步要把产品入口重做成两个清晰的 Agent 入口：一个通过对话追问用户格式要求，一个通过上传格式文档自动分析规则；两条入口都沉淀为命名 Profile，再由用户选择 Profile 上传自己的 Word 文档，批量输出一份或多份规范化 DOCX/PDF。整个链路必须可验证：对声明支持的格式规则，导出前必须机器校验通过；对未支持或不可判定项，系统必须 fail closed，阻止“百分百合规”的误报。
<!-- 下游：proposal.md 的 motivation -->

## Goal

- 用户上传 `.doc/.docx` 报告并选择/生成格式 Profile 后，系统能一键自动完成排版、DOCX/PDF 导出、可下载交付、质量报告、自动修复重试和最终合规状态判定。
- 前端重做为商业级工作流界面，首屏直接呈现两个格式需求入口：`对话生成 Profile` 和 `上传格式文档生成 Profile`，并用清晰步骤引导用户完成 Profile 命名、保存、选择和批量规范化输出。
- 对话入口中，Agent 必须能主动发起追问，直到收集页面、字体、正文、标题、图表、公式、参考文献、页眉页脚、页码、输出格式等必要信息；随后总结所有格式需求并让用户确认。
- 文档入口中，Agent 必须分析用户上传的格式说明 `.doc/.docx`，抽取并总结所有格式需求，标注证据、置信度和不确定项，再让用户确认。
- 确认后的格式需求必须沉淀为可命名、可版本化、可复用的 Profile；用户可以在后续选择某个 Profile，上传一份或多份自己的 Word 文档，获得一份或多份规范化后的 Word/PDF 文件。
- 对系统声明支持的格式规则，最终导出前必须达到 100% 机器校验通过；无法判断、超出能力边界或需要人工确认的项目不得显示为合规。
- 最终交付必须包含可下载 DOCX、可下载 PDF、质量报告 JSON/Markdown、修复记录和原始/最终文件 lineage。
<!-- 下游：proposal.md 的 scope -->

## Non-goals

- 不承诺对任意未知学校模板、任意损坏 Word 文件或任意复杂语义要求无条件“百分百成功”；系统只能对声明支持范围内的规则给出强保证。
- 不自动改写论文语义、公式含义、参考文献真实性、查重结果、学术内容质量或作者写作风格。
- 不把 `unsupported`、低置信度 Agent 判断、PDF 无法抽取文本、复杂 Word 域代码无法更新等情况伪装为 `pass`。
- 不在生产化升级中引入硬编码 API Key、Token 或固定模型配置；模型和密钥必须继续由 `.env` 驱动。
- 不做只好看的 landing page；前端优化必须服务实际工作流，首页就是可操作的 Agent/Profile/文档处理界面。
<!-- 下游：proposal.md 的 scope -->

## 当前仓库事实

- 当前 README 说明项目已经实现基础平台、Profile、首版 DOCX 格式化、规则抽取、质量报告和 fix-plan 审阅控件：`README.md:3`。
- 当前 README 明确写着尚不包含文件下载接口、真实在线 LLM 调用实现或真正改写文件的二次修复 worker：`README.md:5`。
- 当前启动文档要求后端、前端和 worker 分别运行；worker 仍是手工执行示例，不是自动常驻队列：`README.md:32`、`README.md:49`。
- 当前 API 列表只有文件元数据读取，没有输出文件下载 endpoint；质量 fix-loop 确认接口当前只创建 lineage 记录，不直接改写输出文件：`README.md:90`、`README.md:109`。
- 当前 Agent 规则抽取默认在线 LLM provider 尚未实现真实网络调用，缺少模型配置时返回本地 MVP 错误：`README.md:123`。
- 当前质量报告会独立检查输出并按 `pass/fixed/warning/fail/unsupported` 分组，但 fix-plan 仍是 deterministic fallback，确认后不会生成新 job、新输出或 updated report：`README.md:126`、`README.md:133`。
- 当前文档引擎保留段落文本并应用页面、正文、标题、题注、公式、参考文献和基础表格边框规则，但不做复杂目录/域代码/图片位置/参考文献排序或下载接口：`README.md:137`、`README.md:140`。
- 后端 README 说明 document service 已有可选 PDF export 能力，但默认 worker 当前只记录 DOCX：`backend/README.md:39`、`backend/README.md:43`。
- 前端 README 说明质量报告 UI 只在 job 有输出和 profile 引用后创建报告，fix-plan UI 展示解释和 lineage，当前确认记录 lineage only：`frontend/README.md:48`、`frontend/README.md:62`。
- 用户反馈当前前端页面“太丑”，并要求产品入口调整为两种 Agent 入口：对话追问生成格式需求、上传格式文档分析格式需求；随后沉淀为命名 Profile，用户选择 Profile 后上传 Word 文档并获得一份或多份规范化输出：未验证；补证路径为本 plan 对话输入。
- 当前 OpenSpec `openspec/specs/` 没有归档 specs，活跃 changes 均可 strict validate；补证路径是后续生产化前先归档已完成 changes 或建立 baseline specs。
- 当前核心记录模型包括 `FileRecord`、`JobRecord`、`ProfileExtractionRecord`、`QualityReport`、`FixPlan`、`FixLoopRecord`，其中 `JobStatus` 仍只有 `queued/running/completed/failed`：`backend/app/models.py:9`、`backend/app/models.py:19`、`backend/app/models.py:42`、`backend/app/models.py:88`、`backend/app/models.py:122`、`backend/app/models.py:139`。
- 当前 JSON repository 已持久化 `files/jobs/profiles/profile_versions/profile_extractions/quality_reports/quality_fix_loops`，但没有 profile requirement sessions、batch jobs、download manifests 或 pipeline run logs：`backend/app/storage/repository.py:19`。
- 当前文档格式化服务 `DocumentFormattingService.format_job(...)` 已支持 `include_pdf` 参数，但 worker 默认没有传入 PDF 导出，也没有质量门或修复重试：`backend/app/documents/service.py:22`、`backend/app/jobs/worker.py:17`。
- 当前 formatter 基于 `python-docx` 直接应用页面、正文、标题、题注、公式段落、参考文献段落和三线表边框，但没有复杂域代码刷新、页码、目录、图片锚定、脚注尾注等生产化能力：`backend/app/documents/formatter.py:18`。
- 当前 `ProfileExtractionService` 支持自然语言和文档来源，但 provider 接口是一次性 `extract(source_text, source_meta)`，没有多轮对话 session、追问状态、需求摘要确认或 Profile 命名流程：`backend/app/agents/extraction.py:31`、`backend/app/agents/extraction.py:117`。
- 当前前端 API client 已有 `FileRecord/JobRecord/ProfileExtractionRecord/QualityReport/FixPlan/FixLoopRecord` 类型和基础请求方法，但没有 batch job、download、requirement conversation session、profile requirement summary 等类型：`frontend/src/api/client.ts:8`、`frontend/src/api/client.ts:18`、`frontend/src/api/client.ts:116`。
<!-- 下游：specs baseline，proposal.md 的 context -->

## 改动边界

- 新增输出下载契约：支持 DOCX、PDF、质量报告 JSON/Markdown、修复记录 manifest 的下载 API 和前端下载控件。
- 重构前端信息架构和视觉系统：从当前模块堆叠式工作台升级为面向论文格式规范化的四步任务流：`获取格式需求 -> 生成/确认 Profile -> 选择 Profile 与上传文档 -> 获取规范化输出与质检报告`。
- 新增对话式 Agent 入口：支持多轮问答、缺失字段追问、格式需求摘要、证据/假设标注、用户确认和一键生成命名 Profile。
- 新增格式文档分析入口：支持上传规则文档、抽取格式需求、显示来源证据、不确定项和冲突项，用户确认后生成命名 Profile。
- 新增 Profile 命名与管理体验：保存 Profile 前必须填写名称、用途/学校/模板说明和版本；保存后进入可选择 Profile 列表，供后续一键格式化复用。
- 新增批量文档处理体验：用户选择一个 Profile 后，可上传一份或多份 Word 文档，系统为每份文档创建独立任务，并在同一输出区展示 DOCX/PDF/report 下载和质量状态。
- 新增自动 worker/队列闭环：任务创建后无需手工命令，自动执行排版、PDF 导出、质量检查、fix-plan、二次修复和状态更新。
- 升级 fix-loop：确认后的白名单格式动作必须真正作用到输出文件，生成新 job、新输出、新 quality report，并保留原始/中间/最终 lineage。
- 升级质量门：每次导出和每轮修复后自动运行 DOCX/PDF 质量检查；只有无 `warning/fail/unsupported` 且所有声明支持项通过时，前端才显示最终合规。
- 扩展复杂 DOCX 支持：覆盖 section breaks、页眉页脚、页码、目录/域代码刷新策略、图片锚定、表格跨页、题注编号、脚注尾注、列表编号、公式 OMML/LaTeX 残留、参考文献段落格式等复杂场景。
- 升级 Profile/规则抽取：接入真实 LLM provider，保留 deterministic fallback，要求输出 evidence、confidence、schema validation 和人工确认后才保存为 active profile。
- 增加生产级状态和可观测性：任务状态区分 `queued/running/completed/quality_failed/manual_review_required/export_failed/failed`，并记录每步日志、错误原因、重试次数、耗时和产物路径。
- 增加回归样本文档库和端到端测试：构造多种复杂 Word 输入和模板规则，验证导出、下载、PDF 可读性、Office Math、质量报告和自动修复闭环。
- 可能需要新增或修改 OpenSpec specs 领域：`file-downloads`、`production-format-pipeline`、`quality-gated-export`、`automatic-fix-worker`、`complex-docx-formatting`、`llm-profile-extraction`。
<!-- 下游：proposal.md scope，design.md scope，spec deltas 范围 -->

## 技术设计补充

### 目标架构

- 前端层：React + TypeScript 保持 Vite 架构，重组为 `RequirementIntake`、`ProfileBuilder`、`ProfileLibrary`、`DocumentBatchUpload`、`ProcessingDashboard`、`DeliveryPanel` 六个高内聚区域。
- API 层：FastAPI 继续使用 `/api` prefix，新增 requirement session、batch job、download、pipeline run、fix-loop execution endpoint；现有 file/profile/job/quality API 保持向后兼容。
- 编排层：新增 production pipeline orchestrator，统一驱动 `profile extraction -> profile save -> format job -> PDF export -> quality report -> fix loop -> delivery manifest`，替代手工 worker 命令。
- 文档处理层：扩展 `app/documents/`，把 formatter 拆成 page/header-footer/paragraph/headings/tables/captions/equations/references/fields/export 子模块，避免单文件继续膨胀。
- Agent 层：把一次性 extraction provider 升级为 requirement session provider，支持多轮追问、文档证据抽取、结构化摘要、Profile draft 生成和 confidence/evidence 校验。
- 存储层：短期继续 JSON repository，生产迁移目标预留 PostgreSQL/SQLite schema；文件仍落 `storage/files`、`storage/outputs`、`storage/reports`、`storage/manifests`。

### 数据模型扩展

- `RequirementSession`
  - 字段：`session_id`、`source_type`、`status`、`messages`、`missing_fields`、`requirement_summary`、`profile_draft`、`evidence`、`uncertain_items`、`confirmed_at`、`created_at`、`updated_at`。
  - 状态：`collecting`、`needs_user_answer`、`ready_for_confirmation`、`confirmed`、`failed`。
  - 作用：承载两种入口的共同状态，避免自然语言入口和文档入口分裂为两套流程。
- `RequirementSummary`
  - 字段：`page`、`fonts`、`body`、`headings`、`abstract`、`tables`、`figures`、`equations`、`references`、`headers_footers`、`page_numbers`、`outputs`、`unsupported_or_uncertain_rules`。
  - 每个规则项包含 `value`、`source`、`confidence`、`evidence_ids`、`needs_confirmation`。
- `ProfileCreationDraft`
  - 字段：`profile_id_candidate`、`name`、`description`、`version`、`source_session_id`、`format_profile`、`validation_errors`。
  - 规则：保存前必须 `name/version` 非空，`format_profile` 通过既有 `FormatProfile` schema。
- `BatchFormatRun`
  - 字段：`batch_id`、`profile_id`、`profile_version`、`input_file_ids`、`job_ids`、`status`、`delivery_manifest_id`、`created_at`、`updated_at`。
  - 状态：`queued`、`running`、`partially_completed`、`completed`、`quality_failed`、`manual_review_required`、`failed`。
- `DeliveryManifest`
  - 字段：`manifest_id`、`batch_id`、`items`、`created_at`。
  - item 字段：`input_file_id`、`final_docx_file_id`、`final_pdf_file_id`、`quality_report_id`、`fix_loop_ids`、`download_urls`、`delivery_status`。
- `PipelineRunLog`
  - 字段：`run_id`、`job_id/batch_id`、`step`、`status`、`started_at`、`finished_at`、`duration_ms`、`message`、`artifact_refs`。
  - 作用：让前端展示每份文档卡在哪一步，便于 debug 和产品信任。

### API 契约草案

- `POST /api/requirement-sessions`
  - payload: `{ source_type: "conversation" | "document", natural_language?: string, file_id?: string }`
  - response: `RequirementSession`
- `POST /api/requirement-sessions/{session_id}/messages`
  - payload: `{ role: "user", content: string }`
  - response: `RequirementSession`
  - 行为：Agent 根据缺失字段追问或生成 `requirement_summary`。
- `POST /api/requirement-sessions/{session_id}/analyze-document`
  - payload: `{ file_id: string }`
  - response: `RequirementSession`
  - 行为：从格式文档抽取规则、证据、不确定项和冲突项。
- `POST /api/requirement-sessions/{session_id}/confirm`
  - payload: `{ profile_name: string, profile_description?: string, profile_version: string, accepted_summary: RequirementSummary }`
  - response: `FormatProfile`
  - 行为：生成并保存命名 Profile，返回可选择的 profile version。
- `POST /api/batches`
  - payload: `{ profile_id: string, profile_version: string, input_file_ids: string[], output_formats: ["docx","pdf"], auto_fix: boolean }`
  - response: `BatchFormatRun`
- `GET /api/batches/{batch_id}`
  - response: batch + jobs + delivery manifest + quality summaries。
- `GET /api/files/{file_id}/download`
  - response: binary stream with `Content-Disposition` and repository MIME。
- `GET /api/quality-reports/{report_id}/download?format=json|markdown`
  - response: JSON 或 Markdown report artifact。
- `POST /api/fix-loops/{fix_loop_id}/execute`
  - response: updated `FixLoopRecord`，执行白名单动作并更新 report lineage。

### Agent 需求收集状态机

- 初始输入：
  - 对话入口：用户自然语言描述目标模板、学校、期刊或格式要求。
  - 文档入口：用户上传格式说明 `.doc/.docx`，系统抽取文本和表格规则。
- 字段覆盖：
  - 必填最小集：页面尺寸/边距、正文中文/英文字体、正文字号、行距、首行缩进、标题层级、图表题注、参考文献、输出格式。
  - 扩展集：页眉页脚、页码位置、目录、公式编号、表格边框、封面、摘要、关键词、脚注尾注。
- 追问策略：
  - 若必填最小集缺失，session 状态为 `needs_user_answer`，Agent 一次最多问 3 个高价值问题。
  - 若存在冲突规则，Agent 必须展示冲突项并要求用户选择，不得自行默认。
  - 若只缺扩展集，Agent 可标注默认值/unsupported，进入 `ready_for_confirmation`。
- 输出约束：
  - Agent 输出必须是结构化 JSON，先通过 `RequirementSummary` schema，再转换为 `FormatProfile` schema。
  - 每个非默认规则必须至少有一条 evidence 或 user-confirmed source。

### DOCX/PDF 生产化处理路线

- DOCX 输入：
  - `.docx` 直接进入 parser；`.doc` 继续通过 LibreOffice 转换，并记录 conversion log。
  - parser 产出 document map：sections、paragraphs、tables、images、headers/footers、styles、fields、footnotes、equations、references candidates。
- 格式化：
  - 按 profile 应用 page/body/heading/table/caption/equation/reference/header/footer/page number rules。
  - 对复杂对象采用保守策略：不破坏内容，无法安全改写则产生 `unsupported` 或 `manual_review_required` issue。
- PDF：
  - 格式化后默认导出 PDF；导出失败时 job 状态进入 `export_failed`。
  - PDF 检查使用 `codex-pdf-inspect` 等价逻辑或内部 parser，至少检查页数、文本可抽取、空白页风险。
- 下载：
  - 仅 repository 中存在且 sha256 匹配的文件可下载。
  - 下载响应必须带原始友好文件名，例如 `<input-stem>-<profile-name>-formatted.docx`。

### 自动修复闭环

- 质量报告触发后按 issue 生成 fix-plan。
- 可自动修复动作映射：
  - `docx.page.margins -> reapply_profile_formatting`
  - `docx.body.style -> apply_body_paragraph_style`
  - `docx.heading.style -> apply_heading_style`
  - `docx.table.borders -> apply_table_borders`
  - 后续新增 `apply_page_numbers`、`apply_header_footer`、`refresh_fields` 必须单独白名单和测试。
- 执行流程：
  - 选择 issue -> validate fix-plan -> copy 原始输出到 work dir -> 应用白名单动作 -> 保存新 DOCX -> 导出 PDF -> 生成新 quality report -> 更新 `FixLoopRecord`。
- 收敛规则：
  - 默认最多 2 轮自动修复。
  - 同一 `check_key + location` 连续失败则标记 `manual_review_required`。
  - 任意语义/内容类 action 直接拒绝。

### 前端结构与视觉方向

- 页面布局：
  - 左侧或顶部保留轻量导航，但主区域必须是四步 workflow，不再以“文件上传/Profile/规则抽取/任务/输出”平铺为主。
  - Step 1：`获取格式需求`，segmented control 切换 `对话生成 Profile` / `上传格式文档生成 Profile`。
  - Step 2：`确认并命名 Profile`，展示可编辑 Requirement Summary、证据、不确定项、Profile 名称/版本表单。
  - Step 3：`选择 Profile 并上传文档`，Profile selector + multi-file upload queue。
  - Step 4：`输出与质检`，output table 展示每份文档状态、DOCX/PDF/report 下载、remaining issue、fix attempts。
- 组件建议：
  - `RequirementChatPanel`
  - `RuleDocumentAnalyzer`
  - `RequirementSummaryEditor`
  - `ProfileNamingForm`
  - `ProfileSelector`
  - `BatchUploadQueue`
  - `ProcessingTimeline`
  - `DeliveryTable`
  - `QualityGateBadge`
  - `FixLoopDrawer`
- 视觉要求：
  - 面向论文/办公生产力工具，整体应安静、专业、信息密度适中，不做夸张 hero 和装饰卡片。
  - 色彩避免单一米色/深绿堆叠；使用中性色底、清晰边界、少量状态色区分 success/warning/fail/unsupported。
  - 所有主要动作必须 icon + 明确标签，例如上传、保存 Profile、开始处理、下载、查看报告、执行修复。
  - 移动端采用单列 stepper；桌面端允许 summary/editor 与 evidence 并排。

### 存储与迁移策略

- 本地阶段：
  - `storage/files`：上传原件。
  - `storage/outputs`：格式化 DOCX/PDF。
  - `storage/reports`：Markdown/JSON 质量报告产物。
  - `storage/manifests`：delivery manifest。
  - `storage/work`：中间文件，可清理。
- JSON repository 新增 collections：
  - `requirement_sessions`
  - `batch_format_runs`
  - `delivery_manifests`
  - `pipeline_run_logs`
- 生产数据库预留：
  - 每个 collection 对应 table。
  - 文件仍可走对象存储，repository 只保存 uri、sha256、mime、size、owner。

### 安全与权限

- 上传限制：
  - 只允许 `.doc/.docx` 格式需求文档和待处理文档。
  - 限制单文件大小、批量数量和总大小，超限给出可读错误。
- 下载限制：
  - 只能下载 repository 中登记的 file/report/manifest。
  - 路径不能由用户传入，防止 path traversal。
- Agent 限制：
  - 真实 LLM 输出必须经过 JSON schema validation。
  - Profile 保存必须经过 `FormatProfile` validation。
  - Fix action 必须白名单，默认 require confirmation。

### 测试矩阵

- Unit：
  - RequirementSummary schema、ProfileDraft 转换、download filename、fix action whitelist。
- Backend API：
  - requirement session conversation/document 两入口。
  - confirm session -> saved profile。
  - batch create/status/download。
  - fix-loop execute lineage。
- Document fixtures：
  - simple thesis。
  - multi-section。
  - header/footer/page number。
  - table-heavy。
  - images/captions。
  - equations/raw LaTeX。
  - references/footnotes。
- Frontend：
  - build。
  - Playwright desktop/mobile smoke。
  - 两入口流程、Profile 命名、multi-file queue、download buttons、quality warning state。
- End-to-end：
  - 对话入口完整闭环。
  - 文档入口完整闭环。
  - 失败/unsupported 阻断“全部合规”。
  - secret scan。

## 约束

- “百分百成立”只能定义为：对声明支持的格式规则和受支持输入类型，最终导出前必须 100% 校验通过；超出范围必须清晰标注并阻断合规声明。
- 任何语义内容、公式含义、参考文献真实性、正文改写都必须默认禁止自动修改，除非后续另有明确人工确认和审计机制。
- 生产化流程必须 fail closed：质量报告缺失、PDF 导出失败、下载文件缺失、文本不可抽取、仍有 unsupported 时，不得显示最终合规。
- 环境变量继续通过 `.env` 管理；不得硬编码 LLM key、token、模型名、本地代理或用户私有路径。
- Python 依赖继续使用项目 `uv` 环境；不得使用 `sudo pip` 或混用系统/Homebrew Python。
- PDF 导出继续优先使用本机 LibreOffice/soffice；正式验证需同时用 `codex-docx-inspect`、`codex-docx-to-pdf`、`codex-pdf-inspect` 做交付 smoke。
- 前端需要保持现有工作台风格，不新增营销页；首屏仍应是实际可用的文档处理工作台。
- 前端视觉优化必须避免当前工程面板感，采用清晰的任务流布局、强状态反馈、可扫描输出表格、明确的 primary action、空状态/错误状态/加载状态；移动端和桌面端都不能出现文本溢出或控件重叠。
- 前端控件语义要清楚：用 tabs/segmented control 表示两种 Agent 入口，用 stepper 表示四步流程，用可编辑摘要确认格式需求，用 Profile selector 选择沉淀模板，用 output table 展示多文档输出。
<!-- 下游：design.md 的 constraints -->

## 验收标准

1. 首页首屏展示实际可用的四步任务流和两个 Agent 入口，不再以松散模块卡片为主；用户无需理解后端 API 即可知道下一步该做什么。
2. 对话式入口中，用户输入自然语言格式目标后，Agent 能主动提出缺失字段问题；信息足够后生成“格式需求摘要”，包含页面、字体、段落、标题、图表、公式、参考文献、页眉页脚、页码和输出格式要求。
3. 格式文档入口中，用户上传格式规则 `.doc/.docx` 后，Agent 能展示抽取出的格式需求、来源证据、置信度、不确定项和冲突项。
4. 两种入口生成的格式需求都必须经过用户确认；确认后用户必须能填写 Profile 名称、说明和版本，并保存为可复用 Profile。
5. Profile 列表中能看到用户创建的命名 Profile；选择某个 Profile 后，用户可以上传一份或多份 Word 文档进入规范化任务。
6. 用户上传 `.docx` 并选择现有 active profile 后，点击一次即可自动完成排版、PDF 导出、质量报告和最终交付状态更新；用户无需手工运行 worker 命令。
7. 用户可以在前端直接下载最终 DOCX、最终 PDF、质量报告 JSON/Markdown 和修复 manifest；下载接口返回正确 MIME type、文件名和内容长度。
8. 多文档批处理时，每个输入文档有独立状态、输出文件、质量报告和错误信息；单个失败不阻塞其他文档查看已完成输出。
9. 如果最终 DOCX/PDF 的声明支持项全部通过，前端显示“可交付 / 全部支持项通过”，并展示质量报告 id、最终输出 file_id、修复轮次和通过时间。
10. 如果仍有 `warning/fail/unsupported/manual_review_required`，前端不得显示“全部合规”，必须展示剩余问题摘要、定位、建议动作和是否需要人工复核。
11. 确认 fix-plan 后，后端必须真正执行白名单修复动作，生成新输出文件、新 quality report，并把 `FixLoopRecord.updated_report_id`、`new_job_id`、`new_output_file_ids` 写入 repository。
12. 自动修复循环必须有最大轮次和收敛判断；同一 issue 连续无法修复时进入 manual review，不得无限重试。
13. DOCX 复杂样例至少覆盖：多 section、页眉页脚、页码、目录/域代码、图片、跨页表格、题注编号、脚注尾注、列表编号、公式和参考文献段落；每类样例都有可重复测试。
14. PDF 导出必须通过打开性、页数大于 0、文本可抽取、明显空白页检查；失败时任务进入 `export_failed` 或 `quality_failed`，不得提供“合规”状态。
15. 真实 LLM profile extraction provider 可通过 `.env` 配置启用；缺配置时系统降级为可读错误或 deterministic provider，测试不依赖真实 key。
16. 端到端测试覆盖两条入口：“对话 -> 追问 -> 需求摘要 -> 命名 Profile -> 上传文档 -> 输出”和“上传格式文档 -> 规则抽取 -> 命名 Profile -> 上传文档 -> 输出”。
17. 前端桌面和移动视口通过 Playwright 截图检查，关键按钮、摘要、Profile selector、上传区、输出表格、质量状态不重叠、不溢出，视觉风格达到可对外演示水准。
18. Secret scan 对后端、前端、文档和 `.env.example` 无硬编码 key/token 命中。
19. 所有新增能力通过 `openspec validate add-production-export-pipeline --strict --no-interactive`、后端测试、前端 build 和文档工具链 smoke。
<!-- 下游：spec deltas 的 Scenarios，tasks.md 的 verification -->

## 验证方式

- `openspec validate add-production-export-pipeline --strict --no-interactive`
- `cd backend && uv run pytest -q`
- `cd frontend && npm run build`
- 使用固定样本文档执行端到端 smoke：上传样例 DOCX，创建 profile job，等待 worker 自动完成，下载 DOCX/PDF/report，并确认质量报告最终无 remaining issue。
- 使用对话入口 smoke：输入一段自然语言格式要求，确认 Agent 追问缺失字段，完成后生成格式需求摘要并保存为命名 Profile。
- 使用格式文档入口 smoke：上传格式规则 DOCX，确认 Agent 抽取需求、展示 evidence/uncertain items，并保存为命名 Profile。
- 使用批处理 smoke：选择一个 Profile，上传两份 Word 文档，确认两个任务独立完成或独立展示失败原因。
- 使用 Playwright 检查桌面与移动视口：前端四步流程、两个入口、Profile 命名、文件上传、输出表格和质量报告均可见且无明显布局问题。
- 对最终 DOCX 执行 `codex-docx-inspect storage/outputs/<file_id>.docx`，检查段落/表格数量、Office Math、LaTeX 残留和关键格式信息。
- 对最终 PDF 执行 `codex-pdf-inspect storage/outputs/<file_id>.pdf`，检查页数、文本可抽取性和空白页风险。
- 对下载接口执行 HTTP smoke，验证状态码、MIME type、文件名、sha256 和 repository `FileRecord` 一致。
- 对自动修复闭环执行 regression：人为制造页边距、正文行距、标题字体、表格边框、LaTeX 残留等错误，确认修复后报告更新，无法修复项进入 manual review。
- 执行 hardcoded secret scan：
  `rg -n "(^|[^A-Za-z])sk-[A-Za-z0-9]{20,}|api[_-]?key\\s*=\\s*['\\\"][^'\\\"]+|LLM_API_KEY\\s*=\\s*[^\\s#]+|Bearer\\s+[A-Za-z0-9._-]{20,}" backend/app backend/tests frontend/src .env.example README.md backend/README.md frontend/README.md || true`
<!-- 下游：tasks.md 的验证步骤 -->

## 迁移 / 回滚 / 降级

- 当前 JSON repository 可继续作为本地 MVP 存储；若生产化引入数据库/队列，需要迁移 `files/jobs/profiles/profile_extractions/quality_reports/fix_loops`，并提供从 `storage/metadata.json` 导入的迁移脚本。
- 下载接口回滚时保留已生成输出文件和 metadata，仅移除新 endpoint 和前端下载控件。
- 自动 worker/队列回滚时保留手工 worker 命令路径，任务可以降级为 queued/manual processing。
- 真实 LLM provider 失败时降级为 deterministic provider 或配置错误提示；不得影响手工 Profile 编辑、已有 profile 排版和质量报告查看。
- 自动修复失败时保留原始输出和原始质量报告，新增失败 fix-loop 记录，不覆盖原文件。
- 若 PDF 导出失败，DOCX 输出可以保留但最终交付状态必须是 `export_failed` 或 `quality_failed`，不能显示完全合规。
<!-- 下游：proposal.md 的 risks，spec deltas 的 REMOVED/MODIFIED -->

## 参考

- `README.md:3`
- `README.md:5`
- `README.md:32`
- `README.md:49`
- `README.md:90`
- `README.md:109`
- `README.md:123`
- `README.md:126`
- `README.md:133`
- `README.md:137`
- `README.md:140`
- `backend/README.md:39`
- `backend/README.md:43`
- `frontend/README.md:48`
- `frontend/README.md:62`
- 用户补充需求：前端页面需要生产化视觉优化；产品入口为对话式 Agent 和格式文档分析 Agent，二者都总结格式需求并沉淀为命名 Profile，用户选择 Profile 后上传 Word 文档获得一份或多份规范化输出。
