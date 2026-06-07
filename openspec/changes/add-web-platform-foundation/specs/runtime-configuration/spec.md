## ADDED Requirements

### Requirement: Environment-driven configuration
The system SHALL load runtime settings from environment variables and local `.env` files without requiring secrets in source code.

#### Scenario: Configuration loads in development
- **WHEN** the backend starts with a valid local environment
- **THEN** it loads database, queue, storage, LLM, and LibreOffice path settings from environment sources

#### Scenario: Optional services are not configured
- **WHEN** optional services such as LLM or LibreOffice are not configured for the foundation stage
- **THEN** the backend still starts for health, upload, and placeholder job APIs while marking those services unavailable or unused

### Requirement: Example environment file
The repository SHALL provide an `.env.example` that documents required and optional runtime variables.

#### Scenario: Developer reads environment example
- **WHEN** a developer opens `.env.example`
- **THEN** it lists `DATABASE_URL`, `REDIS_URL`, `FILE_STORAGE_ROOT`, `LLM_API_KEY`, `LLM_MODEL`, and `SOFFICE_BIN` with comments describing purpose, how to obtain the value, and whether it is required for the foundation stage

#### Scenario: Secrets are excluded
- **WHEN** `.env.example` is committed
- **THEN** it contains no real API keys, tokens, or passwords

### Requirement: Local startup documentation
The repository SHALL document how to start the backend, frontend, and worker in local development.

#### Scenario: Developer follows startup docs
- **WHEN** a developer follows the documented commands
- **THEN** they can install dependencies, start the backend, start the frontend, and run the placeholder worker locally

#### Scenario: Developer runs verification commands
- **WHEN** a developer follows the documented verification section
- **THEN** they can run backend tests and frontend build or tests from the documented commands
