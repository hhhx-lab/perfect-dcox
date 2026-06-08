# Word Format Agent

Word Format Agent 是一个前后端分离的 Word 论文格式规范化工作台。当前仓库已实现基础平台、版本化格式 Profile、首版 DOCX/PDF 格式化引擎、双入口 Agent 需求会话、批量交付、结构化质量报告和用户确认的修复执行闭环：文件上传、文件下载、文件元数据、带 profile 的排版任务、内置 ECNU 示例 profile、Profile API、结构化编辑器、YAML 导入/导出、DOC/DOCX 输入处理、DOCX/PDF 输出登记、前端四步工作流、requirement session API、quality report 下载、batch delivery manifest 和 Agent fix-plan 执行控件。

当前阶段已支持基础页面尺寸/方向、页边距、正文/标题/题注/参考文献样式、基础三线表、基础页眉文字、页脚 PAGE 页码字段和 Word 字段刷新策略的格式化、质检与白名单修复；复杂目录域、分节、多图表、脚注尾注、浮动图片、编号列表和 PDF 文本可抽取性会进入独立质量门，能机器确认的才通过，不能机器确认的会保留为 `warning/fail/unsupported`，不会伪装成合规。带 `profile_id + profile_version` 的任务会调用文档引擎生成规范化 DOCX，并在 `SOFFICE_BIN` 可用时同步导出 PDF；未带 profile 的任务仍走兼容的 placeholder 完成路径。需求会话必须配置可用的 `LLM_API_KEY + LLM_MODEL`，并通过 OpenAI-compatible provider 完成 Agent 分析；LLM 未配置、超时或返回非法结构时会直接报错，不会用本地规则伪装成 Agent 分析成功。本地确定性规则只作为 LLM 成功后的真实文档 guard，用来覆盖文档中明确写出的 A4、页边距、字体、字号、页码等硬规则，防止模型跑偏。批量任务默认执行 `format -> quality report -> safe auto-fix -> updated quality report -> delivery manifest`；只要最终仍有 warning/fail/unsupported，job/batch 会以 `quality_failed` 或 `manual_review_required` 形式 fail closed，不会显示“百分百合规”。

## 目录

```text
backend/     FastAPI 后端、文件存储、Profile API、任务 API、DOCX 格式化 worker、规则抽取 API、质量报告 API
frontend/    React + TypeScript + Vite 工作台、Profile 编辑器、规则抽取面板、任务输出面板和质量报告面板
docs/        产品方案
openspec/    OpenSpec change artifacts
plan/        MyPlan 需求质量门产物
profiles/    内置 profile YAML seed，例如 ecnu_thesis.yaml
issues/      MyPipeline issues CSV 状态源
storage/     本地上传文件和 metadata.json，运行产物默认不入库
```

## 环境准备

不要使用 `sudo pip`，不要混用系统 Python/Homebrew Python 与 Conda/uv 环境。后端推荐使用本机 Conda 优先路径下的 `uv` 管理独立 `.venv`。

复制环境示例：

```bash
cp .env.example .env
```

本地上传、Profile、规则抽取状态记录和 `.docx` 格式化至少需要保留 `FILE_STORAGE_ROOT`。当前默认从 `backend/` 目录启动后端，因此 `.env.example` 使用 `FILE_STORAGE_ROOT=../storage` 指向仓库根目录下的 `storage/`。处理 legacy `.doc` 输入或导出 PDF 时必须配置 `SOFFICE_BIN`，本机常见路径是 `/opt/homebrew/bin/soffice`。`LLM_API_KEY`、`LLM_MODEL` 是对话/上传规则文档 Agent 分析的硬依赖；`LLM_TIMEOUT_SECONDS` 控制长规则文档的模型等待时间，超时会返回可读错误，系统不会继续生成假 profile。

## 本地启动

后端：

```bash
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

worker 手工执行示例：

```bash
cd backend
uv run python -c "from pathlib import Path; from app.core.config import get_settings; from app.jobs.worker import process_next_queued_job; from app.storage.local import LocalFileStorage; from app.storage.repository import JsonMetadataRepository; settings=get_settings(); storage=LocalFileStorage(settings.file_storage_root); print(process_next_queued_job(JsonMetadataRepository(settings.file_storage_root / 'metadata.json'), storage=storage, soffice_bin=settings.soffice_bin))"
```

带 profile 的 queued job 会读取上传文件和 profile 版本，必要时把 `.doc` 转成 `.docx`，再生成 `storage/outputs/<file_id>.docx` 并把输出 file_id 写回任务。未带 profile 的 queued job 只校验输入文件存在并完成 placeholder 状态更新。

## 验证

后端快速验证：

```bash
cd backend
uv run pytest
```

前端构建验证：

```bash
cd frontend
npm run build
```

OpenSpec 验证：

```bash
openspec validate add-docx-formatting-engine --strict --no-interactive
openspec validate add-agent-rule-extraction --strict --no-interactive
openspec validate add-quality-fix-loop --strict --no-interactive
```

文档工具链 smoke check：

```bash
codex-docx-inspect storage/outputs/<generated-file-id>.docx
codex-docx-to-pdf storage/outputs/<generated-file-id>.docx storage/outputs
codex-pdf-inspect storage/outputs/<generated-file-id>.pdf
```

当前真实链路已验证过一条生产化路径：上传华东师范大学毕业论文格式要求 `.doc`，由 LLM Agent 生成并确认命名 Profile，再上传 RISC-V 课程报告 `.docx` 批量导出 DOCX/PDF。质量报告在页面、页边距、正文/标题字体字号、字色、行距、首行缩进、页码、题注、表格线、PDF 可读性等机器可确认项上返回全通过。对脚注尾注、复杂浮动图片、复杂分节页码等当前 schema 仍无法完全自动执行的规则，系统会以 `warning/fail/unsupported` 或 `uncertain_items` 暴露，保持 fail-closed，不伪装成百分百合规。

## API

- `GET /api/health`：后端健康检查和可选服务配置状态。
- `POST /api/files`：上传 `.doc` 或 `.docx`。
- `GET /api/files/{file_id}`：读取文件元数据。
- `GET /api/profiles`：读取 Profile 摘要列表。
- `GET /api/profiles/{profile_id}/versions/{version}`：读取指定 Profile 版本。
- `POST /api/profiles`：创建新 Profile 的首个版本。
- `POST /api/profiles/{profile_id}/versions`：保存指定 Profile 的新版本，重复版本会被拒绝。
- `POST /api/profiles/{profile_id}/archive`：归档 Profile，保留历史版本。
- `POST /api/profiles/import`：从 YAML 导入 Profile。
- `GET /api/profiles/{profile_id}/versions/{version}/export`：导出指定 Profile 版本 YAML。
- `POST /api/requirement-sessions`：创建格式需求会话；支持 `conversation` 自然语言入口和 `document` 规则文档入口。
- `GET /api/requirement-sessions/{session_id}`：读取 Agent 追问、规则摘要、缺失项、profile draft、evidence 和 uncertain items。
- `POST /api/requirement-sessions/{session_id}/messages`：继续向 Agent 补充格式要求并刷新结构化摘要。
- `POST /api/requirement-sessions/{session_id}/confirm`：确认会话并保存命名 Profile。
- `POST /api/profile-extractions`：兼容旧版规则 `.doc/.docx` 或自然语言 profile extraction job。
- `GET /api/profile-extractions/{extraction_id}`：读取旧版规则抽取状态、profile draft、uncertain items、evidence 和错误信息。
- `POST /api/jobs`：基于单个已上传文件创建 format job，可选传入 `profile_id` 和 `profile_version`；带 profile 的任务会立即生成 DOCX，并在 `SOFFICE_BIN` 可用时生成 PDF。
- `GET /api/jobs/{job_id}`：读取任务状态。
- `POST /api/batches`：基于多个已上传文件和同一个 Profile 创建批量格式化 run，默认开启 `auto_quality` 和 `auto_fix`，返回每份文档的 job、DOCX/PDF、quality report、fix-loop id 和下载 URL manifest。
- `GET /api/batches/{batch_id}`：读取批量格式化 run 和 delivery manifest。
- `GET /api/batches/{batch_id}/manifest`：下载批量交付 manifest JSON。
- `POST /api/quality-reports`：对已生成输出文件按指定 profile 创建结构化质量报告。
- `GET /api/quality-reports/{report_id}`：读取质量报告、summary counts、issue list 和 `issues_by_status`。
- `GET /api/quality-reports/{report_id}/download?format=json|markdown`：下载质量报告 JSON 或 Markdown。
- `POST /api/quality-reports/{report_id}/fix-plan`：为 warning/fail/unsupported issue 生成 deterministic Agent fix-plan。
- `POST /api/quality-reports/{report_id}/fix-loops`：用户确认选中的 issue 后创建 fix-loop 记录。
- `POST /api/quality-reports/{report_id}/fix-loops/{fix_loop_id}/execute`：执行白名单格式修复，生成新 job、新输出文件和 updated quality report。

## Profile 工作流

- 内置 `profiles/ecnu_thesis.yaml` 会在后端启动时写入本地 `metadata.json`，作为 `active` / `system` / `1.0.0` 示例。
- Profile 使用确定性结构化字段，而不是提示词；字段覆盖页面、字体、正文、标题、摘要、图表题注、公式、参考文献、页眉页脚和 quality 配置。
- Web 端 Profile 面板支持列表、详情、纸张/方向/页边距/字体/行距/首行缩进/页眉页码等常用字段结构化编辑、保存新版本、YAML 导入和 YAML 导出。
- 历史版本不会被覆盖，排版任务记录中保存具体 `profile_id + profile_version`，格式化 worker 按该版本应用页面、正文、标题、题注、公式、参考文献和基础表格边框规则。

## Agent 需求会话与规则抽取能力

- 前端首屏提供两个入口：对话生成 Profile、上传格式文档生成 Profile。
- `requirement-sessions` 会先调用 LLM Agent 分析用户输入或规则文档，再把结果拆为 `RequirementSummary`，覆盖纸张/边距、正文中英文字体、字号、行距、首行缩进、标题、图表题注、参考文献和输出格式。
- 缺失必填字段会出现在 `missing_fields` 和 `uncertain_items` 中；用户可继续发送补充回答，Agent 会刷新摘要和 Profile 草案。
- 标题、图题/表题、参考文献等可安全沿用 Profile 默认值的规则会以 `system_default` 和 `needs_confirmation` 显示，不阻断 Profile 保存，但前端会要求用户在保存前显式看到这些默认项。
- 保存 Profile 前必须填写名称和版本，确认后才写入 `profiles/profile_versions`，后续可被批量格式化任务复用。
- 这条链路不绑定华师大模板；内置 ECNU profile 只是 schema 默认值和演示基线，用户可以通过对话或任意规则文档沉淀新的命名 Profile。LLM 输出成功后，系统会用真实输入文本中可确定识别的硬规则做 guard，防止模型把文档明确写出的 A4/纵向/宋体小四等规则改成无关 profile。

## 兼容 Profile Extraction 能力与限制

- 规则抽取 job 支持两类来源：已上传的 `.doc/.docx` 格式要求文档，或用户输入的自然语言规则描述。
- Agent 输出必须是结构化 JSON/YAML，并包含 `profile_draft`、`uncertain_items` 和 `evidence`；`profile_draft` 必须通过现有 `FormatProfile` schema。
- 抽取结果不会自动保存或激活为 profile。Web 端只展示 draft、证据和不确定项，用户点击“载入草案”后才能进入现有 Profile 编辑/保存流程。
- 旧版 `ConfiguredLLMRuleExtractionProvider` 仍保持只做配置检查；生产 UI 已迁移到 `requirement-sessions`。
- Agent 不允许直接写最终 DOCX、不允许绕过 profile schema、不允许把低置信度或无证据规则静默作为 active profile 使用。

## 质量报告与 Agent 修复闭环

- 质量报告由 `POST /api/quality-reports` 用户触发，读取已有 `FileRecord` 输出和指定 `profile_id + profile_version`，不把 job `completed` 状态等同于完全合规。
- DOCX 检查覆盖页面尺寸/方向、页边距、页眉页脚/页码、正文段落样式、标题样式、基础三线表边框、图表题注、原始 LaTeX 残留、角色样式一致性，以及 OOXML 层面的字段刷新策略、TOC 域、分节、脚注尾注、浮动/内嵌图片题注配对、编号列表和 OMML 公式计数；无法可靠判断的项目会保留为 `unsupported`，不会静默标记为 `pass`。
- PDF 检查覆盖 PDF envelope、页数大于零、基础文本可抽取性和明显空白页警告；轻量检查无法确认时返回 `fail` 或 `unsupported` 并给出可读诊断。
- 报告 summary 使用 `pass`、`fixed`、`warning`、`fail`、`unsupported` 五类计数；只要仍有 `warning/fail/unsupported`，前端就显示剩余问题摘要，不展示“全部合规”。
- Agent fix-plan 当前是 deterministic fallback：只解释 warning/fail/unsupported issue，并只允许白名单格式动作 `reapply_profile_formatting`、`apply_table_borders`、`apply_body_paragraph_style`、`apply_heading_style`、`mark_manual_review`；页面设置、页边距、字段刷新、目录域、页眉页脚和页码类问题会通过重套 Profile 或字段刷新策略自动修复。
- 批量任务默认会自动执行一次安全 fix-loop；手动查看 fix-plan 不会立即执行修复，前端仍提供选择 issue 并点击执行的复核入口。后端执行白名单格式动作后会生成新 job、新输出和 updated report，并记录 original report、fix plan、selected issue/action 和状态。

## 文档引擎能力与限制

- `.docx` 输入会直接进入解析和格式化流程；`.doc` 输入需要 `SOFFICE_BIN` 指向可用的 LibreOffice/soffice。
- 格式化引擎保留原文段落文本，并应用 profile 中的 A4/Letter 页面尺寸、横纵向、页边距、基础页眉文字、页脚 PAGE 页码开关、正文中英文字体、字号、行距、首行缩进、标题样式、题注/公式/参考文献段落和基础三线表边框。
- 输出 DOCX/PDF 会登记为普通 `FileRecord`，存放在 `storage/outputs/`，前端任务面板会按 `output_file_ids` 或 batch delivery manifest 拉取文件名、大小、MIME type、file_id 和下载链接。
- 当前不做语义级章节重排、手写目录生成、分节页码格式重编排、图片位置优化、脚注尾注重排或参考文献自动排序；这些内容会被质量门显式标记为需要复核或未支持，而不会计入“全部合规”。
- PDF 导出依赖 `SOFFICE_BIN`；未配置时系统仍能生成 DOCX，并在健康状态和质量报告中保留能力边界。

## 安全与提交约定

- `.env`、`storage/` 运行产物、`node_modules/`、前端 `dist/` 和 Python 虚拟环境不入库。
- 不要提交 API Key、Token、本地代理配置或调试产物。
- GitHub 发布使用 SSH remote；提交前先确认 `.env`、运行产物和本地日志没有进入暂存区。
