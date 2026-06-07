## 1. Quality Report Models and Storage

- [x] 1.1 Add quality report, quality issue, fix plan, and fix loop record models.
- [x] 1.2 Extend the JSON metadata repository with quality report and fix loop persistence.
- [x] 1.3 Add repository tests for report grouping, legacy metadata defaults, and fix loop lineage records.

## 2. DOCX and PDF Quality Checks

- [x] 2.1 Implement DOCX quality inspection for profile margins, body style, headings, table borders, captions, raw LaTeX residue, and page-number unsupported status.
- [x] 2.2 Implement PDF quality inspection for openability, page count, text extractability, and blank-page warnings.
- [x] 2.3 Add quality service tests for pass, warning, fail, and unsupported report generation.

## 3. Agent Fix Planning

- [x] 3.1 Implement deterministic issue explanations and whitelisted fix-plan schema validation.
- [x] 3.2 Add fix-plan tests for supported actions, unsafe actions, manual-review items, and missing LLM fallback behavior.

## 4. Quality API

- [x] 4.1 Add quality report creation and retrieval APIs for formatted output files.
- [ ] 4.2 Add fix-plan creation and user-confirmed fix-loop APIs.
- [ ] 4.3 Add API tests for report retrieval, grouped status counts, fix-plan validation, and confirmation gating.

## 5. Frontend Quality Review

- [ ] 5.1 Extend frontend API client types and methods for quality reports, fix plans, and fix loops.
- [ ] 5.2 Add quality report panel grouped by pass/fixed/warning/fail/unsupported with remaining issue summary.
- [ ] 5.3 Add fix-plan review and confirmation controls without displaying “全部合规” when unresolved issues remain.

## 6. Documentation and Verification

- [ ] 6.1 Update README, backend README, and frontend README for quality reports, Agent fix safety, and verification commands.
- [ ] 6.2 Run OpenSpec validation, backend tests, frontend build, quality smoke tests, and hardcoded secret scan.
