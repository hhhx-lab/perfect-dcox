# Perfect DOCX / Word Format Agent

一个面向论文、课程报告和机构文档的 Word/PDF 格式规范化工作台。

项目目标不是简单地“套一个模板”，而是把格式要求沉淀为可版本化的 `Profile`，再用前后端工作流完成上传、规则抽取、格式化、质检、自动修复和下载交付。

## 现在能做什么

- 通过对话或上传格式要求文档，让 LLM Agent 拆解格式规则并生成 Profile 草案。
- 保存不同学校、机构、期刊或课程要求对应的版本化 Profile。
- 上传 `.doc` / `.docx` 文档，按指定 Profile 导出规范化 `.docx`，在 LibreOffice 可用时同步导出 PDF。
- 对生成结果做结构化质量检查，覆盖页面、页边距、正文/标题字体字号、行距、缩进、页眉页脚、页码、题注、表格线和 PDF 可抽取性等项目。
- 对可安全自动处理的问题执行白名单修复，并重新生成质量报告。
- 批量处理多份文档，并生成 delivery manifest 供下载和追踪。

系统采用 fail-closed 策略：如果 LLM 不可用、规则无法可靠解析、或质量检查仍有 `warning` / `fail` / `unsupported`，系统会明确报错或要求复核，不会把不确定结果伪装成“完全合规”。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | React 19, TypeScript, Vite, lucide-react |
| 后端 | FastAPI, Pydantic, python-docx, pypdf |
| 运行环境 | uv, npm, LibreOffice/soffice |
| 存储 | 当前 MVP 使用本地 JSON metadata + `storage/` 文件目录 |
| Agent | OpenAI-compatible LLM 接口，必须配置 `LLM_API_KEY` 和 `LLM_MODEL` 后才会执行规则分析 |

## 快速启动

先准备环境变量：

```bash
cp .env.example .env
```

然后一键启动前后端：

```bash
./scripts/start-dev.sh
```

默认地址：

| 服务 | 地址 |
| --- | --- |
| 前端 | `http://127.0.0.1:5173` |
| 后端 | `http://127.0.0.1:8000` |
| 健康检查 | `http://127.0.0.1:8000/api/health` |

常用管理命令：

```bash
./scripts/start-dev.sh --status
./scripts/start-dev.sh --restart
./scripts/start-dev.sh --stop
```

如果默认端口被占用，可以指定端口：

```bash
./scripts/start-dev.sh --backend-port 8010 --frontend-port 5174
```

启动脚本会：

- 检查 `uv`、`npm`、`curl`、`lsof`、`python3` 是否可用。
- 在前端缺少 `node_modules` 时自动执行 `npm install`。
- 后台启动 FastAPI 和 Vite dev server。
- 写入日志到 `storage/logs/backend.log` 和 `storage/logs/frontend.log`。
- 写入 PID/端口记录到 `storage/pids/`。
- 只停止它自己启动的进程；如果端口被未知进程占用，会提示并退出。

## 环境变量

`.env.example` 已包含完整注释。最常用配置如下：

| 变量 | 是否必需 | 说明 |
| --- | --- | --- |
| `FILE_STORAGE_ROOT` | 必需 | 上传文件、输出文件、metadata、报告和 manifest 的本地存储目录。默认 `../storage`。 |
| `SOFFICE_BIN` | 推荐 | LibreOffice `soffice` 路径。处理 legacy `.doc` 和导出 PDF 时必需。 |
| `LLM_API_KEY` | Agent 必需 | 对话生成 Profile、上传格式要求文档抽取规则时必需。 |
| `LLM_MODEL` | Agent 必需 | LLM 模型名称。 |
| `LLM_BASE_URL` | 可选 | OpenAI-compatible 服务地址；使用 provider 默认地址时可留空。 |
| `DATABASE_URL` | 可选 | 当前本地 MVP 未强依赖，生产化可接 PostgreSQL。 |
| `REDIS_URL` | 可选 | 当前本地 MVP 未强依赖，生产化可接异步队列。 |

不要提交 `.env`、API Key、Token、本地代理配置或运行产物。

## 典型工作流

1. 创建格式 Profile

   - 入口 A：和 Agent 对话，由 Agent 追问并汇总格式要求。
   - 入口 B：上传格式要求 `.doc` / `.docx`，由 Agent 读取文档并拆解规则。
   - 用户确认规则摘要、补齐缺失项、命名 Profile 并保存版本。

2. 上传待处理文档

   - 选择一个 Profile。
   - 上传一份或多份 Word 文档。
   - 创建格式化 job 或 batch run。

3. 导出和质检

   - 后端生成规范化 `.docx`。
   - 如果 `SOFFICE_BIN` 可用，同步导出 PDF。
   - 系统生成 quality report，并对安全项执行自动修复。

4. 下载交付物

   - 下载最终 DOCX/PDF。
   - 下载质量报告 JSON/Markdown。
   - 批量任务可下载 delivery manifest。

## 项目结构

```text
backend/      FastAPI 后端、Profile API、文件存储、文档格式化、质量报告和修复闭环
frontend/     React + TypeScript + Vite 工作台
profiles/     内置和示例 Profile，例如 ecnu_thesis.yaml
storage/      本地上传、输出、报告、manifest 和 metadata，默认不入库
scripts/      本地开发脚本，例如一键启动脚本
docs/         产品方案和设计文档
openspec/     OpenSpec change artifacts
plan/         MyPlan 需求质量门产物
issues/       MyPipeline issues CSV 状态源
```

## 手工启动

一键脚本是推荐方式。需要手工调试时可以分开启动。

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

手工执行一个 queued worker：

```bash
cd backend
uv run python -c "from app.core.config import get_settings; from app.jobs.worker import process_next_queued_job; from app.storage.local import LocalFileStorage; from app.storage.repository import JsonMetadataRepository; settings=get_settings(); storage=LocalFileStorage(settings.file_storage_root); print(process_next_queued_job(JsonMetadataRepository(settings.file_storage_root / 'metadata.json'), storage=storage, soffice_bin=settings.soffice_bin))"
```

## 验证

后端测试：

```bash
cd backend
uv run pytest
```

前端构建：

```bash
cd frontend
npm run build
```

OpenSpec 校验：

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

## API 概览

| API | 用途 |
| --- | --- |
| `GET /api/health` | 后端健康检查和可选服务配置状态 |
| `POST /api/files` | 上传 `.doc` 或 `.docx` |
| `GET /api/files/{file_id}` | 读取文件元数据 |
| `GET /api/files/{file_id}/download` | 下载文件 |
| `GET /api/profiles` | 读取 Profile 列表 |
| `POST /api/profiles` | 创建 Profile 首个版本 |
| `POST /api/profiles/{profile_id}/versions` | 保存 Profile 新版本 |
| `POST /api/requirement-sessions` | 创建对话/文档规则分析会话 |
| `POST /api/requirement-sessions/{session_id}/messages` | 继续补充规则要求 |
| `POST /api/requirement-sessions/{session_id}/confirm` | 确认会话并保存 Profile |
| `POST /api/jobs` | 创建单文档格式化任务 |
| `GET /api/jobs/{job_id}` | 读取任务状态 |
| `POST /api/batches` | 创建批量格式化任务 |
| `GET /api/batches/{batch_id}` | 读取批量任务和交付 manifest |
| `POST /api/quality-reports` | 对输出文件生成质量报告 |
| `POST /api/quality-reports/{report_id}/fix-plan` | 生成可复核修复方案 |
| `POST /api/quality-reports/{report_id}/fix-loops` | 创建修复闭环记录 |
| `POST /api/quality-reports/{report_id}/fix-loops/{fix_loop_id}/execute` | 执行白名单修复 |

## 当前能力边界

已支持：

- A4/Letter、横纵向、页边距。
- 正文、标题、摘要、题注、公式、参考文献的基础样式应用。
- 中文/西文字体、字号、字色、加粗、行距、首行缩进、对齐。
- 基础页眉文字、页脚 PAGE 页码字段和 Word 字段刷新策略。
- 基础三线表边框。
- DOCX 输出、PDF 输出、质量报告、批量 manifest。

当前不会静默承诺完全自动处理：

- 复杂目录域和跨节页码重编排。
- 复杂分节、脚注尾注、浮动图片位置优化。
- 图表与正文的语义级重排。
- 参考文献自动排序和引用一致性校正。
- 超出当前 Profile schema 的学校/期刊特殊规则。

这些项目会进入质量报告的 `warning`、`fail` 或 `unsupported`，需要继续扩展 schema、格式化引擎和检测器。

## 开发约定

- Python 依赖使用 `uv` 或项目约定环境，不使用 `sudo pip`，不混用系统 Python/Homebrew Python 和项目环境。
- 环境变量只放在 `.env` 或部署环境中，不写死到代码里。
- `.env`、`storage/` 运行产物、`node_modules/`、前端 `dist/`、Python 虚拟环境和本地日志不入库。
- GitHub remote 使用 SSH：`git@github.com:hhhx-lab/perfect-dcox.git`。
