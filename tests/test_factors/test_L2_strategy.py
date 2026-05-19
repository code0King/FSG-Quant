"""
L2StrategyFactor单元测试

测试目标：
1. 正确计算营收承诺兑现率
2. 正确计算利润承诺兑现率
3. 正确处理无承诺的情况
4. 正确整合情绪分析结果
5. 生成合理的战略执行评分
6. 处理边界情况（除零、空值等）
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestL2StrategyFactor:
    """L2战略执行层因子测试类"""
    
    @pytest.fixture
    def mock_data_loader(self):
        """模拟DataLoader"""
        loader = Mock()
        
        # 创建一个Mock DataFrame
        import pandas as pd
        
        # 当前年份数据
        current_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'revenue': [1000.0],
            'net_profit': [100.0]
        })
        
        # 上年数据
        last_year_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2022],
            'revenue': [800.0],
            'net_profit': [80.0]
        })
        
        # Mock load_financial方法，根据year参数返回不同数据
        def mock_load_financial(stock_code=None, year=None):
            if year == 2023:
                return current_df
            elif year == 2022:
                return last_year_df
            else:
                return pd.DataFrame()  # 空DataFrame
        
        loader.load_financial.side_effect = mock_load_financial
        
        return loader
    
    @pytest.fixture
    def mock_commitment_parser(self):
        """模拟CommitmentParser"""
        parser = Mock()
        
        # 模拟抽取到的承诺
        parser.extract_commitments.return_value = {
            'has_explicit': True,
            'revenue_growth_target': 20.0,  # 承诺增长20%
            'profit_growth_target': 15.0,   # 承诺增长15%
            'capex_target': None
        }
        
        return parser
    
    @pytest.fixture
    def mock_finbert_analyzer(self):
        """模拟FinBERTAnalyzer"""
        analyzer = Mock()
        
        # 模拟情绪分析结果
        analyzer.analyze_mda_section.return_value = {
            'overall_sentiment': 0.65,
            'overall_label': 'positive',
            'segment_count': 10
        }
        
        return analyzer
    
    @pytest.fixture
    def strategy_calculator(self, mock_data_loader, mock_commitment_parser, mock_finbert_analyzer):
        """创建L2StrategyFactor实例"""
        from factors.L2_strategy import L2StrategyFactor
        
        calculator = L2StrategyFactor(
            data_loader=mock_data_loader,
            commitment_parser=mock_commitment_parser,
            finbert_analyzer=mock_finbert_analyzer
        )
        
        return calculator
    
    def test_revenue_fulfillment_rate_exceeds(self, strategy_calculator):
        """测试营收兑现率 - 超额完成"""
        # 上年承诺增长20%，实际从800增长到1000（增长25%）
        last_year_data = {'revenue': 800.0}
        current_year_data = {'revenue': 1000.0}
        
        rate = strategy_calculator._calculate_revenue_fulfillment_rate(
            last_year_data, current_year_data, 20.0
        )
        
        # 实际增长25%，承诺20%，兑现率应该是125%
        assert rate > 100
        assert abs(rate - 125.0) < 0.1
    
    def test_revenue_fulfillment_rate_partial(self, strategy_calculator):
        """测试营收兑现率 - 部分完成"""
        # 上年承诺增长20%，实际从800增长到900（增长12.5%）
        last_year_data = {'revenue': 800.0}
        current_year_data = {'revenue': 900.0}
        
        rate = strategy_calculator._calculate_revenue_fulfillment_rate(
            last_year_data, current_year_data, 20.0
        )
        
        # 实际增长12.5%，承诺20%，兑现率应该是62.5%
        assert 60 < rate < 65
    
    def test_revenue_fulfillment_rate_no_growth(self, strategy_calculator):
        """测试营收兑现率 - 负增长"""
        # 上年承诺增长20%，实际从800降到700
        last_year_data = {'revenue': 800.0}
        current_year_data = {'revenue': 700.0}
        
        rate = strategy_calculator._calculate_revenue_fulfillment_rate(
            last_year_data, current_year_data, 20.0
        )
        
        # 负增长，兑现率应该很低或为0
        assert rate >= 0
        assert rate < 50
    
    def test_profit_fulfillment_rate(self, strategy_calculator):
        """测试利润兑现率"""
        # 上年承诺增长15%，实际从80增长到100（增长25%）
        last_year_data = {'net_profit': 80.0}
        current_year_data = {'net_profit': 100.0}
        
        rate = strategy_calculator._calculate_profit_fulfillment_rate(
            last_year_data, current_year_data, 15.0
        )
        
        # 实际增长25%，承诺15%，兑现率应该是166.7%
        assert rate > 150
    
    def test_fulfillment_rate_division_by_zero(self, strategy_calculator):
        """测试兑现率计算 - 除零处理"""
        # 上年收入为0
        last_year_data = {'revenue': 0.0}
        current_year_data = {'revenue': 100.0}
        
        rate = strategy_calculator._calculate_revenue_fulfillment_rate(
            last_year_data, current_year_data, 20.0
        )
        
        # 应该返回合理的默认值而不是抛出异常
        assert isinstance(rate, (int, float))
        assert rate >= 0
    
    def test_management_sentiment_score(self, strategy_calculator):
        """测试管理层情绪得分"""
        mda_text = "公司业绩良好，未来发展可期"
        
        score = strategy_calculator._calculate_management_sentiment(mda_text)
        
        # 应该返回-1到1之间的值
        assert -1 <= score <= 1
    
    def test_management_sentiment_empty_text(self, strategy_calculator):
        """测试管理层情绪得分 - 空文本"""
        score = strategy_calculator._calculate_management_sentiment("")
        
        # 空文本应该返回0（中性）
        assert score == 0.0
    
    def test_strategy_execution_score_high(self, strategy_calculator):
        """测试战略执行评分 - 高质量"""
        fulfillment_rate = 120.0  # 超额完成
        sentiment_score = 0.8     # 积极情绪
        
        score = strategy_calculator._composite_strategy_score(fulfillment_rate, sentiment_score)
        
        # 高质量应该得分高
        assert score > 70
    
    def test_strategy_execution_score_low(self, strategy_calculator):
        """测试战略执行评分 - 低质量"""
        fulfillment_rate = 30.0   # 未完成
        sentiment_score = -0.5    # 消极情绪
        
        score = strategy_calculator._composite_strategy_score(fulfillment_rate, sentiment_score)
        
        # 低质量应该得分低
        assert score < 50
    
    def test_strategy_execution_score_range(self, strategy_calculator):
        """测试战略执行评分范围"""
        for fulfillment in [0, 50, 100, 150]:
            for sentiment in [-1.0, -0.5, 0.0, 0.5, 1.0]:
                score = strategy_calculator._composite_strategy_score(fulfillment, sentiment)
                assert 0 <= score <= 100, f"Score {score} out of range for fulfillment={fulfillment}, sentiment={sentiment}"
    
    def test_calculate_all_complete_result(self, strategy_calculator):
        """测试完整计算流程"""
        result = strategy_calculator.calculate_all('000001.SZ', 2023)
        
        # 验证返回结构
        assert isinstance(result, dict)
        assert 'revenue_fulfillment_rate' in result
        assert 'profit_fulfillment_rate' in result
        assert 'management_sentiment' in result
        assert 'strategy_execution_score' in result
    
    def test_calculate_all_score_ranges(self, strategy_calculator):
        """测试所有分数的合理范围"""
        result = strategy_calculator.calculate_all('000001.SZ', 2023)
        
        # 兑现率应该在合理范围（可能超过100%）
        assert result['revenue_fulfillment_rate'] >= 0
        assert result['profit_fulfillment_rate'] >= 0
        
        # 情绪得分在-1到1之间
        assert -1 <= result['management_sentiment'] <= 1
        
        # 综合评分在0到100之间
        assert 0 <= result['strategy_execution_score'] <= 100
    
    def test_no_explicit_commitment(self, mock_data_loader, mock_finbert_analyzer):
        """测试无明确承诺的情况"""
        # 修改Mock返回无承诺
        mock_parser = Mock()
        mock_parser.extract_commitments.return_value = {
            'has_explicit': False,
            'revenue_growth_target': None,
            'profit_growth_target': None,
            'capex_target': None
        }
        
        from factors.L2_strategy import L2StrategyFactor
        calculator = L2StrategyFactor(
            data_loader=mock_data_loader,
            commitment_parser=mock_parser,
            finbert_analyzer=mock_finbert_analyzer
        )
        
        result = calculator.calculate_all('000001.SZ', 2023)
        
        # 无承诺时，兑现率应该是None或0
        assert result['revenue_fulfillment_rate'] is None or result['revenue_fulfillment_rate'] == 0
        assert result['profit_fulfillment_rate'] is None or result['profit_fulfillment_rate'] == 0
    
    def test_missing_last_year_data(self, mock_data_loader, mock_commitment_parser, mock_finbert_analyzer):
        """测试缺少上年数据的情况"""
        # 修改Mock返回空数据
        mock_data_loader.load_financial.return_value = Mock(to_dict=lambda: {})
        
        from factors.L2_strategy import L2StrategyFactor
        calculator = L2StrategyFactor(
            data_loader=mock_data_loader,
            commitment_parser=mock_commitment_parser,
            finbert_analyzer=mock_finbert_analyzer
        )
        
        result = calculator.calculate_all('000001.SZ', 2023)
        
        # 应该有合理的默认值或None
        assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
