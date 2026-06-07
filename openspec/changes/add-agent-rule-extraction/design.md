## Context

The repository now has upload/file metadata APIs, versioned deterministic profiles, a DOCX formatting engine, and a frontend task/profile workbench. Users still need to manually translate school formatting instructions into profile fields. The product plan requires an Agent that can read formatting requirements or natural-language descriptions, but it also requires structured output, source evidence, explicit uncertainty, schema validation, and user confirmation before a profile becomes executable.

No archived OpenSpec specs exist yet, so this change introduces new behavior rather than modifying an existing spec baseline.

## Goals / Non-Goals

**Goals:**

- Create profile extraction jobs from either uploaded `.doc/.docx` rule documents or natural-language text.
- Extract rule document text locally before invoking the Agent, including legacy `.doc` conversion when `SOFFICE_BIN` is configured.
- Ask the Agent for one strict structured result containing `profile_draft`, `uncertain_items`, and `evidence`.
- Validate `profile_draft` with the existing `FormatProfile` schema before it can be saved.
- Surface invalid JSON/YAML, schema errors, missing evidence, and missing LLM configuration as readable extraction job failures or review states.
- Let users inspect, modify, and save extracted drafts through existing profile save APIs.

**Non-Goals:**

- No Agent writes directly to final DOCX files.
- No automatic activation of low-confidence drafts.
- No deep structure-recognition Agent for thesis body content.
- No replacement of the deterministic profile editor or document formatting engine.
- No production-grade queue/database migration beyond the current local JSON repository unless required by existing patterns.

## Decisions

### Store extraction jobs beside existing metadata records

Add extraction job/result records to the JSON metadata repository so the MVP stays local-first and consistent with file, job, and profile storage. Each record should include source type, optional file id, optional natural-language input, status, profile draft, uncertain items, evidence, error message, and timestamps.

Alternative considered: introduce PostgreSQL tables immediately. The current app has no active database integration, so a JSON record keeps the change testable and reversible.

### Keep the LLM behind a narrow extractor interface

Create an Agent service with a provider interface such as `extract_rules(source_text, source_meta) -> AgentExtractionResult`. The default provider reads `LLM_API_KEY` and `LLM_MODEL`; tests can use deterministic fake providers. Prompting and parsing stay behind this boundary so API/worker code only handles validated domain objects.

Alternative considered: call the LLM directly from the API route. That would make validation, tests, and future model swaps messy.

### Validate before persistence as a usable profile

Agent raw output must be parsed and normalized into a strict result model, then `profile_draft` must pass the existing `FormatProfile` schema. Invalid JSON/YAML, missing required fields, invalid enum values, unknown critical fields, or missing evidence should fail the extraction job or mark it `needs_review`; none of these should become active profiles automatically.

Alternative considered: save partial drafts with defaults. That risks hiding hallucinations and violates the plan requirement to expose uncertainty.

### Require evidence and explicit uncertainty

Every extracted rule should either reference a source evidence item or be listed in `uncertain_items` with a field path, message, and suggested handling. The frontend should show these separately from confirmed fields so users can decide before saving.

Alternative considered: rely on an overall confidence score. Per-field evidence is more reviewable and easier to audit.

### Reuse existing profile save flow

The extraction result should produce a draft object that the frontend can load into the existing profile editor/save APIs. Saving as `draft` or `active` remains a user action through existing profile endpoints.

Alternative considered: add a special “promote extraction” endpoint. Reusing profile APIs avoids a second profile lifecycle.

## Risks / Trade-offs

- LLM output may be malformed or hallucinated -> strict output parsing, profile schema validation, evidence requirements, and user confirmation before save.
- `.doc` rule sources require LibreOffice -> fail with clear `SOFFICE_BIN` diagnostics and allow natural-language fallback.
- The ECNU sample is a legacy `.doc` file -> tests should run deterministic extraction from either converted text or a fixture text fallback when LibreOffice is not available.
- JSON repository concurrency is limited -> acceptable for local MVP; keep repository methods isolated for future migration.
- Prompt/provider behavior may vary -> tests should use fake providers for schema behavior and a deterministic ECNU heuristic/provider for smoke coverage, not live API calls by default.

## Migration Plan

No database migration is required for the local JSON repository. Existing metadata files without extraction records remain valid because repository methods can default missing collections to an empty list. Rollback is limited to removing extraction routes/services/UI and leaving existing profiles, uploads, and formatting jobs untouched.

## Open Questions

- Whether later production mode should store Agent raw messages for audit, redaction, and replay.
- Whether user approval should support per-field acceptance instead of editing the whole profile draft.
