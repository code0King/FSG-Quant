"""
CSV数据加载器

从本地CSV/Excel文件加载财务、治理和行情数据。

使用场景：
- 手工整理的Excel数据
- 从其他系统导出的CSV文件
- 快速原型验证

使用示例：
    >>> loader = CSVDataLoader(financial_dir='data/local/financial')
    >>> df = loader.load_financial(stock_code='000001.SZ', year=2023)
"""
import pandas as pd
from pathlib import Path
import logging
from typing import Optional, List
import glob

logger = logging.getLogger(__name__)


class CSVDataLoader:
    """
    CSV数据加载器
    
    从本地CSV/Excel文件加载各类数据。
    
    Attributes:
        financial_dir: 财务数据目录
        governance_dir: 治理数据目录
        market_dir: 行情数据目录
        factors_dir: 因子数据目录
        encoding: 文件编码
    """
    
    def __init__(self, 
                 financial_dir: str,
                 governance_dir: str,
                 market_dir: str,
                 factors_dir: str,
                 encoding: str = 'utf-8'):
        """
        初始化CSV加载器
        
        Args:
            financial_dir: 财务数据目录
            governance_dir: 治理数据目录
            market_dir: 行情数据目录
            factors_dir: 因子数据目录
            encoding: 文件编码
        """
        self.financial_dir = Path(financial_dir)
        self.governance_dir = Path(governance_dir)
        self.market_dir = Path(market_dir)
        self.factors_dir = Path(factors_dir)
        self.encoding = encoding
        
        # 确保目录存在
        for dir_path in [self.financial_dir, self.governance_dir, 
                        self.market_dir, self.factors_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"CSVDataLoader initialized")
        logger.info(f"  Financial dir: {self.financial_dir}")
        logger.info(f"  Governance dir: {self.governance_dir}")
        logger.info(f"  Market dir: {self.market_dir}")
        logger.info(f"  Factors dir: {self.factors_dir}")
    
    def load_financial(self, stock_code: Optional[str] = None,
                      year: Optional[int] = None) -> pd.DataFrame:
        """
        从CSV加载财务数据
        
        文件格式要求：
        - 文件名格式：{stock_code}_{year}.csv 或 financial_data.csv
        - 必需列：stock_code, report_year, revenue, net_profit等
        
        Args:
            stock_code: 股票代码
            year: 报告年度
            
        Returns:
            DataFrame包含财务数据
        """
        try:
            # 策略1: 查找特定股票的文件
            if stock_code and year:
                file_path = self.financial_dir / f"{stock_code}_{year}.csv"
                if file_path.exists():
                    return self._load_single_csv(file_path, stock_code, year)
            
            # 策略2: 查找合并的财务数据文件
            merged_file = self.financial_dir / "financial_data.csv"
            if merged_file.exists():
                df = self._load_merged_financial(merged_file, stock_code, year)
                if not df.empty:
                    return df
            
            # 策略3: 查找所有CSV文件并合并
            df = self._load_all_financial_csv(stock_code, year)
            if not df.empty:
                return df
            
            logger.warning(f"No financial data found for stock={stock_code}, year={year}")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to load financial data: {e}")
            return pd.DataFrame()
    
    def _load_single_csv(self, file_path: Path, 
                        stock_code: str, year: int) -> pd.DataFrame:
        """加载单个CSV文件"""
        try:
            df = pd.read_csv(file_path, encoding=self.encoding)
            
            # 添加缺失的列
            if 'stock_code' not in df.columns:
                df['stock_code'] = stock_code
            if 'report_year' not in df.columns:
                df['report_year'] = year
            
            logger.info(f"Loaded financial data from {file_path.name}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return pd.DataFrame()
    
    def _load_merged_financial(self, file_path: Path,
                              stock_code: Optional[str],
                              year: Optional[int]) -> pd.DataFrame:
        """加载合并的财务数据文件并过滤"""
        try:
            df = pd.read_csv(file_path, encoding=self.encoding)
            
            # 过滤
            if stock_code:
                df = df[df['stock_code'] == stock_code]
            if year:
                df = df[df['report_year'] == year]
            
            logger.info(f"Loaded {len(df)} records from merged financial file")
            return df
            
        except Exception as e:
            logger.error(f"Failed to load merged financial file: {e}")
            return pd.DataFrame()
    
    def _load_all_financial_csv(self, stock_code: Optional[str],
                               year: Optional[int]) -> pd.DataFrame:
        """加载所有财务CSV文件并合并"""
        csv_files = list(self.financial_dir.glob("*.csv"))
        
        if not csv_files:
            return pd.DataFrame()
        
        all_dfs = []
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, encoding=self.encoding)
                
                # 尝试从文件名提取信息
                if 'stock_code' not in df.columns or 'report_year' not in df.columns:
                    # 从文件名解析
                    parts = csv_file.stem.split('_')
                    if len(parts) >= 2:
                        if 'stock_code' not in df.columns:
                            df['stock_code'] = parts[0]
                        if 'report_year' not in df.columns:
                            df['report_year'] = int(parts[1])
                
                all_dfs.append(df)
                
            except Exception as e:
                logger.warning(f"Failed to load {csv_file}: {e}")
        
        if not all_dfs:
            return pd.DataFrame()
        
        # 合并所有DataFrame
        merged_df = pd.concat(all_dfs, ignore_index=True)
        
        # 过滤
        if stock_code:
            merged_df = merged_df[merged_df['stock_code'] == stock_code]
        if year:
            merged_df = merged_df[merged_df['report_year'] == year]
        
        logger.info(f"Loaded {len(merged_df)} records from {len(csv_files)} CSV files")
        return merged_df
    
    def load_governance(self, data_type: str = 'pledge',
                       stock_code: Optional[str] = None,
                       year: Optional[int] = None) -> pd.DataFrame:
        """
        从CSV加载治理数据
        
        Args:
            data_type: 数据类型（暂不支持，返回全部）
            stock_code: 股票代码
            year: 报告年度
            
        Returns:
            DataFrame包含治理数据
        """
        try:
            # 查找治理数据文件
            merged_file = self.governance_dir / "governance_data.csv"
            
            if merged_file.exists():
                df = pd.read_csv(merged_file, encoding=self.encoding)
                
                # 过滤
                if stock_code:
                    df = df[df['stock_code'] == stock_code]
                if year:
                    df = df[df['report_year'] == year]
                
                logger.info(f"Loaded {len(df)} governance records")
                return df
            
            logger.warning("No governance data file found")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Failed to load governance data: {e}")
            return pd.DataFrame()
    
    def load_factors(self, factor_type: str = 'L1',
                    year: Optional[int] = None) -> pd.DataFrame:
        """
        从Parquet加载因子数据（保持与DataLoader一致）
        
        Args:
            factor_type: 因子类型
            year: 报告年度
            
        Returns:
            DataFrame包含因子数据
        """
        filename_map = {
            'L1': 'L1_factors.parquet',
            'L2': 'L2_factors.parquet',
            'L3': 'L3_factors.parquet',
            'orthogonal': 'orthogonal_factors.parquet',
            'composite': 'composite_scores.parquet'
        }
        
        if factor_type not in filename_map:
            raise ValueError(f"Invalid factor_type: {factor_type}")
        
        file_path = self.factors_dir / filename_map[factor_type]
        
        if not file_path.exists():
            logger.warning(f"Factor file not found: {file_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_parquet(file_path)
            
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
        从CSV加载行情数据
        
        Args:
            year: 年份
            stock_code: 股票代码
            
        Returns:
            DataFrame包含行情数据
        """
        try:
            file_path = self.market_dir / f"{year}.csv"
            
            if not file_path.exists():
                logger.warning(f"Market data file not found: {file_path}")
                return pd.DataFrame()
            
            df = pd.read_csv(file_path, encoding=self.encoding)
            
            if stock_code and 'stock_code' in df.columns:
                df = df[df['stock_code'] == stock_code]
            
            logger.info(f"Loaded {len(df)} market data records for year {year}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            return pd.DataFrame()
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        从财务数据中提取股票列表
        
        Returns:
            DataFrame包含stock_code等信息
        """
        # 从财务数据中提取唯一的股票代码
        df = self.load_financial()
        
        if df.empty:
            return pd.DataFrame()
        
        if 'stock_code' in df.columns:
            stocks = df[['stock_code']].drop_duplicates()
            logger.info(f"Found {len(stocks)} unique stocks")
            return stocks
        
        return pd.DataFrame()
