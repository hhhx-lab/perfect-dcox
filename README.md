# Word Format Agent

Word Format Agent 是一个前后端分离的 Word 论文格式规范化工作台。当前仓库已实现基础平台、版本化格式 Profile 和首版 DOCX 格式化引擎：文件上传、文件元数据、带 profile 的排版任务、内置 ECNU 示例 profile、Profile API、结构化编辑器、YAML 导入/导出、DOC/DOCX 输入处理、DOCX 输出登记和前端输出可视化。

当前阶段不包含 Agent 规则抽取、自动质检修正循环或文件下载接口。带 `profile_id + profile_version` 的任务会由 worker 调用文档引擎生成规范化 DOCX；未带 profile 的任务仍走兼容的 placeholder 完成路径。PDF 导出已经在 service 层实现，当前任务 API 默认只登记 DOCX 输出，PDF 可通过 service/测试路径验证。

## 目录

```text
backend/     FastAPI 后端、文件存储、Profile API、任务 API、DOCX 格式化 worker
frontend/    React + TypeScript + Vite 工作台、Profile 编辑器和任务输出面板
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

本地上传、Profile 和 `.docx` 格式化至少需要保留 `FILE_STORAGE_ROOT=./storage`。处理 legacy `.doc` 输入或导出 PDF 时必须配置 `SOFFICE_BIN`，本机常见路径是 `/opt/homebrew/bin/soffice`。`LLM_API_KEY`、`LLM_MODEL` 仍留给后续 Agent 规则抽取/修正解释阶段使用。

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
- `POST /api/jobs`：基于已上传文件创建 format job，可选传入 `profile_id` 和 `profile_version`；带 profile 的任务由 worker 生成 DOCX 输出。
- `GET /api/jobs/{job_id}`：读取任务状态。

## Profile 工作流

- 内置 `profiles/ecnu_thesis.yaml` 会在后端启动时写入本地 `metadata.json`，作为 `active` / `system` / `1.0.0` 示例。
- Profile 使用确定性结构化字段，而不是提示词；字段覆盖页面、字体、正文、标题、摘要、图表题注、公式、参考文献和 quality 配置。
- Web 端 Profile 面板支持列表、详情、常用字段结构化编辑、保存新版本、YAML 导入和 YAML 导出。
- 历史版本不会被覆盖，排版任务记录中保存具体 `profile_id + profile_version`，格式化 worker 按该版本应用页面、正文、标题、题注、公式、参考文献和基础表格边框规则。

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
