## ADDED Requirements

### Requirement: Extraction result retrieval
The system SHALL expose profile extraction job status and results through the backend API.

#### Scenario: Retrieve queued or running extraction job
- **WHEN** a client requests an extraction job before completion
- **THEN** the API returns the job id, source metadata, current status, and no completed profile draft

#### Scenario: Retrieve completed extraction result
- **WHEN** a client requests a completed extraction job
- **THEN** the API returns the profile draft, uncertain items, evidence, and timestamps

#### Scenario: Retrieve failed extraction result
- **WHEN** a client requests a failed extraction job
- **THEN** the API returns the failed status and readable error message

### Requirement: Web review and confirmation
The web workbench SHALL display Agent extraction results for user review before saving.

#### Scenario: Display extraction result
- **WHEN** an extraction job has completed
- **THEN** the frontend displays the profile draft summary, uncertain items, and evidence without hiding the existing manual profile editor

#### Scenario: Save reviewed draft
- **WHEN** a user edits or confirms the extracted draft and chooses to save it
- **THEN** the frontend sends the draft through the existing profile save API as `draft` or `active` according to the user's selected status

#### Scenario: Do not auto-activate unconfirmed draft
- **WHEN** the Agent extraction completes
- **THEN** the system does not make the extracted profile active unless the user explicitly saves it as active

### Requirement: Extraction UI failure visibility
The web workbench SHALL show extraction validation and Agent failures clearly while preserving manual profile management.

#### Scenario: Display extraction failure
- **WHEN** an extraction job fails due to missing configuration, invalid source, invalid Agent output, or schema validation
- **THEN** the frontend displays the error message and keeps upload/Profile editing controls usable
