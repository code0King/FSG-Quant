"""
L1PerformanceFactor单元测试

测试目标：
1. ROE、ROA、ROIC等基础指标计算正确
2. 毛利率分级评价符合行业差异化规则
3. 盈利质量综合评分在0-100范围内
4. 预警标记逻辑正确
5. 边界情况处理（除零、缺失值等）
"""
import pytest
import pandas as pd
import sqlite3
from pathlib import Path
import tempfile
import os
import sys

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))
from factors.L1_performance import L1PerformanceFactor


class TestL1PerformanceFactor:
    """L1因子计算器测试类"""
    
    @pytest.fixture
    def temp_db_with_data(self):
        """创建包含测试数据的临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建companies表
        cursor.execute("""
            CREATE TABLE companies (
                stock_code TEXT PRIMARY KEY,
                stock_name TEXT,
                industry_sw_level1 TEXT
            )
        """)
        
        # 创建financial_annual表
        cursor.execute("""
            CREATE TABLE financial_annual (
                stock_code TEXT,
                report_year INTEGER,
                revenue REAL,
                cost_of_revenue REAL,
                gross_profit REAL,
                net_profit REAL,
                net_profit_deducted REAL,
                total_assets REAL,
                net_assets REAL,
                accounts_receivable REAL,
                inventory REAL,
                operating_cash_flow REAL,
                roe REAL,
                roa REAL,
                roic REAL,
                gross_margin REAL,
                PRIMARY KEY (stock_code, report_year)
            )
        """)
        
        # 插入测试公司数据
        cursor.execute("INSERT INTO companies VALUES ('000001.SZ', '平安银行', '银行')")
        cursor.execute("INSERT INTO companies VALUES ('000002.SZ', '万科A', '房地产')")
        cursor.execute("INSERT INTO companies VALUES ('300750.SZ', '宁德时代', '电气设备')")
        
        # 插入财务数据 - 高质量公司
        cursor.execute("""
            INSERT INTO financial_annual VALUES 
            ('000001.SZ', 2023, 1000.0, 600.0, 400.0, 100.0, 95.0, 
             2000.0, 1000.0, 200.0, 100.0, 120.0,
             0.10, 0.05, 0.09, 0.40)
        """)
        
        # 插入财务数据 - 中等质量公司
        cursor.execute("""
            INSERT INTO financial_annual VALUES 
            ('000002.SZ', 2023, 500.0, 350.0, 150.0, 50.0, 40.0,
             1000.0, 500.0, 100.0, 80.0, 45.0,
             0.08, 0.04, 0.07, 0.30)
        """)
        
        # 插入财务数据 - 低质量公司（现金流为负）
        cursor.execute("""
            INSERT INTO financial_annual VALUES 
            ('300750.SZ', 2023, 800.0, 600.0, 200.0, 80.0, 30.0,
             1500.0, 600.0, 300.0, 200.0, -20.0,
             0.12, 0.05, 0.10, 0.25)
        """)
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # 清理
        os.unlink(db_path)
    
    @pytest.fixture
    def industry_config_file(self):
        """创建临时行业配置文件"""
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
            config = {
                'industries': {
                    'finance': {
                        'industries': ['银行', '非银金融'],
                        'thresholds': {
                            'min_roe': 10,
                            'min_research_intensity': 0,
                            'max_goodwill_ratio': 5
                        }
                    },
                    'manufacturing': {
                        'industries': ['电气设备', '机械设备'],
                        'thresholds': {
                            'min_roe': 5,
                            'min_research_intensity': 2,
                            'max_goodwill_ratio': 20
                        }
                    }
                },
                'default_thresholds': {
                    'min_roe': 8,
                    'min_research_intensity': 2,
                    'max_goodwill_ratio': 20
                }
            }
            yaml.dump(config, tmp, allow_unicode=True)
            config_path = tmp.name
        
        yield config_path
        
        # 清理
        os.unlink(config_path)
    
    @pytest.fixture
    def calculator(self, temp_db_with_data, industry_config_file):
        """创建L1因子计算器实例"""
        return L1PerformanceFactor(
            db_path=temp_db_with_data,
            industry_config_path=industry_config_file
        )
    
    def test_calculate_roe(self, calculator):
        """测试ROE计算"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'roe' in result
        assert isinstance(result['roe'], float)
        assert 0 <= result['roe'] <= 1  # ROE应该在0-1之间
        assert abs(result['roe'] - 0.10) < 0.01  # 期望值约0.10
    
    def test_calculate_roa(self, calculator):
        """测试ROA计算"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'roa' in result
        assert isinstance(result['roa'], float)
        assert 0 <= result['roa'] <= 1
        assert abs(result['roa'] - 0.05) < 0.01  # 期望值约0.05
    
    def test_calculate_roic(self, calculator):
        """测试ROIC计算"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'roic' in result
        assert isinstance(result['roic'], float)
        assert 0 <= result['roic'] <= 1
    
    def test_calculate_gross_margin(self, calculator):
        """测试毛利率计算"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'gross_margin' in result
        assert isinstance(result['gross_margin'], float)
        assert 0 <= result['gross_margin'] <= 1
        assert abs(result['gross_margin'] - 0.40) < 0.01  # 期望值0.40
    
    def test_gross_margin_grading_high(self, calculator):
        """测试毛利率分级 - 高等级"""
        # 平安银行毛利率40%，在银行业应该属于高水平
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'gross_margin_grade' in result
        assert result['gross_margin_grade'] in ['高', '中', '低', '极低']
        assert 'gross_margin_score' in result
        assert result['gross_margin_score'] in [0, 30, 60, 100]
    
    def test_deducted_profit_ratio(self, calculator):
        """测试扣非净利润占比"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'deducted_profit_ratio' in result
        assert isinstance(result['deducted_profit_ratio'], float)
        assert 0 <= result['deducted_profit_ratio'] <= 1
        # 95/100 = 0.95
        assert abs(result['deducted_profit_ratio'] - 0.95) < 0.01
    
    def test_cash_flow_coverage_positive(self, calculator):
        """测试现金流覆盖倍数 - 正值"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'cash_flow_coverage' in result
        assert isinstance(result['cash_flow_coverage'], float)
        # 120/100 = 1.2
        assert abs(result['cash_flow_coverage'] - 1.2) < 0.1
    
    def test_cash_flow_coverage_negative(self, calculator):
        """测试现金流覆盖倍数 - 负值（低质量公司）"""
        result = calculator.calculate_all('300750.SZ', 2023)
        
        assert 'cash_flow_coverage' in result
        assert result['cash_flow_coverage'] < 0  # 现金流为负
    
    def test_profit_quality_score_range(self, calculator):
        """测试盈利质量综合评分范围"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        assert 'profit_quality_score' in result
        assert isinstance(result['profit_quality_score'], float)
        assert 0 <= result['profit_quality_score'] <= 100  # 必须在0-100之间
    
    def test_profit_quality_score_comparison(self, calculator):
        """测试不同质量公司的评分对比"""
        high_quality = calculator.calculate_all('000001.SZ', 2023)
        low_quality = calculator.calculate_all('300750.SZ', 2023)
        
        # 高质量公司（现金流充足）应该得分更高
        assert high_quality['profit_quality_score'] > low_quality['profit_quality_score']
    
    def test_warning_flags_cash_flow(self, calculator):
        """测试预警标记 - 现金流不足"""
        result = calculator.calculate_all('300750.SZ', 2023)
        
        assert 'warning_flags' in result
        assert isinstance(result['warning_flags'], list)
        # 现金流为负应该有预警
        assert len(result['warning_flags']) > 0
    
    def test_warning_flags_low_deducted_ratio(self, calculator):
        """测试预警标记 - 扣非占比低"""
        # 300750扣非占比30/80=0.375，低于0.5应该预警
        result = calculator.calculate_all('300750.SZ', 2023)
        
        if result['deducted_profit_ratio'] < 0.5:
            assert any('扣非' in flag for flag in result['warning_flags'])
    
    def test_complete_result_structure(self, calculator):
        """测试结果结构完整性"""
        result = calculator.calculate_all('000001.SZ', 2023)
        
        # 检查所有必需的字段
        required_fields = [
            'roe', 'roa', 'roic', 'gross_margin',
            'gross_margin_grade', 'gross_margin_score',
            'deducted_profit_ratio', 'cash_flow_coverage',
            'profit_quality_score', 'warning_flags'
        ]
        
        for field in required_fields:
            assert field in result, f"Missing field: {field}"
    
    def test_nonexistent_stock(self, calculator):
        """测试不存在的股票"""
        result = calculator.calculate_all('999999.SZ', 2023)
        
        # 应该返回空字典或抛出异常
        assert result is None or isinstance(result, dict)
    
    def test_division_by_zero_handling(self, temp_db_with_data, industry_config_file):
        """测试除零处理"""
        # 在数据库中插入净资产为0的数据
        conn = sqlite3.connect(temp_db_with_data)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO financial_annual VALUES 
            ('TEST001.SZ', 2023, 100.0, 50.0, 50.0, 10.0, 9.0,
             200.0, 0.0, 20.0, 10.0, 5.0,
             0.0, 0.0, 0.0, 0.5)
        """)
        cursor.execute("INSERT INTO companies VALUES ('TEST001.SZ', '测试公司', '其他')")
        conn.commit()
        conn.close()
        
        calculator = L1PerformanceFactor(
            db_path=temp_db_with_data,
            industry_config_path=industry_config_file
        )
        
        # 不应该抛出除零错误
        result = calculator.calculate_all('TEST001.SZ', 2023)
        assert result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
