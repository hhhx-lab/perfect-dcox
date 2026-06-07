## ADDED Requirements

### Requirement: Structured Agent extraction result
The system SHALL require the Rule Extraction Agent to return structured output containing a profile draft, uncertain items, and evidence.

#### Scenario: Return structured extraction result
- **WHEN** an extraction job completes successfully
- **THEN** the result contains `profile_draft`, `uncertain_items`, and `evidence`

#### Scenario: Uncertain items include review guidance
- **WHEN** the Agent cannot confidently map a rule to the profile schema
- **THEN** each uncertain item includes a field path, message, and suggested handling

#### Scenario: Evidence is attached to extracted rules
- **WHEN** the Agent claims a formatting rule as extracted from a source
- **THEN** the result includes evidence that references source text or marks the field as lacking direct evidence

### Requirement: Profile schema validation
The system SHALL validate Agent-generated profile drafts against the existing profile schema before they can be saved.

#### Scenario: Valid profile draft is accepted for review
- **WHEN** the Agent returns a profile draft that passes schema validation
- **THEN** the extraction job stores the draft and makes it available for user review

#### Scenario: Invalid profile draft fails safely
- **WHEN** the Agent returns missing required fields, invalid enum values, unknown critical fields, or schema-invalid data
- **THEN** the extraction job is marked `failed` or `needs_review` with a readable validation error and the draft is not saved as a usable profile

### Requirement: LLM configuration and output safety
The system SHALL fail extraction jobs safely when the LLM is unavailable or returns invalid structured output.

#### Scenario: Missing LLM configuration is diagnostic
- **WHEN** an extraction job requires the Agent but `LLM_API_KEY` or `LLM_MODEL` is not configured
- **THEN** the job fails with a readable configuration error and existing manual profile management remains usable

#### Scenario: Invalid Agent output is diagnostic
- **WHEN** the Agent returns invalid JSON/YAML or omits required result sections
- **THEN** the job fails with a readable Agent output error and no profile is created automatically

### Requirement: ECNU sample extraction coverage
The system SHALL extract key profile fields from the local ECNU formatting requirements sample.

#### Scenario: Extract ECNU formatting rules
- **WHEN** extraction runs on `格式集/华东师范大学毕业论文格式要求.doc` or its extracted text
- **THEN** the profile draft includes A4 page size, page margins, body first-line indent, 1.5 line spacing, Times New Roman Latin font, abstract length range, SimSun body font, SimHei heading font, page number placement, three-line table rule, figure/table caption placement, and equation alignment or numbering guidance
