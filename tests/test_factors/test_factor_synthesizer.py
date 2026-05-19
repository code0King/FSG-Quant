"""
FactorSynthesizer单元测试

测试目标：
1. 正确执行施密特正交化
2. 正确计算进攻型打分卡
3. 正确计算防御型打分卡
4. 正确评定综合风险等级
5. 处理边界情况（空值、异常数据等）
6. 生成完整的合成结果
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock
import pandas as pd
import numpy as np

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestFactorSynthesizer:
    """因子合成器测试类"""
    
    @pytest.fixture
    def mock_data_loader(self):
        """模拟DataLoader"""
        loader = Mock()
        
        # Mock L1因子数据
        l1_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ'],
            'report_year': [2023, 2023],
            'roe': [0.15, 0.08],
            'revenue_growth': [0.25, 0.10],
            'profit_quality_score': [85.0, 60.0],
            'cash_flow_coverage': [1.5, 0.8],
            'asset_health_score': [75.0, 55.0]
        })
        
        # Mock L2因子数据
        l2_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ'],
            'report_year': [2023, 2023],
            'revenue_fulfillment_rate': [125.0, 80.0],
            'management_sentiment': [0.65, -0.2],
            'strategy_execution_score': [85.0, 50.0]
        })
        
        # Mock L3因子数据
        l3_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ'],
            'report_year': [2023, 2023],
            'pledge_ratio': [15.0, 45.0],
            'executive_turnover': [5.0, 25.0],
            'governance_risk_level': ['green', 'orange']
        })
        
        def mock_load_factors(factor_type, year=None):
            if factor_type == 'L1':
                return l1_df
            elif factor_type == 'L2':
                return l2_df
            elif factor_type == 'L3':
                return l3_df
            else:
                return pd.DataFrame()
        
        loader.load_factors.side_effect = mock_load_factors
        
        return loader
    
    @pytest.fixture
    def synthesizer(self, mock_data_loader):
        """创建FactorSynthesizer实例"""
        from factors.factor_synthesizer import FactorSynthesizer
        
        synthesizer = FactorSynthesizer(data_loader=mock_data_loader)
        
        return synthesizer
    
    def test_schmidt_orthogonalization_basic(self, synthesizer):
        """测试基础施密特正交化"""
        # 创建两个相关的向量
        v1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        v2 = np.array([2.0, 4.0, 6.0, 8.0, 10.0])  # 与v1完全相关
        
        vectors = [v1, v2]
        orthogonal_vectors = synthesizer._schmidt_orthogonalization(vectors)
        
        # 验证输出数量
        assert len(orthogonal_vectors) == 2
        
        # 验证正交性（点积接近0）
        dot_product = np.dot(orthogonal_vectors[0], orthogonal_vectors[1])
        assert abs(dot_product) < 1e-6
    
    def test_schmidt_orthogonalization_three_vectors(self, synthesizer):
        """测试三个向量的正交化"""
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([1.0, 1.0, 0.0])
        v3 = np.array([1.0, 1.0, 1.0])
        
        vectors = [v1, v2, v3]
        orthogonal_vectors = synthesizer._schmidt_orthogonalization(vectors)
        
        # 验证两两正交
        for i in range(len(orthogonal_vectors)):
            for j in range(i+1, len(orthogonal_vectors)):
                dot_product = np.dot(orthogonal_vectors[i], orthogonal_vectors[j])
                assert abs(dot_product) < 1e-6, f"Vectors {i} and {j} are not orthogonal"
    
    def test_offensive_score_calculation(self, synthesizer):
        """测试进攻型打分卡计算"""
        stock_factors = {
            'l2_fulfillment': 125.0,      # 高兑现率
            'l1_revenue_growth': 25.0,    # 高增长
            'l1_profit_quality': 85.0,    # 高质量
            'l3_governance': 90.0,        # 好治理
            'l2_sentiment': 82.5          # 积极情绪（已映射到0-100）
        }
        
        score = synthesizer._calculate_offensive_score(stock_factors)
        
        # 高质量公司应该得分较高（允许一定误差）
        assert score > 65
        assert 0 <= score <= 100
    
    def test_defensive_score_calculation(self, synthesizer):
        """测试防御型打分卡计算"""
        stock_factors = {
            'l3_governance': 90.0,        # 好治理
            'l1_cash_quality': 85.0,      # 好现金流
            'l1_asset_health': 75.0,      # 健康资产
            'l2_consistency': 80.0,       # 战略一致
            'l1_stability': 70.0          # 稳定盈利
        }
        
        score = synthesizer._calculate_defensive_score(stock_factors)
        
        # 稳健公司应该得分高
        assert score > 70
        assert 0 <= score <= 100
    
    def test_offensive_vs_defensive_scoring(self, synthesizer):
        """测试进攻型vs防御型评分差异"""
        # 高增长但高风险的公司
        growth_stock = {
            'l2_fulfillment': 150.0,
            'l1_revenue_growth': 50.0,
            'l1_profit_quality': 60.0,
            'l3_governance': 50.0,
            'l2_sentiment': 0.8
        }
        
        offensive_score = synthesizer._calculate_offensive_score(growth_stock)
        defensive_score = synthesizer._calculate_defensive_score(growth_stock)
        
        # 成长股进攻型评分应该高于防御型
        assert offensive_score > defensive_score
    
    def test_risk_level_green(self, synthesizer):
        """测试绿色风险等级"""
        result = synthesizer._assess_composite_risk(
            offensive_score=85.0,
            defensive_score=80.0,
            governance_level='green'
        )
        
        assert result == 'green'
    
    def test_risk_level_yellow(self, synthesizer):
        """测试黄色风险等级"""
        result = synthesizer._assess_composite_risk(
            offensive_score=60.0,
            defensive_score=65.0,
            governance_level='yellow'
        )
        
        assert result == 'yellow'
    
    def test_risk_level_orange(self, synthesizer):
        """测试橙色风险等级"""
        result = synthesizer._assess_composite_risk(
            offensive_score=45.0,
            defensive_score=50.0,
            governance_level='orange'
        )
        
        assert result == 'orange'
    
    def test_risk_level_red_low_scores(self, synthesizer):
        """测试红色风险等级 - 低分"""
        result = synthesizer._assess_composite_risk(
            offensive_score=30.0,
            defensive_score=35.0,
            governance_level='red'
        )
        
        assert result == 'red'
    
    def test_risk_level_red_governance(self, synthesizer):
        """测试红色风险等级 - 治理风险"""
        # 即使分数尚可，治理红色也应触发红色
        result = synthesizer._assess_composite_risk(
            offensive_score=70.0,
            defensive_score=65.0,
            governance_level='red'  # 治理红色
        )
        
        assert result == 'red'
    
    def test_calculate_all_complete_result(self, synthesizer):
        """测试完整计算流程"""
        result = synthesizer.calculate_all(2023)
        
        # 验证返回结构
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # 2只股票
        
        # 验证列存在
        required_columns = [
            'stock_code',
            'offensive_score',
            'defensive_score',
            'composite_risk_level'
        ]
        for col in required_columns:
            assert col in result.columns
    
    def test_calculate_all_score_ranges(self, synthesizer):
        """测试所有评分的合理范围"""
        result = synthesizer.calculate_all(2023)
        
        # 进攻型评分应该在0-100之间
        assert all(0 <= result['offensive_score'])
        assert all(result['offensive_score'] <= 100)
        
        # 防御型评分应该在0-100之间
        assert all(0 <= result['defensive_score'])
        assert all(result['defensive_score'] <= 100)
    
    def test_calculate_all_risk_levels(self, synthesizer):
        """测试风险等级取值"""
        result = synthesizer.calculate_all(2023)
        
        valid_levels = ['green', 'yellow', 'orange', 'red']
        assert all(level in valid_levels for level in result['composite_risk_level'])
    
    def test_empty_data_handling(self):
        """测试空数据处理"""
        mock_loader = Mock()
        mock_loader.load_factors.return_value = pd.DataFrame()
        
        from factors.factor_synthesizer import FactorSynthesizer
        synthesizer = FactorSynthesizer(data_loader=mock_loader)
        
        result = synthesizer.calculate_all(2023)
        
        # 应该返回空DataFrame而不是报错
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_missing_factors_handling(self, mock_data_loader):
        """测试缺失因子处理"""
        # Mock返回部分数据
        partial_l1 = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'roe': [0.15]
            # 缺少其他因子
        })
        
        def mock_load_partial(factor_type, year=None):
            if factor_type == 'L1':
                return partial_l1
            else:
                return pd.DataFrame()
        
        mock_data_loader.load_factors.side_effect = mock_load_partial
        
        from factors.factor_synthesizer import FactorSynthesizer
        synthesizer = FactorSynthesizer(data_loader=mock_data_loader)
        
        result = synthesizer.calculate_all(2023)
        
        # 应该有合理的默认值或跳过
        assert isinstance(result, pd.DataFrame)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
