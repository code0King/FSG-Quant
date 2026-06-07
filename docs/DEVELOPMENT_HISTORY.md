# 开发历程

**项目**: FSG-Quant - A股上市公司全方位量化分析框架

---

## 项目概览

基于"财报-战略-治理"三维视角的 A 股上市公司量化分析工具，将年报信息自动化转化为可回测的 Alpha 因子体系。

| 阶段 | 模块 | 测试 | 代码行数 | 日期 |
|------|------|------|---------|------|
| Phase 1 | DataLoader + L1PerformanceFactor | 24 | ~1,250 | 2026-05-14 |
| Phase 2 | CommitmentParser + FinBERTAnalyzer + L2 + L3 | 56 | ~2,040 | 2026-05-14 |
| Phase 3 | FactorSynthesizer + BacktestEngine | 27 | ~785 | 2026-05-14 |
| 增强 | DataLoader 方法补充 + 多数据源 | 9 | ~707 | 2026-05-19 |
| 管道 | PDF 解析管线重构 | 36 | ~1,200+ | 2026-06-06 |

**总测试数**: 128 个，100% 通过

---

## Phase 1：数据层与 L1 业绩验证（2026-05-14）

**完成模块**: DataLoader + L1PerformanceFactor（2/8，25%）

### DataLoader

统一封装 SQLite 和 Parquet 数据访问，支持按股票代码和年份过滤。

**文件**: `src/data_pipeline/data_loader.py`（209 行）  
**测试**: 9 个用例，覆盖数据加载、过滤、异常处理

### L1PerformanceFactor

核心财务指标计算引擎，行业差异化毛利率分级。

**文件**: `src/factors/L1_performance.py`（493 行）  
**测试**: 15 个用例，覆盖边界情况和除零处理

**计算指标**: ROE、ROA、ROIC、毛利率分级（行业分位数）、扣非净利润占比、现金流覆盖倍数、盈利质量综合评分（0-100）

**评分公式**: `0.25×ROE + 0.20×ROIC + 0.20×现金流 + 0.15×扣非占比 + 0.20×毛利率等级`

---

## Phase 2：NLP 与 L2/L3 因子（2026-05-14）

**完成模块**: 4/4（75% 总体进度）

### CommitmentParser

从 MD&A 文本中抽取营收增长、利润增长、CAPEX 承诺。

**文件**: `src/nlp/commitment_parser.py`（152 行）  
**测试**: 13 个用例  
**技术**: 正则表达式匹配，支持多种中文表述方式

### FinBERTAnalyzer

基于开源中文 FinBERT 模型的金融文本情绪分析。

**文件**: `src/nlp/finbert_analyzer.py`（256 行）  
**测试**: 11 个用例（Mock 隔离 torch）  
**输出**: sentiment_score（-1 到 1）、label（positive/neutral/negative）、confidence

### L2StrategyFactor

整合承诺兑现率和情绪得分的战略执行评估。

**文件**: `src/factors/L2_strategy.py`（323 行）  
**测试**: 14 个用例  
**公式**: 综合评分 = 0.7 × 兑现率映射分 + 0.3 × 情绪映射分

### L3GovernanceFactor

治理排雷层：股权质押、审计意见、高管流失率。

**文件**: `src/factors/L3_governance.py`（335 行）  
**测试**: 18 个用例  
**风险等级**: green / yellow / orange / red（非标审计意见直接红色）

---

## Phase 3：因子合成与回测（2026-05-14）

**完成模块**: 2/2（100% 总体进度）

### FactorSynthesizer

因子正交化 + 双维度打分卡 + 综合风险分级。

**文件**: `src/factors/factor_synthesizer.py`（388 行）  
**测试**: 15 个用例

**进攻型权重**: L2 兑现率 30%、L1 营收增长 25%、L1 盈利质量 20%、L3 治理 15%、L2 情绪 10%

**防御型权重**: L3 治理 35%、L1 现金流 30%、L1 资产健康 20%、L2 一致性 10%、L1 稳定性 5%

### BacktestEngine

年度调仓回测引擎，支持进攻型/防御型策略。

**文件**: `src/backtest/backtest_engine.py`（397 行）  
**测试**: 12 个用例  
**指标**: 累计收益、年化收益、夏普比率、最大回撤、胜率

---

## 增强功能（2026-05-19）

### DataLoader 方法补充

新增 `load_governance()` 和 `load_composite_scores()` 方法，解锁完整分析流程。

**新增代码**: ~108 行，测试 164 行，6 个新测试用例

### 多数据源框架

配置驱动的多数据源支持，实现 DataSourceManager + CSVDataLoader。

**新增**: `config/data_source.yaml`（90 行）、`data_source_manager.py`（275 行）、`csv_loader.py`（324 行）
**测试**: 3 个场景，100% 通过

---

## PDF 解析管线重构（2026-06-06）

整合 PDF-Extract-Kit（MDA 文本）+ Camelot（高管离职表）+ akshare（质押比例），对接 quant_DB 统一数据接口。

**新增/修改**:
- `scripts/quantdb_bridge.py` — quant_DB 集成、akshare 质押、PDF 高管 turnover
- `src/data_pipeline/pdf_extractor.py` — PDF-Extract-Kit + PyMuPDF 降级
- `src/data_pipeline/executive_parser.py` — Camelot 表格解析 + 降级
- `src/data_pipeline/pdf_parser.py` — 重构，改进 MDA 提取、审计意见、缓存

**关键修复**:
- 缓存 key 冲突：`{stem}.txt` → `{parent.name}_{stem}.txt`（防止不同股票同一年份 PDF 互相污染）
- `save_governance_from_pdf` 保留已有质押数据不被 PDF 覆盖
- L3 治理因子 `if executive_turnover` → `if executive_turnover is not None`（0.0 不被视为缺失）
- `factor_synthesizer._extract_factors` 正确处理 None 值

**测试**: +36 个新测试用例，总计 128 个全部通过

---

## 技术亮点

1. **TDD 开发模式** — 128 个测试覆盖正常流程和边界情况
2. **三层因子架构** — L1 财务硬约束、L2 战略软指标、L3 风险排雷
3. **施密特正交化** — 消除因子多重共线性
4. **双维度打分卡** — 进攻型（成长导向）vs 防御型（稳健导向）
5. **风险分级系统** — 红橙黄绿四级，治理风险一票否决
6. **Mock 隔离** — 解决 torch DLL 兼容性问题，测试速度快
7. **优雅降级** — pdf-extract-kit / camelot / akshare 均为可选依赖

## 相关文档

- [PRD v2.0](./PRD_v2.0.md) — 产品需求文档
- [系统设计 v2.0](./system_design_v2.0.md) — 系统架构设计
- [详细设计](./detailed_design.md) — 模块详细设计
- [DataLoader 使用指南](./DATALOADER_GUIDE.md) — 数据加载 API
- [多数据源框架指南](./MULTI_DATASOURCE_GUIDE.md) — 数据源配置与管理
