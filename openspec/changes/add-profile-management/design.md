## Context

The foundation change introduced FastAPI endpoints, local JSON metadata, file upload, placeholder jobs, and a React workbench. Profile management now needs to become the deterministic configuration layer that later document formatting and quality changes can consume.

The repository currently has no archived profile specs. This change therefore adds profile capabilities as new spec deltas and keeps persistence compatible with the existing local JSON repository.

## Goals / Non-Goals

**Goals:**

- Define a typed profile model that validates required formatting sections and rejects malformed profiles.
- Seed an `ecnu_thesis` profile based on the local ECNU format sample and the product plan.
- Store profile versions immutably enough that jobs can reference `profile_id + profile_version`.
- Expose API endpoints for list/detail/create-version/archive/import/export.
- Provide a web profile management surface with structured fields for common edits and YAML import/export for advanced use.
- Allow placeholder jobs to carry profile references while still not performing formatting.

**Non-Goals:**

- No Agent extraction from natural language or format documents.
- No actual DOCX formatting, PDF conversion, or quality inspection.
- No organization-level permissions, collaborative approval, or paid template marketplace.

## Decisions

### Represent profiles as typed Pydantic models plus YAML files

Pydantic gives the backend strong validation and field-level errors. YAML keeps profiles readable, exportable, and easy to seed from `profiles/ecnu_thesis.yaml`.

Alternative considered: store free-form JSON only. That would be faster initially but would allow prompt-like or incomplete profiles to enter the system, violating the plan's requirement that profiles be deterministic.

### Extend the existing JSON repository for profile metadata and versions

The foundation already uses local JSON metadata for files and jobs. Extending it keeps MVP local startup simple and avoids introducing PostgreSQL before the profile behavior is proven.

Alternative considered: add database migrations now. That is more production-like but unnecessary for this stage and would complicate local verification.

### Treat versions as explicit records, not mutable profile blobs

Every save creates a version record. A profile's current version can point to the latest active version, while previous versions remain retrievable for job references and export.

Alternative considered: overwrite the profile in place. That is simpler but breaks traceability for historical jobs.

### Provide structured editing for common fields and YAML for advanced edits

The UI should not force ordinary users into YAML, but YAML import/export is needed for reproducibility and advanced profile work.

Alternative considered: YAML-only UI. That is compact but poor for the target workflow and would make validation errors harder to understand.

### Add profile references to placeholder jobs without formatting behavior

Job creation can accept `profile_id + profile_version` now, so later formatting work can rely on the contract. The worker remains a placeholder and does not interpret profile rules yet.

Alternative considered: wait until DOCX formatting to add profile references. That would delay an important API contract and make frontend profile selection harder to validate.

## Risks / Trade-offs

- ECNU profile may over-interpret ambiguous school rules → Keep it source-derived, limited to documented fields, and editable by users.
- JSON persistence has limited concurrency semantics → Use it for MVP only and keep profile storage behind repository methods.
- YAML import can be malformed or too broad → Validate through the profile model before saving and return field-level errors.
- UI structured editing can cover only part of the schema → Keep YAML advanced mode for full-fidelity import/export.
- Existing `add-web-platform-foundation` change remains active → This change adds separate deltas and should later be archived in dependency order.
