# 快速开始指南

## 🚀 5分钟快速上手

### 1. 安装依赖

```bash
# 使用国内镜像源加速安装（推荐）
pip install pytest pandas pyarrow scipy pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或使用官方源
pip install pytest pandas pyarrow scipy pyyaml
```

### 2. 运行测试

```bash
# 运行DataLoader测试
python -m pytest tests/test_data_pipeline/test_data_loader.py -v

# 运行L1因子测试
python -m pytest tests/test_factors/test_L1_performance.py -v

# 运行所有测试
python -m pytest tests/ -v
```

### 3. 查看测试结果

如果看到类似输出，说明测试通过：
```
test_data_loader.py::TestDataLoader::test_load_financial_all_data PASSED
test_data_loader.py::TestDataLoader::test_load_financial_filter_by_stock PASSED
...
========================= 10 passed in 0.5s =========================
```

---

## 📖 使用示例

### 示例1：使用DataLoader加载数据

```python
from src.data_pipeline.data_loader import DataLoader

# 初始化加载器
loader = DataLoader(data_dir='data')

# 加载财务数据
df = loader.load_financial(stock_code='000001.SZ', year=2023)
print(df)

# 加载因子数据
l1_factors = loader.load_factors('L1', year=2023)
print(l1_factors.head())
```

### 示例2：计算L1因子

```python
from src.factors.L1_performance import L1PerformanceFactor

# 初始化计算器
calculator = L1PerformanceFactor(
    db_path='data/raw/financial_data.sqlite',
    industry_config_path='config/industry_thresholds.yaml'
)

# 计算某股票的L1因子
result = calculator.calculate_all('000001.SZ', 2023)

if result:
    print(f"ROE: {result['roe']:.2%}")
    print(f"毛利率等级: {result['gross_margin_grade']}")
    print(f"盈利质量评分: {result['profit_quality_score']}")
    print(f"预警项: {result['warning_flags']}")
```

---

## 🗂️ 准备测试数据

由于项目需要真实的财务数据才能运行，您需要：

### 方式1：使用示例数据（推荐用于测试）

运行以下脚本创建示例数据库：

```python
# scripts/create_sample_data.py
import sqlite3
from pathlib import Path

def create_sample_db():
    """创建示例SQLite数据库"""
    db_path = Path('data/raw/financial_data.sqlite')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 创建表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            stock_code TEXT PRIMARY KEY,
            stock_name TEXT,
            industry_sw_level1 TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS financial_annual (
            stock_code TEXT,
            report_year INTEGER,
            revenue REAL,
            net_profit REAL,
            roe REAL,
            PRIMARY KEY (stock_code, report_year)
        )
    """)
    
    # 插入示例数据
    cursor.execute("INSERT INTO companies VALUES ('000001.SZ', '平安银行', '银行')")
    cursor.execute("INSERT INTO financial_annual VALUES ('000001.SZ', 2023, 1000.0, 100.0, 0.10)")
    
    conn.commit()
    conn.close()
    print(f"Sample database created at {db_path}")

if __name__ == '__main__':
    create_sample_db()
```

运行：
```bash
python scripts/create_sample_data.py
```

### 方式2：从真实数据源导入

1. **从Tushare获取数据**
   ```python
   import tushare as ts
   
   # 设置token
   ts.set_token('your_token')
   pro = ts.pro_api()
   
   # 获取财务数据
   df = pro.income(ts_code='000001.SZ', period='20231231')
   print(df)
   ```

2. **从巨潮资讯下载年报PDF**
   - 访问：http://www.cninfo.com.cn/
   - 搜索股票代码
   - 下载年度报告PDF
   - 保存到 `data/raw/annual_reports/`

---

## 🔍 常见问题

### Q1: 测试失败，提示"No module named 'src'"

**解决**：确保在项目根目录运行测试
```bash
cd c:\python-file\FSG-Quant
python -m pytest tests/ -v
```

### Q2: 提示"Database not found"

**解决**：先创建示例数据库或准备真实数据
```bash
python scripts/create_sample_data.py
```

### Q3: 依赖安装失败

**解决**：使用国内镜像源
```bash
pip install pytest pandas pyarrow scipy pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q4: 如何查看测试覆盖率？

**解决**：安装pytest-cov并运行
```bash
pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html
# 打开 htmlcov/index.html 查看报告
```

---

## 📚 下一步学习

1. **阅读文档**
   - [PRD v2.0](docs/PRD_v2.0.md) - 了解产品需求
   - [系统设计](docs/system_design_v2.0.md) - 理解架构设计
   - [详细设计](docs/detailed_design.md) - 深入学习实现细节

2. **探索代码**
   - 查看 `src/data_pipeline/data_loader.py` 学习数据加载
   - 查看 `src/factors/L1_performance.py` 学习因子计算

3. **参与开发**
   - 按照TDD流程添加新因子
   - 编写测试 → 实现代码 → 运行测试

---

## 💬 获取帮助

- 查看 [README.md](README.md) 了解项目概况
- 查看 [DEVELOPMENT_PROGRESS.md](docs/DEVELOPMENT_PROGRESS.md) 了解开发进度
- 提交Issue报告问题

---

**祝您使用愉快！** 🎉
