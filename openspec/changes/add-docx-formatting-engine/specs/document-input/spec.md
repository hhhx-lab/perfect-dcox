## ADDED Requirements

### Requirement: Legacy DOC conversion
The system SHALL convert legacy `.doc` uploads to `.docx` before any formatting edits are attempted.

#### Scenario: Convert DOC before processing
- **WHEN** a formatting job references an uploaded `.doc` input file and LibreOffice is configured
- **THEN** the system converts the file to an intermediate `.docx` and uses the converted file for parsing and formatting

#### Scenario: Conversion failure is diagnostic
- **WHEN** `.doc` conversion fails or LibreOffice is unavailable
- **THEN** the job is marked `failed` with a readable error message and the original uploaded file remains available

### Requirement: DOCX structure parsing
The system SHALL parse `.docx` files into a compact structural summary before formatting.

#### Scenario: Parse DOCX summary
- **WHEN** a formatting job processes a `.docx` input
- **THEN** the parser reports paragraph count, table count, image or drawing count, heading candidates, and basic paragraph style information

#### Scenario: Invalid DOCX is rejected
- **WHEN** a formatting job receives a corrupt or unreadable `.docx`
- **THEN** the job is marked `failed` with a diagnostic parser error

### Requirement: Input content preservation
The system SHALL preserve existing document text content while parsing and preparing for formatting.

#### Scenario: Parser does not delete text
- **WHEN** a `.docx` input contains normal paragraphs, headings, captions, equations, or references
- **THEN** parsing and preparation do not remove paragraph text from the source document
