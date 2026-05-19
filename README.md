# 上市公司全方位量化分析框架

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

基于"财报-战略-治理"三维视角的A股上市公司量化分析工具，将年报信息自动化转化为可回测的Alpha因子体系。

## 🎯 项目特色

- **零运维成本**：无需数据库服务器、API服务，本地即可运行
- **交互式分析**：通过Jupyter Notebook灵活探索数据
- **一键执行**：简单脚本完成从数据下载到因子计算的全流程
- **透明可控**：所有代码和数据结构清晰可见，便于定制修改

## 📋 功能模块

### L1 业绩验证层
- ROE、ROA、ROIC等盈利能力指标
- 毛利率分级评价（行业差异化）
- 盈利质量综合评分（0-100分）

### L2 战略执行层
- FinBERT-CN情绪分析
- 战略承诺抽取与兑现率计算
- 研发强度、CAPEX兑现率

### L3 治理排雷层
- 大股东质押率监控
- 审计意见一票否决
- 核心人员流失率分析

### 因子合成与回测
- 施密特正交化消除多重共线性
- 进攻型/防御型打分卡模型
- Qlib回测引擎集成

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/yourname/FSG-Quant.git
cd FSG-Quant

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据准备

```bash
# 创建数据目录
mkdir data\raw\annual_reports
mkdir data\market_data\daily_quotes

# 下载年报PDF（手动或自动）
# 从巨潮资讯下载年报PDF到 data/raw/annual_reports/

# 导出行情数据（从Tushare/Akshare）
# 保存为Parquet格式到 data/market_data/daily_quotes/
```

### 3. 运行Pipeline

```bash
# 执行完整计算流程
python scripts\run_all.bat  # Windows
# bash scripts/run_all.sh   # Linux/Mac
```

### 4. 交互式分析

```bash
# 启动Jupyter Notebook
jupyter notebook

# 打开 notebooks/02_factor_analysis.ipynb 开始分析
```

## 📁 项目结构

```
FSG-Quant/
├── config/                    # 配置文件
│   ├── industry_thresholds.yaml    # 行业阈值
│   ├── factor_weights.yaml         # 打分卡权重
│   └── settings.py                 # 全局配置
│
├── data/                      # 数据目录（gitignore）
│   ├── raw/                   # 原始数据
│   ├── processed/             # 处理后数据
│   ├── factors/               # 因子数据
│   └── market_data/           # 行情数据
│
├── src/                       # 源代码
│   ├── data_pipeline/         # 数据管道
│   ├── factors/               # 因子计算
│   ├── nlp/                   # NLP模块
│   └── backtest/              # 回测模块
│
├── scripts/                   # 执行脚本
│   ├── 01_download_reports.py
│   ├── 03_calculate_L1.py
│   └── run_all.bat
│
├── tests/                     # 测试代码
├── notebooks/                 # Jupyter Notebook
├── docs/                      # 文档
├── requirements.txt
└── README.md
```

## 📖 文档

- [PRD v2.0](docs/PRD_v2.0.md) - 产品需求文档
- [系统设计v2.0](docs/system_design_v2.0.md) - 系统架构设计
- [详细设计](docs/detailed_design.md) - 模块详细设计

## 🔧 开发指南

### TDD开发流程

本项目采用测试驱动开发（TDD）：

1. 先编写单元测试（`tests/`目录）
2. 运行测试确认失败
3. 实现代码使测试通过
4. 重构优化

### 示例：添加新因子

```python
# 1. 在 src/factors/L1_performance.py 中添加计算方法
def calculate_new_factor(self, financial: dict) -> float:
    """计算新因子"""
    return ...

# 2. 在 tests/test_factors/test_L1_performance.py 中添加测试
def test_new_factor():
    result = calculator.calculate_new_factor(test_data)
    assert 0 <= result <= 1

# 3. 运行测试
pytest tests/test_factors/test_L1_performance.py -v
```

## 📊 示例分析

### 筛选高分股票

```python
import pandas as pd

# 加载因子数据
composite = pd.read_parquet('data/factors/composite_scores.parquet')

# 筛选进攻型Top 20
top20 = composite.nlargest(20, 'offensive_score')
print(top20[['stock_code', 'offensive_score', 'risk_level']])
```

### 可视化ROE分布

```python
import matplotlib.pyplot as plt

l1 = pd.read_parquet('data/factors/L1_factors.parquet')

plt.figure(figsize=(10, 6))
plt.hist(l1['roe'], bins=50, edgecolor='black')
plt.title('ROE分布')
plt.xlabel('ROE')
plt.ylabel('股票数量')
plt.show()
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题，请提交Issue或发送邮件至：your-email@example.com

---

**注意**：本工具仅供个人研究使用，不构成投资建议。投资有风险，入市需谨慎。
