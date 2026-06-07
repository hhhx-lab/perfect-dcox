# Word Format Agent

Word Format Agent 是一个前后端分离的 Word 论文格式规范化工作台。当前仓库已实现基础平台、版本化格式 Profile、首版 DOCX 格式化引擎、受限 Agent 规则抽取流程、结构化质量报告和用户确认的修复闭环入口：文件上传、文件元数据、带 profile 的排版任务、内置 ECNU 示例 profile、Profile API、结构化编辑器、YAML 导入/导出、DOC/DOCX 输入处理、DOCX 输出登记、前端输出可视化、profile extraction API、规则抽取 review 面板、quality report API 和 Agent fix-plan 审阅控件。

当前阶段不包含文件下载接口、真实在线 LLM 调用实现或真正改写文件的二次修复 worker。带 `profile_id + profile_version` 的任务会由 worker 调用文档引擎生成规范化 DOCX；未带 profile 的任务仍走兼容的 placeholder 完成路径。规则抽取已经有 API、状态记录、schema 校验和前端 review 入口；默认 LLM provider 只做配置检查，测试和 smoke 通过 deterministic provider 验证安全边界。质量报告会独立检查已生成输出并分组展示 `pass/fixed/warning/fail/unsupported`；Agent fix-plan 只生成可解释、白名单动作，必须由用户确认后才创建 fix-loop lineage 记录。PDF 导出已经在 service 层实现，当前任务 API 默认只登记 DOCX 输出，PDF 可通过 service/测试路径验证。

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

本地上传、Profile、规则抽取状态记录和 `.docx` 格式化至少需要保留 `FILE_STORAGE_ROOT=./storage`。处理 legacy `.doc` 输入或导出 PDF 时必须配置 `SOFFICE_BIN`，本机常见路径是 `/opt/homebrew/bin/soffice`。`LLM_API_KEY`、`LLM_MODEL` 用于后续接入真实在线 Agent provider；当前默认 provider 在缺少配置时返回可读错误，测试不依赖真实 API Key。

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
- `POST /api/profile-extractions`：从上传的规则 `.doc/.docx` 或自然语言创建 profile extraction job。
- `GET /api/profile-extractions/{extraction_id}`：读取规则抽取状态、profile draft、uncertain items、evidence 和错误信息。
- `POST /api/jobs`：基于已上传文件创建 format job，可选传入 `profile_id` 和 `profile_version`；带 profile 的任务由 worker 生成 DOCX 输出。
- `GET /api/jobs/{job_id}`：读取任务状态。
- `POST /api/quality-reports`：对已生成输出文件按指定 profile 创建结构化质量报告。
- `GET /api/quality-reports/{report_id}`：读取质量报告、summary counts、issue list 和 `issues_by_status`。
- `POST /api/quality-reports/{report_id}/fix-plan`：为 warning/fail/unsupported issue 生成 deterministic Agent fix-plan。
- `POST /api/quality-reports/{report_id}/fix-loops`：用户确认选中的 issue 后创建 fix-loop lineage 记录；当前不直接改写输出文件。

## Profile 工作流

- 内置 `profiles/ecnu_thesis.yaml` 会在后端启动时写入本地 `metadata.json`，作为 `active` / `system` / `1.0.0` 示例。
- Profile 使用确定性结构化字段，而不是提示词；字段覆盖页面、字体、正文、标题、摘要、图表题注、公式、参考文献和 quality 配置。
- Web 端 Profile 面板支持列表、详情、常用字段结构化编辑、保存新版本、YAML 导入和 YAML 导出。
- 历史版本不会被覆盖，排版任务记录中保存具体 `profile_id + profile_version`，格式化 worker 按该版本应用页面、正文、标题、题注、公式、参考文献和基础表格边框规则。

## Agent 规则抽取能力与限制

- 规则抽取 job 支持两类来源：已上传的 `.doc/.docx` 格式要求文档，或用户输入的自然语言规则描述。
- Agent 输出必须是结构化 JSON/YAML，并包含 `profile_draft`、`uncertain_items` 和 `evidence`；`profile_draft` 必须通过现有 `FormatProfile` schema。
- 抽取结果不会自动保存或激活为 profile。Web 端只展示 draft、证据和不确定项，用户点击“载入草案”后才能进入现有 Profile 编辑/保存流程。
- 默认在线 LLM provider 尚未实现真实网络调用；缺少 `LLM_API_KEY` 或 `LLM_MODEL` 会返回可读配置错误。当前测试通过 fake/deterministic provider 覆盖合法输出、非法 JSON/YAML、缺少 evidence、未知字段、非法枚举、缺配置和 ECNU 样本字段。
- Agent 不允许直接写最终 DOCX、不允许绕过 profile schema、不允许把低置信度或无证据规则静默作为 active profile 使用。

## 质量报告与 Agent 修复闭环

- 质量报告由 `POST /api/quality-reports` 用户触发，读取已有 `FileRecord` 输出和指定 `profile_id + profile_version`，不把 job `completed` 状态等同于完全合规。
- DOCX 检查覆盖页边距、正文段落样式、标题样式、基础三线表边框、图表题注、原始 LaTeX 残留和页码检查能力边界；无法可靠判断的项目会保留为 `unsupported`，不会静默标记为 `pass`。
- PDF 检查覆盖 PDF envelope、页数大于零、基础文本可抽取性和明显空白页警告；轻量检查无法确认时返回 `fail` 或 `unsupported` 并给出可读诊断。
- 报告 summary 使用 `pass`、`fixed`、`warning`、`fail`、`unsupported` 五类计数；只要仍有 `warning/fail/unsupported`，前端就显示剩余问题摘要，不展示“全部合规”。
- Agent fix-plan 当前是 deterministic fallback：只解释 warning/fail/unsupported issue，并只允许白名单格式动作 `reapply_profile_formatting`、`apply_table_borders`、`apply_body_paragraph_style`、`apply_heading_style`、`mark_manual_review`。
- 查看 fix-plan 不会执行修复。用户必须在前端选择 issue 并点击确认，后端才会创建 `FixLoopRecord`，记录 original report、fix plan、selected issue/action 和状态。当前 MVP 不会直接生成新 job、新输出或 updated report。

## 文档引擎能力与限制

- `.docx` 输入会直接进入解析和格式化流程；`.doc` 输入需要 `SOFFICE_BIN` 指向可用的 LibreOffice/soffice。
- 格式化引擎保留原文段落文本，并应用 profile 中的 A4 页面边距、正文中英文字体、字号、行距、首行缩进、标题样式、题注/公式/参考文献段落和基础三线表边框。
- 输出 DOCX 会登记为普通 `FileRecord`，存放在 `storage/outputs/`，前端任务面板会按 `output_file_ids` 拉取文件名、大小、MIME type 和 file_id。
- 当前不做语义级章节重排、复杂域代码/目录更新、图片位置优化、参考文献自动排序或 Word 下载接口；这些属于后续 Agent/质检闭环 change。
- PDF 导出函数已经存在，依赖 `SOFFICE_BIN`；当前默认 worker 只请求 DOCX 输出，PDF smoke 可通过 service 测试或文档工具链单独执行。

## 安全与提交约定

- `.env`、`storage/` 运行产物、`node_modules/`、前端 `dist/` 和 Python 虚拟环境不入库。
- 不要提交 API Key、Token、本地代理配置或调试产物。
- 本轮 MyPipeline 只做本地 commit，不 push。
