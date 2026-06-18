## ADDED Requirements

### Requirement: Profile v2 rule contract
The system SHALL support a Profile v2 contract that can represent reusable formatting rules, rule provenance, missing fields, unsupported rules, template binding, and delivery gate settings.

#### Scenario: Save a Profile v2 draft
- **WHEN** a valid Profile v2 payload is submitted through profile creation or requirement session confirmation
- **THEN** the system stores the profile version with `schema_version`, formatting sections, template binding data, rule evidence, missing fields, unsupported rules, and delivery gate settings

#### Scenario: Load existing v1 profiles
- **WHEN** an existing v1 profile YAML or metadata record is loaded
- **THEN** the system accepts it with safe default values for v2 fields and preserves existing formatting behavior

#### Scenario: Normalize font color rules
- **WHEN** a profile contains a font color such as black or `#000000`
- **THEN** the saved profile exposes the value as a six-digit uppercase RGB string that the formatter can apply

#### Scenario: Represent advanced Word layout rules
- **WHEN** a user or Agent defines production thesis rules for page grid, table of contents, paragraph spacing, heading spacing, page headers, page footers, page numbers, list numbering, table captions, figure captions, figure sizing, measurement units, or currency units
- **THEN** the profile stores those rules in structured v2 fields with safe defaults for omitted fields

#### Scenario: Represent table and figure academic conventions
- **WHEN** a profile requires table captions above tables, bilingual table captions, three-line tables, inline figures, figure captions below figures, bilingual figure captions, half-column figure width limits, or full-width figure width limits
- **THEN** the profile stores those conventions explicitly so the compiler and internal delivery gate can evaluate them without relying on free-text notes

### Requirement: Agent-derived Profile v2 drafts
The system SHALL require Agent rule intake to produce Profile v2 drafts with evidence, missing fields, and unsupported rules.

#### Scenario: Conversation creates Profile v2 draft
- **WHEN** a user provides formatting requirements through conversation
- **THEN** the requirement session calls the configured LLM provider and stores a Profile v2 draft plus rule summary evidence

#### Scenario: Uploaded format document creates Profile v2 draft
- **WHEN** a user uploads a supported `.doc` or `.docx` formatting requirement document
- **THEN** the requirement session extracts source text, calls the configured LLM provider, and stores a Profile v2 draft plus source evidence

#### Scenario: LLM is unavailable
- **WHEN** a conversation or document rule intake requires LLM analysis but the provider cannot run
- **THEN** the session fails with a readable error and does not create a fake or default profile draft

#### Scenario: Unsupported rules remain explicit
- **WHEN** the Agent or validator identifies a rule that the schema or compiler cannot execute
- **THEN** the rule is recorded in `unsupported_rules` or an equivalent uncertainty list and cannot be counted as compliant
