# Profile 管理

## 1. 模块职责与边界

本模块定义格式 Profile 的数据契约、内置 YAML seed、Profile 版本保存、归档、导入和导出。当前 `FormatProfile` 兼容旧 v1 字段，并新增 Profile v2 的结构化规则字段：`schema_version`、`document_grid`、`toc`、`sections`、`list_numbering`、`numbering`、`unit_rules`、`template_binding`、`delivery_gate`、`rule_evidence`、`missing_fields` 和 `unsupported_rules`。表格和图件规则也包含三线表、表名/图名位置、中外文对照、插图放置方式和图宽限制等论文排版约束。

本模块只负责把格式规则保存为可校验、可版本化的数据结构；不负责从用户文档中抽取规则，也不负责把规则应用到 DOCX。

## 2. 核心实现链路

1. `backend/app/profiles/models.py:FormatProfile` 用 Pydantic 严格定义 Profile schema，并为 v2 字段提供默认值，确保旧 YAML 和旧 metadata 能继续加载。
2. `backend/app/profiles/seed.py:load_builtin_profiles` 启动时扫描 `profiles/*.yaml`，校验为 `FormatProfile`。
3. `backend/app/main.py:create_app` 将缺失的内置 Profile 写入 repository。
4. `backend/app/api/profiles.py` 提供 Profile 创建、新版本保存、归档、YAML 导入和 YAML 导出。
5. 导出任务通过 `profile_id + profile_version` 读取不可变 Profile 版本，供 `FormatCompiler` 和内部 QC gate 使用。

## 3. 输入、输出与状态

- 输入：`FormatProfile` JSON/YAML、`profile_id`、`version`。
- 输出：`ProfileSummary`、完整 `FormatProfile`、YAML 文本。
- 状态：metadata 中的 `profiles` 和 `profile_versions`。
- 副作用：写入本地 metadata；导出 YAML 作为 HTTP response。

## 4. 文件职责清单

| 文件 | 主要职责 | 关键函数/类 | 常见改动场景 |
| --- | --- | --- | --- |
| `backend/app/profiles/models.py` | Profile v1/v2 schema、字体颜色归一化、页面网格、目录、图表、单位、模板绑定和内部交付设置 | `FormatProfile`, `DocumentGridSettings`, `TocSettings`, `TableSettings`, `FigureSettings`, `UnitRulesSettings`, `TemplateBindingSettings`, `DeliveryGateSettings`, `ProfileRuleEvidence` | 扩展格式规则、模板字段、内部 QC 策略 |
| `backend/app/profiles/seed.py` | YAML seed 读取和导出 | `load_builtin_profiles`, `profile_to_yaml` | 新增内置 Profile、调整 YAML 序列化 |
| `backend/app/api/profiles.py` | Profile HTTP API | `build_profiles_router` | API 契约变化、导入导出行为 |
| `profiles/ecnu_thesis.yaml` | 内置 ECNU 示例 Profile | YAML seed | 默认格式调整 |

## 5. 关键规则与实现细节

- `StrictModel` 使用 `extra="forbid"`，未知字段会校验失败。
- Profile id 只能匹配 `^[a-z0-9][a-z0-9_-]*$`。
- 版本必须是 semver 风格，如 `1.0.0`。
- `TextFont.color` 会去掉 `#` 并转为 6 位大写 RGB。
- v2 字段全部有安全默认值，旧 Profile 加载后仍可按 v1 行为导出。
- `document_grid`、`toc`、`list_numbering` 和 `unit_rules` 是结构化规则，不应塞进 `description` 或自由文本。
- `table` 默认表达表名在表格上方、三线表、跨页重复表头；`figure` 默认表达图名在图件下方、图件以内联方式插入，半栏图最大 60mm，通栏图 100mm 到 130mm。
- `unsupported_rules` 会被内部 QC gate 用于 fail-closed 放行判断。

## 6. 常见需求改动入口

- 新增可执行格式规则：通常改 `models.py`，再改 `backend/app/documents/compiler.py` 和 `backend/app/quality/delivery_gate.py`。
- 新增模板字段：通常改 `TemplateBindingSettings`、前端 `FormatProfile` 类型和模板绑定 UI。
- 新增内部放行策略：通常改 `DeliveryGateSettings` 和内部 QC 逻辑。

## 7. 测试与验证

- 相关测试：`backend/tests/test_profiles.py`、`backend/tests/test_profiles_api.py`、`backend/tests/test_requirement_sessions_api.py`。
- 后端测试命令：`cd backend && uv run pytest tests/test_profiles.py tests/test_profiles_api.py`。
- 手工验证：导入/导出 `profiles/ecnu_thesis.yaml`，创建新版本并确认重复版本返回 409。
