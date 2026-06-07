## 1. Profile Schema and Seed

- [ ] 1.1 Add typed backend profile models that validate deterministic profile sections, enum values, numeric ranges, and unknown fields.
- [ ] 1.2 Add the built-in `ecnu_thesis` YAML seed profile with source-derived page, font, body, heading, caption, equation, reference, and quality settings.
- [ ] 1.3 Add backend schema tests for valid ECNU YAML, missing required fields, invalid enum/range values, and unknown fields.

## 2. Backend Profile APIs and Versioning

- [ ] 2.1 Extend the JSON metadata repository to persist profile summaries and immutable profile version records.
- [ ] 2.2 Add profile list, detail/version retrieval, create-version, archive, YAML import, and YAML export APIs.
- [ ] 2.3 Extend placeholder job creation and job records with optional `profile_id` and `profile_version`, rejecting missing profile references.
- [ ] 2.4 Add API tests for profile CRUD/versioning, import/export, archive behavior, and job profile references.

## 3. Frontend Profile Workbench

- [ ] 3.1 Extend the frontend API client with profile summary/detail, save version, archive, import, export, and profile-aware job creation calls.
- [ ] 3.2 Add profile list and detail loading UI that displays name, status, current version, source, and updated timestamp with non-blocking errors.
- [ ] 3.3 Add structured profile editing controls for common page, body, heading, caption, and quality fields, saving valid edits as new versions.
- [ ] 3.4 Add YAML import/export controls that surface backend validation errors without losing draft state.
- [ ] 3.5 Update placeholder job creation UI to send the selected `profile_id + profile_version` when a profile is selected.

## 4. Documentation and Verification

- [ ] 4.1 Update README documentation for profile storage, ECNU seed data, API routes, frontend workflow, and the current no-formatting boundary.
- [ ] 4.2 Run backend tests and frontend build verification for the profile management workflow.
