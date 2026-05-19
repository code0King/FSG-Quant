# DataLoader vs CSVDataLoader 对比说明

**更新日期**: 2026-05-19

---

## 📋 核心区别总结

| 特性 | DataLoader | CSVDataLoader |
|------|-----------|---------------|
| **数据源** | SQLite数据库 + Parquet文件 | CSV/Excel文件 |
| **主要用途** | 生产环境、大规模数据 | 开发测试、小规模数据、手工数据 |
| **性能** | ⚡ 快（数据库索引） | 🐢 较慢（文件扫描） |
| **查询能力** | ✅ 支持SQL复杂查询 | ❌ 仅简单过滤 |
| **数据编辑** | ❌ 需要SQL工具 | ✅ 可用Excel直接编辑 |
| **适用场景** | 正式分析、回测 | 原型验证、演示、小数据集 |
| **实现复杂度** | 中等 | 简单 |
| **依赖** | sqlite3, pyarrow | pandas |

---

## 🔍 详细对比

### 1. 数据存储方式

#### DataLoader（SQLite）

```python
# 数据结构化存储在SQLite数据库中
data/raw/financial_data.sqlite
├── companies表          # 股票基本信息
├── financial_annual表   # 年度财务数据
└── governance_data表    # 治理数据

# 因子数据存储在Parquet文件中
data/factors/
├── L1_factors.parquet
├── L2_factors.parquet
├── L3_factors.parquet
└── composite_scores.parquet
```

**优势**:
- ✅ 数据结构清晰，关系明确
- ✅ 支持ACID事务
- ✅ 可以建立索引加速查询
- ✅ 适合大规模数据（百万级记录）

**劣势**:
- ❌ 需要专门的工具查看和编辑
- ❌ 不便于版本控制（二进制文件）
- ❌ 导入数据需要编写脚本

#### CSVDataLoader（CSV文件）

```python
# 数据以文本文件形式存储
data/local/financial/
├── financial_data.csv           # 合并文件
├── 000001.SZ_2023.csv          # 或分股票文件
└── 000002.SZ_2023.csv

data/local/governance/
└── governance_data.csv

data/local/market/
└── 2023.csv
```

**优势**:
- ✅ 可用Excel/记事本直接编辑
- ✅ 便于版本控制（Git可以diff）
- ✅ 易于分享和传输
- ✅ 无需数据库软件

**劣势**:
- ❌ 查询速度慢（需要读取整个文件）
- ❌ 不支持复杂的关系查询
- ❌ 大文件处理效率低
- ❌ 没有数据类型约束

---

### 2. 初始化方式

#### DataLoader

```python
from data_pipeline.data_loader import DataLoader

# 方式1: 默认配置
loader = DataLoader()
# 自动查找 data/raw/financial_data.sqlite

# 方式2: 指定数据库路径
loader = DataLoader(data_dir='data/raw/financial_data.sqlite')

# 方式3: 指定目录
loader = DataLoader(data_dir='data', db_filename='financial_data.sqlite')
```

#### CSVDataLoader

```python
from data_pipeline.csv_loader import CSVDataLoader

# 必须指定各个数据目录
loader = CSVDataLoader(
    financial_dir='data/local/financial',
    governance_dir='data/local/governance',
    market_dir='data/local/market',
    factors_dir='data/factors',
    encoding='utf-8'  # 可选，默认utf-8
)
```

---

### 3. API接口对比

两者提供**相同的API接口**，这是设计的关键点！

#### 加载财务数据

```python
# DataLoader
loader = DataLoader()
df = loader.load_financial(stock_code='000001.SZ', year=2023)

# CSVDataLoader
loader = CSVDataLoader(...)
df = loader.load_financial(stock_code='000001.SZ', year=2023)

# 返回值相同：DataFrame
```

#### 加载治理数据

```python
# 两者都支持
governance = loader.load_governance(
    data_type='pledge',  # 'pledge', 'audit', 'executive', 'all'
    stock_code='000001.SZ',
    year=2023
)
```

#### 其他接口

```python
# 完全一致的API
loader.load_factors(factor_type='L1', year=2023)
loader.load_composite_scores(year=2023)
loader.load_market_data(year=2023, stock_code='000001.SZ')
loader.get_stock_list()
```

**设计理念**: 
> 通过统一的API，上层业务代码不需要关心底层使用哪种数据源。

---

### 4. 内部实现差异

#### DataLoader - SQL查询

```python
def load_financial(self, stock_code=None, year=None):
    conn = sqlite3.connect(self.db_path)
    
    # 构建SQL查询
    query = "SELECT * FROM financial_annual WHERE 1=1"
    params = []
    
    if stock_code:
        query += " AND stock_code = ?"
        params.append(stock_code)
    
    if year:
        query += " AND report_year = ?"
        params.append(year)
    
    # 执行SQL查询（高效）
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df
```

**特点**:
- 使用SQL WHERE子句过滤
- 数据库引擎优化查询
- 可以利用索引加速
- 只读取需要的数据

#### CSVDataLoader - 文件扫描

```python
def load_financial(self, stock_code=None, year=None):
    # 策略1: 查找特定文件
    if stock_code and year:
        file_path = self.financial_dir / f"{stock_code}_{year}.csv"
        if file_path.exists():
            df = pd.read_csv(file_path)
            return df
    
    # 策略2: 读取合并文件后过滤
    merged_file = self.financial_dir / "financial_data.csv"
    if merged_file.exists():
        df = pd.read_csv(merged_file)
        
        # 在内存中过滤
        if stock_code:
            df = df[df['stock_code'] == stock_code]
        if year:
            df = df[df['report_year'] == year]
        
        return df
    
    # 策略3: 扫描所有CSV文件并合并
    csv_files = list(self.financial_dir.glob("*.csv"))
    all_dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(all_dfs)
    
    # 在内存中过滤
    if stock_code:
        df = df[df['stock_code'] == stock_code]
    if year:
        df = df[df['report_year'] == year]
    
    return df
```

**特点**:
- 需要读取整个文件到内存
- 在DataFrame中进行过滤
- 多个文件时需要合并
- 大数据量时效率低

---

### 5. 性能对比

假设数据量：**1000只股票 × 5年 = 5000条记录**

| 操作 | DataLoader (SQLite) | CSVDataLoader |
|------|-------------------|---------------|
| 加载单只股票单年 | ~5ms | ~50ms |
| 加载单只股票全部年份 | ~10ms | ~100ms |
| 加载全部数据 | ~50ms | ~500ms |
| 按条件过滤 | ~5ms (索引) | ~100ms (全表扫描) |
| 内存占用 | 低（按需加载） | 高（全部加载） |

**结论**: 
- 小数据量（<1000条）：差异不明显
- 中等数据量（1000-10000条）：DataLoader快5-10倍
- 大数据量（>10000条）：DataLoader快10-100倍

---

### 6. 使用场景建议

#### 使用 DataLoader 的场景

✅ **推荐场景**:
1. **生产环境** - 正式的量化分析
2. **大规模数据** - 全市场5000+股票
3. **频繁查询** - 交互式分析、回测
4. **复杂查询** - 多表JOIN、聚合统计
5. **数据完整性要求高** - ACID事务保证

```python
# 示例：全市场回测
from data_pipeline.data_loader import DataLoader

loader = DataLoader()

# 快速获取所有股票的ROE数据
all_stocks = loader.get_stock_list()
for stock in all_stocks['stock_code']:
    df = loader.load_financial(stock, year=2023)
    # 处理...
```

#### 使用 CSVDataLoader 的场景

✅ **推荐场景**:
1. **开发阶段** - 快速原型验证
2. **小规模数据** - <100只股票
3. **手工数据** - Excel整理的数据
4. **演示Demo** - 便于展示和分享
5. **版本控制** - Git管理数据变更

```python
# 示例：快速测试新因子
from data_pipeline.csv_loader import CSVDataLoader

loader = CSVDataLoader(
    financial_dir='data/local/financial',
    governance_dir='data/local/governance',
    market_dir='data/local/market',
    factors_dir='data/factors'
)

# 用Excel准备10只股票的测试数据
df = loader.load_financial('000001.SZ', 2023)
# 快速验证因子计算逻辑
```

---

### 7. 数据准备工作

#### DataLoader - 需要导入脚本

```python
# scripts/import_to_sqlite.py
import sqlite3
import pandas as pd

# 1. 从API或其他来源获取数据
data = get_data_from_tushare()

# 2. 导入SQLite
conn = sqlite3.connect('data/raw/financial_data.sqlite')
data.to_sql('financial_annual', conn, if_exists='replace', index=False)
conn.close()
```

**工作量**: ⭐⭐⭐ 中等
- 需要编写导入脚本
- 需要处理数据清洗
- 需要维护表结构

#### CSVDataLoader - 直接放置文件

```bash
# 1. 用Excel整理数据
# 2. 另存为CSV
# 3. 放到指定目录
cp my_data.csv data/local/financial/financial_data.csv

# 完成！可以直接使用
```

**工作量**: ⭐ 简单
- 无需编程
- Excel即可操作
- 立即可用

---

### 8. 通过 DataSourceManager 统一使用

**最佳实践**: 使用 `DataSourceManager` 统一管理，通过配置文件切换。

```python
from data_pipeline.data_source_manager import DataSourceManager

# 创建管理器（自动读取 config/data_source.yaml）
manager = DataSourceManager()

# 加载数据（不关心底层是SQLite还是CSV）
df = manager.load_financial('000001.SZ', 2023)

# 切换数据源只需修改配置文件
# config/data_source.yaml:
#   type: 'sqlite'  -> 使用 DataLoader
#   type: 'local_csv' -> 使用 CSVDataLoader
```

**优势**:
- ✅ 业务代码无需修改
- ✅ 灵活切换数据源
- ✅ 便于测试不同场景

---

## 🎯 选择建议

### 决策流程图

```
开始
  ↓
数据量大小？
  ├─ < 1000条 → 可以用CSV
  └─ > 1000条 → 推荐SQLite
  ↓
是否需要频繁查询？
  ├─ 是 → 推荐SQLite
  └─ 否 → 可以用CSV
  ↓
是否需要Excel编辑？
  ├─ 是 → 用CSV
  └─ 否 → 推荐SQLite
  ↓
是否在生产环境？
  ├─ 是 → 必须SQLite
  └─ 否 → 都可以
```

### 具体建议

| 项目阶段 | 推荐方案 | 原因 |
|---------|---------|------|
| **学习/探索** | CSV | 简单直观，易于理解 |
| **原型开发** | CSV | 快速迭代，方便修改 |
| **小规模测试** | CSV | <100只股票，足够用 |
| **正式分析** | SQLite | 性能好，稳定可靠 |
| **全市场回测** | SQLite | 必须，否则太慢 |
| **生产部署** | SQLite | 标准方案 |

---

## 💡 混合使用策略

可以同时使用两种数据源：

```python
# 策略1: 开发用CSV，生产用SQLite
# config/dev.yaml
data_source:
  type: 'local_csv'

# config/prod.yaml  
data_source:
  type: 'sqlite'

# 策略2: 不同类型数据用不同来源
# 财务数据从SQLite（结构化好）
financial_mgr = DataSourceManager('config/financial_sqlite.yaml')

# 治理数据从CSV（经常手工更新）
governance_mgr = DataSourceManager('config/governance_csv.yaml')
```

---

## 📊 总结对比表

| 维度 | DataLoader | CSVDataLoader |  winner |
|------|-----------|---------------|---------|
| **性能** | ⚡⚡⚡⚡⚡ | ⚡⚡ | DataLoader |
| **易用性** | ⚡⚡⚡ | ⚡⚡⚡⚡⚡ | CSVDataLoader |
| **灵活性** | ⚡⚡⚡ | ⚡⚡⚡⚡ | CSVDataLoader |
| **可扩展性** | ⚡⚡⚡⚡⚡ | ⚡⚡ | DataLoader |
| **维护成本** | ⚡⚡⚡ | ⚡⚡⚡⚡ | CSVDataLoader |
| **数据安全** | ⚡⚡⚡⚡⚡ | ⚡⚡ | DataLoader |
| **版本控制** | ⚡⚡ | ⚡⚡⚡⚡⚡ | CSVDataLoader |

---

## 🔗 相关文档

- [DataLoader使用指南](../docs/DATALOADER_NEW_METHODS_GUIDE.md)
- [CSVDataLoader实现](../src/data_pipeline/csv_loader.py)
- [多数据源框架](../docs/MULTI_DATASOURCE_GUIDE.md)
- [配置文件示例](../config/data_source.yaml)

---

**核心要点**: 
> 两者API完全相同，选择哪个取决于您的具体需求。推荐使用 `DataSourceManager` 统一管理，通过配置文件灵活切换。
