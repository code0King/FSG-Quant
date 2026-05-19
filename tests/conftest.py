"""
pytest配置文件

定义全局fixtures和配置
"""
import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture
def sample_financial_data():
    """示例财务数据"""
    return {
        'stock_code': '000001.SZ',
        'report_year': 2023,
        'revenue': 1000.0,
        'net_profit': 100.0,
        'net_assets': 1000.0,
        'total_assets': 2000.0,
        'roe': 0.10,
    }


@pytest.fixture
def sample_industry_margins():
    """示例行业毛利率数据"""
    return [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
