# 文件存储与运行配置

## 1. 模块职责与边界

本模块负责本地文件存储、metadata JSON repository 和运行配置读取。它为上传文件、生成输出、manifest、Profile、Job、Session、当前质量相关记录提供持久化基础。它不负责业务格式化、LLM 抽取或前端展示。

## 2. 输入内容

- 外部入口：`POST /api/files`、`GET /api/files/{file_id}`、`GET /api/files/{file_id}/download`、应用启动配置读取。
- 主要参数：上传的 `.doc/.docx` 文件、`file_id`、环境变量。
- 读取的数据：`.env`、`../.env`、`storage/metadata.json`、`storage/files`、`storage/outputs`。
- 配置/环境变量：`APP_NAME`、`API_PREFIX`、`CORS_ORIGINS`、`FILE_STORAGE_ROOT`、`DATABASE_URL`、`REDIS_URL`、`LLM_*`、`SOFFICE_BIN`。
- 上游依赖：FastAPI UploadFile、文件系统。

## 3. 步骤实际动作

### 上传与下载

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `backend/app/api/files.py:upload_file` | 校验后缀仅 `.doc/.docx`，读取上传 bytes | 非 Word 后缀返回 400 |
| 2 | `backend/app/storage/local.py:store_bytes` | 创建目录，生成 `file_{uuid}`，写入 `storage/files`，计算 sha256 | 返回 file id/path/hash/size |
| 3 | `backend/app/storage/repository.py:add_file` | 将 FileRecord 写入 metadata | `metadata.json` 原子替换 |
| 4 | `backend/app/api/files.py:download_file` | 读取 FileRecord，校验文件存在，返回 FileResponse | 下载原始或输出文件 |

### 配置和 metadata

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `backend/app/core/config.py:Settings` | 从 `.env` 和 `../.env` 读取配置 | pydantic settings cache |
| 2 | `backend/app/storage/repository.py:_load` | metadata 不存在时返回空结构；存在时补齐默认 key | 本地 JSON repository |
| 3 | `backend/app/storage/repository.py:_save` | 写入 `.tmp` 后 replace | 降低半写风险 |

## 4. 最终输出结果

- 返回值/API 响应：`FileRecord`、文件下载响应、health 中的配置状态。
- 数据库或外部系统写入：当前只写本地 JSON 和文件系统。
- 文件/产物：`storage/files/*`、`storage/outputs/*`、`storage/manifests/*`、`storage/metadata.json`。
- 下游触发：所有 job、batch、Profile、session 都依赖 repository。
- 错误或跳过结果：文件不存在返回 404；非法上传类型返回 400。

## 5. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/storage/local.py` | 本地文件目录和生成文件复制 | `LocalFileStorage` | 对象存储、目录结构、文件命名 |
| `backend/app/storage/repository.py` | JSON metadata repository | `JsonMetadataRepository` | PostgreSQL 迁移、实体字段新增 |
| `backend/app/core/config.py` | 环境变量和服务配置 | `Settings`, `get_settings` | 新增 env、生产化配置 |
| `backend/app/api/files.py` | 文件上传、元数据读取、下载 API | `build_files_router` | 支持更多文件类型、下载权限 |

## 6. 关键规则与实现细节

- `.env` 搜索顺序是当前目录 `.env` 和上级 `../.env`。
- `FILE_STORAGE_ROOT` 默认 `../storage`，从 `backend/` 目录启动时指向仓库根 `storage/`。
- `LocalFileStorage.ensure_ready` 当前也创建 `reports_dir`，后续内部 QC 化时可保留或清理。
- metadata 当前包含 `quality_reports` 和 `quality_fix_loops`；生产化计划会迁移为 `export_results` / internal QC 状态。

## 7. 测试与验证

- 相关测试：`backend/tests/test_foundation.py`、`backend/tests/test_profiles_api.py`、`backend/tests/test_document_worker.py`。
- 后端测试命令：`cd backend && uv run pytest tests/test_foundation.py`。
- 手工验证：上传 `.docx`，读取 metadata，下载同一 file id。
