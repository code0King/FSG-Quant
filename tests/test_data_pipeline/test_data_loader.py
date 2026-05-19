"""
DataLoader单元测试

测试目标：
1. 正确加载SQLite中的财务数据
2. 正确加载Parquet格式的因子数据
3. 支持按股票代码和年份过滤
4. 处理数据缺失的异常情况
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
from data_pipeline.data_loader import DataLoader


class TestDataLoader:
    """DataLoader测试类"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时SQLite数据库用于测试"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        # 创建测试表和数据
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
                net_profit REAL,
                roe REAL,
                PRIMARY KEY (stock_code, report_year)
            )
        """)
        
        # 插入测试数据
        cursor.execute("INSERT INTO companies VALUES ('000001.SZ', '平安银行', '银行')")
        cursor.execute("INSERT INTO companies VALUES ('000002.SZ', '万科A', '房地产')")
        
        cursor.execute("INSERT INTO financial_annual VALUES ('000001.SZ', 2023, 1000.0, 100.0, 0.10)")
        cursor.execute("INSERT INTO financial_annual VALUES ('000001.SZ', 2022, 900.0, 90.0, 0.09)")
        cursor.execute("INSERT INTO financial_annual VALUES ('000002.SZ', 2023, 500.0, 50.0, 0.08)")
        
        conn.commit()
        conn.close()
        
        yield db_path
        
        # 清理临时文件
        os.unlink(db_path)
    
    @pytest.fixture
    def temp_parquet(self):
        """创建临时Parquet文件用于测试"""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp:
            parquet_path = tmp.name
        
        # 创建测试DataFrame并保存
        df = pd.DataFrame({
            'stock_code': ['000001.SZ', '000002.SZ'],
            'report_year': [2023, 2023],
            'roe': [0.10, 0.08],
            'profit_quality_score': [85.5, 72.3]
        })
        df.to_parquet(parquet_path, index=False)
        
        yield parquet_path
        
        # 清理临时文件
        os.unlink(parquet_path)
    
    def test_init_with_custom_data_dir(self, temp_db):
        """测试初始化时指定数据库文件路径"""
        # 直接传入数据库文件路径
        loader = DataLoader(data_dir=temp_db)
        
        assert loader.db_path == Path(temp_db)
    
    def test_load_financial_all_data(self, temp_db):
        """测试加载全部财务数据"""
        loader = DataLoader(data_dir=temp_db)
        
        df = loader.load_financial()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3  # 3条测试数据
        assert 'stock_code' in df.columns
        assert 'report_year' in df.columns
        assert 'roe' in df.columns
    
    def test_load_financial_filter_by_stock(self, temp_db):
        """测试按股票代码过滤"""
        loader = DataLoader(data_dir=temp_db)
        
        df = loader.load_financial(stock_code='000001.SZ')
        
        assert len(df) == 2  # 000001.SZ有2年数据
        assert all(df['stock_code'] == '000001.SZ')
    
    def test_load_financial_filter_by_year(self, temp_db):
        """测试按年份过滤"""
        loader = DataLoader(data_dir=temp_db)
        
        df = loader.load_financial(year=2023)
        
        assert len(df) == 2  # 2023年有2只股票
        assert all(df['report_year'] == 2023)
    
    def test_load_financial_filter_by_both(self, temp_db):
        """测试同时按股票和年份过滤"""
        loader = DataLoader(data_dir=temp_db)
        
        df = loader.load_financial(stock_code='000001.SZ', year=2023)
        
        assert len(df) == 1
        assert df.iloc[0]['stock_code'] == '000001.SZ'
        assert df.iloc[0]['report_year'] == 2023
        assert df.iloc[0]['roe'] == 0.10
    
    def test_load_financial_no_data(self, temp_db):
        """测试查询不存在的数据"""
        loader = DataLoader(data_dir=temp_db)
        
        df = loader.load_financial(stock_code='999999.SZ')
        
        assert len(df) == 0
    
    def test_load_factors(self, temp_parquet):
        """测试加载因子数据"""
        data_dir = Path(temp_parquet).parent
        
        # 创建factors子目录
        factors_dir = data_dir / 'factors'
        factors_dir.mkdir(exist_ok=True)
        
        loader = DataLoader(data_dir=str(data_dir))
        
        # 复制文件到factors目录
        import shutil
        expected_path = factors_dir / 'L1_factors.parquet'
        shutil.copy(temp_parquet, expected_path)
        
        df = loader.load_factors(factor_type='L1')
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'profit_quality_score' in df.columns
        
        # 清理
        expected_path.unlink()
        factors_dir.rmdir()
    
    def test_load_factors_with_year_filter(self, temp_parquet):
        """测试加载因子数据并按年份过滤"""
        data_dir = Path(temp_parquet).parent
        
        # 创建factors子目录
        factors_dir = data_dir / 'factors'
        factors_dir.mkdir(exist_ok=True)
        
        loader = DataLoader(data_dir=str(data_dir))
        
        import shutil
        expected_path = factors_dir / 'L1_factors.parquet'
        shutil.copy(temp_parquet, expected_path)
        
        df = loader.load_factors(factor_type='L1', year=2023)
        
        assert len(df) == 2
        assert all(df['report_year'] == 2023)
        
        # 清理
        expected_path.unlink()
        factors_dir.rmdir()
    
    def test_load_market_data(self, temp_parquet):
        """测试加载行情数据"""
        data_dir = Path(temp_parquet).parent
        loader = DataLoader(data_dir=str(data_dir))
        
        # 创建行情数据目录结构
        market_dir = data_dir / 'market_data' / 'daily_quotes'
        market_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        market_file = market_dir / '2023.parquet'
        shutil.copy(temp_parquet, market_file)
        
        df = loader.load_market_data(year=2023)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        
        # 清理
        market_file.unlink()
        market_dir.rmdir()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
