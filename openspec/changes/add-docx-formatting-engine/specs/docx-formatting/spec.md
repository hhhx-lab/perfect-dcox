## ADDED Requirements

### Requirement: Profile page and body formatting
The system SHALL apply selected profile page and body text settings to formatted DOCX outputs.

#### Scenario: Apply page settings
- **WHEN** a formatting job runs with a valid profile version
- **THEN** the output DOCX uses the profile page size, orientation, and margins

#### Scenario: Apply body paragraph settings
- **WHEN** normal body paragraphs are formatted
- **THEN** the output DOCX applies the profile body Chinese and Latin fonts, font size, line spacing, first-line indent, and alignment without changing paragraph text

### Requirement: Heading and special paragraph formatting
The system SHALL apply profile rules to headings and common thesis special paragraphs using deterministic heuristics.

#### Scenario: Apply heading styles
- **WHEN** a paragraph is already styled as a heading or matches a conservative heading candidate pattern
- **THEN** the output DOCX applies the matching profile heading font, alignment, and style metadata

#### Scenario: Apply caption and equation paragraph settings
- **WHEN** paragraphs look like table captions, figure captions, or equation paragraphs
- **THEN** the output DOCX applies profile caption or equation alignment and font settings without rewriting the caption or formula text

#### Scenario: Apply reference paragraph settings
- **WHEN** paragraphs are in or after a references section
- **THEN** the output DOCX applies the profile reference font and hanging-indent defaults without changing reference content

### Requirement: Table basic formatting
The system SHALL apply profile table rules for common thesis tables.

#### Scenario: Apply basic three-line table style
- **WHEN** a formatting job processes ordinary DOCX tables
- **THEN** the output DOCX applies profile-driven basic top, header-bottom, and bottom borders while preserving cell text

### Requirement: Conservative unsupported handling
The system SHALL preserve structures it cannot safely transform.

#### Scenario: Unsupported structure is preserved
- **WHEN** the formatter encounters complex Word structures it cannot safely edit
- **THEN** the formatter leaves the structure in place and continues formatting supported content where possible
