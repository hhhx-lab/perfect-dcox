# Perfect DOCX 真实进度状态

更新时间：2026-06-13 00:20:24 +0800
对应主文档：`docs/production-format-upgrade-change-document.md`
对应 OpenSpec Change：`openspec/changes/update-production-export/`
当前结论：LLM 不是不可用；本轮已确认当前网关需要 `stream=true`，后端已适配 SSE 返回，真实华东师范大学格式文档提取接口已跑通。但项目仍未达到“任意复杂论文 / 任意模板 / 百分百稳定导出”的商业级完成状态。

## 1. 一句话真实结论

现在系统已经具备生产化主链路雏形：

- Profile JSON v2
- Agent 规则入口
- 对话 / 上传规则文档 / 上传样本文档 / 可视化编辑合流
- 规则能力覆盖声明
- DOCX 格式执行
- 内部 QC 与自动修复门
- PDF 导出检查
- LLM final review fail-closed
- 前端 LLM 状态检测与下载入口

但是它还不能诚实承诺“换任意学校格式要求或复杂毕业论文都百分百成功”。原因不是 LLM 完全不可用，而是：

- 真实 Agent 提取已经可用，但 LLM 返回的字段路径和值域仍会波动，需要更严格的 schema merge / JSON Patch 协议。
- 真实格式文档中存在 `units`、装订、封面、目录格式细则等当前尚未全部落入可执行 formatter/QC 字段的规则。
- 复杂模板、多 section 页眉页脚、固定封面/声明页、复杂目录、真实毕业论文样本矩阵仍未完整验收。
- 最终 LLM layout review 的 required 真实导出闭环还需要用 Agent 生成的 Profile 再跑一次完整 DOCX/PDF 样本。

## 2. 本轮已修正的关键事实

之前判断“LLM 不可用 / chat completions 空 event-stream 阻塞”是不完整的。真实根因是：

- 当前 OpenAI-compatible 网关在非流式请求下会返回空 `text/event-stream`。
- 显式传入 `stream: true` 后，最小 chat completion 和 JSON response 都可以返回 assistant 内容。
- 后端原来只按普通 JSON `choices[0].message.content` 解析，不兼容 SSE delta。

本轮已经完成：

- `backend/app/llm/openai_compat.py` 新增统一解析器：
  - 支持普通 JSON。
  - 支持 SSE / `text/event-stream`。
  - 对没有 assistant content 的响应明确报错。
- `backend/app/llm/diagnostics.py` 的健康检查改为 `stream: true`。
- `backend/app/agents/requirements.py` 的 Agent 规则提取改为 `stream: true` 并复用统一解析器。
- `backend/app/quality/final_layout_review.py` 的最终 LLM 版面检查改为 `stream: true` 并复用统一解析器。
- 前端已接入 `/api/health/llm`，可显示 `missing / unverified / reachable / failed` 并提供“检测 LLM”按钮。

当前实测：

- `GET http://127.0.0.1:8010/api/health/llm`
- 返回 `configured=true`、`reachable=true`、`status=reachable`、`model=gpt-5.4`。

## 3. 真实规则文档提取结果

使用真实格式规则文档：

- `华东师范大学毕业论文格式要求.doc`
- 已上传文件 id：`file_11b014e3ce204e9280534333f9364b99`

最新真实接口：

```text
POST http://127.0.0.1:8010/api/requirement-sessions
```

最新摘要：

- `session_id=rs_0ff77049c8cc4e3caf4c4d034a3ee424`
- `status=ready_for_confirmation`
- `item_count=21`
- `missing_count=0`
- `uncertain_count=19`
- `unsupported_count=1`
- `unsupported_sample=units`

关键 Profile 结果：

- 页面：A4、纵向、上 2.5cm、下 2.0cm、左 3.0cm、右 2.5cm。
- 正文：中文宋体、英文 Times New Roman、12pt、黑色。
- 表格：三线表、表题在表格上方。
- 图件：inline、图题在图片下方。
- 输出：DOCX/PDF 编排字段已在导出层支持。

重要限制：

- LLM 提取结果存在波动：同一规则文档曾返回更长的 86 条规则摘要，最新稳定摘要为 21 条主规则。
- `title_cn.*`、`binding.*` 等 LLM 常见字段如果不在当前 Rule Registry 中，会被标记为不支持或待扩展，避免误导为“已经自动执行”。
- `units` 当前被识别为 unsupported，说明单位/计量/计价规则还需要进一步映射到 `unit_rules` 可执行字段或扩展 schema。

## 4. 已经完成并有证据的部分

### 4.1 Profile JSON 与规则来源

已完成：

- Profile v2 已覆盖页面、正文、标题、文档网格、目录、序号、页眉页脚、表格、图件、摘要、公式、参考文献、单位、模板绑定、交付门、LLM final review、脚注/尾注、附录基础字段。
- Profile 保存 `source_documents`、`rule_evidence`、`missing_fields`、`unsupported_rules`、`capability_coverage`、`locked_fields`。

主要文件：

- `backend/app/profiles/models.py`
- `backend/app/agents/requirements.py`
- `backend/app/documents/rule_registry.py`
- `profiles/ecnu_thesis.yaml`

### 4.2 Agent 规则抽取链路

已完成：

- 对话入口、上传规则文档、上传样本文档都能进入 requirement session。
- 用户补充自然语言时会携带当前 Profile 和 locked fields。
- LLM 未配置或真实生成失败时 fail-closed，不生成假规则。
- LLM 返回对象枚举、未知顶层字段、自然语言枚举、字符串标题层级时，后端会防御式归一化或记录为 unsupported。

主要文件：

- `backend/app/api/requirement_sessions.py`
- `backend/app/agents/requirements.py`
- `backend/tests/test_requirement_sessions_api.py`

### 4.3 前端工作台

已完成：

- Profile 创建与选择。
- 规则文档 / 样本文档 / 待处理文档上传。
- Agent 对话补充。
- 可视化编辑正文、标题、页边距、目录、页眉页脚、图表题注、单位、模板绑定、内部 QC、LLM final review 等字段。
- 规则检查器展示 Agent / Formatter / QC / LLM 支持状态。
- 前端 LLM 状态检测按钮。
- DOCX/PDF 下载入口。

主要文件：

- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/styles.css`

当前限制：

- 前端仍是大型单文件工作台，尚未拆成 feature 组件。
- 规则树仍不是完整 JSON tree inspector。
- 视觉和信息架构比早期好，但还没达到最终商业产品质感。

### 4.4 格式执行与内部 QC

已完成：

- `scripts/build_final_docx.py` 可作为 CLI 样本入口。
- `FormatCompiler` 已形成 candidate -> gate -> final 边界。
- DOCX formatter 支持页面、正文、标题、目录、页眉页脚、题注、三线表、图片尺寸、单位等基础规则。
- 内部交付门会检查 unsupported、DOCX QC、PDF QC、registry verifier dispatch。
- 可安全修复项会自动重做一次，再验一次。

主要文件：

- `backend/app/documents/compiler.py`
- `backend/app/documents/formatter.py`
- `backend/app/quality/delivery_gate.py`
- `backend/app/quality/inspection.py`
- `backend/app/quality/final_layout_review.py`

当前限制：

- Formatter 仍是函数式主流程，没有完全由 Rule Registry 逐字段动态调度。
- 复杂模板、多 slot、多 section、固定页、异常空白页仍需真实样本矩阵验证。
- required final LLM review 还需要和 Agent 生成 Profile 再跑完整真实导出闭环。

## 5. 当前验证记录

本轮最新验证：

- `cd backend && uv run pytest -q`：`186 passed, 2 warnings`
- `cd frontend && npm run build`：通过
- `openspec validate update-production-export --strict --no-interactive`：通过
- `git diff --check`：通过
- `GET /api/health/llm`：`reachable=true`
- 真实华师大格式文档 requirement session：HTTP 201，`status=ready_for_confirmation`

浏览器验证状态：

- `http://127.0.0.1:5174` 可访问。
- Playwright MCP 导航曾超时；随后使用系统 Google Chrome + Playwright 脚本完成前端复验。
- 页面点击“检测 LLM”后显示 `LLM reachable`，并包含 `gpt-5.4 可生成内容`。
- 浏览器 console error / warning 为空。
- API 级 LLM 健康检查已经确认 reachable。

## 6. 明确未完成项

### P0：Agent Profile -> 真实报告导出全链路

未完成：

- 用最新真实 Agent 提取出的 Profile 保存为正式 Profile。
- 用该 Profile 重新格式化真实 RISC-V 课程报告。
- required final LLM review 打开后完成 DOCX/PDF 导出闭环。
- 前端确认最终 DOCX/PDF 可下载。

### P0：字段级能力补齐

未完成：

- `units` 等真实提取 unsupported 字段需要映射或扩展。
- `binding`、封面、目录页、题名页等学校规则需要明确哪些是模板 delegated，哪些由 formatter 执行。
- `title_cn.*`、`title_en.*` 这类 LLM 常见字段需要决定是映射到 `headings[0]`，还是扩展独立 title schema。

### P0：真实样本矩阵

未完成：

- 简单课程报告只完成部分 smoke。
- 复杂毕业论文样本未完整跑通。
- 带封面、声明页、目录、页眉页脚、图表、参考文献、固定模板页的样本未完整跑通。

### P1：前端工程化与视觉

未完成：

- 拆分 `features/profile-intake`、`features/profile-editor`、`features/export`、`features/rule-inspector`。
- 继续优化视觉层级、空状态、进度状态和错误信息。
- 做桌面和移动端截图验收。

## 7. 当前真实完成度判断

按“能否面向真实复杂论文稳定商用”估算：

- 架构和数据契约：约 `78%`
- 前端用户主流程：约 `72%`
- 基础 DOCX 格式执行：约 `70%`
- 内部 QC 与 fail-closed：约 `68%`
- Agent 规则抽取真实可用性：约 `65%`
- 复杂模板适配：约 `35%`
- 真实样本矩阵验收：约 `35%`
- 商业级整体稳定性：约 `58%`

这些百分比不是测试覆盖率，只是按当前证据做的工程进度估算。不能用它们替代验收。

## 8. 下一步最短路径

1. 保存最新真实 Agent 提取出的 ECNU Profile。
2. 把 `units`、title、binding、cover、toc 等字段映射策略补齐：可执行、模板委托、或 unsupported 阻断。
3. 用 Agent Profile 重新格式化真实 RISC-V 报告。
4. 跑 DOCX gate、PDF gate、required final LLM review、`codex-docx-inspect`、`codex-pdf-inspect`。
5. 用前端确认最终 DOCX/PDF 下载。
6. 建立真实样本矩阵，再谈复杂论文高稳定。

## 9. 当前不能说的话

不能说：

- “已经百分百实现。”
- “换任意模板都能完美导出。”
- “复杂论文高稳定已经验证。”
- “所有格式规则都已经能自动执行。”

可以说：

- “LLM 当前已经可用，之前的问题是调用方式和 SSE 解析不兼容。”
- “真实华东师范大学格式规则文档已经可以由 Agent 接口提取成 Profile draft。”
- “系统现在会把不支持字段记录并 fail-closed，避免假成功。”
- “生产化主链路已经搭起来，但距离商业级百分百稳定仍有明确 P0 缺口。”
