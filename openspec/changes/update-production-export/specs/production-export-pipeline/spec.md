## ADDED Requirements

### Requirement: Compiler-driven export pipeline
The system SHALL generate final DOCX/PDF outputs through one deterministic FormatCompiler path.

#### Scenario: Single document export uses compiler
- **WHEN** a job is created with a valid input file and profile version
- **THEN** the backend converts legacy `.doc` if required, parses DOCX, invokes the FormatCompiler, and produces a candidate DOCX before final delivery

#### Scenario: Batch export reuses single-document path
- **WHEN** a batch run processes multiple input files
- **THEN** each item uses the same compiler-driven job path as single document export

#### Scenario: No alternate formatter path publishes downloads
- **WHEN** an API, worker, script, or batch flow needs to produce downloadable files
- **THEN** it uses the shared compiler/service path rather than a separate ad hoc DOCX mutation path

### Requirement: Template-aware DOCX generation
The system SHALL allow an optional DOCX template binding to participate in final document generation.

#### Scenario: Apply explicit body slot
- **WHEN** a selected template declares a supported body slot marker
- **THEN** the generated candidate DOCX preserves fixed template content and places source document body content into that slot

#### Scenario: Preserve fixed template pages
- **WHEN** a template contains fixed cover, declaration, or table-of-contents pages
- **THEN** the generated candidate DOCX preserves those pages unless the profile marks the corresponding template section unsupported

#### Scenario: Template fit failure blocks delivery
- **WHEN** a template has missing required slots, unreplaced placeholders, duplicate fixed pages, or abnormal blank pages
- **THEN** the internal delivery gate fails the export and no final download is published

### Requirement: Final output publication
The system SHALL only register internally verified deliverables as final output file ids.

#### Scenario: Publish verified DOCX
- **WHEN** the compiler candidate passes the internal delivery gate
- **THEN** the final DOCX is stored as a generated file and its file id is included in `output_file_ids`

#### Scenario: Publish verified PDF
- **WHEN** PDF output is requested and the verified DOCX can be exported and inspected successfully
- **THEN** the final PDF is stored as a generated file and its file id is included in `output_file_ids`

#### Scenario: Block failed candidate
- **WHEN** the candidate DOCX fails compiler, template, QC, or PDF readiness checks
- **THEN** the job exposes a failure status and concise reason, and candidate files are not exposed as final downloads
