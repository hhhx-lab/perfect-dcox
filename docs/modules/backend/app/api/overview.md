# 后端 API 壳层

## 1. 模块职责与边界

本模块承载 FastAPI 应用创建、CORS、依赖组装、路由注册、共享 API 数据模型和健康检查。它把 storage、profiles、agents、documents、quality 等模块组装成 HTTP 服务，但不应承载具体业务逻辑。

## 2. 输入内容

- 外部入口：`uvicorn app.main:app`，HTTP `/api/*` 请求。
- 主要参数：各 API payload、路径参数、配置对象。
- 读取的数据：环境变量、metadata、内置 profiles。
- 配置/环境变量：`APP_NAME`、`API_PREFIX`、`CORS_ORIGINS`、`FILE_STORAGE_ROOT`、`LLM_*`、`SOFFICE_BIN`。
- 上游依赖：FastAPI、各 build_router factory、JsonMetadataRepository、LocalFileStorage。

## 3. 步骤实际动作

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `backend/app/main.py:create_app` | 读取 settings，创建 FastAPI app | 应用 title 使用 `app_name` |
| 2 | `backend/app/main.py:create_app` | 注册 CORS middleware | 允许 `cors_origins` |
| 3 | `backend/app/main.py:create_app` | 创建 repository、file_storage、extraction_service、requirement_session_service、quality/fix services | 共享依赖实例 |
| 4 | `backend/app/main.py:create_app` | 加载内置 profiles，缺失时写入 repository | seed profile 入库 |
| 5 | `backend/app/main.py:health` | 返回服务配置状态 | 暴露 database/redis/llm/soffice 是否配置 |
| 6 | `backend/app/main.py:create_app` | include 各模块 router，统一加 `api_prefix` | `/api/files`、`/api/profiles` 等 |

## 4. 最终输出结果

- 返回值/API 响应：FastAPI app 和各路由响应。
- 数据库或外部系统写入：启动时可能写入内置 Profile。
- 文件/产物：无直接文件产物。
- 下游触发：所有前端 API 调用进入本模块注册的路由。
- 错误或跳过结果：service 构建时不会主动验证所有配置；具体请求时由业务模块报错。

## 5. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/main.py` | 应用创建、依赖组装、路由注册、health | `create_app`, `app` | 新增模块 API、替换 quality 为 internal QC |
| `backend/app/models.py` | 跨 API 共享数据模型 | `FileRecord`, `JobRecord`, `BatchFormatRun`, `DeliveryManifestItem`, `RequirementSession`, `QualityReport` | API 契约、状态枚举、内部 QC 摘要、最终交付字段 |
| `backend/app/api/*.py` | 各业务 API router | `build_*_router` | 对应模块 API 改动 |

## 6. 关键规则与实现细节

- `create_app` 支持传入测试用 `settings` 和 `requirement_provider`，便于测试注入。
- `requirement_session_service` 只有在 LLM 配置齐全时使用真实 provider，否则 provider 为 None，请求时 fail closed。
- 当前仍注册 `/api/quality-reports` 作为兼容/调试接口；主导出流通过 job/batch 的 `delivery_gate_summary` 和最终 file ids 表达内部 QC 结果。
- `JobRecord.output_file_ids` 只表示后端放行的最终文件；候选 DOCX 不应出现在该字段中。
- `api_prefix` 默认 `/api`，前端 API base URL 默认包含该前缀。

## 7. 测试与验证

- 相关测试：`backend/tests/test_foundation.py` 和各 API 测试文件。
- 后端测试命令：`cd backend && uv run pytest tests/test_foundation.py`。
- 手工验证：`curl http://127.0.0.1:8000/api/health`。
