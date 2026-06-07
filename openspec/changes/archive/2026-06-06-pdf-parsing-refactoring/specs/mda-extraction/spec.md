## ADDED Requirements

### Requirement: Extract MD&A text from annual report PDF
The system SHALL extract the Management Discussion & Analysis (MD&A) section text from A-share annual report PDFs using PDF-Extract-Kit (pure text mode, no tables/images).

#### Scenario: Successful extraction of MDA section
- **WHEN** an annual report PDF contains "管理层讨论与分析" chapter
- **THEN** the system returns the full text content of that chapter with correct reading order

#### Scenario: Fallback to "董事会报告" when MDA not found
- **WHEN** the PDF does not contain "管理层讨论与分析" but has "董事会报告"
- **THEN** the system extracts the "董事会报告" section instead

#### Scenario: PDF-Extract-Kit not installed
- **WHEN** PDF-Extract-Kit is not available
- **THEN** the system falls back to PyMuPDF text extraction with a warning log

#### Scenario: Cache existing extraction result
- **WHEN** the same PDF has been previously processed
- **THEN** the system returns the cached result without re-parsing
