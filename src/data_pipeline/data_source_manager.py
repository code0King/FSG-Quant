"""
数据源管理器

统一管理不同数据源的加载逻辑，支持：
- SQLite数据库
- 本地CSV/Excel文件
- 本地PDF年报（待实现）
- API接口（Tushare/Akshare，待实现）

使用示例：
    >>> from data_pipeline.data_source_manager import DataSourceManager
    >>> manager = DataSourceManager()
    >>> df = manager.load_financial(stock_code='000001.SZ', year=2023)
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    数据源管理器
    
    根据配置文件自动选择合适的数据源进行数据加载。
    
    Attributes:
        config: 数据源配置字典
        source_type: 当前使用的数据源类型
        project_root: 项目根目录路径
    """
    
    def __init__(self, config_path: str = 'config/data_source.yaml'):
        """
        初始化数据源管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.config = self._load_config(config_path)
        self.source_type = self.config['data_source']['type']
        
        logger.info(f"DataSourceManager initialized with source type: {self.source_type}")
        
        # 初始化对应的数据加载器
        self._init_loader()
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        config_file = self.project_root / config_path
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            return self._default_config()
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"Data source config loaded from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """返回默认配置"""
        return {
            'data_source': {
                'type': 'sqlite',
                'sqlite': {
                    'db_path': 'data/raw/financial_data.sqlite'
                }
            }
        }
    
    def _init_loader(self):
        """根据配置初始化对应的数据加载器"""
        if self.source_type == 'sqlite':
            self.loader = self._init_sqlite_loader()
        elif self.source_type == 'local_csv':
            self.loader = self._init_csv_loader()
        elif self.source_type == 'local_pdf':
            self.loader = self._init_pdf_loader()
        elif self.source_type == 'api':
            self.loader = self._init_api_loader()
        else:
            raise ValueError(f"Unsupported data source type: {self.source_type}")
    
    def _init_sqlite_loader(self):
        """初始化SQLite加载器"""
        from data_pipeline.data_loader import DataLoader
        
        db_config = self.config['data_source']['sqlite']
        db_path = self.project_root / db_config['db_path']
        
        logger.info(f"Using SQLite database: {db_path}")
        return DataLoader(data_dir=str(db_path))
    
    def _init_csv_loader(self):
        """初始化CSV加载器"""
        from data_pipeline.csv_loader import CSVDataLoader
        
        csv_config = self.config['data_source']['local_csv']
        
        logger.info("Using local CSV data source")
        return CSVDataLoader(
            financial_dir=self.project_root / csv_config['financial_dir'],
            governance_dir=self.project_root / csv_config['governance_dir'],
            market_dir=self.project_root / csv_config['market_dir'],
            factors_dir=self.project_root / csv_config['factors_dir'],
            encoding=csv_config.get('encoding', 'utf-8')
        )
    
    def _init_pdf_loader(self):
        """初始化PDF加载器"""
        # TODO: 实现PDF加载器
        logger.warning("PDF loader not yet implemented, falling back to SQLite")
        return self._init_sqlite_loader()
    
    def _init_api_loader(self):
        """初始化API加载器"""
        # TODO: 实现API加载器
        logger.warning("API loader not yet implemented, falling back to SQLite")
        return self._init_sqlite_loader()
    
    # ==================== 数据加载接口 ====================
    
    def load_financial(self, stock_code: Optional[str] = None, 
                      year: Optional[int] = None) -> pd.DataFrame:
        """
        加载财务数据
        
        Args:
            stock_code: 股票代码
            year: 报告年度
            
        Returns:
            DataFrame包含财务数据
        """
        logger.debug(f"Loading financial data: stock={stock_code}, year={year}")
        return self.loader.load_financial(stock_code=stock_code, year=year)
    
    def load_governance(self, data_type: str = 'pledge',
                       stock_code: Optional[str] = None,
                       year: Optional[int] = None) -> pd.DataFrame:
        """
        加载治理数据
        
        Args:
            data_type: 数据类型（'pledge', 'audit', 'executive', 'all'）
            stock_code: 股票代码
            year: 报告年度
            
        Returns:
            DataFrame包含治理数据
        """
        logger.debug(f"Loading governance data: type={data_type}, stock={stock_code}, year={year}")
        
        # 检查loader是否支持该方法
        if hasattr(self.loader, 'load_governance'):
            return self.loader.load_governance(
                data_type=data_type,
                stock_code=stock_code,
                year=year
            )
        else:
            logger.warning(f"Loader does not support load_governance, returning empty DataFrame")
            return pd.DataFrame()
    
    def load_factors(self, factor_type: str = 'L1',
                    year: Optional[int] = None) -> pd.DataFrame:
        """
        加载因子数据
        
        Args:
            factor_type: 因子类型
            year: 报告年度
            
        Returns:
            DataFrame包含因子数据
        """
        logger.debug(f"Loading factors: type={factor_type}, year={year}")
        return self.loader.load_factors(factor_type=factor_type, year=year)
    
    def load_composite_scores(self, year: Optional[int] = None) -> pd.DataFrame:
        """
        加载综合评分数据
        
        Args:
            year: 报告年度
            
        Returns:
            DataFrame包含综合评分数据
        """
        logger.debug(f"Loading composite scores: year={year}")
        
        if hasattr(self.loader, 'load_composite_scores'):
            return self.loader.load_composite_scores(year=year)
        else:
            # 回退到load_factors
            return self.loader.load_factors(factor_type='composite', year=year)
    
    def load_market_data(self, year: int,
                        stock_code: Optional[str] = None) -> pd.DataFrame:
        """
        加载行情数据
        
        Args:
            year: 年份
            stock_code: 股票代码
            
        Returns:
            DataFrame包含行情数据
        """
        logger.debug(f"Loading market data: year={year}, stock={stock_code}")
        return self.loader.load_market_data(year=year, stock_code=stock_code)
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取股票列表
        
        Returns:
            DataFrame包含股票基本信息
        """
        logger.debug("Loading stock list")
        
        if hasattr(self.loader, 'get_stock_list'):
            return self.loader.get_stock_list()
        else:
            logger.warning("Loader does not support get_stock_list, returning empty DataFrame")
            return pd.DataFrame()
    
    # ==================== 工具方法 ====================
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        获取当前数据源信息
        
        Returns:
            数据源信息字典
        """
        return {
            'source_type': self.source_type,
            'config': self.config['data_source'].get(self.source_type, {}),
            'loader_type': type(self.loader).__name__
        }
    
    def switch_source(self, new_type: str):
        """
        切换数据源类型
        
        Args:
            new_type: 新的数据源类型
        """
        if new_type not in ['sqlite', 'local_csv', 'local_pdf', 'api']:
            raise ValueError(f"Invalid source type: {new_type}")
        
        logger.info(f"Switching data source from {self.source_type} to {new_type}")
        self.source_type = new_type
        self._init_loader()
