"""
L3GovernanceFactor单元测试

测试目标：
1. 正确计算股权质押比例
2. 正确识别审计意见类型
3. 正确计算高管流失率
4. 正确评定治理风险等级
5. 处理边界情况（空值、异常数据等）
6. 生成完整的治理因子结果
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock
import pandas as pd

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))


class TestL3GovernanceFactor:
    """L3治理排雷层因子测试类"""
    
    @pytest.fixture
    def mock_data_loader(self):
        """模拟DataLoader"""
        loader = Mock()
        
        # Mock质押数据
        pledge_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'pledged_shares_ratio': [15.5]  # 质押比例15.5%
        })
        
        # Mock审计意见数据
        audit_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'audit_opinion': ['标准无保留意见']
        })
        
        # Mock高管变动数据
        executive_df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000001.SZ'],
            'report_year': [2023, 2023],
            'executive_count_start': [10, 10],
            'executive_count_end': [9, 9],
            'departed_executives': [1, 1]
        })
        
        def mock_load_governance(data_type, stock_code=None, year=None):
            if data_type == 'pledge':
                return pledge_df
            elif data_type == 'audit':
                return audit_df
            elif data_type == 'executive':
                return executive_df
            else:
                return pd.DataFrame()
        
        loader.load_governance.side_effect = mock_load_governance
        
        return loader
    
    @pytest.fixture
    def governance_calculator(self, mock_data_loader):
        """创建L3GovernanceFactor实例"""
        from factors.L3_governance import L3GovernanceFactor
        
        calculator = L3GovernanceFactor(data_loader=mock_data_loader)
        
        return calculator
    
    def test_pledge_ratio_normal(self, governance_calculator):
        """测试正常质押比例"""
        ratio = governance_calculator._calculate_pledge_ratio('000001.SZ', 2023)
        
        assert ratio == 15.5
        assert 0 <= ratio <= 100
    
    def test_pledge_ratio_high_risk(self):
        """测试高质押比例"""
        # 创建新的Mock
        mock_loader = Mock()
        high_pledge_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'pledged_shares_ratio': [65.0]  # 65%质押率
        })
        mock_loader.load_governance.return_value = high_pledge_df
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_loader)
        
        ratio = calculator._calculate_pledge_ratio('000001.SZ', 2023)
        
        assert ratio == 65.0
        assert ratio > 50  # 高风险阈值
    
    def test_pledge_ratio_no_data(self):
        """测试无质押数据"""
        mock_loader = Mock()
        mock_loader.load_governance.return_value = pd.DataFrame()
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_loader)
        
        ratio = calculator._calculate_pledge_ratio('000001.SZ', 2023)
        
        # 无数据应该返回None或0
        assert ratio is None or ratio == 0
    
    def test_audit_opinion_standard(self, governance_calculator):
        """测试标准审计意见"""
        opinion = governance_calculator._get_audit_opinion('000001.SZ', 2023)
        
        assert opinion == '标准无保留意见'
        assert governance_calculator._is_non_standard_audit(opinion) == False
    
    def test_audit_opinion_non_standard(self):
        """测试非标审计意见"""
        mock_loader = Mock()
        non_standard_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'audit_opinion': ['保留意见']
        })
        mock_loader.load_governance.return_value = non_standard_df
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_loader)
        
        opinion = calculator._get_audit_opinion('000001.SZ', 2023)
        
        assert opinion == '保留意见'
        assert calculator._is_non_standard_audit(opinion) == True
    
    def test_is_non_standard_audit_various_types(self, governance_calculator):
        """测试各种非标意见类型识别"""
        non_standard_types = [
            '保留意见',
            '否定意见',
            '无法表示意见',
            '带强调事项段的无保留意见'
        ]
        
        for opinion in non_standard_types:
            assert governance_calculator._is_non_standard_audit(opinion) == True, \
                f"Failed to identify {opinion} as non-standard"
    
    def test_executive_turnover_rate(self, governance_calculator):
        """测试高管流失率计算"""
        rate = governance_calculator._calculate_executive_turnover('000001.SZ', 2023)
        
        # 年初10人，年末9人，流失1人 → 流失率10%
        assert rate == 10.0
        assert 0 <= rate <= 100
    
    def test_executive_turnover_zero(self):
        """测试零流失率"""
        mock_loader = Mock()
        no_turnover_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'executive_count_start': [10],
            'executive_count_end': [10],
            'departed_executives': [0]
        })
        mock_loader.load_governance.return_value = no_turnover_df
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_loader)
        
        rate = calculator._calculate_executive_turnover('000001.SZ', 2023)
        
        assert rate == 0.0
    
    def test_executive_turnover_division_by_zero(self):
        """测试除零处理"""
        mock_loader = Mock()
        zero_start_df = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'report_year': [2023],
            'executive_count_start': [0],  # 年初0人
            'executive_count_end': [0],
            'departed_executives': [0]
        })
        mock_loader.load_governance.return_value = zero_start_df
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_loader)
        
        rate = calculator._calculate_executive_turnover('000001.SZ', 2023)
        
        # 应该返回0而不是抛出异常
        assert rate == 0.0
    
    def test_governance_risk_level_green(self, governance_calculator):
        """测试绿色风险等级（低风险）"""
        risk_level = governance_calculator._assess_governance_risk(
            pledge_ratio=10.0,
            is_non_standard_audit=False,
            executive_turnover=5.0
        )
        
        assert risk_level == 'green'
    
    def test_governance_risk_level_yellow(self, governance_calculator):
        """测试黄色风险等级（中低风险）"""
        risk_level = governance_calculator._assess_governance_risk(
            pledge_ratio=35.0,  # 中等质押
            is_non_standard_audit=False,
            executive_turnover=15.0  # 中等流失
        )
        
        assert risk_level == 'yellow'
    
    def test_governance_risk_level_orange(self, governance_calculator):
        """测试橙色风险等级（中高风险）"""
        risk_level = governance_calculator._assess_governance_risk(
            pledge_ratio=55.0,  # 高质押
            is_non_standard_audit=False,
            executive_turnover=25.0
        )
        
        assert risk_level == 'orange'
    
    def test_governance_risk_level_red(self, governance_calculator):
        """测试红色风险等级（高风险）"""
        risk_level = governance_calculator._assess_governance_risk(
            pledge_ratio=70.0,  # 极高质押
            is_non_standard_audit=True,  # 非标意见
            executive_turnover=40.0  # 高流失
        )
        
        assert risk_level == 'red'
    
    def test_governance_risk_level_red_audit_only(self, governance_calculator):
        """测试仅因审计意见触发红色风险"""
        risk_level = governance_calculator._assess_governance_risk(
            pledge_ratio=10.0,
            is_non_standard_audit=True,  # 非标意见直接红色
            executive_turnover=5.0
        )
        
        assert risk_level == 'red'
    
    def test_calculate_all_complete_result(self, governance_calculator):
        """测试完整计算流程"""
        result = governance_calculator.calculate_all('000001.SZ', 2023)
        
        # 验证返回结构
        assert isinstance(result, dict)
        assert 'pledge_ratio' in result
        assert 'audit_opinion' in result
        assert 'is_non_standard_audit' in result
        assert 'executive_turnover' in result
        assert 'governance_risk_level' in result
    
    def test_calculate_all_risk_level_values(self, governance_calculator):
        """测试风险等级取值范围"""
        result = governance_calculator.calculate_all('000001.SZ', 2023)
        
        valid_levels = ['green', 'yellow', 'orange', 'red']
        assert result['governance_risk_level'] in valid_levels
    
    def test_calculate_all_score_ranges(self, governance_calculator):
        """测试所有数值的合理范围"""
        result = governance_calculator.calculate_all('000001.SZ', 2023)
        
        # 质押比例应该在0-100之间
        if result['pledge_ratio'] is not None:
            assert 0 <= result['pledge_ratio'] <= 100
        
        # 高管流失率应该在0-100之间
        if result['executive_turnover'] is not None:
            assert 0 <= result['executive_turnover'] <= 100
        
        # 审计意见应该是布尔值
        assert isinstance(result['is_non_standard_audit'], bool)
    
    def test_missing_data_handling(self, mock_data_loader):
        """测试缺失数据处理"""
        # Mock返回空数据
        mock_data_loader.load_governance.return_value = pd.DataFrame()
        
        from factors.L3_governance import L3GovernanceFactor
        calculator = L3GovernanceFactor(data_loader=mock_data_loader)
        
        result = calculator.calculate_all('000001.SZ', 2023)
        
        # 应该有合理的默认值
        assert isinstance(result, dict)
        assert 'governance_risk_level' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
