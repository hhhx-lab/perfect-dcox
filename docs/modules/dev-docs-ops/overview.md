# 研发文档与本地运维

## 1. 模块职责与边界

本模块覆盖本地开发脚本、产品/研发计划文档、OpenSpec artifacts、issues CSV 和模块文档体系。它负责让研发改动有可追踪的计划、文档和执行入口，不负责应用运行时业务逻辑。

## 2. 输入内容

- 外部入口：`./scripts/start-dev.sh`、`plan.md`、`docs/change-plans/*`、OpenSpec CLI、文档驱动研发 SOP。
- 主要参数：启动脚本参数 `--restart/--stop/--status/--host/--backend-port/--frontend-port`，研发计划文件路径，OpenSpec change id。
- 读取的数据：`.env`、`backend/`、`frontend/`、`storage/`、`openspec/changes/*`、`issues/*.csv`。
- 配置/环境变量：`HOST`、`BACKEND_PORT`、`FRONTEND_PORT`、`VITE_API_BASE_URL`、后端 `.env` 变量。
- 上游依赖：uv、npm、curl、lsof、python3、LibreOffice、OpenSpec CLI。

## 3. 步骤实际动作

### 一键启动脚本

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `scripts/start-dev.sh` 参数解析 | 解析 start/restart/stop/status 和端口 | 参数非法直接退出 |
| 2 | `scripts/start-dev.sh:ensure_tools` | 检查 uv、npm、curl、lsof、python3 | 缺依赖退出 |
| 3 | `scripts/start-dev.sh:ensure_port_free_for_start` | 检查端口和 PID metadata | 不杀未知进程 |
| 4 | `scripts/start-dev.sh:start_detached` | 用 Python `subprocess.Popen(start_new_session=True)` 后台启动服务 | 写 PID 和日志 |
| 5 | `scripts/start-dev.sh:wait_for_url` | 等待后端 `/api/health` 和前端首页可访问 | 失败时输出日志尾部 |

### 文档驱动研发

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `plan.md` | 承载当前生产化升级方案 | 后续生成 `docs/change-plans` |
| 2 | `docs/modules/module-map.json` | 定义模块与源码路径映射 | 后续需求路由前置条件 |
| 3 | `docs/modules/**/overview.md` | 记录模块当前代码事实 | Docs Driven 基线 |
| 4 | `openspec/changes/*` | 已有 OpenSpec change artifacts | 后续正式变更对齐 |
| 5 | `issues/*.csv` | 历史 MyPipeline 执行状态 | 可追踪任务记录 |

## 4. 最终输出结果

- 返回值/API 响应：脚本输出服务 URL、日志路径、状态。
- 数据库或外部系统写入：无数据库写入。
- 文件/产物：`storage/logs/*`、`storage/pids/*`、`docs/module-tree.md`、`docs/modules/*`、`docs/change-plans/*`。
- 下游触发：启动本地前后端；为 Docs Driven / Fast Fix / 提交流程提供文档落点。
- 错误或跳过结果：端口被未知进程占用时脚本退出；缺模块 docs 时研发路由阻断。

## 5. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `scripts/start-dev.sh` | 前后端一键启动、停止、状态查看 | `start_backend`, `start_frontend`, `stop_pid_file` | 本地开发体验、端口/日志/PID 管理 |
| `plan.md` | 当前生产化升级方案 | Markdown 章节 | 方案调整、需求入口 |
| `docs/modules/module-map.json` | 模块映射 | `modules[]` | 新增/拆分模块 |
| `docs/modules/**/overview.md` | 模块代码事实基线 | Markdown | Docs Driven 前置文档 |
| `openspec/changes/*` | 历史 OpenSpec change | proposal/design/specs/tasks | 正式变更拆解 |
| `issues/*.csv` | 历史任务执行状态 | CSV | 闭环任务追踪 |

## 6. 关键规则与实现细节

- 启动脚本只停止它自己记录 PID 的进程，不接管未知端口占用。
- `storage/*` 运行产物默认不入库，只有 `storage/.gitkeep` 保留。
- 文档驱动研发要求先有 module docs，再生成 change plan，未确认 plan 不实现。
- 当前 `plan.md` 是来源方案，不等同于已确认的 `docs/change-plans/<plan_id>.md`。

## 7. 测试与验证

- 脚本语法：`bash -n scripts/start-dev.sh`。
- 启动验证：`./scripts/start-dev.sh --backend-port 8010 --frontend-port 5174`，再访问 health 和前端首页。
- 文档流程验证：检查 `docs/modules/module-map.json`、各模块 `overview.md` 和 fast-fix CSV 是否存在。
