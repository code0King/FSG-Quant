## Why

当前 `pdf_parser.py` 使用 PyMuPDF `page.get_text()` 提取文本，中文排版错乱严重，MD&A 章节截断不完整，高管变动表格完全无法解析。需要重构 PDF 提取流程，采用专业工具分层提取，以获取干净、完整的结构化数据供 L2/L3 因子计算。

## What Changes

1. **MD&A 文本提取改用 PDF-Extract-Kit（纯文本模式）** — 替代现有的 PyMuPDF 全文提取 + 章节截断
2. **核心人员变动率从 PDF 董监高表格提取** — 新增 Camelot 表格解析，计算 `终止日期在本年人数 / 总人数`
3. **审计意见判定升级** — 已修复，补充"公允反映"+"所有重大方面"+"企业会计准则"语义推断
4. **PDF 解析流程与 DataLoader 解耦** — 独立 PDF 提取模块，数据写入 governance_data/mda_text 表

## Capabilities

### New Capabilities
- `mda-extraction`: 使用 PDF-Extract-Kit 提取年报 MD&A/董事会报告章节纯文本
- `executive-table-parsing`: 使用 Camelot 提取董监高任职表格，计算核心人员变动率

### Modified Capabilities
- `governance-data`: governance_data 表的 `core_personnel_turnover_rate` 字段从 PDF 表格计算写入，不再硬编码为 0.0

## Impact

- 新增依赖：`pdf-extract-kit`, `camelot-py`, `opencv-python`（PDF-Extract-Kit 依赖）
- 修改文件：`src/data_pipeline/pdf_parser.py`（重构）/ `src/data_pipeline/data_loader.py`（扩展）
- 新增文件：`src/data_pipeline/pdf_extractor.py`（PDF-Extract-Kit 封装）/ `src/data_pipeline/executive_parser.py`（高管表格解析）
- 配置更新：`config/data_source.yaml`（PDF 解析器类型新增选项）
