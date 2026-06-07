## 1. 依赖与环境准备

- [x] 1.1 在 requirements.txt 中添加 pdf-extract-kit、camelot-py 可选依赖
- [x] 1.2 新增 src/data_pipeline/pdf_extractor.py（PDF-Extract-Kit 封装），含纯文本模式提取函数和 PyMuPDF 降级路径
- [x] 1.3 新增 src/data_pipeline/executive_parser.py（Camelot 封装），含董监高表格解析与 turnover 计算函数，含 Camelot/Ghostscript 缺失降级

## 2. MDA 文本提取

- [x] 2.1 实现章节定位逻辑：按优先级匹配 "管理层讨论与分析" → "董事会报告" → "经营情况讨论与分析"，提取完整章节文本
- [x] 2.2 实现中间结果缓存：已解析的 PDF 章节文本写入 data/cache/parsed_mda/ 目录（Parquet 格式）
- [x] 2.3 重构 pdf_parser.py：_extract_text 方法增加 PDF-Extract-Kit 分支，替换 PyMuPDF 为默认首选

## 3. 高管人员变动率提取

- [x] 3.1 实现 Camelot 表格提取函数：定位董监高章节、提取表格、合并多页表格
- [x] 3.2 实现 turnover 计算逻辑：解析姓名/职务/起始日期/终止日期列，统计终止日期在本年的人数 / 总人数
- [x] 3.3 集成到 governance_data：新增 update_governance_turnover(db_path, stock_code, year, turnover_rate) 函数
- [x] 3.4 在 quantdb_bridge.py 的 create_database 中集成 turnover 数据获取（优先 PDF → 降级 0.0）

## 4. 测试与验证

- [x] 4.1 为 pdf_extractor.py 编写单元测试（含正常、降级、缓存场景）
- [x] 4.2 为 executive_parser.py 编写单元测试（含表格解析、turnover 计算、降级场景）
- [x] 4.3 为 pdf_parser.py 重构方法编写集成测试
- [x] 4.4 运行完整测试套件，确认 128 tests pass

## 5. 配置与文档

- [x] 5.1 更新 config/data_source.yaml 新增 pdf_extractor 类型配置项（PDF-Extract-Kit 路径、缓存开关）
- [x] 5.2 更新 README 中的 PDF 解析相关说明
