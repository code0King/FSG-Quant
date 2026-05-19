"""
CommitmentParser单元测试

测试目标：
1. 正确抽取营收增长承诺
2. 正确抽取利润增长承诺
3. 正确抽取CAPEX承诺
4. 处理无承诺的情况
5. 处理模糊表述（无数值）
6. 处理多个承诺
"""
import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
from nlp.commitment_parser import CommitmentParser


class TestCommitmentParser:
    """承诺抽取器测试类"""
    
    @pytest.fixture
    def parser(self):
        """创建CommitmentParser实例"""
        return CommitmentParser()
    
    def test_extract_revenue_growth_commitment(self, parser):
        """测试抽取营收增长承诺"""
        text = "公司预计2024年营收增长不低于20%，力争实现高质量发展。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert result['revenue_growth_target'] == 20.0
        assert result['profit_growth_target'] is None
    
    def test_extract_profit_growth_commitment(self, parser):
        """测试抽取利润增长承诺"""
        text = "预计净利润增长15%以上，保持稳健经营。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert result['profit_growth_target'] == 15.0
        assert result['revenue_growth_target'] is None
    
    def test_extract_capex_commitment(self, parser):
        """测试抽取CAPEX承诺"""
        text = "计划资本支出50亿元，用于产能扩张和技术改造。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert result['capex_target'] == 5000000000.0  # 50亿 = 50 * 1e8
    
    def test_extract_multiple_commitments(self, parser):
        """测试抽取多个承诺"""
        text = "预计营收增长20%，净利润增长15%，资本支出30亿元。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert result['revenue_growth_target'] == 20.0
        assert result['profit_growth_target'] == 15.0
        assert result['capex_target'] == 3000000000.0
    
    def test_no_explicit_commitment(self, parser):
        """测试无明确承诺的情况"""
        text = "公司将努力提升业绩，争取实现良好发展。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == False
        assert result['revenue_growth_target'] is None
        assert result['profit_growth_target'] is None
        assert result['capex_target'] is None
    
    def test_vague_commitment(self, parser):
        """测试模糊承诺（无数值）"""
        text = "力争实现稳健增长，保持行业领先地位。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == False
    
    def test_decimal_growth_rate(self, parser):
        """测试小数增长率"""
        text = "预计营业收入增长12.5%。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert abs(result['revenue_growth_target'] - 12.5) < 0.01
    
    def test_alternative_revenue_terms(self, parser):
        """测试不同的营收表述"""
        texts = [
            "营业收入增长18%",
            "收入增长25%",
            "营收同比增长30%",
        ]
        
        for text in texts:
            result = parser.extract_commitments(text)
            assert result['has_explicit'] == True
            assert result['revenue_growth_target'] is not None
    
    def test_investment_commitment(self, parser):
        """测试投资承诺"""
        text = "计划投资80亿元建设新工厂。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == True
        assert result['capex_target'] == 8000000000.0
    
    def test_empty_text(self, parser):
        """测试空文本"""
        text = ""
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == False
        assert result['revenue_growth_target'] is None
    
    def test_no_numbers(self, parser):
        """测试无数值的文本"""
        text = "公司将加大研发投入，拓展市场份额。"
        
        result = parser.extract_commitments(text)
        
        assert result['has_explicit'] == False
    
    def test_complex_mda_text(self, parser):
        """测试复杂的MD&A文本"""
        text = """
        展望未来，公司将继续坚持创新驱动发展战略。
        预计2024年营业收入增长20%-25%，净利润增长15%左右。
        计划资本支出约40亿元，主要用于智能制造升级和研发中心建设。
        公司将积极应对市场挑战，努力实现可持续发展目标。
        """
        
        result = parser.extract_commitments(text)
        
        # 应该能抽取到第一个匹配的承诺
        assert result['has_explicit'] == True
        # 注意：正则可能只匹配第一个数值
        assert result['revenue_growth_target'] is not None or \
               result['profit_growth_target'] is not None
    
    def test_result_structure(self, parser):
        """测试结果结构完整性"""
        text = "预计营收增长10%"
        
        result = parser.extract_commitments(text)
        
        # 检查所有必需的字段
        required_fields = [
            'revenue_growth_target',
            'profit_growth_target',
            'capex_target',
            'has_explicit'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
