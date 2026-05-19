"""
BacktestEngine单元测试

测试目标：
1. 正确转换因子数据为Qlib格式
2. 正确执行年度调仓策略
3. 正确计算绩效指标
4. 处理边界情况（空数据、缺失值等）
5. 生成完整的回测结果
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import pandas as pd
import numpy as np

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestBacktestEngine:
    """回测引擎测试类"""
    
    @pytest.fixture
    def mock_data_loader(self):
        """模拟DataLoader"""
        loader = Mock()
        
        # Mock综合评分数据
        scores_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ', '600519.SH'],
            'report_year': [2023, 2023, 2023],
            'offensive_score': [85.0, 55.0, 78.0],
            'defensive_score': [80.0, 62.0, 85.0],
            'composite_risk_level': ['green', 'yellow', 'green']
        })
        
        # Mock行情数据
        market_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000001.SZ', '000002.SZ', '000002.SZ'],
            'date': ['2023-01-01', '2023-12-31', '2023-01-01', '2023-12-31'],
            'close': [10.0, 12.0, 20.0, 18.0],
            'volume': [1000000, 1200000, 800000, 900000]
        })
        
        def mock_load_composite_scores(year=None):
            if year == 2023:
                return scores_df
            else:
                return pd.DataFrame()
        
        def mock_load_market_data(stock_codes=None, start_date=None, end_date=None):
            return market_df
        
        loader.load_composite_scores.side_effect = mock_load_composite_scores
        loader.load_market_data.side_effect = mock_load_market_data
        
        return loader
    
    @pytest.fixture
    def backtest_engine(self, mock_data_loader):
        """创建BacktestEngine实例"""
        from backtest.backtest_engine import BacktestEngine
        
        engine = BacktestEngine(data_loader=mock_data_loader)
        
        return engine
    
    def test_convert_to_qlib_format(self, backtest_engine):
        """测试转换为Qlib格式"""
        scores_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ'],
            'report_year': [2023, 2023],
            'offensive_score': [85.0, 55.0]
        })
        
        qlib_data = backtest_engine._convert_to_qlib_format(scores_df)
        
        # 验证返回类型
        assert isinstance(qlib_data, pd.DataFrame)
        # 验证列存在
        assert 'instrument' in qlib_data.columns or 'stock_code' in qlib_data.columns
    
    def test_select_top_stocks_offensive(self, backtest_engine):
        """测试进攻型选股"""
        scores_df = pd.DataFrame({
            'stock_code': ['A', 'B', 'C', 'D'],
            'offensive_score': [90.0, 70.0, 85.0, 60.0]
        })
        
        selected = backtest_engine._select_top_stocks(scores_df, strategy='offensive', top_n=2)
        
        # 应该选择得分最高的2只
        assert len(selected) == 2
        assert 'A' in selected['stock_code'].values  # 90分
        assert 'C' in selected['stock_code'].values  # 85分
    
    def test_select_top_stocks_defensive(self, backtest_engine):
        """测试防御型选股"""
        scores_df = pd.DataFrame({
            'stock_code': ['A', 'B', 'C'],
            'defensive_score': [75.0, 85.0, 80.0]
        })
        
        selected = backtest_engine._select_top_stocks(scores_df, strategy='defensive', top_n=2)
        
        # 应该选择防御型得分最高的2只
        assert len(selected) == 2
        assert 'B' in selected['stock_code'].values  # 85分
        assert 'C' in selected['stock_code'].values  # 80分
    
    def test_select_stocks_exclude_red_risk(self, backtest_engine):
        """测试排除红色风险股票"""
        scores_df = pd.DataFrame({
            'stock_code': ['A', 'B', 'C'],
            'offensive_score': [90.0, 85.0, 80.0],
            'composite_risk_level': ['green', 'red', 'yellow']  # B是红色风险
        })
        
        selected = backtest_engine._select_top_stocks(scores_df, strategy='offensive', top_n=2)
        
        # 不应该选择红色风险的股票
        assert 'B' not in selected['stock_code'].values
    
    def test_calculate_portfolio_return(self, backtest_engine):
        """测试组合收益率计算"""
        # 模拟持仓和价格数据
        holdings = pd.DataFrame({
            'stock_code': ['A', 'B'],
            'weight': [0.5, 0.5],
            'entry_price': [10.0, 20.0],
            'exit_price': [12.0, 18.0]
        })
        
        portfolio_return = backtest_engine._calculate_portfolio_return(holdings)
        
        # A收益20%，B收益-10%，平均5%
        expected_return = 0.5 * 0.2 + 0.5 * (-0.1)
        assert abs(portfolio_return - expected_return) < 0.01
    
    def test_calculate_sharpe_ratio(self, backtest_engine):
        """测试夏普比率计算"""
        # 模拟日收益率序列
        returns = pd.Series([0.01, -0.005, 0.008, 0.012, -0.003])
        
        sharpe = backtest_engine._calculate_sharpe_ratio(returns, risk_free_rate=0.03)
        
        # 夏普比率应该是数值
        assert isinstance(sharpe, (int, float))
    
    def test_calculate_max_drawdown(self, backtest_engine):
        """测试最大回撤计算"""
        # 模拟净值曲线：100 -> 110 -> 105 -> 115 -> 108
        net_values = pd.Series([100, 110, 105, 115, 108])
        
        max_dd = backtest_engine._calculate_max_drawdown(net_values)
        
        # 最大回撤应该是正数
        assert max_dd >= 0
        # 从115跌到108，回撤约6.1%
        assert max_dd < 0.1  # 小于10%
    
    def test_annual_rebalancing_strategy(self, backtest_engine):
        """测试年度调仓策略"""
        result = backtest_engine.run_annual_rebalancing(
            start_year=2023,
            end_year=2023,
            strategy='offensive',
            top_n=2
        )
        
        # 验证返回结构
        assert isinstance(result, dict)
        assert 'portfolio_returns' in result
        assert 'performance_metrics' in result
    
    def test_performance_metrics_structure(self, backtest_engine):
        """测试绩效指标结构"""
        result = backtest_engine.run_annual_rebalancing(
            start_year=2023,
            end_year=2023,
            strategy='offensive',
            top_n=2
        )
        
        metrics = result['performance_metrics']
        
        # 验证关键指标存在
        required_metrics = [
            'total_return',
            'annualized_return',
            'sharpe_ratio',
            'max_drawdown',
            'win_rate'
        ]
        
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
    
    def test_empty_data_handling(self, mock_data_loader):
        """测试空数据处理"""
        mock_data_loader.load_composite_scores.return_value = pd.DataFrame()
        
        from backtest.backtest_engine import BacktestEngine
        engine = BacktestEngine(data_loader=mock_data_loader)
        
        result = engine.run_annual_rebalancing(
            start_year=2023,
            end_year=2023,
            strategy='offensive',
            top_n=2
        )
        
        # 应该返回合理的默认结果
        assert isinstance(result, dict)
        assert 'performance_metrics' in result
    
    def test_invalid_strategy_handling(self, backtest_engine):
        """测试无效策略处理"""
        result = backtest_engine.run_annual_rebalancing(
            start_year=2023,
            end_year=2023,
            strategy='invalid_strategy',  # 无效策略
            top_n=2
        )
        
        # 应该有合理的错误处理
        assert isinstance(result, dict)
    
    def test_multi_year_backtest(self, backtest_engine):
        """测试多年回测"""
        # Mock多年数据
        multi_year_df = pd.DataFrame({
            'stock_code': ['A', 'B', 'A', 'B'],
            'report_year': [2022, 2022, 2023, 2023],
            'offensive_score': [80.0, 70.0, 85.0, 75.0],
            'defensive_score': [75.0, 80.0, 80.0, 85.0],
            'composite_risk_level': ['green', 'yellow', 'green', 'green']
        })
        
        backtest_engine.data_loader.load_composite_scores.side_effect = lambda year=None: \
            multi_year_df[multi_year_df['report_year'] == year] if year else pd.DataFrame()
        
        result = backtest_engine.run_annual_rebalancing(
            start_year=2022,
            end_year=2023,
            strategy='offensive',
            top_n=1
        )
        
        # 应该包含多年的结果
        assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
