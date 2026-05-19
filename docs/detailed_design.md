# 上市公司全方位量化分析框架 - 详细设计说明书

**文档版本**：v1.0  
**编写日期**：2026-05-14  
**关联文档**：PRD v2.0、系统设计v2.0  
**目标读者**：开发工程师

---

## 1. 引言

### 1.1 编写目的
本文档详细描述各模块的实现细节，包括类设计、函数签名、算法流程、数据结构等，指导编码实现。

### 1.2 适用范围
- 数据管道模块
- 因子计算模块（L1/L2/L3）
- NLP模块
- 正交化模块
- 打分卡模块
- 回测模块

---

## 2. 数据管道模块详细设计

### 2.1 DataLoader类

**文件**：`src/data_pipeline/data_loader.py`

#### 2.1.1 类定义

```python
class DataLoader:
    """
    数据加载器
    
    封装SQLite和Parquet数据源的访问逻辑，提供简洁的API。
    
    Attributes:
        data_dir: 数据根目录路径
        db_path: SQLite数据库完整路径
    """
```

#### 2.1.2 核心方法

```python
def load_financial(self, stock_code: Optional[str] = None, 
                  year: Optional[int] = None) -> pd.DataFrame:
    """
    从SQLite加载财务数据
    
    Args:
        stock_code: 股票代码（如'000001.SZ'），None表示加载全部
        year: 报告年度（如2023），None表示加载全部年份
        
    Returns:
        DataFrame包含财务数据
    """

def load_factors(self, factor_type: str = 'L1', 
                year: Optional[int] = None) -> pd.DataFrame:
    """
    从Parquet文件加载因子数据
    
    Args:
        factor_type: 因子类型，可选值：'L1', 'L2', 'L3', 'orthogonal', 'composite'
        year: 报告年度，None表示加载全部年份
        
    Returns:
        DataFrame包含因子数据
    """

def load_market_data(self, year: int, 
                    stock_code: Optional[str] = None) -> pd.DataFrame:
    """
    从Parquet文件加载行情数据
    
    Args:
        year: 年份（如2023）
        stock_code: 股票代码，None表示加载全部股票
        
    Returns:
        DataFrame包含行情数据
    """
```

---

## 3. L1因子计算模块详细设计

### 3.1 L1PerformanceFactor类

**文件**：`src/factors/L1_performance.py`

#### 3.1.1 类定义

```python
class L1PerformanceFactor:
    """
    L1业绩验证层因子计算器
    
    Attributes:
        db_path: SQLite数据库路径
        industry_config: 行业阈值配置字典
    """
```

#### 3.1.2 核心方法

```python
def calculate_all(self, stock_code: str, year: int) -> dict:
    """
    计算L1层所有因子
    
    Returns:
        {
            "roe": float,
            "roa": float,
            "roic": float,
            "gross_margin": float,
            "gross_margin_grade": str,
            "gross_margin_score": int,
            "deducted_profit_ratio": float,
            "cash_flow_coverage": float,
            "profit_quality_score": float,
            "warning_flags": list
        }
    """

def _evaluate_gross_margin(self, stock_code: str, year: int, margin: float) -> tuple:
    """
    行业差异化的毛利率分级
    
    Returns:
        (等级, 分数)，如 ("高", 100)
    """

def _composite_profit_quality(self, roe, roic, cash_cov, deducted_ratio, margin_score) -> float:
    """
    盈利质量综合评分
    
    公式：
    0.25×ROE标准化 + 0.20×ROIC标准化 + 0.20×现金流标准化 + 
    0.15×扣非占比 + 0.20×毛利率等级分
    """
```

---

## 4. L2因子计算模块详细设计

### 4.1 L2StrategyFactor类

**文件**：`src/factors/L2_strategy.py`

```python
class L2StrategyFactor:
    """
    L2战略执行层因子计算器
    """
    
    def calculate_all(self, stock_code: str, year: int) -> dict:
        """
        计算L2层所有因子
        
        Returns:
            {
                "strategy_fulfillment_rate": float,
                "rd_intensity": float,
                "mda_sentiment_score": float,
                "sentiment_label": str,
                "risk_warning_density": float,
                ...
            }
        """
```

---

### 4.2 FinBERTAnalyzer类

**文件**：`src/nlp/finbert_analyzer.py`

```python
class FinBERTAnalyzer:
    """
    FinBERT情绪分析器
    """
    
    def __init__(self, model_name: str = "uer/finbert-cn"):
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
    
    def analyze_sentiment(self, text: str) -> dict:
        """
        分析文本情绪
        
        Returns:
            {
                "sentiment_score": float (-1 to 1),
                "label": str,
                "confidence": float
            }
        """
```

---

### 4.3 CommitmentParser类

**文件**：`src/nlp/commitment_parser.py`

```python
class CommitmentParser:
    """
    战略承诺抽取器（方案A：正则表达式）
    """
    
    PATTERNS = [
        (r'营收.*?增长.*?(\d+\.?\d*)\s*%', 'revenue_growth'),
        (r'净利润.*?增长.*?(\d+\.?\d*)\s*%', 'profit_growth'),
        (r'资本支出.*?(\d+\.?\d*)\s*亿元', 'capex'),
    ]
    
    def extract_commitments(self, text: str) -> dict:
        """
        从文本中抽取承诺指标
        
        Returns:
            {
                "revenue_growth_target": float or None,
                "has_explicit": bool
            }
        """
```

---

## 5. L3因子计算模块详细设计

### 5.1 L3GovernanceFactor类

**文件**：`src/factors/L3_governance.py`

```python
class L3GovernanceFactor:
    """
    L3治理排雷层因子计算器
    """
    
    def calculate_all(self, stock_code: str, year: int) -> dict:
        """
        计算L3层所有因子
        
        Returns:
            {
                "major_shareholder_pledge_ratio": float,
                "governance_score": float,
                "audit_opinion_code": float,
                "veto_reasons": list
            }
        """
    
    def _check_veto(self, pledge_ratio: float, audit_opinion: str) -> list:
        """一票否决检查"""
```

---

## 6. 正交化模块详细设计

### 6.1 SchmidtOrthogonalizer类

**文件**：`src/factors/orthogonalization.py`

```python
class SchmidtOrthogonalizer:
    """
    施密特正交化实现
    """
    
    def orthogonalize(self, factors_df: pd.DataFrame) -> pd.DataFrame:
        """
        对因子进行施密特正交化
        
        Args:
            factors_df: DataFrame, shape=(n_stocks, n_factors)
            
        Returns:
            DataFrame: 正交化后的因子
        """
```

**算法流程**：
1. 标准化所有因子（均值0，标准差1）
2. 依次对每个因子减去在已正交因子上的投影
3. 归一化处理
4. 验证正交性（相关系数<0.3）

---

## 7. 打分卡模块详细设计

### 7.1 CompositeScorer类

**文件**：`src/factors/composite_scorer.py`

```python
class CompositeScorer:
    """
    打分卡模型
    """
    
    def __init__(self, weights_config_path: str):
        import yaml
        with open(weights_config_path, 'r', encoding='utf-8') as f:
            self.weights = yaml.safe_load(f)
    
    def calculate_offensive_score(self, factors: dict) -> float:
        """进攻型综合得分"""
        
    def calculate_defensive_score(self, factors: dict) -> float:
        """防御型综合得分"""
        
    def assign_risk_level(self, l3_factors: dict, l1_factors: dict) -> dict:
        """
        风险分级
        
        Returns:
            {
                "risk_level": str (red/orange/yellow/green),
                "risk_score": float,
                "recommendation": str
            }
        """
```

---

## 8. 回测模块详细设计

### 8.1 QlibAdapter类

**文件**：`src/backtest/qlib_adapter.py`

```python
class QlibAdapter:
    """
    Qlib回测适配器
    """
    
    def __init__(self, qlib_data_path: str = "~/.qlib/qlib_data/cn_data"):
        import qlib
        from qlib.config import REG_CN
        
        qlib.init(provider_uri=qlib_data_path, region=REG_CN)
    
    def run_backtest(self, strategy_type: str = 'offensive', 
                    start_year: int = 2018, 
                    end_year: int = 2023) -> dict:
        """
        执行回测
        
        Returns:
            {
                "annual_return": float,
                "sharpe_ratio": float,
                "max_drawdown": float
            }
        """
```

---

## 9. 配置文件示例

### 9.1 industry_thresholds.yaml

```yaml
industries:
  technology:
    industries: ["电子", "计算机", "通信", "传媒"]
    thresholds:
      min_roe: 8
      min_research_intensity: 10
      max_goodwill_ratio: 40
  
  manufacturing:
    industries: ["机械设备", "电气设备", "汽车"]
    thresholds:
      min_roe: 5
      min_research_intensity: 2
      max_goodwill_ratio: 20

default_thresholds:
  min_roe: 8
  min_research_intensity: 2
  max_goodwill_ratio: 20
```

### 9.2 factor_weights.yaml

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

---

## 10. 测试用例设计

### 10.1 DataLoader测试

```python
def test_load_financial_filter_by_stock():
    """测试按股票代码过滤"""
    df = loader.load_financial(stock_code='000001.SZ')
    assert len(df) > 0
    assert all(df['stock_code'] == '000001.SZ')

def test_load_factors_with_year_filter():
    """测试加载因子数据并按年份过滤"""
    df = loader.load_factors('L1', year=2023)
    assert all(df['report_year'] == 2023)
```

### 10.2 L1因子测试

```python
def test_roe_calculation():
    """测试ROE计算"""
    result = calculator.calculate_all("000001.SZ", 2023)
    assert 0 <= result['roe'] <= 1

def test_gross_margin_grading():
    """测试毛利率分级"""
    grade, score = calculator._evaluate_gross_margin("000001.SZ", 2023, 0.45)
    assert grade in ["高", "中", "低", "极低"]
    assert score in [0, 30, 60, 100]
```

---

**详细设计说明书状态**：✅ 已完成
