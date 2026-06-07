## 1. Dependencies and Document Module Foundation

- [ ] 1.1 Add project-local document processing dependencies and create backend document module structure.
- [ ] 1.2 Add test helpers for generating minimal DOCX fixtures and inspecting formatted DOCX outputs.

## 2. Document Input Conversion and Parsing

- [ ] 2.1 Implement LibreOffice adapter for `.doc` to `.docx` conversion with diagnostic failure errors.
- [ ] 2.2 Implement DOCX parser that returns paragraph, table, image/drawing, heading candidate, and style summaries.
- [ ] 2.3 Add tests for DOCX parsing, corrupt DOCX failure, content preservation, and `.doc` conversion failure when LibreOffice is unavailable.

## 3. Profile-Based DOCX Formatting

- [ ] 3.1 Implement page, body paragraph, and heading formatting from a selected profile.
- [ ] 3.2 Implement caption, equation, reference paragraph, and basic three-line table formatting helpers.
- [ ] 3.3 Add tests confirming ECNU profile margins, body fonts, line spacing, first-line indent, heading style, table borders, and text preservation in formatted DOCX.

## 4. Output Registration and Worker Lifecycle

- [ ] 4.1 Extend local file storage/repository support for registering generated DOCX and PDF output files.
- [ ] 4.2 Implement document formatting service that resolves input/profile, formats DOCX, optionally exports PDF, and returns output file records.
- [ ] 4.3 Update worker lifecycle so profile-referenced formatting jobs run the document engine and record completed/failed status, progress, outputs, and diagnostic errors.
- [ ] 4.4 Add backend API/worker tests for successful formatted DOCX output, missing profile/input failure, and PDF export failure diagnostics.

## 5. Frontend Output Visibility

- [ ] 5.1 Extend frontend API usage and task panel to load output file metadata for job `output_file_ids`.
- [ ] 5.2 Display DOCX/PDF output metadata, selected profile reference, and formatting errors without hiding uploaded file context.

## 6. Documentation and Verification

- [ ] 6.1 Update README documentation for DOC/DOCX conversion, formatting engine limits, PDF export, environment requirements, and verification commands.
- [ ] 6.2 Run OpenSpec validation, backend tests, frontend build, and document tool smoke checks for generated DOCX/PDF outputs.
