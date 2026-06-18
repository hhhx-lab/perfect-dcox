## ADDED Requirements

### Requirement: Profile creation workbench
The frontend SHALL provide clear entry points for creating or selecting formatting profiles.

#### Scenario: Conversation entry
- **WHEN** the user chooses the conversation entry
- **THEN** the UI lets the user talk with the Agent, shows extracted rule summaries, missing fields, unsupported rules, and allows saving a named profile

#### Scenario: Format document entry
- **WHEN** the user uploads a format requirement document
- **THEN** the UI shows the Agent extraction state, evidence-backed summary, missing fields, unsupported rules, and allows saving a named profile

#### Scenario: Visual rule entry
- **WHEN** the user edits rules manually
- **THEN** the UI updates the same profile draft contract used by Agent-created drafts

#### Scenario: Advanced visual rule coverage
- **WHEN** the user opens the visual rule editor
- **THEN** the UI exposes editable groups for profile naming, page setup, margins, document grid, body Chinese/Latin font settings, body color, paragraph spacing, first-line indent, heading levels 1 through 3, table of contents, list numbering, header/footer/page number settings, table caption conventions, figure caption conventions, figure sizing, abstract/equation/reference settings, unit rules, template binding, and internal delivery gate settings

### Requirement: Export workbench
The frontend SHALL guide users through profile selection, template binding, document upload, export progress, and final download.

#### Scenario: Export with selected profile
- **WHEN** a user selects a profile and uploads a Word document
- **THEN** the UI can create an export job and display progress, final DOCX/PDF downloads, or concise failure reasons

#### Scenario: Export with optional template
- **WHEN** a user attaches or selects a template before export
- **THEN** the UI sends the template binding to the backend and displays template fit failures distinctly from formatting failures

#### Scenario: No visible quality report workflow
- **WHEN** an export completes or fails
- **THEN** the primary UI does not ask the user to download a QC report or manually run a quality fix loop
