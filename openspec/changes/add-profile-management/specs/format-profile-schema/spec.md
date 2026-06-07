## ADDED Requirements

### Requirement: Deterministic profile schema
The system SHALL validate Word formatting profiles as deterministic structured data rather than free-form prompts.

#### Scenario: Valid profile is accepted
- **WHEN** a profile includes required sections for identity, page, fonts, body, headings, captions, equations, references, and quality settings
- **THEN** the system accepts it as a valid profile definition

#### Scenario: Missing required field is rejected
- **WHEN** a profile omits a required field such as `id`, `name`, `version`, page margins, or body font settings
- **THEN** the system rejects it with a field-level validation error

#### Scenario: Invalid enum or numeric range is rejected
- **WHEN** a profile includes unsupported status, orientation, caption position, or invalid numeric values
- **THEN** the system rejects it with a field-level validation error

### Requirement: Built-in ECNU thesis profile
The system SHALL provide a built-in `ecnu_thesis` profile based on repository source materials.

#### Scenario: ECNU profile is available
- **WHEN** the profile service starts
- **THEN** `ecnu_thesis` is available with status `active`, version `1.0.0`, and source `system`

#### Scenario: ECNU profile includes required format fields
- **WHEN** a client retrieves the ECNU profile version
- **THEN** it contains A4 page settings, documented margins, Songti/Heiti/Times New Roman font rules, body line spacing, heading rules, abstract settings, table and figure captions, equation settings, reference settings, and quality flags

### Requirement: YAML profile serialization
The system SHALL import and export profile versions as YAML without losing validated profile fields.

#### Scenario: Export profile YAML
- **WHEN** a client requests YAML for a profile version
- **THEN** the system returns YAML representing the validated profile definition

#### Scenario: Import valid YAML
- **WHEN** a client submits valid profile YAML
- **THEN** the system validates it and creates a draft profile version

#### Scenario: Import invalid YAML
- **WHEN** a client submits malformed YAML or YAML that fails schema validation
- **THEN** the system rejects the import and does not save a profile version
