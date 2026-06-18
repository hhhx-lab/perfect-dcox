## 1. Profile v2 and Agent Rule Intake

- [x] 1.1 Extend backend `FormatProfile` and frontend API types with Profile v2 metadata, template binding, rule evidence, missing fields, unsupported rules, and delivery gate defaults.
- [x] 1.2 Update requirement session mapping so conversation and format-document intake store Profile v2 drafts and remain fail-closed when the LLM provider is unavailable.
- [x] 1.3 Add tests for v1 compatibility, color normalization, Agent fail-closed behavior, and Profile v2 draft metadata.

## 2. Compiler and Template-Aware Export

- [x] 2.1 Add `backend/app/documents/compiler.py` and `backend/app/documents/template.py` so exports go through a shared FormatCompiler and optional template binding layer.
- [x] 2.2 Update `DocumentFormattingService` and worker/job flow to produce candidate DOCX, run the delivery gate, and register only verified final DOCX/PDF outputs.
- [x] 2.3 Update batch manifest generation so batch items expose final downloads and concise failure reasons without user-visible QC report fields.

## 3. Internal QC Delivery Gate

- [x] 3.1 Add an internal delivery gate wrapper around existing DOCX/PDF inspection that returns pass/fail and concise failure reason without producing user-facing reports.
- [x] 3.2 Add automatic safe correction/rerun behavior where existing whitelist actions can be used without requiring user-facing fix-loop confirmation.
- [x] 3.3 Add tests for passing candidate publication, failing candidate blocking, PDF readiness, and no final file ids on QC failure.

## 4. Frontend Workbench Upgrade

- [x] 4.1 Refactor the frontend workbench into clear sections for Profile creation/selection, template binding, document upload, export progress, and final downloads.
- [x] 4.2 Remove primary user-facing QC report/fix-loop interactions from the export path and replace them with export state and concise failure reasons.
- [x] 4.3 Improve visual design, responsive layout, and scanability of the main workflow using existing React/Vite/lucide stack.

## 5. Documentation and Verification

- [x] 5.1 Update README and module docs to describe Profile v2, template-aware export, internal QC gate, final download semantics, and current capability limits.
- [x] 5.2 Run `openspec validate update-production-export --strict --no-interactive`.
- [x] 5.3 Run `cd backend && uv run pytest` and `cd frontend && npm run build`.
