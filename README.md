# Word Format Agent

Word Format Agent 是一个前后端分离的 Word 论文格式规范化工作台。当前仓库已实现基础平台和 MyPipeline `add-profile-management`：文件上传、文件元数据、占位排版任务、版本化格式 Profile、内置 ECNU 示例 profile、Profile API、结构化编辑器和 YAML 导入/导出。

当前阶段不包含真实 DOCX 重排、PDF 转换、Agent 规则抽取或质检引擎。占位排版任务可以引用 `profile_id + profile_version`，但 worker 暂不解释格式规则；真实重排由后续 OpenSpec change 接入。

## 目录

```text
backend/     FastAPI 后端、文件存储、Profile API、任务 API、placeholder worker
frontend/    React + TypeScript + Vite 工作台和 Profile 编辑器
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

当前阶段只需要保留 `FILE_STORAGE_ROOT=./storage` 即可启动上传、Profile 和任务 API。`LLM_API_KEY`、`LLM_MODEL`、`SOFFICE_BIN` 在后续 Agent 和文档转换阶段启用。

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

placeholder worker 手工执行示例：

```bash
cd backend
uv run python -c "from pathlib import Path; from app.storage.repository import JsonMetadataRepository; from app.jobs.worker import process_next_queued_job; print(process_next_queued_job(JsonMetadataRepository(Path('../storage/metadata.json'))))"
```

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
openspec validate add-profile-management --strict --no-interactive
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
- `POST /api/jobs`：基于已上传文件创建 placeholder format job，可选传入 `profile_id` 和 `profile_version`。
- `GET /api/jobs/{job_id}`：读取任务状态。

## Profile 工作流

- 内置 `profiles/ecnu_thesis.yaml` 会在后端启动时写入本地 `metadata.json`，作为 `active` / `system` / `1.0.0` 示例。
- Profile 使用确定性结构化字段，而不是提示词；字段覆盖页面、字体、正文、标题、摘要、图表题注、公式、参考文献和 quality 配置。
- Web 端 Profile 面板支持列表、详情、常用字段结构化编辑、保存新版本、YAML 导入和 YAML 导出。
- 历史版本不会被覆盖，排版任务记录中保存具体 `profile_id + profile_version`，方便后续格式引擎追溯。

## 安全与提交约定

- `.env`、`storage/` 运行产物、`node_modules/`、前端 `dist/` 和 Python 虚拟环境不入库。
- 不要提交 API Key、Token、本地代理配置或调试产物。
- 本轮 MyPipeline 只做本地 commit，不 push。
