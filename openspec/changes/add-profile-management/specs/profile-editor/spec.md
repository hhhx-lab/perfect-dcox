## ADDED Requirements

### Requirement: Profile list UI
The web workbench SHALL display available profiles and their key metadata.

#### Scenario: Profiles are loaded
- **WHEN** the frontend loads profile data from the backend
- **THEN** it displays profile name, status, current version, source, and updated timestamp

#### Scenario: Profile load fails
- **WHEN** the backend profile API is unavailable
- **THEN** the frontend displays a non-blocking error state

### Requirement: Structured profile editing
The web workbench SHALL allow users to edit common profile fields through structured controls.

#### Scenario: User edits common fields
- **WHEN** a user changes fields such as profile name, version, body font, line spacing, page margins, caption positions, or quality flags
- **THEN** the editor updates the draft profile state without requiring direct YAML editing

#### Scenario: User saves edited profile
- **WHEN** a user saves a valid edited profile version
- **THEN** the frontend sends it to the backend and refreshes the profile list/detail after success

#### Scenario: Save validation fails
- **WHEN** the backend rejects a profile save because of validation errors
- **THEN** the frontend displays the error without losing the user's draft

### Requirement: YAML import and export UI
The web workbench SHALL provide YAML import and export controls for advanced profile work.

#### Scenario: User imports valid YAML
- **WHEN** a user submits valid profile YAML
- **THEN** the frontend creates a draft profile through the backend and displays it in the profile list

#### Scenario: User imports invalid YAML
- **WHEN** a user submits invalid profile YAML
- **THEN** the frontend displays the validation error and does not show a successful import

#### Scenario: User exports YAML
- **WHEN** a user exports the selected profile version
- **THEN** the frontend displays or downloads the YAML returned by the backend

### Requirement: Profile-aware job creation UI
The web workbench SHALL allow users to create placeholder jobs with the selected profile version.

#### Scenario: User creates job with selected profile
- **WHEN** a user has uploaded a Word file and selected a profile version
- **THEN** creating a placeholder job sends `profile_id` and `profile_version` with the file id

#### Scenario: No profile selected
- **WHEN** a user creates a placeholder job without selecting a profile
- **THEN** the frontend either sends no profile reference or clearly indicates that the job is unprofiled
