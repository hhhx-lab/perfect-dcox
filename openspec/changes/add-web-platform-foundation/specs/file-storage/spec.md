## ADDED Requirements

### Requirement: Word file upload
The system SHALL accept single-file uploads for `.doc` and `.docx` Word documents through the backend API.

#### Scenario: Upload DOCX file
- **WHEN** a client uploads a valid `.docx` file
- **THEN** the backend stores the original file and returns a `file_id`, filename, MIME type, size, sha256, and created timestamp

#### Scenario: Upload legacy DOC file
- **WHEN** a client uploads a valid `.doc` file
- **THEN** the backend stores the original file and returns a `file_id`, filename, MIME type, size, sha256, and created timestamp

#### Scenario: Reject unsupported upload
- **WHEN** a client uploads a file whose extension is not `.doc` or `.docx`
- **THEN** the backend rejects the upload with a validation error and does not create file metadata

### Requirement: File metadata retrieval
The system SHALL expose uploaded file metadata by file identifier.

#### Scenario: Retrieve existing file metadata
- **WHEN** a client requests metadata for an existing `file_id`
- **THEN** the backend returns the original filename, MIME type, size, sha256, storage path, and created timestamp

#### Scenario: Retrieve missing file metadata
- **WHEN** a client requests metadata for a missing `file_id`
- **THEN** the backend returns a not found error

### Requirement: Configurable local storage root
The system SHALL store uploaded originals under a configurable local storage root for development.

#### Scenario: Storage root is configured
- **WHEN** `FILE_STORAGE_ROOT` is configured
- **THEN** uploaded files are written under that directory using generated identifiers rather than user-provided filenames as paths

#### Scenario: Storage write fails
- **WHEN** the backend cannot write the uploaded file to storage
- **THEN** the upload request fails with a diagnostic error and no successful metadata record is returned
