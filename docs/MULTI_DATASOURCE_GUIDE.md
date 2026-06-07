# 多数据源框架使用指南

**版本**: v1.0  
**更新日期**: 2026-05-19

---

## 概述

框架支持多种数据源，通过配置文件驱动，业务代码零修改即可切换。

| 数据源类型 | 说明 | 适用场景 | 状态 |
|-----------|------|---------|------|
| **sqlite** | SQLite 数据库 | 默认方式，适合结构化数据 | ✅ 已实现 |
| **local_csv** | 本地 CSV/Excel 文件 | 手工数据、快速原型 | ✅ 已实现 |
| **local_pdf** | PDF 年报解析 | 从年报自动提取数据 | ✅ 已实现 |
| **api** | 在线 API（Tushare/Akshare） | 实时数据 | 🚧 规划中 |

---

## 快速开始

### 方式 1：直接使用 DataLoader

```python
from src.data_pipeline.data_loader import DataLoader

loader = DataLoader(data_dir='data')
df = loader.load_financial(stock_code='000001.SZ', year=2023)
governance = loader.load_governance('pledge', '000001.SZ', 2023)
scores = loader.load_composite_scores(2023)
```

### 方式 2：使用 DataSourceManager（推荐）

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()  # 自动读取 config/data_source.yaml
print(manager.get_source_info()['source_type'])

df = manager.load_financial(stock_code='000001.SZ', year=2023)
governance = manager.load_governance('audit', '000001.SZ', 2023)
scores = manager.load_composite_scores(2023)
```

---

## 架构设计

```
DataSourceManager
├── 读取 config/data_source.yaml
├── 根据 type 选择加载器
│   ├── sqlite    → DataLoader
│   ├── local_csv → CSVDataLoader
│   ├── local_pdf → PDFDataLoader (quantdb_bridge)
│   └── api       → APIDataLoader (待实现)
└── 提供统一接口
```

### 策略模式

所有数据源加载器实现相同 API，用户代码不需要关心底层实现：

```python
# 底层自动选择合适的加载器
if source_type == 'sqlite':
    return sqlite_loader.load_financial(...)
elif source_type == 'csv':
    return csv_loader.load_financial(...)
```

---

## 配置数据源

编辑 `config/data_source.yaml`：

### SQLite（默认）

```yaml
data_source:
  type: 'sqlite'
  sqlite:
    db_path: 'data/raw/financial_data.sqlite'
```

### CSV

```yaml
data_source:
  type: 'local_csv'
  local_csv:
    financial_dir: 'data/local/financial'
    governance_dir: 'data/local/governance'
    market_dir: 'data/local/market'
    factors_dir: 'data/factors'
    encoding: 'utf-8'
```

---

## CSV 数据格式

### 财务数据

**位置**: `data/local/financial/`

方式 1 - 单文件：`financial_data.csv`
```csv
stock_code,report_year,revenue,net_profit,total_assets,net_assets
000001.SZ,2023,1500.0,150.0,3000.0,1500.0
```

方式 2 - 分股票：`{stock_code}_{year}.csv`
```csv
revenue,net_profit,total_assets,net_assets
1500.0,150.0,3000.0,1500.0
```

### 治理数据

**位置**: `data/local/governance/governance_data.csv`

```csv
stock_code,report_year,major_shareholder_pledge_ratio,audit_opinion,is_standard_audit,core_personnel_turnover_rate
000001.SZ,2023,0.0,标准无保留意见,1,0.0
```

### 行情数据

**位置**: `data/local/market/{year}.csv`

```csv
trade_date,stock_code,open,high,low,close,volume
2023-01-03,000001.SZ,10.5,10.8,10.4,10.7,1000000
```

---

## 动态切换数据源

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()
print(manager.get_source_info()['source_type'])  # 'sqlite'

manager.switch_source('local_csv')
print(manager.get_source_info()['source_type'])  # 'local_csv'

# 自动从新数据源加载
df = manager.load_financial('000001.SZ', 2023)
```

---

## 数据源对比

### SQLite
- **优点**: 查询快、支持复杂查询、数据结构清晰
- **缺点**: 需预先导入、不便于手工编辑
- **适用**: 生产环境、大量数据

### CSV
- **优点**: Excel 可直接编辑、便于版本控制（Git diff）
- **缺点**: 查询较慢、不支持复杂关系
- **适用**: 小规模数据、快速原型

### PDF
- **优点**: 直接解析年报、数据权威
- **缺点**: 解析复杂、速度较慢
- **适用**: 特色数据集构建、研究用途

---

## 最佳实践

### 开发用 CSV，生产用 SQLite

```yaml
# config/dev.yaml
data_source:
  type: 'local_csv'

# config/prod.yaml
data_source:
  type: 'sqlite'
```

### 错误处理

```python
try:
    df = manager.load_financial('000001.SZ', 2023)
    if df.empty:
        logger.warning("No data found")
except Exception as e:
    logger.error(f"Failed to load data: {e}")
```

### 安全检查

- 不要将包含 API Token 的配置文件提交到 Git
- 使用 `.env` 文件管理敏感信息
- 提供 `data_source.example.yaml` 作为模板

---

## 故障排查

### 找不到配置文件
```
Config file not found: config/data_source.yaml
```
确保在项目根目录运行，或检查文件路径。

### CSV 编码错误
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```
修改 `config/data_source.yaml` 中的 encoding 为 `'gbk'` 或 `'gb2312'`。

### 数据为空
- 检查文件路径和格式
- 过滤条件可能太严格
- 启用 DEBUG 日志排查：
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```
