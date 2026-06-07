## ADDED Requirements

### Requirement: Placeholder format job creation
The system SHALL create an observable placeholder format job for a previously uploaded Word file.

#### Scenario: Create job for uploaded file
- **WHEN** a client requests a placeholder format job with an existing `file_id`
- **THEN** the backend returns a `job_id`, job type, input file identifier, current status, and created timestamp

#### Scenario: Create job for missing file
- **WHEN** a client requests a placeholder format job with a missing `file_id`
- **THEN** the backend rejects the request and does not create a job

### Requirement: Job lifecycle states
The system SHALL represent job progress using explicit lifecycle states.

#### Scenario: Job is queued
- **WHEN** a placeholder format job is first created
- **THEN** the job status is `queued` or another documented initial state

#### Scenario: Job is processed
- **WHEN** a worker processes the placeholder job
- **THEN** the job status transitions to `running` and then to `completed` or `failed`

#### Scenario: Job fails
- **WHEN** placeholder processing encounters an error
- **THEN** the job status becomes `failed` and the job includes a human-readable error message

### Requirement: Job status retrieval
The system SHALL expose job status and metadata by job identifier.

#### Scenario: Retrieve existing job
- **WHEN** a client requests an existing `job_id`
- **THEN** the backend returns job type, status, progress or current step if available, input file identifier, output references if available, and timestamps

#### Scenario: Retrieve missing job
- **WHEN** a client requests a missing `job_id`
- **THEN** the backend returns a not found error
