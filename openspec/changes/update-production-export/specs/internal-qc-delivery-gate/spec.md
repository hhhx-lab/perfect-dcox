## ADDED Requirements

### Requirement: Internal QC delivery gate
The system SHALL run an internal QC delivery gate before final DOCX/PDF files are published.

#### Scenario: Validate supported profile rules
- **WHEN** a candidate DOCX is generated from a profile
- **THEN** the internal gate checks supported page, font, paragraph, heading, table, caption, header/footer, and reference rules before publishing

#### Scenario: Validate document health
- **WHEN** a candidate DOCX is generated
- **THEN** the internal gate checks that the file can be parsed, fields can be refreshed, and obvious corrupt or empty outputs are rejected

#### Scenario: Validate PDF readiness
- **WHEN** PDF output is requested
- **THEN** the internal gate verifies the final DOCX can be converted to a readable PDF before the PDF is published

### Requirement: Fail-closed delivery behavior
The system SHALL fail closed when supported rules cannot be verified or safely corrected.

#### Scenario: Safe automatic correction succeeds
- **WHEN** the internal gate finds only safe, whitelisted formatting issues
- **THEN** the system may correct them, rerun internal checks, and publish only if the rerun passes

#### Scenario: Remaining issues block final delivery
- **WHEN** warning, failure, unsupported, or unverified issues remain after automatic correction
- **THEN** the job or batch item is not marked completed and final downloads are not exposed

#### Scenario: No user-visible QC report artifact
- **WHEN** an export fails internal QC
- **THEN** the user-facing API and frontend expose a concise failure reason or requested next action, not a downloadable QC report artifact
