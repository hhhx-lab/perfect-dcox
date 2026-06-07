## ADDED Requirements

### Requirement: Structured quality report
The system SHALL generate structured quality reports for formatted document outputs.

#### Scenario: Generate quality report for formatted output
- **WHEN** a formatted output is inspected against a profile
- **THEN** the report contains a report id, related job/output/profile references, summary counts, issue list, timestamps, and status groups

#### Scenario: Quality report does not imply all compliant
- **WHEN** a report contains warning, fail, or unsupported issues
- **THEN** the report summary and frontend SHALL NOT present the output as fully compliant

### Requirement: Quality status classification
The system SHALL classify quality checks using `pass`, `fixed`, `warning`, `fail`, and `unsupported`.

#### Scenario: Group issues by quality status
- **WHEN** a report contains checks with different statuses
- **THEN** the system groups and counts issues for each status

#### Scenario: Unsupported checks remain visible
- **WHEN** a feature cannot be judged by the current toolchain
- **THEN** the report records an `unsupported` issue with a readable reason instead of marking it `pass`

### Requirement: DOCX quality checks
The system SHALL inspect common thesis formatting rules in DOCX outputs.

#### Scenario: Inspect DOCX profile rules
- **WHEN** a DOCX output and profile are available
- **THEN** the system checks page margins, body paragraph style, heading style, basic three-line table rules, figure/table caption placement, raw LaTeX residue, and page-number presence or unsupported status

#### Scenario: Detect DOCX formatting failures
- **WHEN** a DOCX output violates a supported profile rule
- **THEN** the report includes a warning or fail issue with profile rule reference, location, and suggested action

### Requirement: PDF quality checks
The system SHALL inspect basic PDF deliverability when a PDF output is available.

#### Scenario: Inspect PDF deliverability
- **WHEN** a PDF output is available
- **THEN** the system checks whether the file opens, page count is greater than zero, text is extractable, and obvious blank pages are not present

#### Scenario: PDF check failure is explicit
- **WHEN** the PDF cannot be opened, has zero pages, or has no extractable text
- **THEN** the report records a fail or unsupported issue with a readable diagnostic
