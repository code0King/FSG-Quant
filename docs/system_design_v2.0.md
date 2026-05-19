# 上市公司全方位量化分析框架 - 系统设计说明书 v2.0（个人版）

**文档版本**：v2.0  
**编写日期**：2026-05-14  
**关联文档**：PRD v2.0

---

## 1. 系统概述

### 1.1 设计目标
构建一个轻量级、易部署、交互式强的个人量化分析工具，避免企业级系统的复杂性，聚焦核心因子计算与分析功能。

### 1.2 设计原则
- **极简主义**：最少的外部依赖，零配置启动
- **本地优先**：所有数据存储在本地，无需网络连接（除数据下载阶段）
- **透明可见**：所有中间结果以文件形式保存，便于检查与调试
- **渐进式增强**：基础功能先上线，高级功能按需添加

---

## 2. 系统架构

### 2.1 分层架构

```
┌─────────────────────────────────┐
│  Presentation Layer             │
│  Jupyter Notebook               │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Application Layer              │
│  Python Scripts                 │
│  ├─ Data Pipeline               │
│  ├─ Factor Calculation          │
│  ├─ NLP Engine                  │
│  └─ Backtest Engine             │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Data Access Layer              │
│  ├─ SQLite (structured data)    │
│  └─ Parquet (factors + texts)   │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│  Data Source Layer              │
│  ├─ CNINFO (annual reports)     │
│  └─ Tushare (market data)       │
└─────────────────────────────────┘
```

### 2.2 数据流设计

#### 2.2.1 年度因子计算流程（简化版）

```
[手动触发或定时任务]
    ↓
Step 1: 下载年报PDF
    python scripts/01_download_reports.py
    ↓
Step 2: 解析PDF
    ├─ 提取财务数据 → SQLite
    └─ 提取MD&A文本 → Parquet
    ↓
Step 3: 计算L1因子
    python scripts/03_calculate_L1.py
    → data/factors/L1_factors.parquet
    ↓
Step 4: 计算L2因子
    python scripts/04_calculate_L2.py
    ├─ FinBERT推理
    └─ 承诺抽取
    → data/factors/L2_factors.parquet
    ↓
Step 5: 计算L3因子
    python scripts/05_calculate_L3.py
    → data/factors/L3_factors.parquet
    ↓
Step 6: 正交化 + 打分卡
    python scripts/06_orthogonalize.py
    python scripts/07_composite_score.py
    → data/factors/composite_scores.parquet
    ↓
Step 7: 回测（可选）
    python scripts/08_run_backtest.py
    ↓
[完成] 查看logs/pipeline.log
```

#### 2.2.2 交互式分析流程

```
[Jupyter Notebook启动]
    ↓
加载Parquet文件
    pd.read_parquet('data/factors/L1_factors.parquet')
    ↓
Pandas数据分析
    df[df['profit_quality_score'] > 80]
    ↓
Matplotlib可视化
    plt.hist(df['roe'])
    ↓
[实时反馈]
```

---

## 3. 数据库设计（简化版）

### 3.1 SQLite Schema

```sql
-- companies表
CREATE TABLE companies (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT NOT NULL,
    industry_sw_level1 TEXT,
    listing_date TEXT
);

-- financial_annual表
CREATE TABLE financial_annual (
    stock_code TEXT NOT NULL,
    report_year INTEGER NOT NULL,
    
    -- 利润表
    revenue REAL,
    cost_of_revenue REAL,
    gross_profit REAL,
    net_profit REAL,
    net_profit_deducted REAL,
    rd_expenses REAL,
    
    -- 资产负债表
    total_assets REAL,
    net_assets REAL,
    accounts_receivable REAL,
    inventory REAL,
    goodwill REAL,
    
    -- 现金流量表
    operating_cash_flow REAL,
    capex REAL,
    
    -- 关键指标
    roe REAL,
    roa REAL,
    roic REAL,
    gross_margin REAL,
    
    PRIMARY KEY (stock_code, report_year),
    FOREIGN KEY (stock_code) REFERENCES companies(stock_code)
);

-- governance_data表
CREATE TABLE governance_data (
    stock_code TEXT NOT NULL,
    report_year INTEGER NOT NULL,
    
    major_shareholder_pledge_ratio REAL,
    audit_opinion TEXT,
    is_standard_audit BOOLEAN,
    core_personnel_turnover_rate REAL,
    
    PRIMARY KEY (stock_code, report_year),
    FOREIGN KEY (stock_code) REFERENCES companies(stock_code)
);

-- 索引
CREATE INDEX idx_financial_year ON financial_annual(report_year);
CREATE INDEX idx_governance_year ON governance_data(report_year);
```

### 3.2 Parquet文件Schema

#### L1_factors.parquet
```python
columns = [
    'stock_code',           # str
    'report_year',          # int
    'roe',                  # float32
    'roa',                  # float32
    'roic',                 # float32
    'gross_margin',         # float32
    'gross_margin_grade',   # str: 高/中/低/极低
    'gross_margin_score',   # int: 0/30/60/100
    'deducted_profit_ratio',# float32
    'cash_flow_coverage',   # float32
    'profit_quality_score'  # float32: 0-100
]
```

#### L2_factors.parquet
```python
columns = [
    'stock_code',
    'report_year',
    'revenue_growth_target',     # float32 or NaN
    'strategy_fulfillment_rate', # float32
    'rd_intensity',              # float32
    'capex_fulfillment_rate',    # float32
    'mda_sentiment_score',       # float32: -1 to 1
    'sentiment_label',           # str: positive/neutral/negative
    'risk_warning_density',      # float32
    'has_explicit_commitment'    # bool
]
```

#### L3_factors.parquet
```python
columns = [
    'stock_code',
    'report_year',
    'major_shareholder_pledge_ratio',  # float32
    'governance_score',                # float32: 0-100
    'audit_opinion_code',              # float32: 1/0.5/0/-1
    'core_personnel_turnover_rate',    # float32
    'veto_reasons'                     # str: JSON数组
]
```

#### composite_scores.parquet
```python
columns = [
    'stock_code',
    'report_year',
    'offensive_score',      # float32: 0-100
    'offensive_rank',       # int
    'defensive_score',      # float32: 0-100
    'defensive_rank',       # int
    'risk_level',           # str: red/orange/yellow/green
    'risk_score',           # float32
    'recommendation'        # str
]
```

---

## 4. 模块设计

### 4.1 数据管道模块

#### 4.1.1 PDF解析器

**职责**：从年报PDF中提取财务数据和MD&A文本

**输入**：PDF文件路径  
**输出**：结构化数据（写入SQLite）+ 文本数据（写入Parquet）

**关键方法**：
```python
class AnnualReportParser:
    def parse(self, pdf_path: str) -> dict:
        """解析单个PDF"""
        
    def batch_parse(self, pdf_dir: str):
        """批量解析目录下的所有PDF"""
```

**依赖库**：
- pdfplumber（表格提取）
- PyMuPDF（文本提取）

---

### 4.2 因子计算模块

#### 4.2.1 L1因子计算器

**文件**：`src/factors/L1_performance.py`

**输入**：SQLite中的财务数据  
**输出**：L1_factors.parquet

**核心算法**：
```python
def calculate_roe(net_profit, avg_net_assets):
    return net_profit / avg_net_assets

def evaluate_gross_margin_industry(margin, industry_margins):
    percentile = stats.percentileofscore(industry_margins, margin)
    if percentile >= 75: return "高", 100
    elif percentile >= 50: return "中", 60
    elif percentile >= 25: return "低", 30
    else: return "极低", 0

def composite_profit_quality(roe, roic, cash_cov, deducted_ratio, margin_score):
    return 0.25*roe + 0.20*roic + 0.20*cash_cov + 0.15*deducted_ratio + 0.20*margin_score
```

---

#### 4.2.2 L2因子计算器

**文件**：`src/factors/L2_strategy.py`

**输入**：Parquet中的MD&A文本  
**输出**：L2_factors.parquet

**核心流程**：
1. 加载MD&A文本
2. FinBERT-CN推理 → 情绪得分
3. 正则表达式抽取承诺
4. 对比T年承诺与T+1年实际 → 兑现率
5. 计算研发强度、CAPEX兑现率

---

#### 4.2.3 L3因子计算器

**文件**：`src/factors/L3_governance.py`

**输入**：SQLite中的治理数据  
**输出**：L3_factors.parquet

**核心逻辑**：
```python
def check_veto(pledge_ratio, audit_opinion):
    """一票否决检查"""
    if pledge_ratio > 0.6:
        return True, "质押率>60%"
    if audit_opinion != "标准无保留":
        return True, "非标准审计意见"
    return False, None
```

---

### 4.3 NLP模块

#### 4.3.1 FinBERT分析器

**文件**：`src/nlp/finbert_analyzer.py`

**模型**：`uer/finbert-cn`（HuggingFace）

**核心方法**：
```python
class FinBERTAnalyzer:
    def __init__(self):
        self.model = AutoModelForSequenceClassification.from_pretrained("uer/finbert-cn")
        self.tokenizer = AutoTokenizer.from_pretrained("uer/finbert-cn")
    
    def analyze_sentiment(self, text: str) -> dict:
        """
        Returns:
            {
                "sentiment_score": float (-1 to 1),
                "label": str,
                "confidence": float
            }
        """
```

**性能优化**：
- 批量推理（batch_size=32）
- CPU即可运行（无需GPU）
- 5000只股票约需1分钟

---

### 4.4 正交化模块

**文件**：`src/factors/orthogonalization.py`

**算法**：施密特正交化（Gram-Schmidt Process）

**输入**：合并后的L1/L2/L3因子DataFrame  
**输出**：正交化后的因子DataFrame

**验证**：
- 输出相关系数矩阵
- 确保所有因子间相关性 < 0.3

---

### 4.5 打分卡模块

**文件**：`src/factors/composite_scorer.py`

**权重配置**：`config/factor_weights.yaml`

```yaml
offensive:
  l2_fulfillment: 0.30
  l1_revenue_growth: 0.25
  l1_profit_quality: 0.20
  l3_governance: 0.15
  l2_sentiment: 0.10

defensive:
  l3_governance: 0.35
  l1_cash_quality: 0.30
  l1_asset_health: 0.20
  l2_consistency: 0.10
  l1_stability: 0.05
```

**风险分级逻辑**：
```python
def assign_risk_level(l3_score, l1_score, warning_count):
    if has_veto: return "red"
    elif l3_score < 40 or l1_score < 30: return "orange"
    elif warning_count >= 3: return "yellow"
    else: return "green"
```

---

### 4.6 回测模块

**文件**：`src/backtest/qlib_adapter.py`

**功能**：
1. 将Parquet因子转换为Qlib格式
2. 配置进攻型/防御型策略
3. 执行回测
4. 输出绩效指标

**关键配置**：
```python
# Qlib配置
provider_uri = "~/.qlib/qlib_data/cn_data"
region = "cn"

# 策略参数
top_n = 30  # 持仓股票数
rebalance_freq = "yearly"  # 年度调仓
start_time = "2018-01-01"
end_time = "2023-12-31"
```

---

## 5. 接口设计（简化为函数接口）

由于是个人工具，不设计REST API，而是提供Python函数接口供Jupyter调用。

### 5.1 数据加载接口

```python
# src/data_pipeline/data_loader.py
class DataLoader:
    def load_financial(self, stock_code=None, year=None) -> pd.DataFrame
    def load_factors(self, factor_type='L1', year=None) -> pd.DataFrame
    def load_market_data(self, year, stock_code=None) -> pd.DataFrame
```

### 5.2 因子查询接口

```python
# notebooks/utils.py
def get_stock_factors(stock_code: str, year: int) -> dict:
    """获取某股票某年的完整因子"""
    
def screen_stocks(strategy_type='offensive', min_score=70, top_n=50) -> pd.DataFrame:
    """筛选高分股票"""
```

### 5.3 回测接口

```python
# src/backtest/qlib_adapter.py
def run_backtest(strategy_type='offensive', start_year=2018, end_year=2023) -> dict:
    """
    Returns:
        {
            "annual_return": float,
            "sharpe_ratio": float,
            "max_drawdown": float,
            ...
        }
    """
```

---

## 6. 配置管理

### 6.1 配置文件结构

```
config/
├── industry_thresholds.yaml    # 行业阈值
├── factor_weights.yaml         # 打分卡权重
└── settings.py                 # 全局配置
```

### 6.2 settings.py示例

```python
# config/settings.py
from pathlib import Path

# 路径配置
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
FACTORS_DIR = DATA_DIR / 'factors'
MARKET_DATA_DIR = DATA_DIR / 'market_data'

# 数据库配置
DB_PATH = RAW_DIR / 'financial_data.sqlite'

# 模型配置
FINBERT_MODEL_NAME = "uer/finbert-cn"

# 业务配置
REPORT_YEAR = 2023  # 当前分析的年报年度
TOP_N_STOCKS = 30   # 策略持仓数量
```

---

## 7. 日志与错误处理

### 7.1 日志配置

```python
# logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)

logger = logging.getLogger(__name__)
```

### 7.2 错误处理策略

| 错误类型 | 处理方式 | 示例 |
|---------|---------|------|
| PDF解析失败 | 记录日志，跳过该股票 | `logger.error(f"Failed to parse {pdf}")` |
| 财务数据缺失 | 标记为NaN，后续过滤 | `df.dropna(subset=['roe'])` |
| FinBERT推理超时 | 重试3次，仍失败则标记为neutral | `try-except with retry` |
| 数据库锁定 | 等待5秒后重试 | `sqlite3.OperationalError handling` |

---

## 8. 测试策略（简化版）

### 8.1 单元测试

```python
# tests/test_L1_factors.py
import pytest
from src.factors.L1_performance import L1PerformanceFactor

def test_roe_calculation():
    calculator = L1PerformanceFactor(...)
    result = calculator.calculate_all("000001.SZ", 2023)
    assert 0 <= result['roe'] <= 1

def test_gross_margin_grading():
    grade, score = evaluate_gross_margin_industry(0.45, [0.1, 0.2, 0.3, 0.4, 0.5])
    assert grade in ["高", "中", "低", "极低"]
```

### 8.2 集成测试

```python
# tests/test_pipeline.py
def test_full_pipeline():
    """测试完整pipeline是否正常运行"""
    os.system("bash scripts/run_all.sh")
    assert Path("data/factors/composite_scores.parquet").exists()
```

---

## 9. 部署指南

### 9.1 环境要求

- **操作系统**：Windows 10/11, macOS, Linux
- **Python版本**：3.9+
- **内存**：8GB+（推荐16GB）
- **磁盘空间**：100GB（含历史数据）

### 9.2 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourname/FSG-Quant.git
cd FSG-Quant

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 下载FinBERT模型（首次运行时自动下载）
python -c "from transformers import AutoModel; AutoModel.from_pretrained('uer/finbert-cn')"

# 5. 创建数据目录
mkdir -p data/raw/annual_reports
mkdir -p data/market_data/daily_quotes
```

### 9.3 首次运行

```bash
# 下载示例数据（或使用自己的数据）
python scripts/download_sample_data.py

# 执行完整pipeline
bash scripts/run_all.sh

# 启动Jupyter
jupyter notebook
```

---

**系统设计v2.0状态**：✅ 已完成
