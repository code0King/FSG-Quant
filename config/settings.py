"""
全局配置模块

定义项目中使用的所有路径、常量等配置信息
"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
FACTORS_DIR = DATA_DIR / 'factors'
MARKET_DATA_DIR = DATA_DIR / 'market_data'

# 数据库配置
DB_PATH = RAW_DIR / 'financial_data.sqlite'
DB_FILENAME = 'financial_data.sqlite'

# 配置文件路径
INDUSTRY_CONFIG_PATH = BASE_DIR / 'config' / 'industry_thresholds.yaml'
WEIGHTS_CONFIG_PATH = BASE_DIR / 'config' / 'factor_weights.yaml'

# NLP模型配置
FINBERT_MODEL_NAME = "uer/finbert-cn"

# 业务配置
REPORT_YEAR = 2023  # 当前分析的年报年度
TOP_N_STOCKS = 30   # 策略持仓数量

# 日志配置
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'pipeline.log'
