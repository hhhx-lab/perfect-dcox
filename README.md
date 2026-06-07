# Word Format Agent

Word Format Agent 是一个前后端分离的 Word 论文格式规范化工作台。当前仓库实现的是 MyPipeline `add-web-platform-foundation` 的基础平台阶段：文件上传、文件元数据、占位排版任务、前端工作台和运行配置。

当前阶段不包含真实 DOCX 重排、PDF 转换、Profile 编辑、Agent 规则抽取或质检引擎。这些能力由后续 OpenSpec change 接入。

## 目录

```text
backend/     FastAPI 后端、文件存储、任务 API、placeholder worker
frontend/    React + TypeScript + Vite 工作台
docs/        产品方案
openspec/    OpenSpec change artifacts
plan/        MyPlan 需求质量门产物
issues/      MyPipeline issues CSV 状态源
storage/     本地上传文件和 metadata.json，运行产物默认不入库
```

## 环境准备

不要使用 `sudo pip`，不要混用系统 Python/Homebrew Python 与 Conda/uv 环境。后端推荐使用本机 Conda 优先路径下的 `uv` 管理独立 `.venv`。

复制环境示例：

```bash
cp .env.example .env
```

Foundation 阶段只需要保留 `FILE_STORAGE_ROOT=./storage` 即可启动基础上传和任务 API。`LLM_API_KEY`、`LLM_MODEL`、`SOFFICE_BIN` 在后续 Agent 和文档转换阶段启用。

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
openspec validate add-web-platform-foundation --strict --no-interactive
```

## API

- `GET /api/health`：后端健康检查和可选服务配置状态。
- `POST /api/files`：上传 `.doc` 或 `.docx`。
- `GET /api/files/{file_id}`：读取文件元数据。
- `POST /api/jobs`：基于已上传文件创建 placeholder format job。
- `GET /api/jobs/{job_id}`：读取任务状态。

## 安全与提交约定

- `.env`、`storage/` 运行产物、`node_modules/`、前端 `dist/` 和 Python 虚拟环境不入库。
- 不要提交 API Key、Token、本地代理配置或调试产物。
- 本轮 MyPipeline 只做本地 commit，不 push。
