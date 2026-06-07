## ADDED Requirements

### Requirement: Agent issue explanation
The system SHALL provide user-readable explanations for warning and fail quality issues.

#### Scenario: Explain quality issue
- **WHEN** a quality report contains warning or fail issues
- **THEN** the Agent explanation includes the issue id, reason, impact, whether automatic repair is allowed, and manual-review guidance when needed

#### Scenario: Unsupported issue explanation
- **WHEN** a quality issue is unsupported by the current toolchain
- **THEN** the explanation states that the system cannot judge or repair it automatically

### Requirement: Structured fix plan
The system SHALL represent fix suggestions as schema-valid structured plans.

#### Scenario: Create whitelisted fix plan
- **WHEN** a warning or fail issue is automatically repairable
- **THEN** the fix plan includes only whitelisted formatting actions, target issue ids, parameters, and `requires_user_confirmation=true`

#### Scenario: Reject unsafe fix action
- **WHEN** a fix plan contains an unknown action, semantic edit, formula-content edit, reference-content edit, or missing issue target
- **THEN** the system rejects the plan with a readable validation error

### Requirement: Deterministic fallback explanations
The system SHALL provide deterministic fix guidance when live Agent configuration is unavailable.

#### Scenario: LLM unavailable fallback
- **WHEN** `LLM_API_KEY` or `LLM_MODEL` is not configured
- **THEN** the system still returns deterministic explanations and fix-plan candidates for known supported quality issues
