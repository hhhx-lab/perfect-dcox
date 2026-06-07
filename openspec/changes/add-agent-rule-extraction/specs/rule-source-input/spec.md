## ADDED Requirements

### Requirement: Rule document extraction source
The system SHALL create profile extraction jobs from uploaded `.doc` and `.docx` formatting requirement documents.

#### Scenario: Create extraction job from DOCX source
- **WHEN** a user starts profile extraction with a valid uploaded `.docx` file id
- **THEN** the system creates a queued extraction job that records the file id and source type `document`

#### Scenario: Convert DOC source before extraction
- **WHEN** a user starts profile extraction with a valid uploaded `.doc` file id and LibreOffice is configured
- **THEN** the system converts the rule source to readable DOCX/text before invoking the Agent

#### Scenario: Reject unsupported rule source file
- **WHEN** a user starts profile extraction with a missing file id or unsupported file type
- **THEN** the API rejects the request or the job fails with a readable source error

### Requirement: Natural-language extraction source
The system SHALL create profile extraction jobs from natural-language formatting requirements without requiring an uploaded file.

#### Scenario: Create extraction job from natural language
- **WHEN** a user submits non-empty natural-language formatting rules
- **THEN** the system creates a queued extraction job with source type `natural_language`

#### Scenario: Reject empty extraction source
- **WHEN** a user submits neither a valid rule document nor non-empty natural-language text
- **THEN** the API rejects the request with a readable validation error

### Requirement: Extraction source traceability
The system SHALL retain enough source metadata for review and diagnostics.

#### Scenario: Source metadata is recorded
- **WHEN** an extraction job is created
- **THEN** the result includes source type, source file id when present, and timestamps for created/updated state
