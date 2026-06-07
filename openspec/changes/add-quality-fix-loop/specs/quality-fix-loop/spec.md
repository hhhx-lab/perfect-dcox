## ADDED Requirements

### Requirement: User-confirmed fix execution
The system SHALL require explicit user confirmation before executing automatic quality fixes.

#### Scenario: Do not execute unconfirmed fix plan
- **WHEN** a fix plan exists but the user has not confirmed it
- **THEN** the system does not create a fix job or modify output files

#### Scenario: Execute confirmed fix plan
- **WHEN** a user confirms a schema-valid fix plan
- **THEN** the system creates a second-pass fix job that records original report id, selected issue ids, selected actions, and status

### Requirement: Fix loop lineage
The system SHALL preserve report and output lineage across second-pass fixes.

#### Scenario: Preserve original report
- **WHEN** a second-pass fix job runs
- **THEN** the original quality report remains available and the fix record references it

#### Scenario: Link updated report
- **WHEN** a second-pass fix job produces new outputs and a new quality report
- **THEN** the fix record references the new output ids and updated report id

### Requirement: Frontend report and fix-loop visibility
The web workbench SHALL display quality reports, explanations, fix plans, and remaining issue summaries.

#### Scenario: Display grouped quality report
- **WHEN** a quality report is available
- **THEN** the frontend displays pass, fixed, warning, fail, and unsupported groups with counts and issue details

#### Scenario: Display remaining issues after fix
- **WHEN** a report still has warning, fail, or unsupported issues after a fix loop
- **THEN** the frontend displays the remaining issue summary instead of “全部合规”
