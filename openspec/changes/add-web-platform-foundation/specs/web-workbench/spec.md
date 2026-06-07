## ADDED Requirements

### Requirement: Workbench navigation shell
The system SHALL provide a browser-based workbench shell that exposes the core product areas needed by the MVP foundation.

#### Scenario: User opens the workbench
- **WHEN** a user opens the frontend application
- **THEN** the page displays navigation or entry points for file upload, profiles, tasks, quality reports, and outputs

#### Scenario: Backend availability is visible
- **WHEN** the frontend successfully calls the backend health endpoint
- **THEN** the workbench displays the backend as available

#### Scenario: Backend is unavailable
- **WHEN** the frontend cannot reach the backend health endpoint
- **THEN** the workbench displays a non-blocking unavailable state with enough information for local debugging

### Requirement: Upload entry point
The system SHALL allow a user to select a `.doc` or `.docx` file from the workbench and submit it to the backend upload API.

#### Scenario: User uploads supported Word file
- **WHEN** a user selects a `.doc` or `.docx` file and submits the upload form
- **THEN** the frontend sends the file to the backend and displays the returned file identifier and metadata

#### Scenario: User selects unsupported file type
- **WHEN** a user selects a file type outside `.doc` and `.docx`
- **THEN** the frontend prevents submission or displays the backend validation error without creating a task

### Requirement: Task status visibility
The system SHALL allow a user to inspect created job states from the workbench.

#### Scenario: Job is created
- **WHEN** a user creates a placeholder format job for an uploaded file
- **THEN** the task list or task detail view displays the returned job identifier and current lifecycle state

#### Scenario: Job status changes
- **WHEN** a job status changes on the backend
- **THEN** the frontend refreshes or re-fetches the job detail and displays the updated state
