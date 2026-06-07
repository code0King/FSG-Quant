## ADDED Requirements

### Requirement: Extract executive personnel table from annual report
The system SHALL extract the directors, supervisors, and senior management personnel table from annual report PDFs using Camelot (lattice mode), identifying columns: 姓名, 年龄, 职务, 起始日期, 终止日期.

#### Scenario: Extract table with termination dates
- **WHEN** the PDF contains the "董事、监事、高级管理人员和员工情况" section with a table
- **THEN** the system extracts rows and calculates turnover_rate = count(终止日期 in year) / total_rows * 100

#### Scenario: Multiple tables in section
- **WHEN** the personnel section spans multiple pages with separate tables
- **THEN** the system merges all extracted tables before computing turnover rate

#### Scenario: Camelot or Ghostscript not available
- **WHEN** Camelot or Ghostscript is not installed
- **THEN** the system logs a warning and returns turnover_rate = 0.0

### Requirement: Write turnover rate to governance_data
The system SHALL write the computed `core_personnel_turnover_rate` to the governance_data table in the SQLite database.

#### Scenario: Update existing record
- **WHEN** the governance_data record already exists for (stock_code, report_year)
- **THEN** the system updates `core_personnel_turnover_rate` in place

#### Scenario: No table data available
- **WHEN** the personnel table cannot be parsed or is empty
- **THEN** the system sets `core_personnel_turnover_rate` = 0.0 and logs a warning
