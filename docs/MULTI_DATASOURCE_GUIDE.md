# 多数据源框架使用指南

**版本**: v1.0  
**更新日期**: 2026-05-19

---

## 📋 概述

本框架支持多种数据源，可以根据需求灵活切换：

| 数据源类型 | 说明 | 适用场景 | 实现状态 |
|-----------|------|---------|---------|
| **sqlite** | SQLite数据库 | 默认方式，适合结构化数据 | ✅ 已实现 |
| **local_csv** | 本地CSV/Excel文件 | 手工数据、快速原型 | ✅ 已实现 |
| **local_pdf** | PDF年报解析 | 从年报自动提取数据 | 🚧 规划中 |
| **api** | 在线API（Tushare/Akshare） | 实时数据、全市场覆盖 | 🚧 规划中 |

---

## 🚀 快速开始

### 方式1：直接使用 DataLoader（SQLite）

这是最简单的方式，适合已有SQLite数据库的情况。

```python
from src.data_pipeline.data_loader import DataLoader

# 初始化
loader = DataLoader(data_dir='data')

# 加载财务数据
df = loader.load_financial(stock_code='000001.SZ', year=2023)
print(df)

# 加载治理数据
governance = loader.load_governance('pledge', '000001.SZ', 2023)
print(governance)

# 加载综合评分
scores = loader.load_composite_scores(2023)
print(scores)
```

### 方式2：使用 DataSourceManager（推荐）

通过配置文件管理数据源，更灵活。

```python
from src.data_pipeline.data_source_manager import DataSourceManager

# 初始化（自动读取 config/data_source.yaml）
manager = DataSourceManager()

# 查看当前数据源信息
info = manager.get_source_info()
print(f"当前数据源: {info['source_type']}")

# 加载数据（接口与DataLoader相同）
df = manager.load_financial(stock_code='000001.SZ', year=2023)
governance = manager.load_governance('audit', '000001.SZ', 2023)
scores = manager.load_composite_scores(2023)
```

---

## ⚙️ 配置数据源

编辑 `config/data_source.yaml` 文件：

### 切换到 CSV 数据源

```yaml
data_source:
  type: 'local_csv'  # 改为 local_csv
  
  local_csv:
    financial_dir: 'data/local/financial'
    governance_dir: 'data/local/governance'
    market_dir: 'data/local/market'
    factors_dir: 'data/factors'
    encoding: 'utf-8'
```

### 切换到 API 数据源（待实现）

```yaml
data_source:
  type: 'api'
  
  api:
    provider: 'akshare'  # 或 'tushare'
    
    akshare:
      use_proxy: false
      timeout: 30
      request_interval: 1.0
```

---

## 📁 本地CSV数据格式要求

### 财务数据

**文件位置**: `data/local/financial/`

**方式1: 单个文件合并所有数据**

文件名: `financial_data.csv`

```csv
stock_code,report_year,revenue,net_profit,total_assets,net_assets,...
000001.SZ,2023,1500.0,150.0,3000.0,1500.0,...
000001.SZ,2022,1400.0,140.0,2800.0,1400.0,...
000002.SZ,2023,800.0,80.0,1600.0,800.0,...
```

**方式2: 每个股票单独文件**

文件名格式: `{stock_code}_{year}.csv`

例如: `000001.SZ_2023.csv`

```csv
revenue,net_profit,total_assets,net_assets,...
1500.0,150.0,3000.0,1500.0,...
```

### 治理数据

**文件位置**: `data/local/governance/`

文件名: `governance_data.csv`

```csv
stock_code,report_year,major_shareholder_pledge_ratio,audit_opinion,is_standard_audit,core_personnel_turnover_rate
000001.SZ,2023,0.0,标准无保留意见,1,0.0
000002.SZ,2023,0.15,标准无保留意见,1,0.05
```

### 行情数据

**文件位置**: `data/local/market/`

文件名格式: `{year}.csv`

例如: `2023.csv`

```csv
trade_date,stock_code,open,high,low,close,volume
2023-01-03,000001.SZ,10.5,10.8,10.4,10.7,1000000
2023-01-04,000001.SZ,10.7,11.0,10.6,10.9,1200000
```

---

## 🔄 动态切换数据源

可以在运行时切换数据源：

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()

# 当前使用 SQLite
print(manager.get_source_info()['source_type'])  # 'sqlite'

# 切换到 CSV
manager.switch_source('local_csv')
print(manager.get_source_info()['source_type'])  # 'local_csv'

# 加载数据（自动从CSV读取）
df = manager.load_financial('000001.SZ', 2023)
```

---

## 📊 数据源对比

### SQLite 数据源

**优点**:
- ✅ 查询速度快
- ✅ 支持复杂查询
- ✅ 数据结构清晰

**缺点**:
- ❌ 需要预先导入数据
- ❌ 不便于手工编辑

**适用场景**: 
- 生产环境
- 大量数据
- 频繁查询

### CSV 数据源

**优点**:
- ✅ 易于手工编辑
- ✅ 可用Excel打开
- ✅ 便于版本控制

**缺点**:
- ❌ 查询速度较慢
- ❌ 不支持复杂关系

**适用场景**:
- 小规模数据
- 快速原型
- 测试和演示

### PDF 数据源（待实现）

**优点**:
- ✅ 直接从年报获取
- ✅ 数据权威
- ✅ 无需手动整理

**缺点**:
- ❌ 解析复杂度高
- ❌ 准确率问题
- ❌ 处理速度慢

**适用场景**:
- 特色数据集构建
- 研究用途

### API 数据源（待实现）

**优点**:
- ✅ 数据最新
- ✅ 覆盖全面
- ✅ 自动化程度高

**缺点**:
- ❌ 依赖网络
- ❌ 可能有频率限制
- ❌ Tushare需要积分

**适用场景**:
- 实时分析
- 全市场扫描
- 回测

---

## 🛠️ 实用工具脚本

### 1. 检查数据源状态

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()
info = manager.get_source_info()

print("=" * 60)
print("数据源信息")
print("=" * 60)
print(f"类型: {info['source_type']}")
print(f"加载器: {info['loader_type']}")
print(f"配置: {info['config']}")
```

### 2. 批量测试数据加载

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()

stocks = ['000001.SZ', '000002.SZ', '600519.SH']
years = [2022, 2023]

for stock in stocks:
    for year in years:
        df = manager.load_financial(stock, year)
        if not df.empty:
            print(f"✅ {stock} {year}: {len(df)} records")
        else:
            print(f"❌ {stock} {year}: No data")
```

### 3. 导出数据为CSV

```python
from src.data_pipeline.data_source_manager import DataSourceManager

manager = DataSourceManager()

# 从SQLite加载
df = manager.load_financial(year=2023)

# 导出为CSV
df.to_csv('data/local/financial/financial_data_2023.csv', index=False)
print(f"Exported {len(df)} records to CSV")
```

---

## 🔧 故障排查

### 问题1: 找不到配置文件

**错误信息**:
```
Config file not found: config/data_source.yaml
```

**解决方案**:
- 确保在项目根目录运行
- 检查文件路径是否正确
- 使用默认配置会自动回退到SQLite

### 问题2: CSV文件编码错误

**错误信息**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**解决方案**:
- 修改 `config/data_source.yaml` 中的 `encoding` 配置
- 尝试 `'gbk'` 或 `'gb2312'`（中文Windows常见）

```yaml
local_csv:
  encoding: 'gbk'  # 改为 gbk
```

### 问题3: 数据为空

**可能原因**:
- 文件路径不正确
- 文件格式不符合要求
- 过滤条件太严格

**调试方法**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

manager = DataSourceManager()
df = manager.load_financial('000001.SZ', 2023)
print(f"Loaded {len(df)} records")
```

---

## 📝 最佳实践

### 1. 开发阶段使用CSV

```yaml
# config/data_source.yaml
data_source:
  type: 'local_csv'  # 便于快速迭代
```

### 2. 生产阶段使用SQLite

```yaml
data_source:
  type: 'sqlite'  # 性能更好
```

### 3. 混合使用

对于不同数据类型使用不同来源（需要自定义实现）：

```python
# 财务数据从SQLite
financial_loader = DataSourceManager(config_path='config/financial_sqlite.yaml')

# 治理数据从CSV
governance_loader = DataSourceManager(config_path='config/governance_csv.yaml')
```

---

## 🚀 下一步

1. **准备CSV测试数据** - 创建示例CSV文件
2. **实现PDF解析器** - 从年报自动提取数据
3. **集成API接口** - 对接Tushare/Akshare
4. **创建Web界面** - 可视化管理数据源

---

## 📚 相关文档

- [DataLoader新增方法指南](./DATALOADER_NEW_METHODS_GUIDE.md)
- [DataLoader完成报告](./DATALOADER_COMPLETION_REPORT.md)
- [配置文件示例](../config/data_source.yaml)

---

**有任何问题欢迎提Issue！** 🎉
