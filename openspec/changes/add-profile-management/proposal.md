## Why

Profiles are the product's reusable contract for Word formatting rules. The foundation app can upload files and create placeholder jobs, but it cannot yet define, validate, version, view, import, export, or reference deterministic formatting profiles.

## What Changes

- Add a machine-readable format profile schema covering page, fonts, body text, headings, abstracts, table and figure captions, equations, references, and quality settings.
- Add an ECNU thesis profile seeded from the repository's product plan and local ECNU format sample.
- Add backend profile storage, validation, versioning, CRUD, import, export, and archive APIs.
- Add frontend profile list, detail/editor, create draft, save new version, import YAML, and export YAML UI.
- Update placeholder format job creation so callers can reference `profile_id + profile_version` without requiring actual DOCX formatting yet.
- Do not implement Agent profile extraction, document reformatting, quality inspection, organization permissions, or marketplace templates in this change.

## Capabilities

### New Capabilities

- `format-profile-schema`: The system can validate deterministic Word formatting profile definitions and provide the built-in ECNU thesis profile.
- `profile-versioning`: The backend can store profiles, preserve immutable versions, create new draft/active versions, archive profiles, and export/import profile YAML.
- `profile-editor`: The web workbench can list profiles, view/edit core fields through structured controls, import YAML, export YAML, and create placeholder jobs with a selected profile version.

### Modified Capabilities

- None. No archived OpenSpec specs exist for profile management yet.

## Impact

- Adds backend profile models, schema validation, YAML serialization, repository methods, seed loading, and profile API router.
- Extends placeholder job metadata to optionally include `profile_id` and `profile_version`.
- Adds a `profiles/ecnu_thesis.yaml` seed profile and tests for schema validation, API behavior, import/export, and job profile references.
- Updates frontend API client and workbench UI with profile list, editor, import/export, and profile-aware job creation.
- Updates documentation to describe profile storage and the ECNU seed.
