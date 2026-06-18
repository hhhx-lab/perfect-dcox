# Project File Tree

- Root: `/Users/hwaigc/太空垃圾站/文档全能处理/word自定义格式规范`
- Source: `git ls-files`
- File count: 121

```text
.
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── extraction.py
│   │   │   └── requirements.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── batches.py
│   │   │   ├── files.py
│   │   │   ├── jobs.py
│   │   │   ├── profile_extractions.py
│   │   │   ├── profiles.py
│   │   │   ├── quality_reports.py
│   │   │   └── requirement_sessions.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── documents/
│   │   │   ├── __init__.py
│   │   │   ├── converter.py
│   │   │   ├── exporter.py
│   │   │   ├── formatter.py
│   │   │   ├── ooxml.py
│   │   │   ├── parser.py
│   │   │   ├── service.py
│   │   │   └── structure.py
│   │   ├── jobs/
│   │   │   ├── __init__.py
│   │   │   └── worker.py
│   │   ├── profiles/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── seed.py
│   │   ├── quality/
│   │   │   ├── __init__.py
│   │   │   ├── fix_execution.py
│   │   │   ├── fix_planning.py
│   │   │   ├── inspection.py
│   │   │   └── service.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── local.py
│   │   │   └── repository.py
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── models.py
│   ├── tests/
│   │   ├── document_fixtures.py
│   │   ├── test_document_engine.py
│   │   ├── test_document_formatting.py
│   │   ├── test_document_worker.py
│   │   ├── test_foundation.py
│   │   ├── test_production_profile_pipeline.py
│   │   ├── test_profile_extractions.py
│   │   ├── test_profile_extractions_api.py
│   │   ├── test_profiles.py
│   │   ├── test_profiles_api.py
│   │   ├── test_quality_reports.py
│   │   ├── test_quality_reports_api.py
│   │   └── test_requirement_sessions_api.py
│   ├── README.md
│   ├── pyproject.toml
│   └── uv.lock
├── docs/
│   ├── superpowers/
│   │   └── plans/
│   │       └── 2026-06-08-production-format-upgrade.md
│   └── word-format-agent-web-product-plan.md
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── styles.css
│   │   └── vite-env.d.ts
│   ├── .env.example
│   ├── README.md
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── issues/
│   ├── 2026-06-07_23-47-28-add-profile-management.csv
│   ├── 2026-06-08_00-22-35-add-docx-formatting-engine.csv
│   ├── 2026-06-08_01-23-00-add-agent-rule-extraction.csv
│   ├── 2026-06-08_02-18-00-add-quality-fix-loop.csv
│   └── 20260607-225108-add-web-platform-foundation.csv
├── openspec/
│   └── changes/
│       ├── add-agent-rule-extraction/
│       │   ├── specs/
│       │   │   ├── agent-rule-extraction/
│       │   │   │   └── spec.md
│       │   │   ├── profile-draft-confirmation/
│       │   │   │   └── spec.md
│       │   │   └── rule-source-input/
│       │   │       └── spec.md
│       │   ├── .openspec.yaml
│       │   ├── README.md
│       │   ├── design.md
│       │   ├── proposal.md
│       │   └── tasks.md
│       ├── add-docx-formatting-engine/
│       │   ├── specs/
│       │   │   ├── document-input/
│       │   │   │   └── spec.md
│       │   │   ├── document-output/
│       │   │   │   └── spec.md
│       │   │   └── docx-formatting/
│       │   │       └── spec.md
│       │   ├── .openspec.yaml
│       │   ├── README.md
│       │   ├── design.md
│       │   ├── proposal.md
│       │   └── tasks.md
│       ├── add-profile-management/
│       │   ├── specs/
│       │   │   ├── format-profile-schema/
│       │   │   │   └── spec.md
│       │   │   ├── profile-editor/
│       │   │   │   └── spec.md
│       │   │   └── profile-versioning/
│       │   │       └── spec.md
│       │   ├── .openspec.yaml
│       │   ├── README.md
│       │   ├── design.md
│       │   ├── proposal.md
│       │   └── tasks.md
│       ├── add-quality-fix-loop/
│       │   ├── specs/
│       │   │   ├── agent-fix-planning/
│       │   │   │   └── spec.md
│       │   │   ├── quality-fix-loop/
│       │   │   │   └── spec.md
│       │   │   └── quality-reporting/
│       │   │       └── spec.md
│       │   ├── .openspec.yaml
│       │   ├── README.md
│       │   ├── design.md
│       │   ├── proposal.md
│       │   └── tasks.md
│       └── add-web-platform-foundation/
│           ├── specs/
│           │   ├── file-storage/
│           │   │   └── spec.md
│           │   ├── job-orchestration/
│           │   │   └── spec.md
│           │   ├── runtime-configuration/
│           │   │   └── spec.md
│           │   └── web-workbench/
│           │       └── spec.md
│           ├── .openspec.yaml
│           ├── README.md
│           ├── design.md
│           ├── proposal.md
│           └── tasks.md
├── profiles/
│   └── ecnu_thesis.yaml
├── scripts/
│   └── start-dev.sh
├── storage/
│   └── .gitkeep
├── .env.example
├── .gitignore
├── README.md
└── plan.md
```
