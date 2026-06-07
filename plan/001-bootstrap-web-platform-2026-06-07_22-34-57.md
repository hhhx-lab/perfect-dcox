---
mode: plan
change_id: add-web-platform-foundation
cwd: /Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范
task: 搭建 Word 格式规范化工具的前后端分离基础工程、文件上传、任务编排和运行配置
source_document: docs/word-format-agent-web-product-plan.md
created_at: 2026-06-07T22:34:57+08:00
qualification_status: passed
---

# Plan: 搭建前后端分离基础平台

## 背景与动机

当前产品方案已经明确该工具要面向论文、报告、课题材料和单位规范文档，支持上传 Word、选择或生成格式 profile，并输出 DOCX、PDF 和质检报告。要让后续 profile、文档重排、Agent 和质检能力可靠落地，必须先建立前后端分离的基础工程、文件存储、任务系统和配置约定。
<!-- 下游：proposal.md 的 motivation -->

## Goal

- 建立可本地运行的前后端分离 Web 平台，用户能通过 Web 上传文件、查看任务状态，并由后端持久化文件、profile 元数据、任务记录和输出文件引用。
- 后端提供基础 API、异步任务框架和文件存储抽象，为后续 profile 管理、文档重排、Agent 调用和质检任务提供统一入口。
<!-- 下游：proposal.md 的 scope -->

## Non-goals

- 不实现实际 Word 格式重排、DOCX/PDF 质检或 Agent 规则抽取。
- 不实现复杂账号体系、多人协作、组织模板库或权限管理。
- 不支持批量文档处理，MVP 仅要求单文件任务链路可运行。
<!-- 下游：proposal.md 的 scope -->

## 当前仓库事实

- 产品方案要求第一版支持 `.doc/.docx` 上传、选择 profile、生成 DOCX/PDF、输出质检报告，并允许用户在 Web 页面查看规则、修改规则、重新执行：`docs/word-format-agent-web-product-plan.md:55`、`docs/word-format-agent-web-product-plan.md:59`、`docs/word-format-agent-web-product-plan.md:63`、`docs/word-format-agent-web-product-plan.md:66`。
- 产品方案规定前端推荐 React + TypeScript，状态管理可使用 Vite/Next.js、Zustand 或 TanStack Query，并列出首页、Profile 管理、规则抽取、排版任务、质检报告和输出下载等页面：`docs/word-format-agent-web-product-plan.md:331`、`docs/word-format-agent-web-product-plan.md:335`、`docs/word-format-agent-web-product-plan.md:340`。
- 产品方案规定后端推荐 FastAPI、PostgreSQL、Redis + RQ/Celery/Arq、本地文件存储或 S3，并要求 Python 文档处理环境使用独立 venv 或 uv：`docs/word-format-agent-web-product-plan.md:360`、`docs/word-format-agent-web-product-plan.md:364`、`docs/word-format-agent-web-product-plan.md:368`。
- 产品方案要求后端承担文件上传与安全校验、Profile CRUD、任务编排、Agent 调用、文档转换、质检执行、输出文件管理、日志与任务状态推送：`docs/word-format-agent-web-product-plan.md:370`、`docs/word-format-agent-web-product-plan.md:372`、`docs/word-format-agent-web-product-plan.md:379`。
- 产品方案建议目录结构包含 `backend/`、`frontend/`、`profiles/`、`docs/` 和 `storage/`：`docs/word-format-agent-web-product-plan.md:1023`、`docs/word-format-agent-web-product-plan.md:1026`。
- 现有 OpenSpec specs 基线：未验证；补证路径为初始化 OpenSpec 后读取 `openspec/specs/` 中与 Web 平台、文件、任务、profile 相关的 `spec.md`。
<!-- 下游：specs baseline，proposal.md 的 context -->

## 改动边界

- 新增前端应用壳，包括工作台、文件上传入口、任务列表/详情和基础导航。
- 新增后端 FastAPI 应用壳，包括配置加载、文件上传 API、任务 API、健康检查、错误响应格式和本地文件存储。
- 新增数据库模型或等价持久化结构，覆盖 files、jobs、profiles 的最小元数据。
- 新增异步任务队列抽象，但任务处理可以先以占位 worker 或 no-op worker 验证链路。
- 可能需要新增或修改 OpenSpec specs 领域：`web-platform`、`file-storage`、`job-orchestration`。
<!-- 下游：proposal.md scope，design.md scope，spec deltas 范围 -->

## 约束

- Python 依赖必须使用项目独立环境，优先 uv 或 conda，不能依赖 sudo pip 或混用系统/Homebrew Python。
- 密钥和模型配置必须通过 `.env` 驱动，不能硬编码 API Key、Token 或模型密钥。
- 前后端必须分离，后端 API 不应把文档处理长任务阻塞在同步 HTTP 请求中。
- 本阶段只做基础平台，不引入对 Word 格式效果的成功承诺。
<!-- 下游：design.md 的 constraints -->

## 验收标准

1. 启动后端后，访问健康检查接口返回 200，并能读取 `.env` 或 `.env.example` 中定义的基础配置。
2. 启动前端后，用户能打开工作台页面，并看到文件上传入口、任务列表入口和 profile 入口。
3. 上传一个 `.docx` 或 `.doc` 文件后，后端返回 `file_id`，并在本地存储或对象存储中保存文件及 sha256、文件名、mime type、大小等元数据。
4. 创建一个占位格式化任务后，后端返回 `job_id`，前端能轮询或订阅展示 queued、running、completed、failed 等状态。
5. `.env.example` 中列出 `DATABASE_URL`、`REDIS_URL`、`FILE_STORAGE_ROOT`、`LLM_API_KEY`、`LLM_MODEL`、`SOFFICE_BIN`，并逐项说明用途、获取方式和是否必填。
6. 前后端 README 或开发说明能让开发者用明确命令启动本地前端、后端和 worker。
<!-- 下游：spec deltas 的 Scenarios，tasks.md 的 verification -->

## 验证方式

- 运行后端测试命令，覆盖配置加载、文件上传、任务创建和任务状态查询。
- 运行前端测试或构建命令，确认页面编译通过。
- 手工启动前端、后端和 worker，上传一个小型 `.docx` 样例，观察文件记录和任务状态能在 Web 页面显示。
- 检查 `.env.example`，确认所有环境变量都有中文注释且没有真实密钥。
<!-- 下游：tasks.md 的验证步骤 -->

## 迁移 / 回滚 / 降级

- 低风险，MVP 新建工程为主，迁移 N/A。
- 如后续引入 PostgreSQL schema，必须提供可重复执行的迁移脚本；回滚时删除新增表或回退到前一迁移版本。
- 文件存储失败时应降级为任务失败并保留错误原因，不应吞掉异常或返回假成功。
<!-- 下游：proposal.md 的 risks，spec deltas 的 REMOVED/MODIFIED -->

## 参考

- `docs/word-format-agent-web-product-plan.md:55`
- `docs/word-format-agent-web-product-plan.md:59`
- `docs/word-format-agent-web-product-plan.md:63`
- `docs/word-format-agent-web-product-plan.md:66`
- `docs/word-format-agent-web-product-plan.md:331`
- `docs/word-format-agent-web-product-plan.md:360`
- `docs/word-format-agent-web-product-plan.md:1023`
- `plan/002-profile-management-2026-06-07_22-34-57.md`
- `plan/003-docx-formatting-engine-2026-06-07_22-34-57.md`
- `plan/004-agent-rule-extraction-2026-06-07_22-34-57.md`
- `plan/005-quality-agent-fix-loop-2026-06-07_22-34-57.md`

