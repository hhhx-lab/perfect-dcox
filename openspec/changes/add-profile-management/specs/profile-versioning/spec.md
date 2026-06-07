## ADDED Requirements

### Requirement: Profile listing and detail
The system SHALL expose profile summaries and detailed profile versions through backend APIs.

#### Scenario: List profiles
- **WHEN** a client requests the profile list
- **THEN** the backend returns profile id, name, status, current version, source, and updated timestamp for each profile

#### Scenario: Get profile version
- **WHEN** a client requests an existing `profile_id` and version
- **THEN** the backend returns the validated profile definition and version metadata

#### Scenario: Get missing profile
- **WHEN** a client requests a missing profile or version
- **THEN** the backend returns a not found error

### Requirement: Versioned profile saves
The system SHALL create a new version record when a profile is saved rather than overwriting historical versions.

#### Scenario: Create draft profile
- **WHEN** a client submits a valid new profile with status `draft`
- **THEN** the backend creates a profile record and stores the submitted version

#### Scenario: Save new profile version
- **WHEN** a client saves changes to an existing profile with a new version string
- **THEN** the backend stores a new version and keeps prior versions retrievable

#### Scenario: Reject duplicate version
- **WHEN** a client attempts to save a version string that already exists for the profile
- **THEN** the backend rejects the request without overwriting the existing version

### Requirement: Profile archive
The system SHALL allow a profile to be archived without deleting historical versions.

#### Scenario: Archive profile
- **WHEN** a client archives an existing profile
- **THEN** the profile status becomes `archived` and its versions remain retrievable

### Requirement: Jobs reference profile versions
The system SHALL allow placeholder format jobs to optionally reference a specific profile version.

#### Scenario: Create job with profile reference
- **WHEN** a client creates a placeholder job with an existing `profile_id` and `profile_version`
- **THEN** the job record stores both values

#### Scenario: Reject job with missing profile reference
- **WHEN** a client creates a job with a missing profile id or version
- **THEN** the backend rejects the request and does not create a job
