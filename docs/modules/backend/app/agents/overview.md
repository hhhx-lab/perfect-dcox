# Agent 需求与规则抽取

## 1. 模块职责与边界

本模块负责从自然语言或上传的格式要求文档中提取格式规则，生成 Profile v2 draft、`RequirementSession` 或旧版 `ProfileExtractionRecord`。它读取规则来源、调用 LLM provider、校验结构化输出、补充 deterministic guard，并可在用户确认后保存 Profile。本模块不负责最终 DOCX/PDF 导出，导出由文档导出引擎完成。

## 2. 输入内容

- 外部入口：`POST /api/requirement-sessions`、`POST /api/requirement-sessions/{session_id}/messages`、`POST /api/requirement-sessions/{session_id}/confirm`、`POST /api/profile-extractions`。
- 主要参数：`source_type`、`natural_language`、`file_id`、`profile_name`、`profile_version`。
- 读取的数据：上传文件记录、格式文档文本、内置 ECNU profile、已有 requirement session。
- 配置/环境变量：`LLM_API_KEY`、`LLM_MODEL`、`LLM_BASE_URL`、`LLM_TIMEOUT_SECONDS`、`SOFFICE_BIN`。
- 上游依赖：文件存储、Profile schema、LibreOffice `.doc` 转换、OpenAI-compatible chat completions。

## 3. 步骤实际动作

### Requirement Session 链路

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `backend/app/api/requirement_sessions.py:create_requirement_session` | 接收 conversation/document 请求，转给 service | HTTP 400 映射 `ExtractionSourceError` |
| 2 | `backend/app/agents/requirements.py:RequirementSessionService.create_session` | 校验输入、读取来源文本、构造 draft | 新增 `RequirementSession` |
| 3 | `backend/app/agents/requirements.py:OpenAICompatibleRequirementProvider.extract_summary` | 调用 OpenAI-compatible `/chat/completions`，要求 JSON object | LLM 不可用或返回非法 JSON 时抛错 |
| 4 | `backend/app/agents/requirements.py:_draft_from_provider_payload` | 将 provider payload 映射为 summary/profile/evidence，并写入 Profile v2 metadata | `profile_draft`, `missing_fields`, `uncertain_items`, `rule_evidence`, `unsupported_rules` |
| 5 | `backend/app/agents/requirements.py:_draft_with_deterministic_rules` | 用文本中的硬规则 guard 覆盖字体、字号、颜色等明确规则 | 避免模型跑偏 |
| 6 | `backend/app/agents/requirements.py:confirm_session` | 用户确认后复制 draft，设置 id/name/version/status/source 并保存 Profile | 写入 profile version，session 变 `confirmed` |

### 旧版 Profile Extraction 链路

| 步骤 | 代码入口 | 实际动作 | 关键状态/副作用 |
| --- | --- | --- | --- |
| 1 | `backend/app/api/profile_extractions.py:create_profile_extraction` | 创建 extraction job | `ProfileExtractionRecord(status=queued)` |
| 2 | `backend/app/agents/extraction.py:resolve_extraction_source` | 校验 `.doc/.docx` 或自然语言来源 | 不支持后缀直接失败 |
| 3 | `backend/app/agents/extraction.py:extract_rule_source_text` | 将 `.doc` 转 `.docx`，用 python-docx 提取段落和表格文本 | 依赖 `SOFFICE_BIN` |
| 4 | `backend/app/agents/extraction.py:parse_agent_extraction_output` | 解析 JSON/YAML 并校验 `profile_draft`、`uncertain_items`、`evidence` | evidence 不能为空 |

## 4. 最终输出结果

- 返回值/API 响应：`RequirementSession` 或 `ProfileExtractionRecord`；Requirement Session 的 `profile_draft` 使用 Profile v2 metadata 承载 evidence、missing_fields 和 unsupported_rules。
- 数据库或外部系统写入：本地 metadata 中的 requirement session、profile extraction、profile version。
- 文件/产物：无直接文件输出；读取上传文件和转换工作目录。
- 下游触发：确认后的 Profile 可被文档导出 job 使用。
- 错误或跳过结果：LLM 未配置、LLM 超时、非法 JSON、文档无可抽取文本都会失败，不生成假 profile。

## 5. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/agents/requirements.py` | 新版对话/文档 requirement session、LLM JSON 抽取、deterministic guard、确认保存 Profile | `RequirementSessionService`, `OpenAICompatibleRequirementProvider` | Profile v2、LangChain 化、缺失项追问、证据链 |
| `backend/app/agents/extraction.py` | 旧版 profile extraction job、来源解析、文档文本提取、Agent 输出解析 | `ProfileExtractionService`, `parse_agent_extraction_output` | 兼容旧 API、移除旧链路、扩展 PDF 输入 |
| `backend/app/api/requirement_sessions.py` | requirement session HTTP API | `build_requirement_sessions_router` | 前端对话和规则文档入口契约变化 |
| `backend/app/api/profile_extractions.py` | 旧版 profile extraction HTTP API | `build_profile_extractions_router` | 旧接口保留或下线 |

## 6. 关键规则与实现细节

- LLM 未配置时 requirement session 直接报错，不能 fallback 成本地假分析。
- `OpenAICompatibleRequirementProvider` 使用 `temperature=0` 和 `response_format={"type":"json_object"}`。
- 文档来源只支持 `.doc/.docx`，`.doc` 需要 `SOFFICE_BIN`。
- `REQUIRED_FIELDS` 决定 session 是否 `needs_user_answer`，缺失字段写入 `profile_draft.missing_fields`。
- 真正不支持或不可确认的规则写入 `profile_draft.unsupported_rules`，供内部 QC gate fail-closed。
- 当前 deterministic guard 会识别 A4、页边距、中文字号、颜色等硬规则。

## 7. 测试与验证

- 相关测试：`backend/tests/test_requirement_sessions_api.py`、`backend/tests/test_profile_extractions.py`、`backend/tests/test_profile_extractions_api.py`、`backend/tests/test_production_profile_pipeline.py`。
- 后端测试命令：`cd backend && uv run pytest`。
- 手工验证：配置 `LLM_API_KEY` 和 `LLM_MODEL` 后，分别用自然语言和 `.doc/.docx` 规则文档创建 requirement session。
