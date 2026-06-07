# DataLoader 使用指南

**更新日期**: 2026-05-19

---

## 概述

`DataLoader` 是 FSG-Quant 的核心数据访问层，统一封装 SQLite 数据库和 Parquet 文件的读写操作。提供财务数据、治理数据、因子数据、行情数据的一站式加载接口。

```python
from src.data_pipeline.data_loader import DataLoader

loader = DataLoader(data_dir='data')
```

---

## API 参考

### load_financial()

从 SQLite 加载年度财务数据。

```python
def load_financial(
    self,
    stock_code: Optional[str] = None,
    year: Optional[int] = None
) -> pd.DataFrame
```

**示例**:
```python
# 全部数据
loader.load_financial()
# 单只股票
loader.load_financial(stock_code='000001.SZ')
# 按年份
loader.load_financial(year=2023)
# 组合过滤
loader.load_financial(stock_code='000001.SZ', year=2023)
```

---

### load_governance()

从 SQLite 的 `governance_data` 表加载公司治理数据。

```python
def load_governance(
    self,
    data_type: str = 'pledge',  # 'pledge' | 'audit' | 'executive' | 'all'
    stock_code: Optional[str] = None,
    year: Optional[int] = None
) -> pd.DataFrame
```

**参数说明**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| data_type | str | 'pledge' | 'pledge': 股权质押, 'audit': 审计意见, 'executive': 高管信息, 'all': 全部 |
| stock_code | str | None | 股票代码，None 表示所有 |
| year | int | None | 报告年度，None 表示所有 |

**返回值（按 data_type）**:

- `pledge`: stock_code, report_year, pledged_shares_ratio
- `audit`: stock_code, report_year, audit_opinion, is_standard_audit
- `executive`: stock_code, report_year, core_personnel_turnover_rate, executive_count_start, departed_executives
- `all`: 所有字段

**示例**:
```python
# 质押数据
loader.load_governance('pledge', '000001.SZ', 2023)
# 审计意见
loader.load_governance('audit', '300750.SZ', 2023)
# 高管流失
loader.load_governance('executive', '000002.SZ', 2023)
```

---

### load_composite_scores()

从 Parquet 文件加载因子合成后的综合评分数据。

```python
def load_composite_scores(
    self,
    year: Optional[int] = None
) -> pd.DataFrame
```

**返回值**: stock_code, report_year, offensive_score, defensive_score, composite_risk_level

```python
# 2023年评分
scores = loader.load_composite_scores(2023)
# 筛选高分股票
top10 = scores.nlargest(10, 'offensive_score')
```

---

### 其他接口

```python
loader.load_factors(factor_type='L1', year=2023)     # L1/L2/L3/composite 因子
loader.load_market_data(year=2023, stock_code='000001.SZ')  # 行情数据
loader.get_stock_list()                                # 股票列表
```

---

## DataLoader vs CSVDataLoader

两者提供**完全相同的 API 接口**，可在 `config/data_source.yaml` 中切换。

| 维度 | DataLoader (SQLite) | CSVDataLoader |
|------|-------------------|---------------|
| 数据源 | SQLite + Parquet | CSV/Excel 文件 |
| 性能 | 快（数据库索引） | 较慢（文件扫描） |
| 查询能力 | SQL 复杂查询 | 仅简单过滤 |
| 数据编辑 | 需 SQL 工具 | Excel 直接编辑 |
| 适用场景 | 正式分析、回测 | 原型验证、小规模数据 |
| 初始化 | `DataLoader(data_dir='data')` | `CSVDataLoader(financial_dir=..., governance_dir=...)` |

### 性能对比（1000 股票 × 5 年）

| 操作 | DataLoader | CSVDataLoader |
|------|-----------|---------------|
| 单股单年 | ~5ms | ~50ms |
| 全部加载 | ~50ms | ~500ms |
| 条件过滤 | ~5ms（索引） | ~100ms（全表扫描） |

### 选择建议

| 场景 | 推荐 |
|------|------|
| 学习/探索 | CSVDataLoader |
| 原型开发 | CSVDataLoader |
| 小规模测试（<100 股票） | CSVDataLoader |
| 正式分析 | DataLoader |
| 全市场回测 | DataLoader |

---

## 使用 DataSourceManager 统一管理

**最佳实践**: 通过 `DataSourceManager` 和配置文件切换数据源，业务代码无需修改。

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()  # 自动读取 config/data_source.yaml
df = manager.load_financial('000001.SZ', 2023)

# 运行时切换
manager.switch_source('local_csv')
```

```yaml
# config/data_source.yaml
data_source:
  type: 'sqlite'  # 可切换为 'local_csv'
  sqlite:
    db_path: 'data/raw/financial_data.sqlite'
  local_csv:
    financial_dir: 'data/local/financial'
    governance_dir: 'data/local/governance'
```

---

## 数据库表结构

```sql
CREATE TABLE governance_data (
    stock_code TEXT NOT NULL,
    report_year INTEGER NOT NULL,
    major_shareholder_pledge_ratio REAL,
    audit_opinion TEXT,
    is_standard_audit BOOLEAN,
    core_personnel_turnover_rate REAL,
    PRIMARY KEY (stock_code, report_year)
);
```

综合评分数据位于 `data/factors/composite_scores.parquet`。

---

## 注意事项

- 如果数据不存在，方法返回空 DataFrame，不会抛异常
- 建议在使用前检查 `.empty`：
  ```python
  df = loader.load_governance('pledge', '000001.SZ', 2023)
  if not df.empty:
      # 处理数据
  ```
- `load_composite_scores()` 依赖因子合成后生成的 Parquet 文件
