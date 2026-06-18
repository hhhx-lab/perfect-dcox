## Context

The current implementation already has the right local-first shape: FastAPI APIs, versioned profiles, local file storage, DOC/DOCX conversion, a DOCX formatter, optional PDF export, Agent requirement sessions, and a quality inspection subsystem. The missing production boundary is not another free-form Agent step. The missing boundary is a deterministic contract between rule understanding, document compilation, internal verification, and final delivery.

The target design keeps that separation:

- Agents produce Profile v2 drafts and explanations.
- Profile v2 is the single source of formatting truth.
- Templates provide fixed pages and slots.
- `FormatCompiler` mutates DOCX deterministically.
- Internal QC decides whether the candidate can be published.
- Frontend shows export state and final downloads, not internal inspection artifacts.

## Goals / Non-Goals

**Goals:**

- Support three Profile creation paths: visual editing, Agent conversation, and uploaded format document analysis.
- Require live LLM participation for Agent conversation/document analysis and return explicit failure when unavailable.
- Preserve compatibility with existing v1 profile data while adding v2 metadata and extensibility fields.
- Add a compiler-centered export path that supports optional templates and candidate/final output separation.
- Gate final DOCX/PDF registration on internal validation and safe automatic correction.
- Remove user-facing quality report and fix-loop concepts from the primary frontend export workflow.
- Improve the frontend layout so the core workflow is obvious and visually credible.

**Non-Goals:**

- No production database/Redis migration.
- No semantic rewriting or content generation.
- No guarantee that rules outside Profile v2/supporting QC are automatically compliant.
- No direct browser DOCX compiler as the authoritative path.

## Architecture

### Profile v2 compatibility layer

`FormatProfile` remains the Pydantic entrypoint used by repositories and APIs, but gains optional v2 fields with safe defaults:

- `schema_version`
- `sections`
- `numbering`
- `template_binding`
- `delivery_gate`
- `rule_evidence`
- `missing_fields`
- `unsupported_rules`

Existing v1 YAML and metadata remain valid because v2 fields are optional. New profiles can explicitly set `schema_version: "2.0.0"` and carry richer rule metadata.

### Rule intake

`RequirementSessionService` continues to own conversation and document sessions. It already fails when no provider exists; the target behavior keeps that fail-closed posture and maps provider payloads into Profile v2 metadata. Deterministic guards remain useful, but only as validation/normalization support after the LLM response, not as a fake replacement when the LLM is unavailable.

### Template binding

Templates are represented in Profile v2 as data first:

- template file id or name
- fixed sections such as cover, declaration, toc
- body slot marker
- header/footer inheritance behavior
- placeholder policy

`backend/app/documents/template.py` loads the selected template and returns a binding object for the compiler. For this change, template handling can be conservative: preserve template structure, replace known body slot markers when present, and record unsupported/failed template fit as internal gate failures.

### FormatCompiler

`backend/app/documents/compiler.py` becomes the only production export entrypoint. It composes existing lower-level capabilities:

1. Open or copy input DOCX.
2. Apply optional template binding.
3. Apply profile-driven formatting using existing formatter helpers.
4. Emit a candidate DOCX path and structured compile metadata.

`DocumentFormattingService.format_job` calls the compiler rather than directly calling `format_docx_with_profile` as the final behavior. `format_docx_with_profile` remains as a helper/compatibility layer for supported formatting rules.

### Internal QC delivery gate

The current quality inspection code remains valuable, but the primary export flow should not create downloadable reports. A new internal gate service wraps inspection and returns:

- pass/fail status
- concise failure reason
- issue counts for internal metadata
- whether automatic safe correction was attempted

Only a passing candidate is stored as final output. Failing candidates stay in work storage and are not placed in `output_file_ids`.

### API and frontend contracts

Job and batch records should continue to use existing status fields where possible. The important semantic change is:

- `completed` means final deliverables are internally verified and downloadable.
- `quality_failed` means a candidate exists but the internal delivery gate did not pass.
- `failed` or `export_failed` means conversion/compiler/PDF export failed.

Batch manifest items should expose final DOCX/PDF file ids, download URLs, delivery status, and concise failure reason. They should not expose user-facing report ids in the target flow.

## Decisions

### Keep `FormatProfile` compatible instead of creating a parallel model

Adding optional v2 fields to the existing Pydantic model keeps repositories, YAML import/export, and frontend API types straightforward. A separate model would require broad migration before the compiler can be useful.

### Gate final file registration, not just UI display

If a candidate fails internal QC, it should not be stored as a normal generated output. This prevents accidental download paths from bypassing the frontend state.

### Reuse quality inspection internally

The existing inspection and safe repair work is useful. The change is product boundary: no user-facing quality report artifact in the main workflow. Internal code can still use issue objects to decide whether the candidate is publishable.

### Keep template support conservative

Full Word template merging is complex. The first production version should support fixed page preservation and explicit slot replacement where the template declares a marker. Unsupported template situations should fail clearly instead of silently corrupting layout.

## Risks / Trade-offs

- Optional v2 fields keep compatibility but can make unsupported cases easy to ignore; internal gate checks must enforce fail-closed behavior.
- Template merging through `python-docx` has limitations; conservative slot rules reduce corruption risk.
- Existing frontend state is concentrated in `App.tsx`; redesign should improve UX without introducing a sprawling partial rewrite.
- Tests must avoid requiring a live external LLM; fail-closed and provider-stub paths should cover the contract.

## Migration Plan

- Existing v1 profiles default to `schema_version: "1.0.0"` or an equivalent compatibility value.
- New Profile v2 fields default to empty lists/objects or conservative delivery gate settings.
- Existing output files remain readable as normal `FileRecord`s.
- Existing quality report APIs may remain for backwards compatibility, but the main job/batch/frontend path should no longer depend on user-visible report downloads.

## Open Questions

- Whether future versions should store templates as first-class records instead of file ids plus profile binding.
- Whether unsupported rules should eventually produce an internal-only audit artifact for operators, while keeping it out of the user product flow.
