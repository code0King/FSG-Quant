# DataLoader 新增方法使用指南

## 概述

本次更新为 `DataLoader` 类添加了两个重要方法：
- `load_governance()` - 加载公司治理数据
- `load_composite_scores()` - 加载综合评分数据

---

## 1. load_governance() 方法

### 功能说明

从 SQLite 数据库的 `governance_data` 表中加载公司治理相关数据，包括：
- 股权质押比例
- 审计意见类型
- 高管流失率

### 方法签名

```python
def load_governance(
    self, 
    data_type: str = 'pledge',
    stock_code: Optional[str] = None,
    year: Optional[int] = None
) -> pd.DataFrame
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| data_type | str | 'pledge' | 数据类型：<br>- 'pledge': 股权质押<br>- 'audit': 审计意见<br>- 'executive': 高管信息<br>- 'all': 全部数据 |
| stock_code | str | None | 股票代码，如 '000001.SZ'。<br>None 表示加载所有股票 |
| year | int | None | 报告年度，如 2023。<br>None 表示加载所有年份 |

### 返回值

DataFrame，包含治理数据。不同 data_type 返回的列不同：

**pledge 类型：**
- stock_code: 股票代码
- report_year: 报告年度
- pledged_shares_ratio: 质押比例（%）

**audit 类型：**
- stock_code: 股票代码
- report_year: 报告年度
- audit_opinion: 审计意见文本
- is_standard_audit: 是否标准无保留意见（布尔值）

**executive 类型：**
- stock_code: 股票代码
- report_year: 报告年度
- core_personnel_turnover_rate: 核心人员流失率（%）
- executive_count_start: 年初高管人数（自动添加，默认10）
- departed_executives: 离职高管人数（根据流失率计算）

### 使用示例

```python
from src.data_pipeline.data_loader import DataLoader

# 初始化加载器
loader = DataLoader(data_dir='data')

# 示例1: 加载某股票的股权质押数据
pledge_data = loader.load_governance(
    data_type='pledge',
    stock_code='000001.SZ',
    year=2023
)
print(pledge_data)

# 示例2: 加载某股票的审计意见
audit_data = loader.load_governance(
    data_type='audit',
    stock_code='300750.SZ',
    year=2023
)
print(audit_data['audit_opinion'].values[0])

# 示例3: 加载某股票的高管流失数据
exec_data = loader.load_governance(
    data_type='executive',
    stock_code='000002.SZ',
    year=2023
)
print(f"高管流失率: {exec_data['core_personnel_turnover_rate'].values[0]}%")

# 示例4: 加载2023年所有股票的治理数据
all_governance = loader.load_governance(
    data_type='all',
    year=2023
)
print(f"共 {len(all_governance)} 条记录")
```

---

## 2. load_composite_scores() 方法

### 功能说明

从 Parquet 文件加载因子合成后的综合评分数据，包括进攻型评分、防御型评分和风险等级。

### 方法签名

```python
def load_composite_scores(
    self, 
    year: Optional[int] = None
) -> pd.DataFrame
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| year | int | None | 报告年度，如 2023。<br>None 表示加载所有年份 |

### 返回值

DataFrame，包含以下列：
- stock_code: 股票代码
- report_year: 报告年度
- offensive_score: 进攻型评分（0-100）
- defensive_score: 防御型评分（0-100）
- composite_risk_level: 综合风险等级（green/yellow/orange/red）

### 使用示例

```python
from src.data_pipeline.data_loader import DataLoader

# 初始化加载器
loader = DataLoader(data_dir='data')

# 示例1: 加载2023年综合评分
scores_2023 = loader.load_composite_scores(year=2023)
print(scores_2023.head())

# 示例2: 筛选进攻型高分股票（>80分）
top_offensive = scores_2023[scores_2023['offensive_score'] > 80]
print(f"进攻型高分股票数量: {len(top_offensive)}")
print(top_offensive[['stock_code', 'offensive_score']])

# 示例3: 筛选低风险股票（green等级）
low_risk = scores_2023[scores_2023['composite_risk_level'] == 'green']
print(f"低风险股票数量: {len(low_risk)}")

# 示例4: 加载所有年份的评分数据
all_scores = loader.load_composite_scores(year=None)
print(f"总共 {len(all_scores)} 条评分记录")
```

---

## 完整工作流程示例

```python
from src.data_pipeline.data_loader import DataLoader

# 1. 初始化
loader = DataLoader(data_dir='data')

# 2. 获取股票列表
stocks = loader.get_stock_list()
print(f"共有 {len(stocks)} 只股票")

# 3. 对每只股票进行分析
for _, stock in stocks.iterrows():
    code = stock['stock_code']
    
    # 加载财务数据
    financial = loader.load_financial(stock_code=code, year=2023)
    
    # 加载治理数据
    pledge = loader.load_governance('pledge', code, 2023)
    audit = loader.load_governance('audit', code, 2023)
    
    # 检查风险
    if not pledge.empty and pledge['pledged_shares_ratio'].values[0] > 50:
        print(f"⚠️ {code} 股权质押比例过高!")
    
    if not audit.empty and audit['is_standard_audit'].values[0] == 0:
        print(f"⚠️ {code} 审计意见非标!")

# 4. 加载综合评分进行选股
scores = loader.load_composite_scores(2023)

# 进攻型策略：选择高分且低风险的股票
selected = scores[
    (scores['offensive_score'] > 75) & 
    (scores['composite_risk_level'].isin(['green', 'yellow']))
].nlargest(10, 'offensive_score')

print("推荐的进攻型股票:")
print(selected[['stock_code', 'offensive_score', 'composite_risk_level']])
```

---

## 注意事项

### 1. 数据库表结构

确保 SQLite 数据库中存在 `governance_data` 表，结构如下：

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

### 2. Parquet 文件路径

综合评分数据应位于：
```
data/factors/composite_scores.parquet
```

### 3. 数据依赖关系

- `load_governance()` 依赖于 SQLite 数据库中的治理数据
- `load_composite_scores()` 依赖于因子合成后生成的 Parquet 文件
- 在使用前请确保数据已经正确导入

### 4. 空数据处理

如果数据不存在，方法会返回空的 DataFrame，不会抛出异常。建议在使用前检查：

```python
df = loader.load_governance('pledge', '000001.SZ', 2023)
if df.empty:
    print("未找到治理数据")
else:
    # 处理数据
    pass
```

---

## 测试验证

运行测试脚本验证功能：

```bash
python tests/test_data_pipeline/test_dataloader_new_methods.py
```

预期输出：
```
✅ load_governance测试完成!
✅ load_composite_scores测试完成!
🎉 所有测试通过！
```

---

## 相关代码位置

- **实现文件**: `src/data_pipeline/data_loader.py`
- **测试文件**: `tests/test_data_pipeline/test_dataloader_new_methods.py`
- **使用示例**: `main.py` 中的组合分析流程

---

## 下一步

有了这两个方法，您现在可以：

1. ✅ 加载完整的治理数据进行风险筛查
2. ✅ 获取综合评分进行选股策略
3. ✅ 结合 L1/L2/L3 因子进行全方位分析
4. ✅ 执行回测策略（需要行情数据）

接下来建议：
- 准备真实的治理数据并导入数据库
- 运行因子合成器生成综合评分
- 创建 Jupyter Notebook 进行交互式分析
