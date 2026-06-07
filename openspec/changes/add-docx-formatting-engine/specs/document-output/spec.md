## ADDED Requirements

### Requirement: Formatted output registration
The system SHALL register generated formatted DOCX files and attach them to the formatting job.

#### Scenario: Register formatted DOCX output
- **WHEN** a formatting job completes successfully
- **THEN** the system stores the formatted DOCX, creates a file metadata record for it, and appends its file id to the job `output_file_ids`

#### Scenario: Retrieve output metadata
- **WHEN** a client requests metadata for a generated output file id
- **THEN** the backend returns the same file metadata shape used for uploaded input files

### Requirement: PDF export
The system SHALL export formatted DOCX files to PDF when PDF generation is requested and LibreOffice is available.

#### Scenario: Export PDF output
- **WHEN** a formatting job requests PDF output and DOCX formatting succeeds
- **THEN** the system exports a PDF, registers it as a file metadata record, and appends its file id to the job `output_file_ids`

#### Scenario: PDF export failure is diagnostic
- **WHEN** PDF export fails or LibreOffice is unavailable
- **THEN** the job is marked `failed` or records an explicit export error rather than reporting a successful PDF output

### Requirement: Formatting job lifecycle
The system SHALL expose deterministic formatting job status, progress, outputs, and errors.

#### Scenario: Formatting job completes
- **WHEN** a profile-referenced formatting job processes a valid input and output generation succeeds
- **THEN** the job transitions from `queued` to `running` to `completed`, reaches 100 percent progress, and includes output file ids

#### Scenario: Formatting job fails
- **WHEN** conversion, parsing, profile loading, formatting, or output registration fails
- **THEN** the job transitions to `failed`, reaches 100 percent progress, and includes a readable `error_message`

### Requirement: Frontend output visibility
The web workbench SHALL display generated outputs or formatting errors for a task.

#### Scenario: Display outputs
- **WHEN** a completed formatting job has DOCX or PDF output file ids
- **THEN** the frontend displays those output ids and lets the user inspect their metadata

#### Scenario: Display errors
- **WHEN** a formatting job fails
- **THEN** the frontend displays the error message without hiding the input file or selected profile reference
