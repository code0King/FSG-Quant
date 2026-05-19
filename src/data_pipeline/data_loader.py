"""
数据加载工具模块

提供统一的数据加载接口，支持从SQLite和Parquet文件读取数据。

主要功能：
1. 从SQLite加载财务数据和治理数据
2. 从Parquet文件加载因子数据和综合评分
3. 从Parquet文件加载行情数据
4. 支持按股票代码、年份等条件过滤
5. 支持多数据源切换（通过DataSourceManager）

使用示例：
    >>> # 方式1: 直接使用DataLoader（SQLite）
    >>> loader = DataLoader()
    >>> df = loader.load_financial(stock_code='000001.SZ', year=2023)
    >>> 
    >>> # 方式2: 使用DataSourceManager（多数据源）
    >>> from data_pipeline.data_source_manager import DataSourceManager
    >>> manager = DataSourceManager()
    >>> df = manager.load_financial(stock_code='000001.SZ', year=2023)
"""
import pandas as pd
import sqlite3
from pathlib import Path
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DataLoader:
    """
    数据加载器
    
    封装SQLite和Parquet数据源的访问逻辑，提供简洁的API。
    
    Attributes:
        data_dir: 数据根目录路径
        db_path: SQLite数据库完整路径
    """
    
    def __init__(self, data_dir: str = 'data', db_filename: str = 'financial_data.sqlite'):
        """
        初始化DataLoader
        
        Args:
            data_dir: 数据目录路径（相对于项目根目录）或数据库文件完整路径
            db_filename: SQLite数据库文件名（仅当data_dir是目录时使用）
        """
        data_path = Path(data_dir)
        
        # 如果传入的是文件路径（以.sqlite结尾），直接使用
        if data_path.suffix == '.sqlite':
            self.db_path = data_path
            self.data_dir = data_path.parent
        else:
            # 否则假设是目录，按默认结构查找
            self.data_dir = data_path
            self.db_path = self.data_dir / 'raw' / db_filename
        
        # 验证数据库文件存在
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
    
    def load_financial(self, stock_code: Optional[str] = None, 
                      year: Optional[int] = None) -> pd.DataFrame:
        """
        从SQLite加载财务数据
        
        Args:
            stock_code: 股票代码（如'000001.SZ'），None表示加载全部
            year: 报告年度（如2023），None表示加载全部年份
            
        Returns:
            DataFrame包含财务数据，列包括：stock_code, report_year, revenue, 
            net_profit, roe等
            
        Example:
            >>> loader = DataLoader()
            >>> # 加载某股票某年的数据
            >>> df = loader.load_financial('000001.SZ', 2023)
            >>> # 加载全部数据
            >>> all_data = loader.load_financial()
        """
        if not self.db_path.exists():
            logger.error(f"Database file not found: {self.db_path}")
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 构建查询语句
            query = "SELECT * FROM financial_annual WHERE 1=1"
            params = []
            
            if stock_code:
                query += " AND stock_code = ?"
                params.append(stock_code)
            
            if year:
                query += " AND report_year = ?"
                params.append(year)
            
            # 执行查询
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            logger.info(f"Loaded {len(df)} financial records")
            return df
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return pd.DataFrame()
    
    def load_factors(self, factor_type: str = 'L1', 
                    year: Optional[int] = None) -> pd.DataFrame:
        """
        从Parquet文件加载因子数据
        
        Args:
            factor_type: 因子类型，可选值：'L1', 'L2', 'L3', 'orthogonal', 'composite'
            year: 报告年度，None表示加载全部年份
            
        Returns:
            DataFrame包含因子数据
            
        Example:
            >>> loader = DataLoader()
            >>> l1_factors = loader.load_factors('L1', year=2023)
            >>> composite = loader.load_factors('composite')
        """
        # 映射因子类型到文件名
        filename_map = {
            'L1': 'L1_factors.parquet',
            'L2': 'L2_factors.parquet',
            'L3': 'L3_factors.parquet',
            'orthogonal': 'orthogonal_factors.parquet',
            'composite': 'composite_scores.parquet'
        }
        
        if factor_type not in filename_map:
            raise ValueError(f"Invalid factor_type: {factor_type}. Must be one of {list(filename_map.keys())}")
        
        file_path = self.data_dir / 'factors' / filename_map[factor_type]
        
        if not file_path.exists():
            logger.warning(f"Factor file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(file_path)
            
            # 按年份过滤
            if year is not None and 'report_year' in df.columns:
                df = df[df['report_year'] == year]
            
            logger.info(f"Loaded {len(df)} {factor_type} factor records")
            return df
            
        except Exception as e:
            logger.error(f"Error loading factors: {e}")
            return pd.DataFrame()
    
    def load_market_data(self, year: int, 
                        stock_code: Optional[str] = None) -> pd.DataFrame:
        """
        从Parquet文件加载行情数据
        
        Args:
            year: 年份（如2023）
            stock_code: 股票代码，None表示加载全部股票
            
        Returns:
            DataFrame包含行情数据，列包括：trade_date, open, high, low, 
            close, volume等
            
        Example:
            >>> loader = DataLoader()
            >>> quotes = loader.load_market_data(2023, '000001.SZ')
        """
        file_path = self.data_dir / 'market_data' / 'daily_quotes' / f'{year}.parquet'
        
        if not file_path.exists():
            logger.warning(f"Market data file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(file_path)
            
            # 按股票代码过滤
            if stock_code and 'stock_code' in df.columns:
                df = df[df['stock_code'] == stock_code]
            
            logger.info(f"Loaded {len(df)} market data records for year {year}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            return pd.DataFrame()
    
    def load_governance(self, data_type: str = 'pledge', 
                       stock_code: Optional[str] = None,
                       year: Optional[int] = None) -> pd.DataFrame:
        """
        从SQLite加载治理数据
        
        Args:
            data_type: 数据类型，可选值：'pledge'(股权质押), 'audit'(审计意见), 
                      'executive'(高管信息), 'all'(全部)
            stock_code: 股票代码（如'000001.SZ'），None表示加载全部
            year: 报告年度（如2023），None表示加载全部年份
            
        Returns:
            DataFrame包含治理数据
            - pledge类型：stock_code, report_year, pledged_shares_ratio
            - audit类型：stock_code, report_year, audit_opinion
            - executive类型：stock_code, report_year, executive_count_start, departed_executives
            
        Example:
            >>> loader = DataLoader()
            >>> # 加载某股票的质押数据
            >>> pledge_data = loader.load_governance('pledge', '000001.SZ', 2023)
            >>> # 加载某股票的审计意见
            >>> audit_data = loader.load_governance('audit', '000001.SZ', 2023)
        """
        if not self.db_path.exists():
            logger.error(f"Database file not found: {self.db_path}")
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # 构建查询语句
            query = "SELECT * FROM governance_data WHERE 1=1"
            params = []
            
            if stock_code:
                query += " AND stock_code = ?"
                params.append(stock_code)
            
            if year:
                query += " AND report_year = ?"
                params.append(year)
            
            # 执行查询
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            if df.empty:
                logger.debug(f"No governance data found for stock={stock_code}, year={year}")
                return pd.DataFrame()
            
            # 根据data_type过滤列
            if data_type == 'pledge':
                # 股权质押相关字段
                cols = ['stock_code', 'report_year', 'major_shareholder_pledge_ratio']
                available_cols = [col for col in cols if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                    # 重命名为期望的字段名
                    if 'major_shareholder_pledge_ratio' in df.columns:
                        df = df.rename(columns={'major_shareholder_pledge_ratio': 'pledged_shares_ratio'})
            elif data_type == 'audit':
                # 审计意见相关字段
                cols = ['stock_code', 'report_year', 'audit_opinion', 'is_standard_audit']
                available_cols = [col for col in cols if col in df.columns]
                if available_cols:
                    df = df[available_cols]
            elif data_type == 'executive':
                # 高管流失相关字段
                cols = ['stock_code', 'report_year', 'core_personnel_turnover_rate']
                available_cols = [col for col in cols if col in df.columns]
                if available_cols:
                    df = df[available_cols]
                    # 添加计算所需的字段（如果不存在则设为默认值）
                    if 'executive_count_start' not in df.columns:
                        df['executive_count_start'] = 10  # 默认年初10人
                    if 'departed_executives' not in df.columns:
                        # 根据流失率计算离职人数
                        df['departed_executives'] = (df['executive_count_start'] * 
                                                    df['core_personnel_turnover_rate'] / 100).round()
            # else: data_type == 'all'，返回所有列
            
            logger.info(f"Loaded {len(df)} governance records (type={data_type})")
            return df
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return pd.DataFrame()
    
    def load_composite_scores(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        从Parquet文件加载综合评分数据
        
        Args:
            year: 报告年度，None表示加载全部年份
            
        Returns:
            DataFrame包含综合评分数据，列包括：stock_code, report_year, 
            offensive_score, defensive_score, composite_risk_level等
            
        Example:
            >>> loader = DataLoader()
            >>> scores = loader.load_composite_scores(2023)
            >>> print(scores.head())
        """
        return self.load_factors(factor_type='composite', year=year)
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取所有股票列表
        
        Returns:
            DataFrame包含stock_code, stock_name, industry等信息
        """
        if not self.db_path.exists():
            return pd.DataFrame()
        
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT stock_code, stock_name, industry_sw_level1 FROM companies"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            return df
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            return pd.DataFrame()
